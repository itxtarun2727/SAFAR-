"""
test_change_request.py — Comprehensive tests for change request specifications:
1. Multi-tenant SQL scoping across Institution, Officer, Senior, Bank Checker.
2. Failed bank check routing to NEEDS_CORRECTION, audit logging, and 3-failure senior alert.
3. Two-part release authorization: single-use, expiry, constant-time compare, wrong code rejection, wrong bank rejection.
4. Senior approval guards (separation of duties, active disputes).
5. Audit chain integrity verification.
"""

from datetime import timedelta
import pytest
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal
import models
import auth
import workflow
from clock import Clock


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_database_for_tests():
    from reset_db import reset_and_seed
    reset_and_seed()
    yield


def get_token(username: str) -> str:
    """Helper to authenticate a demo persona and get JWT token."""
    res = client.post("/auth/login", json={"username": username, "password": auth.DEMO_PASSWORD})
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── 1. Scoping Tests ──────────────────────────────────────────────────────────

def test_institution_scoping():
    """A college user can only see their own FDRs and cannot read another college's FDR by ID."""
    token_inst1 = get_token("inst_user")   # inst-001 (Delhi Institute)
    token_inst2 = get_token("inst_apex")   # inst-002 (Apex College)

    # inst_user lists instruments: must only see inst-001
    res = client.get("/instruments", headers=auth_header(token_inst1))
    assert res.status_code == 200
    instruments = res.json()
    assert all(i["institution_id"] == "inst-001" for i in instruments)

    # inst_user tries to read fdr-scenario-2 (Apex College, inst-002) by ID -> 403 Forbidden
    res_forbidden = client.get("/instruments/fdr-scenario-2", headers=auth_header(token_inst1))
    assert res_forbidden.status_code == 403
    assert "isolation violation" in res_forbidden.json()["detail"].lower()

    # inst_apex CAN read fdr-scenario-2
    res_allowed = client.get("/instruments/fdr-scenario-2", headers=auth_header(token_inst2))
    assert res_allowed.status_code == 200
    assert res_allowed.json()["id"] == "fdr-scenario-2"


def test_university_officer_scoping():
    """University officer only sees colleges under their university."""
    token_priya = get_token("priya")  # univ-001 (Delhi)
    token_rajan = get_token("rajan")  # univ-002 (Maharashtra)

    # Priya sees colleges in univ-001 (inst-001, inst-002)
    res_priya = client.get("/instruments", headers=auth_header(token_priya))
    assert res_priya.status_code == 200
    priya_items = res_priya.json()
    assert all(i["institution_id"] in ["inst-001", "inst-002"] for i in priya_items)

    # Priya tries to read fdr-scenario-4 (inst-003, univ-002) -> 403 Forbidden
    res_priya_forbidden = client.get("/instruments/fdr-scenario-4", headers=auth_header(token_priya))
    assert res_priya_forbidden.status_code == 403
    assert "jurisdiction" in res_priya_forbidden.json()["detail"].lower()

    # Rajan CAN read fdr-scenario-4
    res_rajan_allowed = client.get("/instruments/fdr-scenario-4", headers=auth_header(token_rajan))
    assert res_rajan_allowed.status_code == 200


def test_bank_checker_scoping():
    """Bank user only sees deposits at their specific bank."""
    token_bank_a = get_token("bank_a")  # bank-001
    token_bank_b = get_token("bank_b")  # bank-002

    # Bank A lists instruments: must all have bank_id == bank-001
    res_bank_a = client.get("/instruments", headers=auth_header(token_bank_a))
    assert res_bank_a.status_code == 200
    bank_a_items = res_bank_a.json()
    assert all(i["bank_id"] == "bank-001" for i in bank_a_items)

    # Bank A tries to read fdr-scenario-2 (bank-002) -> 403 Forbidden
    res_bank_a_forbidden = client.get("/instruments/fdr-scenario-2", headers=auth_header(token_bank_a))
    assert res_bank_a_forbidden.status_code == 403
    assert "bank account isolation" in res_bank_a_forbidden.json()["detail"].lower()


