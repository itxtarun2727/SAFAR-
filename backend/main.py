"""
main.py — FastAPI Application Entrypoint for SAFAR Portal.

Exposes REST endpoints for:
- /health: Liveness check
- /auth: Login and persona verification
- /instruments: FDR lifecycle management and Two-Column Trust data
- /workflow: State machine transitions
- /audit: SHA-256 hash-chain verification & tamper simulation
- /rules: Configurable AICTE parameters
- /clock: Demo time-travel controls (+30D, +90D)
- /scheduler: Idempotent daily alert execution
"""

from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
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
        "⚠️ **NOTICE: Bank confirmation responses and external verification feeds "
        "are SIMULATED in this prototype.**"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


# ── Institutions ───────────────────────────────────────────────────────────────

@app.get("/institutions", response_model=List[schemas.InstitutionResponse], tags=["Institutions"])
def list_institutions(db: Session = Depends(get_db)):
    """List technical institutions."""
    return crud.get_institutions(db)


# ── Instruments (FDRs) ─────────────────────────────────────────────────────────

@app.get("/instruments", response_model=List[schemas.InstrumentResponse], tags=["Instruments"])
def list_instruments(
    institution_id: Optional[str] = None,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Filter and list instruments with institutional scoping."""
    if user.role == "institution" and user.institution_ids:
        institution_id = user.institution_ids[0]
    return crud.get_instruments(db, institution_id=institution_id, status=status, stage=stage)


@app.post("/instruments", response_model=schemas.InstrumentResponse, tags=["Instruments"])
def create_instrument(
    data: schemas.InstrumentCreate,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Submit a new FDR certificate record (Scenario 1)."""
    # College account isolation: automatically bind to the college's assigned institution
    if user.role == "institution" and user.institution_ids:
        data.institution_id = user.institution_ids[0]
    return crud.create_instrument(db, data, actor_id=user.user_id, role=user.role)


@app.get("/instruments/{instrument_id}", response_model=schemas.InstrumentDetailResponse, tags=["Instruments"])
def get_instrument_detail(instrument_id: str, db: Session = Depends(get_db)):
    """Retrieve full details of an FDR including Two-Column Trust confirmations."""
    inst = crud.get_instrument_by_id(db, instrument_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found.")
    return inst


@app.post("/instruments/{instrument_id}/transition", tags=["Workflow"])
def trigger_transition(
    instrument_id: str,
    req: schemas.TransitionRequest,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Execute a guarded state transition through workflow.transition().
    Commits state update and append-only audit entry in one transaction.
    """
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


@app.post("/instruments/{instrument_id}/verify-bank", tags=["Verification"])
def verify_instrument_with_bank(
    instrument_id: str,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger bank confirmation verification via simulated bank adapter."""
    inst = crud.get_instrument_by_id(db, instrument_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found.")

    res = adapters.bank_adapter.verify(inst.reference_no, inst.bank_name)

    # Update or add field confirmation
    conf = (
        db.query(models.FieldConfirmation)
        .filter(models.FieldConfirmation.instrument_id == inst.id, models.FieldConfirmation.field_name == "maturity_date")
        .first()
    )
    if conf:
        conf.result = res["result"]
        conf.reason_code = res.get("reason_code")
        conf.confirmed_value = res.get("confirmed_data", {}).get("maturity_date") if res.get("confirmed_data") else None
        conf.confirmed_by = "Bank Checker [SIMULATED]"
        conf.confirmed_at = Clock.now()

    # If still in SUBMITTED, advance to BANK_CHECK first
    if inst.status == "SUBMITTED":
        crud.execute_transition(
            db=db,
            instrument_id=inst.id,
            event="send_to_bank",
            actor_id=user.user_id,
            role=user.role,
            reason="Dispatch to bank verification adapter.",
        )

    # If matching, transition to ACTIVE; if mismatch, transition to REJECTED
    event = "bank_confirms" if res["result"] == "match" else "bank_rejects"
    try:
        crud.execute_transition(
            db=db,
            instrument_id=inst.id,
            event=event,
            actor_id="bank-adapter-simulated",
            role="bank_checker",
            reason=res["message"],
        )
    except Exception as e:
        print(f"Auto-transition notice: {e}")

    db.commit()
    return res


@app.get("/instruments/{instrument_id}/lineage", response_model=List[schemas.InstrumentResponse], tags=["Instruments"])
def get_instrument_lineage(instrument_id: str, db: Session = Depends(get_db)):
    """Retrieve full predecessor and successor renewal chain."""
    return crud.get_lineage(db, instrument_id)


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
    )


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


@app.post("/instruments/{instrument_id}/release", response_model=schemas.ReleaseResponse, tags=["Release"])
def request_release_endpoint(
    instrument_id: str,
    req: schemas.ReleaseCreate,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Submit a security deposit release request with clearance checklist."""
    try:
        return crud.create_release_request(
            db=db,
            instrument_id=instrument_id,
            kind=req.kind,
            reason=req.reason,
            checklist=req.checklist,
            maker_id=user.user_id,
            role=user.role,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Dashboard Metrics ──────────────────────────────────────────────────────────

@app.get("/dashboard/stats", tags=["Dashboard"])
def get_dashboard_metrics(
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Return status counts scoped to active user / institution."""
    institution_id = user.institution_ids[0] if (user.role == "institution" and user.institution_ids) else None
    return crud.get_dashboard_counts(db, institution_id=institution_id)


# ── Alerts & Scheduler ─────────────────────────────────────────────────────────

@app.get("/alerts", response_model=List[schemas.AlertResponse], tags=["Alerts"])
def list_alerts(
    instrument_id: Optional[str] = None,
    user: auth.AuthUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """List generated maturity and escalation alerts with institutional isolation."""
    query = db.query(models.Alert)
    if user.role == "institution" and user.institution_ids:
        query = query.join(models.Instrument).filter(models.Instrument.institution_id == user.institution_ids[0])
    if instrument_id:
        query = query.filter(models.Alert.instrument_id == instrument_id)
    return query.order_by(models.Alert.sent_at.desc()).all()


@app.post("/scheduler/run-now", tags=["Scheduler"])
def run_scheduler(db: Session = Depends(get_db)):
    """Trigger manual execution of the idempotent daily alert evaluation."""
    return scheduler.run_daily_alert_job(db)


# ── Audit Chain & Tamper Evidence ──────────────────────────────────────────────

@app.get("/audit/entries", response_model=List[schemas.AuditEntryResponse], tags=["Audit"])
def get_audit_log(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Fetch append-only audit entries in chronological sequence."""
    return db.query(models.AuditEntry).order_by(models.AuditEntry.seq.desc()).offset(skip).limit(limit).all()


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
def simulate_tamper_endpoint(db: Session = Depends(get_db)):
    """Deliberately modify an audit row to demonstrate tamper detection to evaluators."""
    tampered_seq = audit.simulate_tamper(db)
    return {
        "status": "tampered",
        "tampered_sequence": tampered_seq,
        "message": "Audit row tampered. Run /audit/verify to see verification fail immediately."
    }


@app.post("/audit/repair", tags=["Audit"])
def repair_audit_chain(db: Session = Depends(get_db)):
    """Recompute valid cryptographic hashes to restore chain integrity after a tamper demo."""
    recomputed_count = audit.repair_chain(db)
    return {
        "status": "repaired",
        "entries_recomputed": recomputed_count,
        "message": "Audit chain hashes recomputed. Verification is now restored."
    }


# ── Demo Clock (Time Travel) ───────────────────────────────────────────────────

@app.get("/clock", tags=["Clock"])
def get_clock():
    """Get current demo clock status."""
    return {
        "current_time": Clock.now().isoformat(),
        "today": Clock.today().isoformat(),
        "is_simulated": Clock.is_simulated(),
    }


@app.post("/clock/advance", tags=["Clock"])
def advance_clock(days: int = Query(30, ge=1, le=3650), db: Session = Depends(get_db)):
    """Fast-forward system time by N days and evaluate alerts (Scenario 4)."""
    new_dt = Clock.advance_days(days)
    # Auto-run scheduler on time-travel
    sched_result = scheduler.run_daily_alert_job(db)
    return {
        "new_time": new_dt.isoformat(),
        "today": Clock.today().isoformat(),
        "scheduler_run": sched_result,
    }


@app.post("/clock/reset", tags=["Clock"])
def reset_clock():
    """Reset clock to real system time."""
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
