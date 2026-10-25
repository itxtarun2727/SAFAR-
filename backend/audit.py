"""
audit.py — Append-only Cryptographic SHA-256 Hash Chained Audit Service.

Provides tamper-evident event logging and chain integrity verification.
Section 63(4) BSA 2023 evidentiary readiness.
"""

import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from models import AuditEntry
from clock import Clock

GENESIS_HASH = "0" * 64


def canonical_json(data: Any) -> str:
    """Deterministic JSON serializer with sorted keys and no whitespace."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def compute_payload_hash(payload: Any) -> str:
    """Return SHA-256 hex digest of serialized payload."""
    raw = canonical_json(payload)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_row_hash(prev_hash: str, entry_dict: Dict[str, Any]) -> str:
    """Compute row hash = SHA-256(prev_hash || canonical_json(entry_dict))."""
    serialized = canonical_json(entry_dict)
    combined = f"{prev_hash}|{serialized}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def format_timestamp(dt: Any) -> str:
    """Standardized UTC timestamp formatting for hash stability."""
    if isinstance(dt, datetime):
        # Format as UTC without local tz discrepancy
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(dt) if dt else ""


def append_audit_entry(
    db: Session,
    actor_id: str,
    role: str,
    entity: str,
    entity_id: str,
    from_state: Optional[str] = None,
    to_state: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    reason: Optional[str] = None,
) -> AuditEntry:
    """
    Append an immutable, hash-chained record in the current DB transaction.
    Must be called whenever an entity changes state.
    """
    if payload is None:
        payload = {}

    # 1. Fetch previous row's hash
    last_entry = db.query(AuditEntry).order_by(AuditEntry.seq.desc()).first()
    prev_hash = last_entry.row_hash if last_entry else GENESIS_HASH

    payload_hash = compute_payload_hash(payload)
    now_dt = Clock.now()

    # 2. Build entry dict for hashing
    hash_data = {
        "actor_id": actor_id,
        "role": role,
        "entity": entity,
        "entity_id": str(entity_id),
        "from_state": from_state,
        "to_state": to_state,
        "payload_hash": payload_hash,
        "prev_hash": prev_hash,
        "reason": reason,
        "at": format_timestamp(now_dt),
    }

    row_hash = compute_row_hash(prev_hash, hash_data)

    entry = AuditEntry(
        actor_id=actor_id,
        role=role,
        entity=entity,
        entity_id=str(entity_id),
        from_state=from_state,
        to_state=to_state,
        payload_hash=payload_hash,
        prev_hash=prev_hash,
        row_hash=row_hash,
        reason=reason,
        at=now_dt,
    )

    db.add(entry)
    db.flush()
    return entry


def verify_chain_integrity(db: Session) -> Tuple[bool, int, Optional[int], str]:
    """
    Recalculates every SHA-256 hash in sequence from genesis to head.
    Returns: (is_valid, total_entries, first_broken_seq, message)
    """
    entries = db.query(AuditEntry).order_by(AuditEntry.seq.asc()).all()
    if not entries:
        return True, 0, None, "Audit chain is empty. Genesis valid."

    prev_hash = GENESIS_HASH

    for entry in entries:
        # Check linkage
        if entry.prev_hash != prev_hash:
            return (
                False,
                len(entries),
                entry.seq,
                f"Broken chain at sequence {entry.seq}: prev_hash mismatch."
            )

        # Recalculate row hash
        hash_data = {
            "actor_id": entry.actor_id,
            "role": entry.role,
            "entity": entry.entity,
            "entity_id": entry.entity_id,
            "from_state": entry.from_state,
            "to_state": entry.to_state,
            "payload_hash": entry.payload_hash,
            "prev_hash": entry.prev_hash,
            "reason": entry.reason,
            "at": format_timestamp(entry.at),
        }
        expected_hash = compute_row_hash(prev_hash, hash_data)

        if entry.row_hash != expected_hash:
            return (
                False,
                len(entries),
                entry.seq,
                f"Tamper detected at sequence {entry.seq}: row hash verification failed!"
            )

        prev_hash = entry.row_hash

    return True, len(entries), None, "Cryptographic audit chain is 100% intact and verified."


def simulate_tamper(db: Session, target_seq: Optional[int] = None) -> int:
    """
    Demo utility for SIH evaluators:
    Deliberately alters an audit row in the DB to prove the verifier catches tampering.
    """
    if target_seq:
        entry = db.query(AuditEntry).filter(AuditEntry.seq == target_seq).first()
    else:
        entry = db.query(AuditEntry).order_by(AuditEntry.seq.desc()).first()

    if not entry:
        raise ValueError("No audit entries available to tamper.")

    entry.reason = "TAMPERED_BY_SIMULATOR_DEMO"
    entry.payload_hash = "f" * 64
    db.commit()
    return entry.seq


def repair_chain(db: Session) -> int:
    """
    Demo recovery utility:
    Recomputes cryptographic row hashes and links across all entries
    to restore ledger verification after demonstrating tampering.
    """
    entries = db.query(AuditEntry).order_by(AuditEntry.seq.asc()).all()
    prev_hash = GENESIS_HASH
    for entry in entries:
        entry.prev_hash = prev_hash
        hash_data = {
            "actor_id": entry.actor_id,
            "role": entry.role,
            "entity": entry.entity,
            "entity_id": entry.entity_id,
            "from_state": entry.from_state,
            "to_state": entry.to_state,
            "payload_hash": entry.payload_hash,
            "prev_hash": prev_hash,
            "reason": entry.reason,
            "at": format_timestamp(entry.at),
        }
        entry.row_hash = compute_row_hash(prev_hash, hash_data)
        prev_hash = entry.row_hash

    db.commit()
    return len(entries)