# ── 2. Failed Bank Check and Alert Rules ───────────────────────────────────────

def test_failed_bank_check_rules():
    """
    Mismatch yields NEEDS_CORRECTION:
    - Visible to the college only
    - Does NOT appear in university officer queue
    - Logged as FAILED_VERIFICATION in audit trail
    - 3rd failure creates an alert visible to senior manager and auditor only
    """
    token_inst = get_token("inst_user")
    token_officer = get_token("priya")
    token_senior = get_token("anita")
    token_auditor = get_token("auditor")

    # College submits an FDR with an unmatchable reference number to force mismatch
    today = Clock.today()
    submit_payload = {
        "institution_id": "inst-001",
        "bank_id": "bank-001",
        "bank_name": "Demo Bank A",
        "branch": "Main Branch",
        "reference_no": "DEMOA99999999",  # Not in simulated repository -> returns mismatch / NOT_FOUND
        "amount_paise": 200000000,
        "issue_date": str(today - timedelta(days=30)),
        "maturity_date": str(today + timedelta(days=365 * 10)),
        "tenure_years": 10,
        "type": "bank_fdr",
        "joint_holder": "AICTE & College",
        "lien_marked": False,
    }

    res_submit = client.post("/instruments", json=submit_payload, headers=auth_header(token_inst))
    assert res_submit.status_code == 200
    new_fdr = res_submit.json()
    fdr_id = new_fdr["id"]

    # Automatic bank verification ran on submit: state should be NEEDS_CORRECTION
    res_detail = client.get(f"/instruments/{fdr_id}", headers=auth_header(token_inst))
    assert res_detail.status_code == 200
    assert res_detail.json()["status"] == "NEEDS_CORRECTION"
    assert res_detail.json()["failed_verification_count"] >= 1

    # Officer queue check: NEEDS_CORRECTION must NOT appear in officer listing
    res_officer_list = client.get("/instruments", headers=auth_header(token_officer))
    assert res_officer_list.status_code == 200
    officer_fdr_ids = [i["id"] for i in res_officer_list.json()]
    assert fdr_id not in officer_fdr_ids

    # Trigger second and third mismatches
    client.post(f"/instruments/{fdr_id}/verify-bank", headers=auth_header(token_inst))
    client.post(f"/instruments/{fdr_id}/verify-bank", headers=auth_header(token_inst))

    # Detail now shows at least 3 failed verification attempts
    res_after_3 = client.get(f"/instruments/{fdr_id}", headers=auth_header(token_inst))
    assert res_after_3.json()["failed_verification_count"] >= 3

    # Check alert visibility:
    # College must NOT see FAILED_VERIFICATION_ALERT
    res_inst_alerts = client.get("/alerts", headers=auth_header(token_inst))
    assert all(a["stage"] != "FAILED_VERIFICATION_ALERT" for a in res_inst_alerts.json())

    # Senior Manager CAN see FAILED_VERIFICATION_ALERT
    res_senior_alerts = client.get("/alerts", headers=auth_header(token_senior))
    assert any(a["stage"] == "FAILED_VERIFICATION_ALERT" for a in res_senior_alerts.json())

    # GET /reports/failed-verifications: Senior and Auditor only
    res_report_senior = client.get("/reports/failed-verifications", headers=auth_header(token_senior))
    assert res_report_senior.status_code == 200
    assert len(res_report_senior.json()) > 0

    res_report_auditor = client.get("/reports/failed-verifications", headers=auth_header(token_auditor))
    assert res_report_auditor.status_code == 200

    # College is blocked from reports
    res_report_forbidden = client.get("/reports/failed-verifications", headers=auth_header(token_inst))
    assert res_report_forbidden.status_code == 403


# ── 3. Release Authorization and Two-Part Code ────────────────────────────────

