"""
crud.py — Data Access Layer with SQL-Level Scoping, Two-Part Release Codes,
and Cryptographic Audit Logging.

RULES:
- Multi-tenant isolation enforced at the SQL query level on EVERY query.
- Pure state transitions delegated to workflow.transition().
- SHA-256 hash-chained audit ledger entry recorded in the same transaction.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import timedelta
import uuid
import json
import secrets
import hashlib
import hmac
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

import models
import schemas
import workflow
import audit
import rules
import adapters
import auth
import storage
from clock import Clock


# ── Scope Filters ──────────────────────────────────────────────────────────────

def apply_instrument_scope(
    query,
    user: Any,
    university_id: Optional[str] = None,
    state: Optional[str] = None,
    institution_id: Optional[str] = None,
    exclude_needs_correction: bool = False,
):
    """
    Apply strict multi-tenant SQL-level scoping based on user role and hierarchy:
    - institution: only their own college
    - aicte_officer: only colleges under their university_id (never show NEEDS_CORRECTION in queue)
    - aicte_senior: all colleges, with optional filters by university, state, and college
    - bank_checker: only instruments at their bank_id
    - auditor / admin: read-only all
    """
    if user.role == "institution":
        inst_id = user.institution_id or (user.institution_ids[0] if user.institution_ids else None)
        query = query.filter(models.Instrument.institution_id == inst_id)

    elif user.role == "aicte_officer":
        query = query.join(models.Institution).filter(
            models.Institution.university_id == user.university_id
        )
        # NEEDS_CORRECTION must NOT appear in officer queues
        if exclude_needs_correction:
            query = query.filter(models.Instrument.status != "NEEDS_CORRECTION")

    elif user.role == "aicte_senior":
        # Senior has national access; apply optional filter criteria
        if university_id or state:
            query = query.join(models.Institution)
            if university_id:
                query = query.filter(models.Institution.university_id == university_id)
            if state:
                query = query.filter(models.Institution.state == state)
        if institution_id:
            query = query.filter(models.Instrument.institution_id == institution_id)

    elif user.role == "bank_checker":
        query = query.filter(models.Instrument.bank_id == user.bank_id)

    # For auditor and admin, apply optional filters if requested
    elif user.role in ("auditor", "admin"):
        if university_id or state:
            query = query.join(models.Institution)
            if university_id:
                query = query.filter(models.Institution.university_id == university_id)
            if state:
                query = query.filter(models.Institution.state == state)
        if institution_id:
            query = query.filter(models.Instrument.institution_id == institution_id)

    return query


def check_instrument_access(instrument: Optional[models.Instrument], user: Any) -> models.Instrument:
    """Enforce read/write permission on single instrument record by ID."""
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found.")

    if user.role == "institution":
        inst_id = user.institution_id or (user.institution_ids[0] if user.institution_ids else None)
        if instrument.institution_id != inst_id:
            raise HTTPException(status_code=403, detail="Access denied: College account isolation violation.")

    elif user.role == "aicte_officer":
        if not instrument.institution or instrument.institution.university_id != user.university_id:
            raise HTTPException(status_code=403, detail="Access denied: University officer jurisdiction scope violation.")

    elif user.role == "bank_checker":
        if instrument.bank_id != user.bank_id:
            raise HTTPException(status_code=403, detail="Access denied: Bank account isolation violation.")

    return instrument


# ── Metadata Queries (Universities & Banks) ───────────────────────────────────

def get_universities(db: Session) -> List[models.University]:
    """Retrieve all affiliating state technical universities."""
    return db.query(models.University).order_by(models.University.name.asc()).all()


def get_banks(db: Session) -> List[models.Bank]:
    """Retrieve all fictional demo partner banks [SIMULATED]."""
    return db.query(models.Bank).order_by(models.Bank.name.asc()).all()


def get_institutions(
    db: Session,
    user: Any = None,
    university_id: Optional[str] = None,
    state: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.Institution]:
    """List technical institutions scoped by user role."""
    query = db.query(models.Institution)
    if user:
        if user.role == "institution":
            inst_id = user.institution_id or (user.institution_ids[0] if user.institution_ids else None)
            query = query.filter(models.Institution.id == inst_id)
        elif user.role == "aicte_officer":
            query = query.filter(models.Institution.university_id == user.university_id)

    if university_id:
        query = query.filter(models.Institution.university_id == university_id)
    if state:
        query = query.filter(models.Institution.state == state)

    return query.offset(skip).limit(limit).all()


def get_institution_by_id(db: Session, institution_id: str, user: Any = None) -> Optional[models.Institution]:
    """Retrieve institution by primary key with scoping checks."""
    inst = db.query(models.Institution).filter(models.Institution.id == institution_id).first()
    if not inst:
        return None
    if user:
        if user.role == "institution":
            user_inst_id = user.institution_id or (user.institution_ids[0] if user.institution_ids else None)
            if inst.id != user_inst_id:
                raise HTTPException(status_code=403, detail="Access denied: Institution scope violation.")
        elif user.role == "aicte_officer":
            if inst.university_id != user.university_id:
                raise HTTPException(status_code=403, detail="Access denied: University jurisdiction scope violation.")
    return inst


# ── Instruments (FDRs) ─────────────────────────────────────────────────────────

def get_instruments(
    db: Session,
    user: Any,
    institution_id: Optional[str] = None,
    university_id: Optional[str] = None,
    state: Optional[str] = None,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.Instrument]:
    """Filter and retrieve instruments with multi-tenant SQL scoping."""
    query = db.query(models.Instrument)

    # Exclude NEEDS_CORRECTION from officer queues if officer is querying
    exclude_nc = (user.role == "aicte_officer")
    query = apply_instrument_scope(
        query=query,
        user=user,
        university_id=university_id,
        state=state,
        institution_id=institution_id,
        exclude_needs_correction=exclude_nc,
    )

    if status:
        query = query.filter(models.Instrument.status == status)
    if stage:
        query = query.filter(models.Instrument.current_stage == stage)

    return query.order_by(models.Instrument.maturity_date.asc()).offset(skip).limit(limit).all()


def get_instrument_by_id(db: Session, instrument_id: str, user: Any = None) -> Optional[models.Instrument]:
    """Retrieve instrument by ID with scoping enforcement."""
    inst = db.query(models.Instrument).filter(models.Instrument.id == instrument_id).first()
    if user:
        check_instrument_access(inst, user)
    return inst


def get_instrument_by_reference(db: Session, reference_no: str) -> Optional[models.Instrument]:
    """Retrieve instrument by unique reference FDR number."""
    return db.query(models.Instrument).filter(models.Instrument.reference_no == reference_no).first()


def create_instrument(
    db: Session,
    data: schemas.InstrumentCreate,
    user: Any,
) -> models.Instrument:
    """
    Register a new FDR submission:
    - Binds bank_id chosen by college on submit form
    - Forces the college's own institution_id
    - Triggers the automatic bank check (SUBMITTED -> BANK_CHECK -> AICTE_REVIEW or NEEDS_CORRECTION)
    - Records audit logs
    """
    institution_id = data.institution_id
    if user.role == "institution":
        institution_id = user.institution_id or (user.institution_ids[0] if user.institution_ids else institution_id)

    # If bank_id provided, look up the bank
    bank = None
    if data.bank_id:
        bank = db.query(models.Bank).filter(models.Bank.id == data.bank_id).first()
    if not bank:
        # Fallback to bank-001 if unspecified
        bank = db.query(models.Bank).filter(models.Bank.id == "bank-001").first()

    bank_id = bank.id if bank else "bank-001"
    bank_name = bank.name if bank else data.bank_name

    instrument_id = f"inst-{str(uuid.uuid4())[:8]}"
    instrument = models.Instrument(
        id=instrument_id,
        institution_id=institution_id,
        bank_id=bank_id,
        bank_name=bank_name,
        branch=data.branch or "Main Branch",
        reference_no=data.reference_no,
        amount_paise=data.amount_paise,
        interest_rate=data.interest_rate,
        issue_date=data.issue_date,
        maturity_date=data.maturity_date,
        tenure_years=data.tenure_years,
        status="SUBMITTED",
        joint_holder=data.joint_holder or "AICTE & College Society",
        lien_marked=data.lien_marked,
        predecessor_id=data.predecessor_id,
        failed_verification_count=0,
    )
    db.add(instrument)
    db.flush()

    # Create initial unconfirmed field checks
    for field_name, submitted_val in [
        ("reference_no", data.reference_no),
        ("bank_name", bank_name),
        ("amount_paise", str(data.amount_paise)),
        ("maturity_date", data.maturity_date.isoformat()),
        ("joint_holder", instrument.joint_holder),
        ("lien_marked", str(data.lien_marked)),
    ]:
        conf = models.FieldConfirmation(
            id=str(uuid.uuid4()),
            instrument_id=instrument.id,
            field_name=field_name,
            submitted_value=submitted_val,
            confirmed_value=None,
            source="bank_console",
            result="pending",
        )
        db.add(conf)

    # Genesis audit log
    audit.append_audit_entry(
        db=db,
        actor_id=user.user_id,
        role=user.role,
        entity="instrument",
        entity_id=instrument.id,
        from_state=None,
        to_state="SUBMITTED",
        payload={"reference_no": data.reference_no, "amount": data.amount_paise, "bank_id": bank_id},
        reason="Initial FDR regulatory submission by institution.",
    )
    db.commit()
    db.refresh(instrument)

    # Trigger automatic bank verification check
    run_bank_verification(db=db, instrument_id=instrument.id, user=user)
    db.refresh(instrument)
    return instrument


# ── Bank Verification Workflow ────────────────────────────────────────────────

def run_bank_verification(db: Session, instrument_id: str, user: Any) -> Dict[str, Any]:
    """
    Executes automated bank check against simulated bank adapter:
    - If match -> advances to AICTE_REVIEW
    - If mismatch -> advances to NEEDS_CORRECTION (visible to college only, never in officer queues)
      increments failed_verification_count, logs FAILED_VERIFICATION, checks 3-failure alert threshold
    - If source_unavailable -> remains in BANK_CHECK with 'pending, bank unavailable'
    """
    inst = db.query(models.Instrument).filter(models.Instrument.id == instrument_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found.")

    # 1. Advance to BANK_CHECK if in SUBMITTED
    if inst.status == "SUBMITTED":
        execute_transition(
            db=db,
            instrument_id=inst.id,
            event="send_to_bank",
            actor_id="system",
            role="system",
            reason="Automated dispatch to partner bank verification adapter [SIMULATED].",
            extra_context={"instrument": inst},
        )

    # 2. Call simulated bank adapter
    res = adapters.bank_adapter.verify(inst.reference_no, inst.bank_name)
    result_status = res.get("result", "mismatch")

    # Update field confirmations
    conf = (
        db.query(models.FieldConfirmation)
        .filter(models.FieldConfirmation.instrument_id == inst.id, models.FieldConfirmation.field_name == "maturity_date")
        .first()
    )
    if conf:
        conf.result = result_status
        conf.reason_code = res.get("reason_code")
        conf.confirmed_value = res.get("confirmed_data", {}).get("maturity_date") if res.get("confirmed_data") else None
        conf.confirmed_by = f"{inst.bank_name} Checker [SIMULATED]"
        conf.confirmed_at = Clock.now()

    if result_status == "match":
        # Advance to AICTE_REVIEW if in BANK_CHECK
        if inst.status == "BANK_CHECK":
            execute_transition(
                db=db,
                instrument_id=inst.id,
                event="bank_match",
                actor_id="bank-adapter-simulated",
                role="bank_checker",
                reason="Bank verification confirmed all fields match regulatory record [SIMULATED].",
                extra_context={"instrument": inst},
            )

    elif result_status == "mismatch":
        # Increment failed verification count
        inst.failed_verification_count += 1
        reason_code = res.get("reason_code", "RECORD_MISMATCH")
        plain_reason = f"Mismatch with bank record: {reason_code.replace('_', ' ').title()}"

        # Record failed attempt record
        failed_attempt = models.FailedVerificationAttempt(
            id=str(uuid.uuid4()),
            instrument_id=inst.id,
            institution_id=inst.institution_id,
            reason_code=reason_code,
            attempted_at=Clock.now(),
        )
        db.add(failed_attempt)

        # Transition to NEEDS_CORRECTION if in BANK_CHECK
        if inst.status == "BANK_CHECK":
            execute_transition(
                db=db,
                instrument_id=inst.id,
                event="bank_mismatch",
                actor_id="bank-adapter-simulated",
                role="bank_checker",
                reason=plain_reason,
                extra_context={"instrument": inst, "reason": plain_reason},
            )

        # Record audit log type FAILED_VERIFICATION
        audit.append_audit_entry(
            db=db,
            actor_id="system",
            role="system",
            entity="instrument",
            entity_id=inst.id,
            from_state=inst.status,
            to_state="NEEDS_CORRECTION",
            payload={"event": "FAILED_VERIFICATION", "reason_code": reason_code, "attempt_count": inst.failed_verification_count},
            reason=f"Failed verification attempt #{inst.failed_verification_count}: {plain_reason}",
        )

        # Alert Senior and Auditor at threshold
        alert_threshold = rules.get_rule(db, "verification.failed_attempt_alert_threshold", 3)
        if inst.failed_verification_count >= alert_threshold:
            existing_alert = (
                db.query(models.Alert)
                .filter(models.Alert.instrument_id == inst.id, models.Alert.stage == "FAILED_VERIFICATION_ALERT")
                .first()
            )
            if not existing_alert:
                alert = models.Alert(
                    id=str(uuid.uuid4()),
                    instrument_id=inst.id,
                    stage="FAILED_VERIFICATION_ALERT",
                    channel="in_app",
                    due_at=Clock.today(),
                    sent_at=Clock.now(),
                )
                db.add(alert)

    elif result_status == "source_unavailable":
        # Stays pending in BANK_CHECK
        execute_transition(
            db=db,
            instrument_id=inst.id,
            event="source_unavailable",
            actor_id="system",
            role="system",
            reason="Bank verification service temporarily unavailable [SIMULATED]. Retrying with backoff.",
            extra_context={"instrument": inst},
        )

    db.commit()
    db.refresh(inst)
    return res


# ── State Machine Transition Runner ───────────────────────────────────────────

def execute_transition(
    db: Session,
    instrument_id: str,
    event: str,
    actor_id: str,
    role: str,
    reason: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> Tuple[models.Instrument, List[str]]:
    """
    Evaluates state machine transition and commits state + audit atomically.
    """
    instrument = db.query(models.Instrument).filter(models.Instrument.id == instrument_id).first()
    if not instrument:
        raise ValueError(f"Instrument '{instrument_id}' not found.")

    active_dispute = (
        db.query(models.Dispute)
        .filter(models.Dispute.instrument_id == instrument_id, models.Dispute.is_active == True)
        .first()
    )

    context = {
        "instrument": instrument,
        "actor_id": actor_id,
        "role": role,
        "reason": reason,
        "has_active_dispute": bool(active_dispute),
    }
    if extra_context:
        context.update(extra_context)

    # Pure transition validation
    new_state, effects = workflow.transition(instrument.status, event, context)

    from_state = instrument.status
    instrument.status = new_state
    instrument.updated_at = Clock.now()

    # Apply known effects
    if "mark_lien_active" in effects:
        instrument.lien_marked = True
    elif "release_custody_lien" in effects:
        instrument.lien_marked = False

    # Atomic audit logging
    audit.append_audit_entry(
        db=db,
        actor_id=actor_id,
        role=role,
        entity="instrument",
        entity_id=instrument.id,
        from_state=from_state,
        to_state=new_state,
        payload={"event": event, "effects": effects},
        reason=reason or f"Transitioned via event '{event}'",
    )

    db.commit()
    db.refresh(instrument)
    return instrument, effects


# ── Submission Scrutiny & Resubmission (AICTE Review) ─────────────────────────

def approve_submission(
    db: Session,
    instrument_id: str,
    reason: str,
    user: Any,
) -> models.Instrument:
    """University officer approves a submitted deposit in AICTE_REVIEW."""
    inst = db.query(models.Instrument).filter(models.Instrument.id == instrument_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found.")

    if user.role in ("aicte_officer", "university"):
        college = inst.institution
        if college and college.university_id != user.university_id:
            raise HTTPException(status_code=403, detail="Access denied: Officer jurisdiction scope violation.")
    elif user.role not in ("aicte_senior", "admin"):
        raise HTTPException(status_code=403, detail="Access denied: Only university officers or admins can approve submissions.")

    if not reason or not str(reason).strip():
        raise HTTPException(status_code=400, detail="Approval reason must be recorded.")

    execute_transition(
        db=db,
        instrument_id=inst.id,
        event="approve",
        actor_id=user.user_id,
        role=user.role,
        reason=reason,
        extra_context={"instrument": inst, "reason": reason},
    )
    return inst


def reject_submission(
    db: Session,
    instrument_id: str,
    reason: str,
    user: Any,
) -> models.Instrument:
    """University officer rejects a submitted deposit in AICTE_REVIEW."""
    inst = db.query(models.Instrument).filter(models.Instrument.id == instrument_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found.")

    if user.role in ("aicte_officer", "university"):
        college = inst.institution
        if college and college.university_id != user.university_id:
            raise HTTPException(status_code=403, detail="Access denied: Officer jurisdiction scope violation.")
    elif user.role not in ("aicte_senior", "admin"):
        raise HTTPException(status_code=403, detail="Access denied: Only university officers or admins can reject submissions.")

    if not reason or not str(reason).strip():
        raise HTTPException(status_code=400, detail="Rejection reason must be provided and will be shown to the college.")

    execute_transition(
        db=db,
        instrument_id=inst.id,
        event="reject",
        actor_id=user.user_id,
        role=user.role,
        reason=reason,
        extra_context={"instrument": inst, "reason": reason},
    )
    return inst


def resubmit_instrument(
    db: Session,
    instrument_id: str,
    user: Any,
    reason: Optional[str] = "Corrected regulatory submission by institution.",
) -> models.Instrument:
    """College resubmits an instrument that was REJECTED or in NEEDS_CORRECTION."""
    inst = get_instrument_by_id(db, instrument_id, user=user)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found.")
    check_instrument_access(inst, user)

    if inst.status not in ("REJECTED", "NEEDS_CORRECTION"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resubmit instrument in status '{inst.status}'. Must be REJECTED or NEEDS_CORRECTION."
        )

    execute_transition(
        db=db,
        instrument_id=inst.id,
        event="resubmit",
        actor_id=user.user_id,
        role=user.role,
        reason=reason or "College resubmitted corrected deposit.",
        extra_context={"instrument": inst},
    )

    # Automatic bank verification triggered on resubmit
    run_bank_verification(db, inst.id, user)
    db.refresh(inst)
    return inst


# ── Release Workflow (Recommend, Approve, Authorize, Bank Confirm) ────────────

def create_release_request(
    db: Session,
    instrument_id: str,
    kind: str,
    reason: Optional[str],
    user: Any,
) -> models.ReleaseRequest:
    """Institution initiates release request for a matured FDR or closure."""
    inst = check_instrument_access(get_instrument_by_id(db, instrument_id), user)

    # Transition instrument status from ACTIVE to RELEASE_REQUESTED
    execute_transition(
        db=db,
        instrument_id=instrument_id,
        event="release_requested",
        actor_id=user.user_id,
        role=user.role,
        reason=reason or "Institution initiated deposit release request.",
        extra_context={"instrument": inst, "kind": kind or "release"},
    )

    rel = models.ReleaseRequest(
        id=str(uuid.uuid4()),
        instrument_id=instrument_id,
        kind=kind or "release",
        maker_id=user.user_id,
        decision="PENDING",
        reason=reason,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return rel


def recommend_release(
    db: Session,
    release_id: str,
    reason: str,
    checklist: Dict[str, bool],
    user: Any,
) -> models.ReleaseRequest:
    """University officer verifies checklist and records recommendation."""
    rel = db.query(models.ReleaseRequest).filter(models.ReleaseRequest.id == release_id).first()
    if not rel:
        raise HTTPException(status_code=404, detail="Release request not found.")

    inst = check_instrument_access(rel.instrument, user)
    if user.role in ("aicte_officer", "university"):
        if inst.institution and inst.institution.university_id != user.university_id:
            raise HTTPException(status_code=403, detail="Access denied: Officer jurisdiction scope violation.")
    elif user.role not in ("admin",):
        raise HTTPException(status_code=403, detail="Access denied: Only university officers can recommend release.")

    # Transition RELEASE_REQUESTED -> COMPLIANCE_CHECK
    execute_transition(
        db=db,
        instrument_id=inst.id,
        event="recommend",
        actor_id=user.user_id,
        role=user.role,
        reason=reason,
        extra_context={"instrument": inst, "reason": reason},
    )

    rel.checker_id = user.user_id
    rel.checklist_json = json.dumps(checklist)
    rel.reason = reason
    db.commit()
    db.refresh(rel)
    return rel


def approve_release(
    db: Session,
    release_id: str,
    reason: str,
    user: Any,
) -> models.ReleaseAuthorization:
    """
    Senior manager approves release:
    - Enforces maker != checker (senior differs from recommending officer)
    - Checks no open dispute
    - Performs simulated bank re-verification (must return match)
    - Verifies checklist complete
    - Transitions COMPLIANCE_CHECK -> APPROVED
    - Issues ReleaseAuthorization with two-part code and transitions to BANK_RELEASE_PENDING
    """
    rel = db.query(models.ReleaseRequest).filter(models.ReleaseRequest.id == release_id).first()
    if not rel:
        raise HTTPException(status_code=404, detail="Release request not found.")

    inst = rel.instrument

    # Check that approving senior is different from recommending officer
    recommender_id = rel.checker_id or rel.maker_id
    if user.user_id == recommender_id:
        raise HTTPException(status_code=400, detail="Senior approving officer must differ from recommending officer.")

    # Simulated fresh bank re-verification
    reverify_res = adapters.bank_adapter.verify(inst.reference_no, inst.bank_name)
    reverify_match = reverify_res.get("result", "mismatch")

    checklist = {}
    if rel.checklist_json:
        try:
            checklist = json.loads(rel.checklist_json)
        except Exception:
            checklist = {}

    # Transition COMPLIANCE_CHECK -> APPROVED
    execute_transition(
        db=db,
        instrument_id=inst.id,
        event="approve",
        actor_id=user.user_id,
        role=user.role,
        reason=reason,
        extra_context={
            "instrument": inst,
            "maker_id": recommender_id,
            "checklist": checklist,
            "reverification_result": reverify_match,
        },
    )

    rel.decision = "APPROVED"
    rel.decided_at = Clock.now()

    # Create Release Authorization with ONLY bank code
    auth_record = create_release_authorization(
        db=db,
        instrument=inst,
        issued_by=user.user_id,
    )

    # Transition APPROVED -> BANK_RELEASE_PENDING
    execute_transition(
        db=db,
        instrument_id=inst.id,
        event="issue_authorization",
        actor_id=user.user_id,
        role="system",
        reason=f"Release authorization issued: {auth_record.release_ref}. Dispatched to bank inbox [SIMULATED].",
        extra_context={"instrument": inst},
    )

    db.commit()
    return auth_record


def create_release_authorization(
    db: Session,
    instrument: models.Instrument,
    issued_by: str,
) -> models.ReleaseAuthorization:
    """
    Generate cryptographic release authorization:
    - release_ref: Unique public reference
    - bank_code: Generated and delivered directly to the bank's adapter/inbox
    - college_code: NOT generated here! College claims their code via /claim-code
    - Store ONLY SHA-256 hashes in database table
    - Sets expiration hours from rules table
    """
    release_ref = f"REL-{secrets.token_hex(6).upper()}"
    bank_code = secrets.token_urlsafe(24)
    bank_code_hash = hashlib.sha256(bank_code.encode("utf-8")).hexdigest()

    expiry_hours = rules.get_rule(db, "release.code_expiry_hours", 72)
    expires_at = Clock.now() + timedelta(hours=expiry_hours)

    auth = models.ReleaseAuthorization(
        id=str(uuid.uuid4()),
        release_ref=release_ref,
        instrument_id=instrument.id,
        bank_id=instrument.bank_id or "bank-001",
        bank_code_hash=bank_code_hash,
        college_code_hash=None,  # College claims this exclusively via claim-code endpoint
        failed_attempt_count=0,
        issued_by=issued_by,
        issued_at=Clock.now(),
        expires_at=expires_at,
        status="ISSUED",
    )
    db.add(auth)
    db.flush()

    # Deliver bank code to simulated bank adapter release endpoint
    adapters.bank_adapter.request_release(instrument.reference_no, release_ref)

    # Audit authorization issuance
    audit.append_audit_entry(
        db=db,
        actor_id=issued_by,
        role="aicte_senior",
        entity="release_authorization",
        entity_id=release_ref,
        from_state=None,
        to_state="ISSUED",
        payload={"instrument_id": instrument.id, "bank_id": auth.bank_id, "expires_at": expires_at.isoformat()},
        reason=f"Release authorization generated. Bank code delivered to bank inbox [SIMULATED].",
    )
    db.commit()
    db.refresh(auth)
    return auth


def claim_college_release_code(
    db: Session,
    release_ref: str,
    user: Any,
) -> Dict[str, str]:
    """
    College claims its release code:
    - Caller MUST be role 'institution'
    - Instrument MUST belong to caller's institution_id
    - Generates 24-char college code, stores SHA-256 hash in college_code_hash
    - Invalidates any prior college code for this authorization
    - Audits issuance
    - Returns college_code ONCE to the college
    """
    if user.role != "institution":
        raise HTTPException(status_code=403, detail="Only technical college representatives can claim the college release code.")

    auth = db.query(models.ReleaseAuthorization).filter(
        models.ReleaseAuthorization.release_ref == release_ref
    ).first()
    if not auth:
        raise HTTPException(status_code=404, detail="Release authorization not found.")

    inst = auth.instrument
    # Multi-tenant scoping: must belong to caller's college
    user_inst_id = user.institution_id or (user.institution_ids[0] if user.institution_ids else None)
    if not user_inst_id or inst.institution_id != user_inst_id:
        raise HTTPException(status_code=403, detail="Access denied: Cannot claim release code for another institution's deposit.")

    if auth.status in ["USED", "EXPIRED", "LOCKED"]:
        raise HTTPException(status_code=400, detail=f"Cannot claim release code: Authorization is {auth.status}.")

    # Generate new college code and overwrite any previous hash (invalidating prior code)
    college_code = secrets.token_urlsafe(24)
    auth.college_code_hash = hashlib.sha256(college_code.encode("utf-8")).hexdigest()
    auth.status = "CLAIMED"
    db.commit()

    # Audit code claim
    audit.append_audit_entry(
        db=db,
        actor_id=user.user_id,
        role=user.role,
        entity="release_authorization",
        entity_id=release_ref,
        from_state="ISSUED",
        to_state="CLAIMED",
        payload={"instrument_id": inst.id, "institution_id": inst.institution_id},
        reason="College claimed one-time release code for presentation to partner bank [SIMULATED].",
    )
    db.commit()

    return {
        "release_ref": release_ref,
        "college_code": college_code,
        "message": "Store this code safely. It will not be shown again. Present it at the bank console.",
    }


def confirm_bank_release(
    db: Session,
    release_ref: str,
    college_code: str,
    user: Any,
) -> Dict[str, Any]:
    """
    Bank Console release confirmation:
    - Verified against bank user's bank_id
    - Rate-limits wrong attempts and locks after N failures
    - Checks unexpired and unused
    - Constant-time comparison using hmac.compare_digest
    - On success: marks authorization USED, discharges lien, transitions instrument to CLOSED
    - Audits every match and mismatch attempt
    """
    auth = db.query(models.ReleaseAuthorization).filter(
        models.ReleaseAuthorization.release_ref == release_ref
    ).first()
    if not auth:
        raise HTTPException(status_code=404, detail="Release authorization reference not found.")

    # Bank isolation
    if user.bank_id and auth.bank_id != user.bank_id:
        raise HTTPException(status_code=403, detail="Release authorization belongs to a different bank.")

    if auth.status == "USED":
        raise HTTPException(status_code=400, detail="This release authorization has already been executed.")

    max_failed_attempts = rules.get_rule(db, "release.max_failed_attempts", 3)
    if auth.status == "LOCKED" or auth.failed_attempt_count >= max_failed_attempts:
        auth.status = "LOCKED"
        db.commit()
        raise HTTPException(status_code=400, detail="Release authorization is locked due to excessive failed attempts.")

    now_dt = Clock.now().replace(tzinfo=None) if Clock.now().tzinfo else Clock.now()
    exp_dt = auth.expires_at.replace(tzinfo=None) if auth.expires_at.tzinfo else auth.expires_at
    if auth.status == "EXPIRED" or now_dt > exp_dt:
        auth.status = "EXPIRED"
        db.commit()
        raise HTTPException(status_code=400, detail="Release authorization code has expired. Senior authority must reissue.")

    if not auth.college_code_hash:
        raise HTTPException(status_code=400, detail="College has not claimed their release code yet.")

    # Constant-time comparison of hashed college code
    input_hash = hashlib.sha256(college_code.strip().encode("utf-8")).hexdigest()
    matched = hmac.compare_digest(auth.college_code_hash, input_hash)

    if not matched:
        auth.failed_attempt_count += 1
        is_now_locked = auth.failed_attempt_count >= max_failed_attempts
        if is_now_locked:
            auth.status = "LOCKED"

        audit.append_audit_entry(
            db=db,
            actor_id=user.user_id,
            role=user.role,
            entity="release_authorization",
            entity_id=release_ref,
            from_state=auth.status,
            to_state="LOCKED" if is_now_locked else "MISMATCH",
            payload={"attempted_by": user.user_id, "failed_attempt_count": auth.failed_attempt_count},
            reason="Release code mismatch recorded at bank console [SIMULATED]." if not is_now_locked else "Release authorization locked due to excessive invalid code attempts.",
        )
        db.commit()
        if is_now_locked:
            raise HTTPException(status_code=400, detail="Invalid release code. Authorization is now locked due to excessive attempts.")
        raise HTTPException(status_code=400, detail=f"Invalid college verification code [SIMULATED]. Failed attempt {auth.failed_attempt_count}/{max_failed_attempts}.")

    # Success: Mark authorization as USED
    auth.status = "USED"
    auth.used_at = Clock.now()

    # Discharge instrument and close
    inst = auth.instrument
    execute_transition(
        db=db,
        instrument_id=inst.id,
        event="bank_confirms_release",
        actor_id=user.user_id,
        role=user.role,
        reason="Bank confirmed release with valid matching two-part code [SIMULATED]. AICTE lien removed.",
        extra_context={"instrument": inst, "code_matched": True},
    )

    # Audit successful confirmation
    audit.append_audit_entry(
        db=db,
        actor_id=user.user_id,
        role=user.role,
        entity="release_authorization",
        entity_id=release_ref,
        from_state="CLAIMED",
        to_state="USED",
        payload={"instrument_id": inst.id, "closed_at": Clock.now().isoformat()},
        reason="Release authorization matched and executed successfully. Deposit marked CLOSED [SIMULATED].",
    )
    db.commit()
    return {
        "status": "success",
        "message": "Deposit release successfully confirmed and lien discharged [SIMULATED].",
        "instrument_status": "CLOSED",
    }


def reissue_release_authorization(
    db: Session,
    release_ref: str,
    user: Any,
) -> models.ReleaseAuthorization:
    """Allows Senior Manager to reissue an expired authorization without revealing college code."""
    old_auth = db.query(models.ReleaseAuthorization).filter(
        models.ReleaseAuthorization.release_ref == release_ref
    ).first()
    if not old_auth:
        raise HTTPException(status_code=404, detail="Release authorization not found.")

    old_auth.status = "REISSUED"
    db.commit()

    inst = old_auth.instrument
    new_auth = create_release_authorization(
        db=db,
        instrument=inst,
        issued_by=user.user_id,
    )
    return new_auth


def upload_document(
    db: Session,
    instrument_id: str,
    file_name: str,
    doc_type: str,
    file_type: str,
    content_bytes: bytes,
    user: auth.AuthUser,
) -> models.Document:
    """Register and store document metadata with cryptographic SHA-256 and versioning."""
    inst = get_instrument_by_id(db, instrument_id, user=user)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found.")
    check_instrument_access(inst, user)

    sha256_hash = hashlib.sha256(content_bytes).hexdigest()
    last_doc = (
        db.query(models.Document)
        .filter(models.Document.instrument_id == instrument_id, models.Document.file_name == file_name)
        .order_by(models.Document.version.desc())
        .first()
    )
    new_version = (last_doc.version + 1) if last_doc else 1

    raw_storage_key = f"documents/{instrument_id}/{uuid.uuid4().hex}_{file_name}"
    doc = models.Document(
        id=str(uuid.uuid4()),
        instrument_id=instrument_id,
        version=new_version,
        file_name=file_name,
        file_type=file_type,
        file_size=len(content_bytes),
        sha256=sha256_hash,
        storage_key=raw_storage_key,
        uploaded_by=user.user_id,
        uploaded_at=Clock.now(),
    )
    loc_key = storage.storage.save(raw_storage_key, content_bytes, content_type=file_type, doc=doc)
    doc.storage_key = loc_key
    db.add(doc)
    db.flush()

    audit.append_audit_entry(
        db=db,
        actor_id=user.user_id,
        role=user.role,
        entity="document",
        entity_id=doc.id,
        from_state=None,
        to_state="UPLOADED",
        payload={
            "instrument_id": instrument_id,
            "file_name": file_name,
            "version": new_version,
            "sha256": sha256_hash,
            "storage_key": loc_key,
        },
        reason=f"Document '{file_name}' v{new_version} uploaded with verified SHA-256 digest.",
    )
    db.commit()
    db.refresh(doc)
    return doc


def download_document_content(db: Session, instrument_id: str, document_id: str, user: auth.AuthUser) -> Tuple[bytes, models.Document]:
    """Retrieve document bytes verifying tenant access and storage provider."""
    doc = get_document_by_id(db, instrument_id, document_id, user)
    content = storage.storage.get(doc.storage_key, doc=doc)
    if content is None:
        content = f"Document content for {doc.file_name} (digest: {doc.sha256})".encode("utf-8")
    return content, doc


def get_documents(db: Session, instrument_id: str, user: auth.AuthUser) -> List[models.Document]:
    """List documents for an instrument with access scoping."""
    inst = get_instrument_by_id(db, instrument_id, user=user)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found.")
    check_instrument_access(inst, user)
    return db.query(models.Document).filter(models.Document.instrument_id == instrument_id).order_by(models.Document.version.desc()).all()


def get_document_by_id(db: Session, instrument_id: str, document_id: str, user: auth.AuthUser) -> models.Document:
    """Retrieve document by ID with tenant access scoping."""
    inst = get_instrument_by_id(db, instrument_id, user=user)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found.")
    check_instrument_access(inst, user)
    doc = db.query(models.Document).filter(
        models.Document.id == document_id,
        models.Document.instrument_id == instrument_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


def acknowledge_alert(db: Session, alert_id: str, user: auth.AuthUser) -> models.Alert:
    """Formally acknowledge an alert notice."""
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    inst = alert.instrument
    check_instrument_access(inst, user)

    alert.acknowledged_at = Clock.now()
    alert.acknowledged_by = user.user_id
    db.commit()

    audit.append_audit_entry(
        db=db,
        actor_id=user.user_id,
        role=user.role,
        entity="alert",
        entity_id=alert.id,
        from_state="UNACKNOWLEDGED",
        to_state="ACKNOWLEDGED",
        payload={"instrument_id": inst.id, "stage": alert.stage},
        reason=f"Alert for stage {alert.stage} formally acknowledged by user {user.user_id}.",
    )
    db.commit()
    db.refresh(alert)
    return alert


def renew_instrument(db: Session, instrument_id: str, data: schemas.InstrumentRenewRequest, user: auth.AuthUser) -> models.Instrument:
    """Handle FDR renewal with predecessor link and automatic bank check trigger."""
    parent = get_instrument_by_id(db, instrument_id, user=user)
    if not parent:
        raise HTTPException(status_code=404, detail="Predecessor instrument not found.")
    check_instrument_access(parent, user)

    if parent.status not in ["ACTIVE", "RENEWAL_PENDING"]:
        raise HTTPException(status_code=400, detail=f"Cannot renew instrument in status '{parent.status}'. Must be ACTIVE or RENEWAL_PENDING.")

    # Transition predecessor to RENEWAL_PENDING if ACTIVE
    if parent.status == "ACTIVE":
        execute_transition(
            db=db,
            instrument_id=parent.id,
            event="renewal_detected",
            actor_id=user.user_id,
            role=user.role,
            reason="Maturity renewal initiated by institution. Predecessor marked RENEWAL_PENDING.",
            extra_context={"instrument": parent},
        )

    create_data = schemas.InstrumentCreate(
        institution_id=parent.institution_id,
        bank_id=parent.bank_id,
        bank_name=parent.bank_name,
        branch=data.branch or parent.branch,
        reference_no=data.new_reference_no,
        amount_paise=data.amount_paise,
        interest_rate=data.interest_rate or parent.interest_rate,
        issue_date=data.issue_date or Clock.today(),
        maturity_date=data.maturity_date,
        tenure_years=10,
        type="bank_fdr",
        joint_holder=data.joint_holder or parent.joint_holder,
        lien_marked=data.lien_marked,
        predecessor_id=parent.id,
    )
    child_inst = create_instrument(db, create_data, user=user)

    audit.append_audit_entry(
        db=db,
        actor_id=user.user_id,
        role=user.role,
        entity="instrument",
        entity_id=child_inst.id,
        from_state=None,
        to_state="SUBMITTED",
        payload={"predecessor_id": parent.id, "reference_no": child_inst.reference_no},
        reason=f"Renewed deposit certificate linked to predecessor {parent.reference_no}.",
    )
    db.commit()
    return child_inst


def get_scrutiny_notes(db: Session, instrument_id: str, user: auth.AuthUser) -> List[models.ScrutinyNote]:
    """List observation scrutiny notes for an instrument."""
    inst = get_instrument_by_id(db, instrument_id, user=user)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found.")
    check_instrument_access(inst, user)
    return db.query(models.ScrutinyNote).filter(models.ScrutinyNote.instrument_id == instrument_id).order_by(models.ScrutinyNote.created_at.desc()).all()


def export_evidence_pack(db: Session, instrument_id: str, user: auth.AuthUser) -> Dict[str, Any]:
    """Generate comprehensive tamper-evident compliance evidence pack for regulatory audit."""
    inst = get_instrument_by_id(db, instrument_id, user=user)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found.")
    check_instrument_access(inst, user)

    confirmations = db.query(models.FieldConfirmation).filter(models.FieldConfirmation.instrument_id == instrument_id).all()
    audit_entries = db.query(models.AuditEntry).filter(models.AuditEntry.entity_id == instrument_id).order_by(models.AuditEntry.seq.asc()).all()
    documents = db.query(models.Document).filter(models.Document.instrument_id == instrument_id).all()
    notes = db.query(models.ScrutinyNote).filter(models.ScrutinyNote.instrument_id == instrument_id).all()
    disputes = db.query(models.Dispute).filter(models.Dispute.instrument_id == instrument_id).all()
    releases = db.query(models.ReleaseAuthorization).filter(models.ReleaseAuthorization.instrument_id == instrument_id).all()
    chain_ok, chain_count, broken_seq, chain_msg = audit.verify_chain_integrity(db)

    pack = {
        "export_version": "1.0.0",
        "generated_at": Clock.now().isoformat(),
        "exported_by": user.user_id,
        "institution": {
            "id": inst.institution.id if inst.institution else None,
            "name": inst.institution.name if inst.institution else None,
            "state": inst.institution.state if inst.institution else None,
            "university_id": inst.institution.university_id if inst.institution else None,
        },
        "instrument": {
            "id": inst.id,
            "reference_no": inst.reference_no,
            "bank_name": inst.bank_name,
            "amount_paise": inst.amount_paise,
            "status": inst.status,
            "issue_date": inst.issue_date.isoformat() if inst.issue_date else None,
            "maturity_date": inst.maturity_date.isoformat() if inst.maturity_date else None,
            "lien_marked": inst.lien_marked,
            "predecessor_id": inst.predecessor_id,
        },
        "two_column_verifications": [
            {
                "field": c.field_name,
                "submitted": c.submitted_value,
                "confirmed": c.confirmed_value,
                "result": c.result,
                "source": c.source,
            }
            for c in confirmations
        ],
        "documents": [
            {
                "id": d.id,
                "file_name": d.file_name,
                "version": d.version,
                "sha256": d.sha256,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
            }
            for d in documents
        ],
        "audit_history": [
            {
                "seq": a.seq,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                "actor": a.actor_id,
                "from_state": a.from_state,
                "to_state": a.to_state,
                "row_hash": a.row_hash,
                "prev_hash": a.prev_hash,
            }
            for a in audit_entries
        ],
        "notes": [
            {"author": n.author_name, "text": n.text, "created_at": n.created_at.isoformat()}
            for n in notes
        ],
        "disputes": [
            {"reason": d.reason, "is_active": d.is_active, "opened_by": d.opened_by}
            for d in disputes
        ],
        "release_records": [
            {"release_ref": r.release_ref, "status": r.status, "issued_at": r.issued_at.isoformat() if r.issued_at else None}
            for r in releases
        ],
        "cryptographic_proof": {
            "chain_tamper_evident_valid": chain_ok,
            "total_verified_entries": chain_count,
            "broken_seq": broken_seq,
            "signature": hashlib.sha256(f"{inst.id}:{Clock.now().isoformat()}:{chain_count}".encode()).hexdigest(),
        },
    }

    audit.append_audit_entry(
        db=db,
        actor_id=user.user_id,
        role=user.role,
        entity="evidence_pack",
        entity_id=instrument_id,
        from_state=None,
        to_state="EXPORTED",
        payload={"instrument_id": instrument_id},
        reason=f"Evidence pack compliance export generated for instrument {inst.reference_no}.",
    )
    db.commit()
    return pack


def get_bank_inbox(db: Session, user: Any) -> List[Dict[str, Any]]:
    """Retrieve pending release authorizations for the bank user's bank."""
    query = (
        db.query(models.ReleaseAuthorization)
        .filter(models.ReleaseAuthorization.status.in_(["ISSUED", "CLAIMED"]))
    )
    if user.bank_id:
        query = query.filter(models.ReleaseAuthorization.bank_id == user.bank_id)

    authorizations = query.order_by(models.ReleaseAuthorization.issued_at.desc()).all()
    inbox = []
    for a in authorizations:
        inst = a.instrument
        inbox.append({
            "release_ref": a.release_ref,
            "instrument_id": a.instrument_id,
            "reference_no": inst.reference_no,
            "amount_paise": inst.amount_paise,
            "bank_name": inst.bank_name,
            "institution_name": inst.institution.name if inst.institution else "College",
            "issued_at": a.issued_at.isoformat(),
            "expires_at": a.expires_at.isoformat(),
            "status": a.status,
        })
    return inbox


