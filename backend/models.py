"""
models.py — SQLAlchemy ORM models for all SAFAR domain entities.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, BigInteger, Date, DateTime, Boolean, Text,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship

from database import Base
from clock import Clock


class Trust(Base):
    """Sponsoring Trust or Society body."""
    __tablename__ = "trusts"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    registration_no = Column(String(120), nullable=True)
    state = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=Clock.now)

    institutions = relationship("Institution", back_populates="trust")


class Institution(Base):
    """Technical institution registered with AICTE."""
    __tablename__ = "institutions"

    id = Column(String(64), primary_key=True)
    aicte_id = Column(String(64), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    trust_id = Column(String(64), ForeignKey("trusts.id"), nullable=True)
    category = Column(String(100), nullable=True)  # Engineering, Management, Pharmacy, Polytechnic
    state = Column(String(100), nullable=False)
    email = Column(String(120), nullable=False)
    phone = Column(String(30), nullable=True)
    created_at = Column(DateTime, default=Clock.now)

    trust = relationship("Trust", back_populates="institutions")
    instruments = relationship("Instrument", back_populates="institution")


class Instrument(Base):
    """Fixed Deposit Receipt (FDR) or Bank Guarantee regulatory deposit."""
    __tablename__ = "instruments"

    id = Column(String(64), primary_key=True)
    institution_id = Column(String(64), ForeignKey("institutions.id"), nullable=False)
    type = Column(String(30), default="bank_fdr")  # bank_fdr | online_deposit
    bank_name = Column(String(120), nullable=False)
    branch = Column(String(120), nullable=True)
    reference_no = Column(String(120), nullable=False)  # FDR Number
    amount_paise = Column(BigInteger, nullable=False)  # Stored in integer paise (e.g. 1500000_00 = 15 Lakh)
    interest_rate = Column(String(20), nullable=True)
    issue_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False)
    tenure_years = Column(Integer, default=10)
    status = Column(String(50), nullable=False, default="SUBMITTED")
    current_stage = Column(String(50), nullable=True)  # 180D, 90D, 60D, 30D, 7D, DUE_TODAY, OVERDUE
    predecessor_id = Column(String(64), ForeignKey("instruments.id"), nullable=True)  # Renewal lineage
    joint_holder = Column(String(255), nullable=True)  # e.g. "AICTE and Principal / Trust"
    lien_marked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=Clock.now)
    updated_at = Column(DateTime, default=Clock.now, onupdate=Clock.now)

    institution = relationship("Institution", back_populates="instruments")
    confirmations = relationship("FieldConfirmation", back_populates="instrument")
    documents = relationship("Document", back_populates="instrument")
    alerts = relationship("Alert", back_populates="instrument")
    release_requests = relationship("ReleaseRequest", back_populates="instrument")
    notes = relationship("ScrutinyNote", back_populates="instrument")
    disputes = relationship("Dispute", back_populates="instrument")


class FieldConfirmation(Base):
    """Two-Column Trust: submitted institution values vs confirmed bank values."""
    __tablename__ = "field_confirmations"

    id = Column(String(64), primary_key=True)
    instrument_id = Column(String(64), ForeignKey("instruments.id"), nullable=False)
    field_name = Column(String(60), nullable=False)  # reference_no, amount, maturity_date, lien_marked
    submitted_value = Column(String(255), nullable=True)
    confirmed_value = Column(String(255), nullable=True)
    source = Column(String(40), default="bank_console")  # bank_console | bank_file | manual
    confirmed_by = Column(String(120), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    result = Column(String(40), default="pending")  # match | mismatch | pending | source_unavailable | manual_review
    reason_code = Column(String(60), nullable=True)  # MATURITY_MISMATCH, AMOUNT_MISMATCH, LIEN_MISSING, NOT_FOUND

    instrument = relationship("Instrument", back_populates="confirmations")


class Document(Base):
    """Uploaded deposit scan certificate or bank confirmation letter."""
    __tablename__ = "documents"

    id = Column(String(64), primary_key=True)
    instrument_id = Column(String(64), ForeignKey("instruments.id"), nullable=False)
    version = Column(Integer, default=1)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(60), default="application/pdf")
    file_size = Column(Integer, nullable=True)
    sha256 = Column(String(64), nullable=False)  # Document tamper-evidence digest
    storage_key = Column(String(255), nullable=False)
    uploaded_by = Column(String(120), nullable=False)
    uploaded_at = Column(DateTime, default=Clock.now)

    instrument = relationship("Instrument", back_populates="documents")


class Alert(Base):
    """Maturity alerts and unacknowledged escalation notices."""
    __tablename__ = "alerts"

    id = Column(String(64), primary_key=True)
    instrument_id = Column(String(64), ForeignKey("instruments.id"), nullable=False)
    stage = Column(String(40), nullable=False)  # 180D, 90D, 60D, 30D, 7D, DUE_TODAY, OVERDUE
    channel = Column(String(30), default="in_app")  # in_app | email | sms
    due_at = Column(Date, nullable=False)
    sent_at = Column(DateTime, default=Clock.now)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(120), nullable=True)

    __table_args__ = (
        UniqueConstraint("instrument_id", "stage", "channel", name="uq_instrument_stage_channel"),
    )

    instrument = relationship("Instrument", back_populates="alerts")


class ReleaseRequest(Base):
    """FDR release and encashment governance workflow."""
    __tablename__ = "release_requests"

    id = Column(String(64), primary_key=True)
    instrument_id = Column(String(64), ForeignKey("instruments.id"), nullable=False)
    kind = Column(String(30), default="release")  # release | refund | closure
    checklist_json = Column(Text, nullable=True)  # JSON checklist of clearance verifications
    maker_id = Column(String(120), nullable=True)
    checker_id = Column(String(120), nullable=True)
    decision = Column(String(40), default="PENDING")  # PENDING | APPROVED | REJECTED
    reason = Column(Text, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    bank_confirmed_at = Column(DateTime, nullable=True)

    instrument = relationship("Instrument", back_populates="release_requests")


class ScrutinyNote(Base):
    """Case observations and scrutiny history recorded by officers."""
    __tablename__ = "scrutiny_notes"

    id = Column(String(64), primary_key=True)
    instrument_id = Column(String(64), ForeignKey("instruments.id"), nullable=False)
    author_id = Column(String(120), nullable=False)
    author_name = Column(String(120), nullable=False)
    author_role = Column(String(60), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=Clock.now)

    instrument = relationship("Instrument", back_populates="notes")


class Dispute(Base):
    """Dispute or hold lock that prevents premature deposit release."""
    __tablename__ = "disputes"

    id = Column(String(64), primary_key=True)
    instrument_id = Column(String(64), ForeignKey("instruments.id"), nullable=False)
    reason = Column(Text, nullable=False)
    opened_by = Column(String(120), nullable=False)
    opened_at = Column(DateTime, default=Clock.now)
    cleared_by = Column(String(120), nullable=True)
    cleared_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    instrument = relationship("Instrument", back_populates="disputes")


class Rule(Base):
    """Centralized rules table externalizing tenures, amounts, and checklists."""
    __tablename__ = "rules"

    id = Column(String(64), primary_key=True)
    key = Column(String(120), nullable=False)
    value = Column(Text, nullable=False)  # JSON-serialized value
    clause_reference = Column(String(255), nullable=True)
    effective_from = Column(Date, default=Clock.today)
    created_at = Column(DateTime, default=Clock.now)

    __table_args__ = (
        UniqueConstraint("key", "effective_from", name="uq_rule_key_effective"),
    )


class AuditEntry(Base):
    """Append-only cryptographic SHA-256 hash-chained event ledger."""
    __tablename__ = "audit_entries"

    seq = Column(Integer, primary_key=True, autoincrement=True)
    actor_id = Column(String(120), nullable=False)
    role = Column(String(60), nullable=False)
    entity = Column(String(60), nullable=False)
    entity_id = Column(String(64), nullable=True)
    from_state = Column(String(60), nullable=True)
    to_state = Column(String(60), nullable=True)
    payload_hash = Column(String(64), nullable=False)
    prev_hash = Column(String(64), nullable=False)
    row_hash = Column(String(64), nullable=False)
    reason = Column(Text, nullable=True)
    at = Column(DateTime, default=Clock.now)