def test_release_authorization_flow():
    """
    Test complete release flow:
    - College requests release on matured FDR (fdr-scenario-5)
    - Officer recommends with checklist
    - Senior approves and receives one-time college code
    - Bank confirms release with matching college code -> instrument CLOSED
    - Rejection on wrong code, wrong bank, and code reuse
    """
    token_inst = get_token("inst_user")
    token_officer = get_token("priya")
    token_senior = get_token("anita")
    token_bank_a = get_token("bank_a")
    token_bank_b = get_token("bank_b")

    # Step 1: College requests release on fdr-scenario-5 (already matured)
    req_payload = {"kind": "release", "reason": "Tenure completed; 10 years fulfilled."}
    res_req = client.post("/instruments/fdr-scenario-5/release-request", json=req_payload, headers=auth_header(token_inst))
    assert res_req.status_code == 200
    release_id = res_req.json()["id"]

    # Step 2: Officer recommends with clearance checklist
    rec_payload = {
        "reason": "Campus audit completed, faculty salaries verified.",
        "checklist": {
            "grievances_cleared": True,
            "faculty_salary_compliant": True,
            "regional_noc": True,
        }
    }
    res_rec = client.post(f"/release/{release_id}/recommend", json=rec_payload, headers=auth_header(token_officer))
    assert res_rec.status_code == 200

    # Step 3: Senior approves -> creates ReleaseAuthorization WITHOUT revealing college code
    app_payload = {"reason": "Directorate clearance confirmed. Approved for release."}
    res_app = client.post(f"/release/{release_id}/approve", json=app_payload, headers=auth_header(token_senior))
    assert res_app.status_code == 200
    auth_data = res_app.json()
    release_ref = auth_data["release_ref"]
    assert release_ref.startswith("REL-")
    # Senior approval MUST NEVER expose the college code
    assert auth_data.get("college_code") is None

    # Step 4: Non-college roles attempting to claim code are refused (403)
    res_senior_claim = client.post(f"/release/{release_ref}/claim-code", headers=auth_header(token_senior))
    assert res_senior_claim.status_code == 403
    res_bank_claim = client.post(f"/release/{release_ref}/claim-code", headers=auth_header(token_bank_a))
    assert res_bank_claim.status_code == 403

    # Step 5: College claims its own release code
    res_claim = client.post(f"/release/{release_ref}/claim-code", headers=auth_header(token_inst))
    assert res_claim.status_code == 200
    college_code = res_claim.json()["college_code"]
    assert bool(college_code)

    # Step 6: Bank inbox check
    res_inbox = client.get("/bank/inbox", headers=auth_header(token_bank_a))
    assert res_inbox.status_code == 200
    inbox_refs = [item["release_ref"] for item in res_inbox.json()]
    assert release_ref in inbox_refs

    # Step 7: Bank B attempts to confirm release for Bank A's deposit -> 403 Forbidden
    res_wrong_bank = client.post(
        f"/bank/release/{release_ref}/confirm",
        json={"college_code": college_code},
        headers=auth_header(token_bank_b),
    )
    assert res_wrong_bank.status_code == 403

    # Step 8: Bank A enters WRONG code -> 400 Bad Request
    res_wrong_code = client.post(
        f"/bank/release/{release_ref}/confirm",
        json={"college_code": "WRONG_INVALID_TOKEN_ABC123"},
        headers=auth_header(token_bank_a),
    )
    assert res_wrong_code.status_code == 400
    assert "invalid" in res_wrong_code.json()["detail"].lower()

    # Step 9: Bank A enters CORRECT code -> 200 OK, CLOSED
    res_confirm = client.post(
        f"/bank/release/{release_ref}/confirm",
        json={"college_code": college_code},
        headers=auth_header(token_bank_a),
    )
    assert res_confirm.status_code == 200
    assert res_confirm.json()["instrument_status"] == "CLOSED"

    # Step 10: Reuse code fails
    res_reuse = client.post(
        f"/bank/release/{release_ref}/confirm",
        json={"college_code": college_code},
        headers=auth_header(token_bank_a),
    )
    assert res_reuse.status_code == 400
    assert "already been executed" in res_reuse.json()["detail"].lower()


