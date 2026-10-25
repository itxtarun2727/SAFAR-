"""
test_audit.py — Unit tests for cryptographic SHA-256 hash chaining.
"""

import sys
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import audit
from database import Base
import models


@pytest.fixture
def test_db():
    """In-memory SQLite database session for unit testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_canonical_json_deterministic():
    """Different key orders must produce identical canonical JSON strings."""
    d1 = {"z": 1, "a": 2, "m": {"b": 3, "a": 4}}
    d2 = {"a": 2, "z": 1, "m": {"a": 4, "b": 3}}
    assert audit.canonical_json(d1) == audit.canonical_json(d2)


def test_append_and_verify_chain(test_db):
    """Appending 3 entries forms a valid cryptographic hash chain."""
    audit.append_audit_entry(
        db=test_db,
        actor_id="u-01",
        role="aicte_officer",
        entity="instrument",
        entity_id="fdr-1",
        from_state="SUBMITTED",
        to_state="BANK_CHECK",
        reason="Initial bank dispatch",
    )
    audit.append_audit_entry(
        db=test_db,
        actor_id="u-bank",
        role="bank_checker",
        entity="instrument",
        entity_id="fdr-1",
        from_state="BANK_CHECK",
        to_state="ACTIVE",
        reason="Bank confirmation confirmed",
    )
    test_db.commit()

    ok, count, broken_seq, msg = audit.verify_chain_integrity(test_db)
    assert ok is True
    assert count == 2
    assert broken_seq is None


def test_tamper_fails_integrity(test_db):
    """Altering any payload or hash in an existing audit row MUST fail integrity check."""
    audit.append_audit_entry(
        db=test_db,
        actor_id="u-01",
        role="officer",
        entity="instrument",
        entity_id="fdr-1",
        from_state="SUBMITTED",
        to_state="ACTIVE",
        reason="Original reason",
    )
    test_db.commit()

    # Tamper the entry directly
    entry = test_db.query(models.AuditEntry).first()
    entry.reason = "TAMPERED_FRAUDULENT_EDIT"
    test_db.commit()

    ok, count, broken_seq, msg = audit.verify_chain_integrity(test_db)
    assert ok is False
    assert broken_seq == entry.seq
    assert "Tamper detected" in msg