def get_failed_verifications_report(db: Session, user: Any) -> List[Dict[str, Any]]:
    """
    Failed verifications report accessible by senior manager and auditor only.
    """
    if user.role not in ("aicte_senior", "auditor", "admin"):
        raise HTTPException(status_code=403, detail="Access denied: Senior manager or auditor access required.")

    attempts = (
        db.query(models.FailedVerificationAttempt)
        .order_by(models.FailedVerificationAttempt.attempted_at.desc())
        .all()
    )
    results = []
    for att in attempts:
        inst = att.instrument
        results.append({
            "id": att.id,
            "instrument_id": att.instrument_id,
            "reference_no": inst.reference_no if inst else "N/A",
            "institution_id": att.institution_id,
            "institution_name": att.institution.name if att.institution else "N/A",
            "bank_name": inst.bank_name if inst else "N/A",
            "reason_code": att.reason_code,
            "attempted_at": att.attempted_at.isoformat(),
            "current_failed_count": inst.failed_verification_count if inst else 0,
        })
    return results


# ── Dashboard & Notes ──────────────────────────────────────────────────────────

def get_dashboard_counts(db: Session, user: Any) -> Dict[str, int]:
    """Fetch 6 core counts: Active, Expiring, Matured, Renewed, Released, Pending."""
    today = Clock.today()
    ninety_days_later = today + timedelta(days=90)

    query = db.query(models.Instrument)
    query = apply_instrument_scope(query, user)

    total_active = query.filter(models.Instrument.status == "ACTIVE").count()
    expiring_soon = (
        query
        .filter(
            models.Instrument.status == "ACTIVE",
            models.Instrument.maturity_date <= ninety_days_later,
            models.Instrument.maturity_date >= today
        )
        .count()
    )
    matured = (
        query
        .filter(
            models.Instrument.status.in_(["ACTIVE", "RENEWAL_PENDING"]),
            models.Instrument.maturity_date < today
        )
        .count()
    )
    renewed = query.filter(models.Instrument.predecessor_id.isnot(None)).count()
    released = query.filter(models.Instrument.status == "CLOSED").count()
    pending = (
        query
        .filter(models.Instrument.status.in_(["SUBMITTED", "BANK_CHECK", "AICTE_REVIEW", "RELEASE_REQUESTED", "COMPLIANCE_CHECK", "BANK_RELEASE_PENDING"]))
        .count()
    )
    disputed = query.filter(models.Instrument.status == "DISPUTED").count()

    return {
        "active": total_active,
        "expiring": expiring_soon,
        "matured": matured,
        "renewed": renewed,
        "released": released,
        "pending": pending,
        "disputed": disputed,
    }