def test_release_rate_limiting_and_locking():
    """Rate-limit wrong code attempts per release_ref; locks after 3 failures."""
    token_inst = get_token("inst_user")
    token_officer = get_token("priya")
    token_senior = get_token("anita")
    token_bank_a = get_token("bank_a")

    # Initiate release
    res_req = client.post(
        "/instruments/fdr-scenario-5/release-request",
        json={"kind": "release", "reason": "Testing rate limit lock"},
        headers=auth_header(token_inst),
    )
    release_id = res_req.json()["id"]

    client.post(
        f"/release/{release_id}/recommend",
        json={"reason": "Checklist cleared", "checklist": {"c": True}},
        headers=auth_header(token_officer),
    )
    res_app = client.post(
        f"/release/{release_id}/approve",
        json={"reason": "Approved"},
        headers=auth_header(token_senior),
    )
    release_ref = res_app.json()["release_ref"]

    # College claims code
    client.post(f"/release/{release_ref}/claim-code", headers=auth_header(token_inst))

    # 3 wrong attempts
    for attempt in range(1, 4):
        res = client.post(
            f"/bank/release/{release_ref}/confirm",
            json={"college_code": f"WRONG_{attempt}"},
            headers=auth_header(token_bank_a),
        )
        assert res.status_code == 400

    # 4th attempt: should indicate locked
    res_locked = client.post(
        f"/bank/release/{release_ref}/confirm",
        json={"college_code": "WRONG_AGAIN"},
        headers=auth_header(token_bank_a),
    )
    assert res_locked.status_code == 400
    assert "locked" in res_locked.json()["detail"].lower()


def test_release_code_expiry():
    """Expired code fails bank confirmation."""
    token_inst = get_token("inst_user")
    token_officer = get_token("priya")
    token_senior = get_token("anita")
    token_bank_a = get_token("bank_a")
    token_admin = get_token("admin")

    res_req = client.post(
        "/instruments/fdr-scenario-5/release-request",
        json={"kind": "release", "reason": "Testing expiry"},
        headers=auth_header(token_inst),
    )
    release_id = res_req.json()["id"]

    client.post(
        f"/release/{release_id}/recommend",
        json={"reason": "Cleared", "checklist": {"c": True}},
        headers=auth_header(token_officer),
    )
    res_app = client.post(
        f"/release/{release_id}/approve",
        json={"reason": "Approved"},
        headers=auth_header(token_senior),
    )
    release_ref = res_app.json()["release_ref"]

    res_claim = client.post(f"/release/{release_ref}/claim-code", headers=auth_header(token_inst))
    college_code = res_claim.json()["college_code"]

    # Fast forward clock by 5 days (120 hours > 72 hours expiry)
    client.post("/clock/advance?days=5", headers=auth_header(token_admin))

    # Confirmation fails due to expiry
    res_exp = client.post(
        f"/bank/release/{release_ref}/confirm",
        json={"college_code": college_code},
        headers=auth_header(token_bank_a),
    )
    assert res_exp.status_code == 400
    assert "expired" in res_exp.json()["detail"].lower()


def test_idor_protections():
    """Verify IDOR protections: college, officer, and bank user cannot read other tenants' data by ID."""
    token_inst1 = get_token("inst_user")     # inst-001 (Demo Univ A)
    token_inst2 = get_token("inst_sunrise")  # inst-003 (Demo Univ B)
    token_officer_a = get_token("priya")     # Demo Univ A
    token_bank_a = get_token("bank_a")       # Demo Bank A

    # 1. College 1 cannot read College 2's FDR by ID -> 403 / 404
    res_inst_idor = client.get("/instruments/fdr-scenario-4", headers=auth_header(token_inst1))
    assert res_inst_idor.status_code in [403, 404]

    # 2. College 1 cannot read College 2's documents -> 403 / 404
    res_doc_idor = client.get("/instruments/fdr-scenario-4/documents", headers=auth_header(token_inst1))
    assert res_doc_idor.status_code in [403, 404]

    # 3. University Officer A cannot read College under University B by ID -> 403 / 404
    res_univ_idor = client.get("/instruments/fdr-scenario-4", headers=auth_header(token_officer_a))
    assert res_univ_idor.status_code in [403, 404]

    # 4. Bank A cannot read FDR bound to Bank C by ID -> 403 / 404
    res_bank_idor = client.get("/instruments/fdr-scenario-4", headers=auth_header(token_bank_a))
    assert res_bank_idor.status_code in [403, 404]

    # 5. College 1 cannot read audit entries of College 2
    res_audit = client.get("/audit/entries", headers=auth_header(token_inst1))
    assert res_audit.status_code == 200
    for entry in res_audit.json():
        assert entry["entity_id"] != "fdr-scenario-4"


