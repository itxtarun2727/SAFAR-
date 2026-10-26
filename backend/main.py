"""
main.py — FastAPI Application Entrypoint for SAFAR Portal.

Exposes REST endpoints with multi-tenant SQL scoping:
- /auth: Login and persona verification
- /universities, /banks, /institutions: Organization hierarchy
- /instruments: Scoped FDR lifecycle management
- /release: Two-part cryptographic release workflow
- /bank: Bank console inbox & two-part code confirmation [SIMULATED]
- /reports: Failed verifications audit report (Senior & Auditor only)
- /audit: SHA-256 hash-chain verification & DEMO_MODE protected tamper demo
- /rules: Configurable AICTE regulatory parameters
- /clock: Demo time-travel controls (+30D, +90D)
"""

from typing import List, Optional, Dict, Any
import os
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime

import models
import schemas
import crud
import workflow
import audit
import rules
import scheduler
from clock import Clock
import adapters
import auth
from database import engine, Base, get_db

# Create tables on startup if not present
Base.metadata.create_all(bind=engine)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Auto-seed database with default rules and demo scenarios on initial boot."""
    db = next(get_db())
    try:
        from seed import seed_all
        seed_all(db)
    except Exception as e:
        print(f"Startup seed notice: {e}")
    yield


app = FastAPI(
    title="SAFAR — Smart AICTE FDR Automation & Registry API",
    description=(
        "Backend API for SIH Problem Statement 26265.\n\n"
        "⚠️ **NOTICE: Bank confirmation responses, external verification feeds, "
        "and release authorizations in this prototype are SIMULATED.**"
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# CORS setup
cors_origins_env = os.getenv("CORS_ORIGINS", "*")
allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── System Health & Root ───────────────────────────────────────────────────────

@app.get("/", tags=["System"], include_in_schema=False)
def root():
    """Redirect root path to interactive Swagger documentation."""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["System"])
def health_check():
    """Liveness check for container orchestrators and Render deployment."""
    return {
        "status": "ok",
        "service": "safar-backend",
        "clock_simulated": Clock.is_simulated(),
        "current_time": Clock.now().isoformat(),
    }


# ── Authentication ─────────────────────────────────────────────────────────────

@app.post("/auth/login", response_model=schemas.LoginResponse, tags=["Auth"])
def login(req: schemas.LoginRequest):
    """Authenticate demo users with standard password 'demo1234'."""
    user = auth.authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    token = auth.create_access_token(user)
    return schemas.LoginResponse(access_token=token, user=schemas.UserInfo(**user.model_dump()))


@app.get("/auth/me", response_model=schemas.UserInfo, tags=["Auth"])
def get_current_user_profile(user: auth.AuthUser = Depends(auth.get_current_user)):
    """Return currently active user persona."""
    return schemas.UserInfo(**user.model_dump())


# ── Organization Hierarchy (Universities, Banks, Colleges) ────────────────────

@app.get("/universities", response_model=List[schemas.UniversityResponse], tags=["Hierarchy"])
def list_universities(db: Session = Depends(get_db)):
    """List affiliating State Technical Universities."""
    return crud.get_universities(db)


@app.get("/banks", response_model=List[schemas.BankResponse], tags=["Hierarchy"])
def list_banks(db: Session = Depends(get_db)):
    """List fictional demo partner banks [SIMULATED]."""
    return crud.get_banks(db)


@app.get("/institutions", response_model=List[schemas.InstitutionResponse], tags=["Institutions"])
def list_institutions(
    university_id: Optional[str] = None,
    state: Optional[str] = None,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """List technical colleges with multi-tenant scoping."""
    return crud.get_institutions(db, user=user, university_id=university_id, state=state)


# ── Instruments (FDRs) ─────────────────────────────────────────────────────────

@app.get("/instruments", response_model=List[schemas.InstrumentResponse], tags=["Instruments"])
def list_instruments(
    institution_id: Optional[str] = None,
    university_id: Optional[str] = None,
    state: Optional[str] = None,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Filter and list instruments with SQL-level scoping."""
    return crud.get_instruments(
        db,
        user=user,
        institution_id=institution_id,
        university_id=university_id,
        state=state,
        status=status,
        stage=stage,
    )


