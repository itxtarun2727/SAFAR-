"""
crud.py — Data Access Layer.

RULES:
- Pure queries only.
- All instrument state changes MUST delegate to workflow.transition() and
  append an audit log entry in the same transaction.
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
import uuid
import json

import models
import schemas
import workflow
import audit
from clock import Clock


def get_institutions(db: Session, skip: int = 0, limit: int = 50) -> List[models.Institution]:
    """List institutions."""
    return db.query(models.Institution).offset(skip).limit(limit).all()


def get_institution_by_id(db: Session, institution_id: str) -> Optional[models.Institution]:
    """Retrieve institution by primary key."""
    return db.query(models.Institution).filter(models.Institution.id == institution_id).first()


def get_instruments(
    db: Session,
    institution_id: Optional[str] = None,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.Instrument]:
    """Filter and retrieve instruments."""
    query = db.query(models.Instrument)
    if institution_id:
        query = query.filter(models.Instrument.institution_id == institution_id)
    if status:
        query = query.filter(models.Instrument.status == status)
    if stage:
        query = query.filter(models.Instrument.current_stage == stage)
    return query.order_by(models.Instrument.maturity_date.asc()).offset(skip).limit(limit).all()


def get_instrument_by_id(db: Session, instrument_id: str) -> Optional[models.Instrument]:
    """Retrieve instrument by ID with related records."""
    return db.query(models.Instrument).filter(models.Instrument.id == instrument_id).first()


def get_instrument_by_reference(db: Session, reference_no: str) -> Optional[models.Instrument]:
    """Retrieve instrument by unique reference FDR number."""
    return db.query(models.Instrument).filter(models.Instrument.reference_no == reference_no).first()


def create_instrument(
    db: Session,
    data: schemas.InstrumentCreate,
    actor_id: str,
    role: str
) -> models.Instrument:
    """Register a new FDR submission and create genesis audit record."""
    instrument_id = f"inst-{str(uuid.uuid4())[:8]}"
    instrument = models.Instrument(
        id=instrument_id,
        institution_id=data.institution_id,
        bank_name=data.bank_name,
        branch=data.branch,
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
    )
    db.add(instrument)
    db.flush()

    # Create initial unconfirmed field checks
    for field_name, submitted_val in [
        ("reference_no", data.reference_no),
        ("bank_name", data.bank_name),
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

    # Append Genesis Audit Entry
    audit.append_audit_entry(
        db=db,
        actor_id=actor_id,
        role=role,
        entity="instrument",
        entity_id=instrument.id,
        from_state=None,
        to_state="SUBMITTED",
        payload={"reference_no": data.reference_no, "amount": data.amount_paise},
        reason="Initial FDR regulatory submission by institution.",
    )

    db.commit()
    db.refresh(instrument)
    return instrument


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
    instrument = get_instrument_by_id(db, instrument_id)
    if not instrument:
        raise ValueError(f"Instrument '{instrument_id}' not found.")

    # Check active disputes if any
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


def get_dashboard_counts(db: Session) -> Dict[str, int]:
    """Fetch the six core counts for dashboard StatCards."""
    today = Clock.today()
    from datetime import timedelta
    ninety_days_later = today + timedelta(days=90)

    total_active = db.query(models.Instrument).filter(models.Instrument.status == "ACTIVE").count()
    expiring_soon = (
        db.query(models.Instrument)
        .filter(
            models.Instrument.status == "ACTIVE",
            models.Instrument.maturity_date <= ninety_days_later,
            models.Instrument.maturity_date >= today
        )
        .count()
    )
    matured = (
        db.query(models.Instrument)
        .filter(
            models.Instrument.status.in_(["ACTIVE", "RENEWAL_PENDING"]),
            models.Instrument.maturity_date < today
        )
        .count()
    )
    renewed = db.query(models.Instrument).filter(models.Instrument.predecessor_id.isnot(None)).count()
    released = db.query(models.Instrument).filter(models.Instrument.status == "CLOSED").count()
    pending = (
        db.query(models.Instrument)
        .filter(models.Instrument.status.in_(["SUBMITTED", "BANK_CHECK", "RELEASE_REQUESTED", "COMPLIANCE_CHECK"]))
        .count()
    )

    return {
        "active": total_active,
        "expiring": expiring_soon,
        "matured": matured,
        "renewed": renewed,
        "released": released,
        "pending": pending,
    }


def add_scrutiny_note(
    db: Session,
    instrument_id: str,
    author_id: str,
    author_name: str,
    author_role: str,
    text: str,
) -> models.ScrutinyNote:
    """Record an official scrutiny note on an instrument case."""
    note = models.ScrutinyNote(
        id=str(uuid.uuid4()),
        instrument_id=instrument_id,
        author_id=author_id,
        author_name=author_name,
        author_role=author_role,
        text=text,
        created_at=Clock.now(),
    )
    db.add(note)
    audit.append_audit_entry(
        db=db,
        actor_id=author_id,
        role=author_role,
        entity="instrument",
        entity_id=instrument_id,
        payload={"note_id": note.id, "preview": text[:50]},
        reason="Officer recorded scrutiny observation note.",
    )
    db.commit()
    db.refresh(note)
    return note


def create_dispute(
    db: Session,
    instrument_id: str,
    reason: str,
    opened_by: str,
    role: str = "aicte_officer",
) -> models.Dispute:
    """Open an official dispute or compliance hold, locking deposit release."""
    instrument = get_instrument_by_id(db, instrument_id)
    if not instrument:
        raise ValueError(f"Instrument '{instrument_id}' not found.")

    dispute = models.Dispute(
        id=str(uuid.uuid4()),
        instrument_id=instrument_id,
        reason=reason,
        opened_by=opened_by,
        opened_at=Clock.now(),
        is_active=True,
    )
    db.add(dispute)

    # Transition to DISPUTED if currently ACTIVE
    if instrument.status == "ACTIVE":
        execute_transition(
            db=db,
            instrument_id=instrument_id,
            event="dispute_opened",
            actor_id=opened_by,
            role=role,
            reason=f"Dispute opened: {reason}",
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
    resolution_reason: str = "Dispute resolved and compliance verified.",
) -> models.Dispute:
    """Formally resolve and clear a dispute lock."""
    dispute = db.query(models.Dispute).filter(models.Dispute.id == dispute_id).first()
    if not dispute:
        raise ValueError(f"Dispute '{dispute_id}' not found.")

    dispute.is_active = False
    dispute.cleared_by = cleared_by
    dispute.cleared_at = Clock.now()

    # Check if any remaining active disputes on this instrument
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
        )
    else:
        db.commit()

    db.refresh(dispute)
    return dispute


def create_release_request(
    db: Session,
    instrument_id: str,
    kind: str,
    reason: Optional[str],
    checklist: Optional[Dict[str, bool]],
    maker_id: str,
    role: str = "aicte_officer",
) -> models.ReleaseRequest:
    """Submit an FDR release request."""
    inst = get_instrument_by_id(db, instrument_id)
    if not inst:
        raise ValueError(f"Instrument '{instrument_id}' not found.")

    rel = models.ReleaseRequest(
        id=str(uuid.uuid4()),
        instrument_id=instrument_id,
        kind=kind or "release",
        checklist_json=json.dumps(checklist) if checklist else "{}",
        maker_id=maker_id,
        decision="PENDING",
        reason=reason,
    )
    db.add(rel)

    # Transition instrument status from ACTIVE to RELEASE_REQUESTED
    if inst.status == "ACTIVE":
        execute_transition(
            db=db,
            instrument_id=instrument_id,
            event="release_requested",
            actor_id=maker_id,
            role=role,
            reason=reason or "Institution initiated deposit release request.",
            extra_context={"checklist": checklist or {}},
        )
    else:
        db.commit()

    db.refresh(rel)
    return rel


def get_lineage(db: Session, instrument_id: str) -> List[models.Instrument]:
    """Retrieve full predecessor and renewal chain for an instrument."""
    chain = []
    curr = get_instrument_by_id(db, instrument_id)
    if not curr:
        return []

    # Trace backwards to original genesis instrument
    ancestors = []
    crawler = curr
    while crawler.predecessor_id:
        parent = get_instrument_by_id(db, crawler.predecessor_id)
        if parent:
            ancestors.insert(0, parent)
            crawler = parent
        else:
            break

    chain.extend(ancestors)
    chain.append(curr)

    # Trace forwards to any successors
    crawler = curr
    while True:
        child = db.query(models.Instrument).filter(models.Instrument.predecessor_id == crawler.id).first()
        if child:
            chain.append(child)
            crawler = child
        else:
            break

    return chain

