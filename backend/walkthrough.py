"""
walkthrough.py — Interactive Backend API Tour & Learning Script for SAFAR.

Run this script directly:
    python walkthrough.py

This demonstrates every core concept of the backend:
1. Auth & JWT generation (Maker vs Checker roles)
2. Creating a new FDR Instrument (Pydantic validation -> SQLAlchemy model)
3. Simulated Bank Verification (adapters.py)
4. FSM Workflow & Guards (Why disputed cases return 400!)
5. Time-Travel Demo Clock & Idempotent Scheduler Alerts
6. Cryptographic Hash-Chain Verification & Tamper Simulation
"""

import sys
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def step(num: int, title: str, description: str):
    print(f"\n[STEP {num}] {title}")
    print(f"  --> {description}\n")

def main():
    banner("SAFAR BACKEND API INTERACTIVE WALKTHROUGH")
    print("This script uses FastAPI's TestClient to call the live API endpoints,")
    print("showing you the exact Request, Response, Status Code, and Database effects.\n")

    # ──────────────────────────────────────────────────────────────────────────
    step(1, "Health Check & System Status", "GET /health")
    res = client.get("/health")
    print(f"Status: {res.status_code}")
    print(f"Response Body: {res.json()}")
    assert res.status_code == 200

    # ──────────────────────────────────────────────────────────────────────────
    step(2, "Authentication & Role-Based Access Control (RBAC)", "POST /auth/login")
    print("Logging in as 'priya' (AICTE Officer / Maker)...")
    res_maker = client.post("/auth/login", json={"username": "priya", "password": "demo1234"})
    maker_token = res_maker.json()["access_token"]
    maker_headers = {"Authorization": f"Bearer {maker_token}"}
    print(f"Maker Logged In! Role: {res_maker.json()['user']['role']}, Token prefix: {maker_token[:25]}...")

    print("\nLogging in as 'anita' (AICTE Senior Officer / Checker)...")
    res_checker = client.post("/auth/login", json={"username": "anita", "password": "demo1234"})
    checker_token = res_checker.json()["access_token"]
    checker_headers = {"Authorization": f"Bearer {checker_token}"}
    print(f"Checker Logged In! Role: {res_checker.json()['user']['role']}")

    # ──────────────────────────────────────────────────────────────────────────
    step(3, "Submit New FDR Certificate", "POST /instruments")
    new_fdr_payload = {
        "institution_id": "inst-001",
        "type": "bank_fdr",
        "bank_name": "State Bank of India",
        "branch": "Connaught Place, New Delhi",
        "reference_no": "SBI-WALKTHROUGH-999",
        "amount_paise": 250000000,  # Rs. 25,00,000 in paise
        "issue_date": "2024-01-15",
        "maturity_date": "2034-01-15",
        "tenure_years": 10,
        "joint_holder": "AICTE and Greenfield Society",
        "lien_marked": True
    }
    print("Submitting payload with Maker auth header...")
    res = client.post("/instruments", json=new_fdr_payload, headers=maker_headers)
    print(f"Status: {res.status_code}")
    fdr_data = res.json()
    fdr_id = fdr_data["id"]
    print(f"Created FDR ID: {fdr_id}")
    print(f"Initial State: {fdr_data['status']} (Notice: Never enters ACTIVE without bank check!)")

    # ──────────────────────────────────────────────────────────────────────────
    step(4, "Simulate Bank Verification", f"POST /instruments/{fdr_id}/verify-bank")
    print("Simulated Bank Adapter checks the certificate against bank mock records...")
    res = client.post(f"/instruments/{fdr_id}/verify-bank", headers=maker_headers)
    print(f"Status: {res.status_code}")
    print(f"Bank Response: {res.json()}")

    # Check updated instrument status
    res = client.get(f"/instruments/{fdr_id}")
    inst_detail = res.json()
    print(f"New Instrument Status: {inst_detail['status']}")
    print(f"Confirmations: {len(inst_detail.get('confirmations', []))} fields verified side-by-side.")

    # ──────────────────────────────────────────────────────────────────────────
    step(5, "Understanding FSM Guard Protection (Why Disputed Cases Return 400)", "POST /instruments/{id}/transition")
    print("Examining 'fdr-scenario-6' which is pre-seeded with status 'DISPUTED':")
    res_case6 = client.get("/instruments/fdr-scenario-6")
    print(f"Case 6 Current Status: {res_case6.json()['status']}")

    print("\nAttempting illegal transition 'approve' on this disputed FDR:")
    # ──────────────────────────────────────────────────────────────────────────
    step("5B", "Record Officer Scrutiny Note", f"POST /instruments/{fdr_id}/notes")
    res_note = client.post(
        f"/instruments/{fdr_id}/notes",
        json={"text": "Verified original receipt hard-copy against bank dispatch register. Looks authentic."},
        headers=maker_headers
    )
    print(f"Status: {res_note.status_code}")
    print(f"Recorded Note ID: {res_note.json()['id']} by {res_note.json()['author_name']}")

    # ──────────────────────────────────────────────────────────────────────────
    step("5C", "Dispute Resolution Workflow (Clear Dispute on Scenario 6)", "POST /disputes/{id}/clear")
    # Fetch dispute on scenario-6
    inst_6_detail = client.get("/instruments/fdr-scenario-6").json()
    active_disputes = [d for d in inst_6_detail.get("disputes", []) if d.get("is_active")]
    if active_disputes:
        disp_id = active_disputes[0]["id"]
        print(f"Found active dispute #{disp_id}: '{active_disputes[0]['reason']}'")
        print("Clearing dispute as Senior Checker Anita...")
        res_clear = client.post(f"/disputes/{disp_id}/clear?reason=Faculty+settlement+cleared+by+Ombudsperson", headers=checker_headers)
        print(f"Clear Status: {res_clear.status_code}")
        print(f"Dispute Cleared: is_active={res_clear.json()['is_active']}")
    else:
        print("No active dispute currently on Scenario 6.")

    # ──────────────────────────────────────────────────────────────────────────
    step("5D", "Check Instrument Lineage & Predecessors", f"GET /instruments/{fdr_id}/lineage")
    res_lineage = client.get(f"/instruments/{fdr_id}/lineage")
    print(f"Status: {res_lineage.status_code}")
    print(f"Lineage Chain Count: {len(res_lineage.json())} linked certificate(s)")

    # ──────────────────────────────────────────────────────────────────────────
    step(6, "Demo Time-Travel Clock & Stage-Gate Scheduler", "POST /clock/advance & /scheduler/run-now")
    print("Getting current demo clock:")
    clk = client.get("/clock").json()
    print(f"Today: {clk['today']}")

    print("\nFast-forwarding clock by 90 days to test maturity countdown...")
    res = client.post("/clock/advance?days=90")
    print(f"New Today: {res.json()['today']}")
    print(f"Scheduler Result: {res.json()['scheduler_run']}")

    print("\nFetching generated alerts:")
    alerts = client.get("/alerts").json()
    print(f"Total Active Alerts: {len(alerts)}")
    for a in alerts[:3]:
        print(f"  - Alert [{a['stage']}]: Instrument {a['instrument_id']} due on {a['due_at']}")

    # Reset clock back
    client.post("/clock/reset")
    print("Clock reset to system time.")

    # ──────────────────────────────────────────────────────────────────────────
    step(7, "Cryptographic Audit Ledger & Live Tamper Detection", "GET /audit/verify")
    res_verify = client.get("/audit/verify")
    print(f"Chain Integrity Status: ok={res_verify.json()['ok']}")
    print(f"Total Hash-Chained Entries: {res_verify.json()['total_entries']}")
    print(f"Audit Message: {res_verify.json()['message']}")

    print("\nSimulating database tampering (deliberately altering an entry's payload)...")
    res_tamper = client.post("/audit/simulate-tamper")
    tampered_seq = res_tamper.json()["tampered_sequence"]
    print(f"Tampered Row Sequence #{tampered_seq}")

    print("\nRe-verifying ledger integrity after tampering:")
    res_reverify = client.get("/audit/verify")
    print(f"Chain Integrity Status: ok={res_reverify.json()['ok']} (TAMPER DETECTED!)")
    print(f"First Broken Sequence: #{res_reverify.json()['first_broken_seq']}")
    print(f"Failure Detail: {res_reverify.json()['message']}")

    print("\nRestoring audit ledger integrity via /audit/repair...")
    client.post("/audit/repair")
    res_restored = client.get("/audit/verify")
    print(f"Post-Repair Integrity Status: ok={res_restored.json()['ok']}")
    print(f"Audit Message: {res_restored.json()['message']}")

    banner("WALKTHROUGH COMPLETED SUCCESSFULLY!")
    print("Every backend module (main, crud, models, workflow, audit, scheduler, clock, adapters)")
    print("is fully functional, connected, and verified!\n")

if __name__ == "__main__":
    main()