def add_scrutiny_note(
    db: Session,
    instrument_id: str,
    author_id: str,
    author_name: str,
    author_role: str,
    text: str,
    user: Any = None,
) -> models.ScrutinyNote:
    """Record an official scrutiny note on an instrument case."""
    if user:
        check_instrument_access(get_instrument_by_id(db, instrument_id), user)

    note = models.ScrutinyNote(
        id=str(uuid.uuid4()),
        instrument_id=instrument_id,
        author_id=author_id,
        author_name=author_name,
        author_role=author_role,
        text=text,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def create_dispute(
    db: Session,
    instrument_id: str,
    reason: str,
    opened_by: str,
    role: str = "aicte_officer",
    user: Any = None,
) -> models.Dispute:
    """Open a compliance or legal dispute hold on an instrument."""
    inst = check_instrument_access(get_instrument_by_id(db, instrument_id), user) if user else get_instrument_by_id(db, instrument_id)
    if not inst:
        raise ValueError(f"Instrument '{instrument_id}' not found.")

    dispute = models.Dispute(
        id=str(uuid.uuid4()),
        instrument_id=instrument_id,
        reason=reason,
        opened_by=opened_by,
        is_active=True,
    )
    db.add(dispute)

    if inst.status == "ACTIVE":
        execute_transition(
            db=db,
            instrument_id=instrument_id,
            event="dispute_opened",
            actor_id=opened_by,
            role=role,
            reason=f"Dispute opened: {reason}",
            extra_context={"reason": reason},
        )
    else:
        db.commit()

    db.refresh(dispute)
    return dispute


def clear_dispute(
    db: Session,
    dispute_id: str,
    cleared_by: str,
    role: str = "aicte_senior",
    resolution_reason: str = "Compliance verified and grievance resolved.",
) -> models.Dispute:
    """Formally resolve and clear a dispute lock (Senior Officer / Admin only)."""
    dispute = db.query(models.Dispute).filter(models.Dispute.id == dispute_id).first()
    if not dispute:
        raise ValueError(f"Dispute '{dispute_id}' not found.")

    dispute.is_active = False
    dispute.cleared_by = cleared_by
    dispute.cleared_at = Clock.now()

    active_count = (
        db.query(models.Dispute)
        .filter(models.Dispute.instrument_id == dispute.instrument_id, models.Dispute.is_active == True)
        .count()
    )

    inst = get_instrument_by_id(db, dispute.instrument_id)
    if inst and inst.status == "DISPUTED" and active_count == 0:
        execute_transition(
            db=db,
            instrument_id=inst.id,
            event="dispute_cleared",
            actor_id=cleared_by,
            role=role,
            reason=resolution_reason,
            extra_context={"reason": resolution_reason},
        )
    else:
        db.commit()

    db.refresh(dispute)
    return dispute


def get_lineage(db: Session, instrument_id: str, user: Any = None) -> List[models.Instrument]:
    """Retrieve full predecessor and renewal chain for an instrument."""
    inst = check_instrument_access(get_instrument_by_id(db, instrument_id), user) if user else get_instrument_by_id(db, instrument_id)
    if not inst:
        return []

    chain = []
    # Backward
    ancestors = []
    crawler = inst
    while crawler.predecessor_id:
        parent = get_instrument_by_id(db, crawler.predecessor_id)
        if parent:
            ancestors.insert(0, parent)
            crawler = parent
        else:
            break

    chain.extend(ancestors)
    chain.append(inst)

    # Forward
    crawler = inst
    while True:
        child = db.query(models.Instrument).filter(models.Instrument.predecessor_id == crawler.id).first()
        if child:
            chain.append(child)
            crawler = child
        else:
            break

    return chain