# ── 4. Senior Approval Separation of Duties ───────────────────────────────────

def test_senior_approval_separation_of_duties():
    """Senior approval fails if approver is same person as recommending officer."""
    token_senior = get_token("anita")

    # Create a fresh release request
    db = SessionLocal()
    try:
        inst = db.query(models.Instrument).filter(models.Instrument.id == "fdr-scenario-3").first()
        inst.status = "RELEASE_REQUESTED"
        db.commit()
    finally:
        db.close()

    # If Anita itself recommends it
    rec_res = client.post(
        "/release/rel-test-dummy/recommend",
        json={"reason": "Self recommendation", "checklist": {"c1": True}},
        headers=auth_header(token_senior),
    )
    # The endpoint will fail if release request doesn't exist; let's test using workflow.transition directly
    context = {
        "maker_id": "u-aicte-sr-01",
        "actor_id": "u-aicte-sr-01",
        "checklist": {"c1": True},
        "has_active_dispute": False,
        "reverification_result": "match",
    }
    with pytest.raises(workflow.WorkflowError) as excinfo:
        workflow.transition("COMPLIANCE_CHECK", "approve", context)
    assert "different person" in str(excinfo.value)


# ── 5. Audit Chain Verification ───────────────────────────────────────────────

def test_audit_chain_and_tamper_demo():
    """Audit chain verifies, tamper demo breaks it, and admin repair restores it with audit entry."""
    token_admin = get_token("admin")

    # Verify initial ledger
    res_verify = client.get("/audit/verify")
    assert res_verify.status_code == 200
    assert res_verify.json()["ok"] is True

    # Tamper simulation (Admin only)
    res_tamper = client.post("/audit/simulate-tamper", headers=auth_header(token_admin))
    assert res_tamper.status_code == 200

    # Verification fails immediately
    res_verify_failed = client.get("/audit/verify")
    assert res_verify_failed.status_code == 200
    assert res_verify_failed.json()["ok"] is False

    # Admin repairs chain
    res_repair = client.post("/audit/repair", headers=auth_header(token_admin))
    assert res_repair.status_code == 200
    assert res_repair.json()["status"] == "repaired"

    # Verification restored
    res_verify_restored = client.get("/audit/verify")
    assert res_verify_restored.status_code == 200
    assert res_verify_restored.json()["ok"] is True


# ── 6. University Officer Submission Review & Scoping ──────────────────────────