@app.post("/instruments", response_model=schemas.InstrumentResponse, tags=["Instruments"])
def create_instrument(
    data: schemas.InstrumentCreate,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    College submits a new FDR deposit record:
    - Binds college's own institution
    - Accepts bank_id chosen by college
    - Automatically triggers simulated bank verification
    """
    return crud.create_instrument(db, data, user=user)


@app.get("/instruments/{instrument_id}", response_model=schemas.InstrumentDetailResponse, tags=["Instruments"])
def get_instrument_detail(
    instrument_id: str,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full details of an FDR with strict access scoping."""
    inst = crud.get_instrument_by_id(db, instrument_id, user=user)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found.")
    return inst


@app.post("/instruments/{instrument_id}/verify-bank", tags=["Verification"])
def verify_instrument_with_bank(
    instrument_id: str,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger simulated bank confirmation verification."""
    crud.check_instrument_access(crud.get_instrument_by_id(db, instrument_id), user)
    return crud.run_bank_verification(db, instrument_id, user=user)


@app.post("/instruments/{instrument_id}/transition", tags=["Workflow"])
def trigger_transition(
    instrument_id: str,
    req: schemas.TransitionRequest,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Execute a guarded state transition through pure workflow.transition().
    Commits state update and append-only audit entry in one transaction.
    """
    crud.check_instrument_access(crud.get_instrument_by_id(db, instrument_id), user)
    try:
        inst, effects = crud.execute_transition(
            db=db,
            instrument_id=instrument_id,
            event=req.event,
            actor_id=user.user_id,
            role=user.role,
            reason=req.reason,
            extra_context=req.payload or {},
        )
        return {"status": "success", "new_state": inst.status, "effects": effects}
    except workflow.WorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/instruments/{instrument_id}/lineage", response_model=List[schemas.InstrumentResponse], tags=["Instruments"])
def get_instrument_lineage(
    instrument_id: str,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full predecessor and successor renewal chain."""
    return crud.get_lineage(db, instrument_id, user=user)


@app.post("/instruments/{instrument_id}/renew", response_model=schemas.InstrumentResponse, tags=["Instruments"])
def renew_instrument_endpoint(
    instrument_id: str,
    req: schemas.InstrumentRenewRequest,
    user: auth.AuthUser = Depends(auth.require_role("institution", "admin")),
    db: Session = Depends(get_db),
):
    """Submit FDR renewal linked to predecessor instrument."""
    return crud.renew_instrument(db, instrument_id, req, user)


@app.post("/instruments/{instrument_id}/approve", response_model=schemas.InstrumentResponse, tags=["Scrutiny"])
def approve_submission_endpoint(
    instrument_id: str,
    req: schemas.ScrutinyDecisionRequest,
    user: auth.AuthUser = Depends(auth.require_role("aicte_officer", "admin")),
    db: Session = Depends(get_db),
):
    """University Officer approves a submitted FDR in AICTE_REVIEW."""
    return crud.approve_submission(db, instrument_id, req.reason, user)


@app.post("/instruments/{instrument_id}/reject", response_model=schemas.InstrumentResponse, tags=["Scrutiny"])
def reject_submission_endpoint(
    instrument_id: str,
    req: schemas.ScrutinyDecisionRequest,
    user: auth.AuthUser = Depends(auth.require_role("aicte_officer", "admin")),
    db: Session = Depends(get_db),
):
    """University Officer rejects a submitted FDR in AICTE_REVIEW with reason for the college."""
    return crud.reject_submission(db, instrument_id, req.reason, user)


@app.post("/instruments/{instrument_id}/resubmit", response_model=schemas.InstrumentResponse, tags=["Instruments"])
def resubmit_instrument_endpoint(
    instrument_id: str,
    req: Optional[schemas.ResubmitRequest] = None,
    user: auth.AuthUser = Depends(auth.require_role("institution", "admin")),
    db: Session = Depends(get_db),
):
    """College resubmits an instrument that was REJECTED or in NEEDS_CORRECTION."""
    reason = req.reason if req else "College corrected and resubmitted FDR."
    return crud.resubmit_instrument(db, instrument_id, user, reason=reason)


# ── Documents & Tamper-Evident Artifacts ───────────────────────────────────────

@app.post("/instruments/{instrument_id}/documents", response_model=schemas.DocumentResponse, tags=["Documents"])
def upload_document_endpoint(
    instrument_id: str,
    req: schemas.DocumentUploadRequest,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Upload and register a document with cryptographic SHA-256 and automatic versioning."""
    import base64
    content = base64.b64decode(req.content_b64) if req.content_b64 else f"Mock document content for {req.file_name}".encode("utf-8")
    return crud.upload_document(
        db=db,
        instrument_id=instrument_id,
        file_name=req.file_name,
        doc_type=req.doc_type,
        file_type=req.file_type,
        content_bytes=content,
        user=user,
    )


@app.get("/instruments/{instrument_id}/documents", response_model=List[schemas.DocumentResponse], tags=["Documents"])
def list_documents_endpoint(
    instrument_id: str,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """List documents attached to an instrument with tenant access scoping."""
    return crud.get_documents(db, instrument_id, user)


@app.get("/instruments/{instrument_id}/documents/{document_id}", response_model=schemas.DocumentResponse, tags=["Documents"])
def get_document_endpoint(
    instrument_id: str,
    document_id: str,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve document metadata by ID."""
    return crud.get_document_by_id(db, instrument_id, document_id, user)


@app.get("/instruments/{instrument_id}/documents/{document_id}/download", tags=["Documents"])
def download_document_endpoint(
    instrument_id: str,
    document_id: str,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Download document content bytes verifying SHA-256 integrity."""
    content_bytes, doc = crud.download_document_content(db, instrument_id, document_id, user)
    return Response(
        content=content_bytes,
        media_type=doc.file_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{doc.file_name}"',
            "X-Document-SHA256": doc.sha256,
        },
    )


@app.get("/instruments/{instrument_id}/evidence-pack", tags=["Compliance"])
def get_evidence_pack_endpoint(
    instrument_id: str,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Export comprehensive cryptographic evidence pack for regulatory compliance audit."""
    return crud.export_evidence_pack(db, instrument_id, user)


# ── Release Governance (Two-Part Code Workflow) ───────────────────────────────

@app.post("/instruments/{instrument_id}/release-request", response_model=schemas.ReleaseResponse, tags=["Release"])
def request_release_endpoint(
    instrument_id: str,
    req: schemas.ReleaseCreate,
    user: auth.AuthUser = Depends(auth.require_role("institution", "admin")),
    db: Session = Depends(get_db),
):
    """College submits release request for matured FDR (or closure)."""
    try:
        return crud.create_release_request(
            db=db,
            instrument_id=instrument_id,
            kind=req.kind,
            reason=req.reason,
            user=user,
        )
    except workflow.WorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/release/{release_id}/recommend", response_model=schemas.ReleaseResponse, tags=["Release"])
def recommend_release_endpoint(
    release_id: str,
    req: schemas.ReleaseRecommendRequest,
    user: auth.AuthUser = Depends(auth.require_role("aicte_officer", "admin")),
    db: Session = Depends(get_db),
):
    """University Officer completes scrutiny checklist and records recommendation."""
    try:
        return crud.recommend_release(
            db=db,
            release_id=release_id,
            reason=req.reason,
            checklist=req.checklist,
            user=user,
        )
    except workflow.WorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/release/{release_id}/approve", response_model=schemas.ReleaseAuthorizationResponse, tags=["Release"])
def approve_release_endpoint(
    release_id: str,
    req: schemas.ReleaseApproveRequest,
    user: auth.AuthUser = Depends(auth.require_role("aicte_senior", "admin")),
    db: Session = Depends(get_db),
):
    """
    Senior Manager approves release:
    - Enforces maker != checker
    - Fresh bank reverification match
    - Generates Two-Part ReleaseAuthorization (bank code sent to bank inbox)
    - NEVER returns or exposes college code to senior manager
    - Advances to BANK_RELEASE_PENDING
    """
    try:
        auth_record = crud.approve_release(
            db=db,
            release_id=release_id,
            reason=req.reason,
            user=user,
        )
        return schemas.ReleaseAuthorizationResponse(
            id=auth_record.id,
            release_ref=auth_record.release_ref,
            instrument_id=auth_record.instrument_id,
            bank_id=auth_record.bank_id,
            issued_by=auth_record.issued_by,
            issued_at=auth_record.issued_at,
            expires_at=auth_record.expires_at,
            used_at=auth_record.used_at,
            status=auth_record.status,
            failed_attempt_count=auth_record.failed_attempt_count,
        )
    except workflow.WorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/release/{release_ref}/claim-code", response_model=schemas.ClaimCodeResponse, tags=["Release"])
def claim_release_code_endpoint(
    release_ref: str,
    user: auth.AuthUser = Depends(auth.require_role("institution")),
    db: Session = Depends(get_db),
):
    """College claims its one-time release code for presentation at the partner bank."""
    return crud.claim_college_release_code(db, release_ref, user)


@app.post("/release/{release_ref}/reissue", response_model=schemas.ReleaseAuthorizationResponse, tags=["Release"])
def reissue_release_endpoint(
    release_ref: str,
    user: auth.AuthUser = Depends(auth.require_role("aicte_senior", "admin")),
    db: Session = Depends(get_db),
):
    """Senior Manager reissues an expired release authorization without revealing college code."""
    new_auth = crud.reissue_release_authorization(db, release_ref, user)
    return schemas.ReleaseAuthorizationResponse(
        id=new_auth.id,
        release_ref=new_auth.release_ref,
        instrument_id=new_auth.instrument_id,
        bank_id=new_auth.bank_id,
        issued_by=new_auth.issued_by,
        issued_at=new_auth.issued_at,
        expires_at=new_auth.expires_at,
        used_at=new_auth.used_at,
        status=new_auth.status,
        failed_attempt_count=new_auth.failed_attempt_count,
    )


# ── Bank Console (Release Inbox & Confirmation) [SIMULATED] ───────────────────

@app.get("/bank/inbox", tags=["Bank Console"])
def get_bank_inbox_endpoint(
    user: auth.AuthUser = Depends(auth.require_role("bank_checker", "admin")),
    db: Session = Depends(get_db),
):
    """List pending deposits awaiting release confirmation at user's bank [SIMULATED]."""
    return crud.get_bank_inbox(db, user)


@app.post("/bank/release/{release_ref}/confirm", tags=["Bank Console"])
def confirm_bank_release_endpoint(
    release_ref: str,
    req: schemas.BankReleaseConfirmRequest,
    user: auth.AuthUser = Depends(auth.require_role("bank_checker", "admin")),
    db: Session = Depends(get_db),
):
    """
    Bank confirms release by presenting matching college code:
    - Constant-time verification
    - Marks authorization USED, removes lien, moves instrument to CLOSED
    """
    return crud.confirm_bank_release(db, release_ref, req.college_code, user)


# ── Reports (Failed Verifications) ────────────────────────────────────────────

@app.get("/reports/failed-verifications", tags=["Reports"])
def get_failed_verifications_report(
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """List failed bank verification attempts (Senior AICTE Director & Auditor only)."""
    return crud.get_failed_verifications_report(db, user)


# ── Scrutiny Notes & Disputes ──────────────────────────────────────────────────

@app.post("/instruments/{instrument_id}/notes", response_model=schemas.ScrutinyNoteResponse, tags=["Scrutiny"])
def add_note_endpoint(
    instrument_id: str,
    req: schemas.ScrutinyNoteCreate,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Add an official observation note to an instrument case."""
    return crud.add_scrutiny_note(
        db=db,
        instrument_id=instrument_id,
        author_id=user.user_id,
        author_name=user.name,
        author_role=user.role,
        text=req.text,
        user=user,
    )


@app.get("/instruments/{instrument_id}/notes", response_model=List[schemas.ScrutinyNoteResponse], tags=["Scrutiny"])
def list_notes_endpoint(
    instrument_id: str,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """List observation scrutiny notes for an instrument with tenant scoping."""
    return crud.get_scrutiny_notes(db, instrument_id, user)


@app.post("/instruments/{instrument_id}/disputes", response_model=schemas.DisputeResponse, tags=["Disputes"])
def open_dispute_endpoint(
    instrument_id: str,
    req: schemas.DisputeCreate,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Open an official dispute/hold on an instrument, locking release transitions."""
    try:
        return crud.create_dispute(
            db=db,
            instrument_id=instrument_id,
            reason=req.reason,
            opened_by=user.user_id,
            role=user.role,
            user=user,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/disputes/{dispute_id}/clear", response_model=schemas.DisputeResponse, tags=["Disputes"])
def clear_dispute_endpoint(
    dispute_id: str,
    reason: Optional[str] = Query("Compliance verified and grievance resolved."),
    user: auth.AuthUser = Depends(auth.require_role("aicte_senior", "admin")),
    db: Session = Depends(get_db),
):
    """Formally resolve and clear a dispute hold (Senior Officer / Admin only)."""
    try:
        return crud.clear_dispute(
            db=db,
            dispute_id=dispute_id,
            cleared_by=user.user_id,
            role=user.role,
            resolution_reason=reason,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Dashboard Metrics ──────────────────────────────────────────────────────────

@app.get("/dashboard/stats", tags=["Dashboard"])
def get_dashboard_metrics(
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Return 6 core counts scoped to active user: Active, Expiring, Matured, Renewed, Released, Pending."""
    return crud.get_dashboard_counts(db, user)


# ── Alerts & Scheduler ─────────────────────────────────────────────────────────

@app.get("/alerts", response_model=List[schemas.AlertResponse], tags=["Alerts"])
def list_alerts(
    instrument_id: Optional[str] = None,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """List alerts with institutional and role-based scoping."""
    query = db.query(models.Alert)
    if user.role == "institution":
        inst_id = user.institution_id or (user.institution_ids[0] if user.institution_ids else None)
        query = query.join(models.Instrument).filter(models.Instrument.institution_id == inst_id)
        # Never show senior failed verification alerts to institutions
        query = query.filter(models.Alert.stage != "FAILED_VERIFICATION_ALERT")

    elif user.role == "aicte_officer":
        query = query.join(models.Instrument).join(models.Institution).filter(
            models.Institution.university_id == user.university_id
        )
        query = query.filter(models.Alert.stage != "FAILED_VERIFICATION_ALERT")

    if instrument_id:
        query = query.filter(models.Alert.instrument_id == instrument_id)
    return query.order_by(models.Alert.sent_at.desc()).all()


@app.post("/alerts/{alert_id}/acknowledge", response_model=schemas.AlertResponse, tags=["Alerts"])
def acknowledge_alert_endpoint(
    alert_id: str,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Acknowledge an alert notice with audit logging."""
    return crud.acknowledge_alert(db, alert_id, user)


@app.post("/scheduler/run-now", tags=["Scheduler"])
def run_scheduler(
    user: auth.AuthUser = Depends(auth.require_role("admin")),
    db: Session = Depends(get_db),
):
    """Trigger manual execution of the idempotent daily alert evaluation (Admin only)."""
    res = scheduler.run_daily_alert_job(db)
    audit.append_audit_entry(
        db=db,
        actor_id=user.user_id,
        role=user.role,
        entity="scheduler",
        entity_id="daily_job",
        from_state=None,
        to_state="RUN",
        payload={"result": res},
        reason="Manual execution of daily alert evaluation triggered by Admin.",
    )
    db.commit()
    return res


# ── Audit Chain & Tamper Evidence ──────────────────────────────────────────────

@app.get("/audit/entries", response_model=List[schemas.AuditEntryResponse], tags=["Audit"])
def get_audit_log(
    skip: int = 0,
    limit: int = 100,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch append-only audit entries with tenant access scoping."""
    query = db.query(models.AuditEntry)
    if user.role == "institution":
        inst_id = user.institution_id or (user.institution_ids[0] if user.institution_ids else None)
        inst_ids = [i.id for i in db.query(models.Instrument.id).filter(models.Instrument.institution_id == inst_id).all()]
        query = query.filter((models.AuditEntry.entity_id.in_(inst_ids)) | (models.AuditEntry.entity_id == inst_id))
    elif user.role == "aicte_officer":
        univ_inst_ids = [i.id for i in db.query(models.Instrument.id).join(models.Institution).filter(models.Institution.university_id == user.university_id).all()]
        query = query.filter(models.AuditEntry.entity_id.in_(univ_inst_ids))

    return query.order_by(models.AuditEntry.seq.desc()).offset(skip).limit(limit).all()


@app.get("/audit/verify", response_model=schemas.ChainVerificationResult, tags=["Audit"])
def verify_audit_ledger(db: Session = Depends(get_db)):
    """Recalculate SHA-256 hash chain and report tamper status."""
    ok, count, broken_seq, msg = audit.verify_chain_integrity(db)
    return schemas.ChainVerificationResult(
        ok=ok,
        total_entries=count,
        first_broken_seq=broken_seq,
        message=msg
    )


@app.post("/audit/simulate-tamper", tags=["Audit"])
def simulate_tamper_endpoint(
    user: auth.AuthUser = Depends(auth.require_role("admin")),
    db: Session = Depends(get_db),
):
    """
    Deliberately modify an audit row to demonstrate tamper detection to evaluators.
    Admin only AND DEMO_MODE=true only.
    """
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    if not demo_mode:
        raise HTTPException(status_code=403, detail="Simulate tamper is disabled outside DEMO_MODE.")

    tampered_seq = audit.simulate_tamper(db)
    return {
        "status": "tampered",
        "tampered_sequence": tampered_seq,
        "message": "Audit row tampered. Run /audit/verify to observe immediate cryptographic failure."
    }


@app.post("/audit/tamper-demo", tags=["Audit"])
def tamper_demo_alias(
    user: auth.AuthUser = Depends(auth.require_role("admin")),
    db: Session = Depends(get_db),
):
    """Demonstrate cryptographic tamper detection (Admin only, DEMO_MODE=true)."""
    return simulate_tamper_endpoint(user, db)


@app.post("/audit/repair", tags=["Audit"])
def repair_audit_chain(
    user: auth.AuthUser = Depends(auth.require_role("admin")),
    db: Session = Depends(get_db),
):
    """
    Recompute valid cryptographic hashes to restore chain integrity after a tamper demo.
    Admin only AND DEMO_MODE=true only. Writes an audit entry so repairs are never invisible.
    """
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    if not demo_mode:
        raise HTTPException(status_code=403, detail="Chain repair is disabled outside DEMO_MODE.")

    recomputed_count = audit.repair_chain(db)
    # The repair must write its own audit entry so a repair is never invisible
    audit.append_audit_entry(
        db=db,
        actor_id=user.user_id,
        role=user.role,
        entity="audit_ledger",
        entity_id="repair",
        from_state="TAMPERED",
        to_state="VALID",
        payload={"recomputed_count": recomputed_count},
        reason="Cryptographic hash repair executed by Portal Admin after tamper demonstration.",
    )
    db.commit()
    return {
        "status": "repaired",
        "entries_recomputed": recomputed_count,
        "message": "Audit chain hashes recomputed. Repair logged to audit ledger.",
    }


@app.post("/audit/repair-demo", tags=["Audit"])
def repair_demo_alias(
    user: auth.AuthUser = Depends(auth.require_role("admin")),
    db: Session = Depends(get_db),
):
    """Recompute and restore cryptographic chain after tamper demo (Admin only, DEMO_MODE=true)."""
    return repair_audit_chain(user, db)


# ── Demo Clock (Time Travel) ───────────────────────────────────────────────────

@app.get("/clock", tags=["Clock"])
def get_clock():
    """Get current demo clock status."""
    return {
        "current_time": Clock.now().isoformat(),
        "today": Clock.today().isoformat(),
        "is_simulated": Clock.is_simulated(),
    }


@app.get("/clock/current", tags=["Clock"])
def get_current_clock():
    """Get current active system clock time."""
    return {
        "current_time": Clock.now().isoformat(),
        "today": Clock.today().isoformat(),
        "is_simulated": Clock.is_simulated(),
    }


@app.post("/clock/advance", tags=["Clock"])
def advance_clock(
    days: int = Query(30, ge=1, le=3650),
    user: auth.AuthUser = Depends(auth.require_role("admin")),
    db: Session = Depends(get_db),
):
    """Fast-forward system time by N days and evaluate alerts (Admin only, DEMO_MODE=true)."""
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    if not demo_mode:
        raise HTTPException(status_code=403, detail="Clock advance is disabled outside DEMO_MODE.")
    new_dt = Clock.advance_days(days)
    sched_result = scheduler.run_daily_alert_job(db)
    return {
        "new_time": new_dt.isoformat(),
        "today": Clock.today().isoformat(),
        "scheduler_run": sched_result,
    }


@app.post("/clock/reset", tags=["Clock"])
def reset_clock(
    user: auth.AuthUser = Depends(auth.require_role("admin")),
):
    """Reset clock to real system time (Admin only, DEMO_MODE=true)."""
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    if not demo_mode:
        raise HTTPException(status_code=403, detail="Clock reset is disabled outside DEMO_MODE.")
    Clock.clear_override()
    return {"status": "reset", "current_time": Clock.now().isoformat()}


# ── Rules Table ────────────────────────────────────────────────────────────────

@app.get("/rules", response_model=List[schemas.RuleResponse], tags=["Rules"])
def list_rules(db: Session = Depends(get_db)):
    """List regulatory configuration parameters."""
    return db.query(models.Rule).all()


@app.post("/rules", response_model=schemas.RuleResponse, tags=["Rules"])
def create_or_update_rule(
    data: schemas.RuleCreate,
    user: auth.AuthUser = Depends(auth.require_role("admin")),
    db: Session = Depends(get_db),
):
    """Update regulatory rule threshold (Admin only)."""
    return rules.set_rule(db, data.key, data.value, data.clause_reference)