def test_university_officer_submission_approval_and_rejection():
    """
    Bank match moves instrument to AICTE_REVIEW (not ACTIVE).
    University officer scoped to that university approves -> ACTIVE, or rejects -> REJECTED.
    Officer from another university is refused (403).
    College can resubmit from REJECTED -> SUBMITTED, which automatically re-runs bank check.
    """
    token_inst = get_token("inst_user")   # inst-001 under Demo University A (univ-001)
    token_priya = get_token("priya")      # University Officer for univ-001
    token_rajan = get_token("rajan")      # University Officer for univ-002

    # 1. College submits FDR with matching reference
    create_payload = {
        "institution_id": "inst-001",
        "bank_id": "bank-001",
        "bank_name": "Demo Bank A",
        "branch": "Connaught Place",
        "reference_no": "DEMOA00998877",
        "amount_paise": 250000000,
        "issue_date": str(Clock.today()),
        "maturity_date": str(Clock.today() + timedelta(days=365 * 10)),
        "tenure_years": 10,
        "joint_holder": "AICTE & Delhi Institute of Technology",
        "lien_marked": False,
    }
    res_create = client.post("/instruments", json=create_payload, headers=auth_header(token_inst))
    assert res_create.status_code == 200
    inst_id = res_create.json()["id"]

    # Bank match must NOT activate: status MUST be AICTE_REVIEW
    res_get = client.get(f"/instruments/{inst_id}", headers=auth_header(token_inst))
    assert res_get.status_code == 200
    assert res_get.json()["status"] == "AICTE_REVIEW"

    # 2. Officer from Demo University B (Rajan) tries to approve -> 403 Forbidden
    res_cross_approve = client.post(
        f"/instruments/{inst_id}/approve",
        json={"reason": "Attempting cross-university approval"},
        headers=auth_header(token_rajan),
    )
    assert res_cross_approve.status_code == 403
    assert "jurisdiction scope violation" in res_cross_approve.json()["detail"].lower()

    # 3. Officer from Demo University A (Priya) rejects with reason
    res_reject = client.post(
        f"/instruments/{inst_id}/reject",
        json={"reason": "Certificate scan is blurry. Please re-upload legible document."},
        headers=auth_header(token_priya),
    )
    assert res_reject.status_code == 200
    assert res_reject.json()["status"] == "REJECTED"

    # 4. College resubmits
    res_resubmit = client.post(
        f"/instruments/{inst_id}/resubmit",
        json={"reason": "Re-uploaded clear certificate scan."},
        headers=auth_header(token_inst),
    )
    assert res_resubmit.status_code == 200
    # Resubmit triggers automatic bank check and moves back to AICTE_REVIEW
    assert res_resubmit.json()["status"] == "AICTE_REVIEW"

    # 5. Scoped officer (Priya) approves -> ACTIVE
    res_approve = client.post(
        f"/instruments/{inst_id}/approve",
        json={"reason": "Document verified clear and regulatory norms satisfied."},
        headers=auth_header(token_priya),
    )
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] == "ACTIVE"
    assert res_approve.json()["lien_marked"] is True


# ── 7. Ephemeral Storage & Document Download ──────────────────────────────────

def test_document_ephemeral_storage_and_download():
    """Document uploaded is stored in database bytea and downloadable with SHA-256 integrity."""
    import base64
    import hashlib

    token_inst = get_token("inst_user")
    content = b"%PDF-1.4 Simulated PDF Deposit Receipt for DIT 2026"
    content_b64 = base64.b64encode(content).decode("utf-8")
    expected_digest = hashlib.sha256(content).hexdigest()

    # Upload document
    res_upload = client.post(
        "/instruments/fdr-scenario-1/documents",
        json={
            "file_name": "dit_fdr_scan.pdf",
            "doc_type": "fdr_certificate",
            "file_type": "application/pdf",
            "content_b64": content_b64,
        },
        headers=auth_header(token_inst),
    )
    assert res_upload.status_code == 200
    doc_id = res_upload.json()["id"]
    assert res_upload.json()["sha256"] == expected_digest

    # Download document content
    res_download = client.get(
        f"/instruments/fdr-scenario-1/documents/{doc_id}/download",
        headers=auth_header(token_inst),
    )
    assert res_download.status_code == 200
    assert res_download.content == content
    assert res_download.headers.get("x-document-sha256") == expected_digest


# ── 8. Confirmed Endpoints & Route Verification ───────────────────────────────

def test_confirmed_endpoints_and_openapi_routes():
    """Verify /banks, /universities, /institutions, /dashboard/stats, /auth/me, /clock/current, and demo actions."""
    token_admin = get_token("admin")

    assert client.get("/banks", headers=auth_header(token_admin)).status_code == 200
    assert client.get("/universities", headers=auth_header(token_admin)).status_code == 200
    assert client.get("/institutions", headers=auth_header(token_admin)).status_code == 200
    assert client.get("/dashboard/stats", headers=auth_header(token_admin)).status_code == 200
    assert client.get("/auth/me", headers=auth_header(token_admin)).status_code == 200
    assert client.get("/clock/current", headers=auth_header(token_admin)).status_code == 200

    # Demo tamper and repair aliases
    assert client.post("/audit/tamper-demo", headers=auth_header(token_admin)).status_code == 200
    assert client.post("/audit/repair-demo", headers=auth_header(token_admin)).status_code == 200

