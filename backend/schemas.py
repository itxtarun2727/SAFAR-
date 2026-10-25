"""
schemas.py — Pydantic validation and serialization models for SAFAR API.
Modernized for Pydantic v2 using ConfigDict(from_attributes=True).
"""

from datetime import date, datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


# ── Auth & Identity ────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    user_id: str
    role: str
    name: str
    institution_ids: List[str] = []


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


# ── Institutions & Trusts ──────────────────────────────────────────────────────

class TrustResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    registration_no: Optional[str] = None
    state: Optional[str] = None


class InstitutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    aicte_id: str
    name: str
    trust_id: Optional[str] = None
    category: Optional[str] = None
    state: str
    email: str
    phone: Optional[str] = None


# ── Instruments (FDRs) ─────────────────────────────────────────────────────────

class InstrumentCreate(BaseModel):
    institution_id: str
    bank_name: str
    branch: Optional[str] = None
    reference_no: str
    amount_paise: int = Field(gt=0, description="Amount in paise (e.g. Rs 25,00,000 = 250000000)")
    interest_rate: Optional[str] = None
    issue_date: date
    maturity_date: date
    tenure_years: int = Field(ge=1, le=20, default=10)
    type: str = "bank_fdr"
    joint_holder: Optional[str] = "AICTE and Society / Trust"
    lien_marked: bool = False
    predecessor_id: Optional[str] = None


class FieldConfirmationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    field_name: str
    submitted_value: Optional[str] = None
    confirmed_value: Optional[str] = None
    source: str
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    result: str
    reason_code: Optional[str] = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_name: str
    file_type: str
    file_size: Optional[int] = None
    sha256: str
    uploaded_by: str
    uploaded_at: datetime


class InstrumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    type: str
    bank_name: str
    branch: Optional[str] = None
    reference_no: str
    amount_paise: int
    interest_rate: Optional[str] = None
    issue_date: date
    maturity_date: date
    tenure_years: int
    status: str
    current_stage: Optional[str] = None
    predecessor_id: Optional[str] = None
    joint_holder: Optional[str] = None
    lien_marked: bool
    created_at: datetime
    updated_at: datetime


# ── Scrutiny Notes & Disputes ──────────────────────────────────────────────────

class ScrutinyNoteCreate(BaseModel):
    text: str


class ScrutinyNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    instrument_id: str
    author_id: str
    author_name: str
    author_role: str
    text: str
    created_at: datetime


class DisputeCreate(BaseModel):
    reason: str


class DisputeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    instrument_id: str
    reason: str
    opened_by: str
    opened_at: datetime
    cleared_by: Optional[str] = None
    cleared_at: Optional[datetime] = None
    is_active: bool


# ── Release ────────────────────────────────────────────────────────────────────

class ReleaseCreate(BaseModel):
    kind: str = "release"
    reason: Optional[str] = None
    checklist: Optional[Dict[str, bool]] = None


class ReleaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    instrument_id: str
    kind: str
    checklist_json: Optional[str] = None
    maker_id: Optional[str] = None
    checker_id: Optional[str] = None
    decision: str
    reason: Optional[str] = None
    decided_at: Optional[datetime] = None
    bank_confirmed_at: Optional[datetime] = None


class InstrumentDetailResponse(InstrumentResponse):
    institution: Optional[InstitutionResponse] = None
    confirmations: List[FieldConfirmationResponse] = []
    documents: List[DocumentResponse] = []
    notes: List[ScrutinyNoteResponse] = []
    disputes: List[DisputeResponse] = []
    release_requests: List[ReleaseResponse] = []


# ── Workflow & Transitions ─────────────────────────────────────────────────────

class TransitionRequest(BaseModel):
    event: str
    reason: Optional[str] = None
    payload: Optional[dict] = None


# ── Alerts ─────────────────────────────────────────────────────────────────────

class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    instrument_id: str
    stage: str
    channel: str
    due_at: date
    sent_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


# ── Rules ──────────────────────────────────────────────────────────────────────

class RuleCreate(BaseModel):
    key: str
    value: str
    clause_reference: Optional[str] = None
    effective_from: Optional[date] = None


class RuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    key: str
    value: str
    clause_reference: Optional[str] = None
    effective_from: date
    created_at: datetime


# ── Audit ──────────────────────────────────────────────────────────────────────

class AuditEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq: int
    actor_id: str
    role: str
    entity: str
    entity_id: Optional[str] = None
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    payload_hash: str
    prev_hash: str
    row_hash: str
    reason: Optional[str] = None
    at: datetime


class ChainVerificationResult(BaseModel):
    ok: bool
    total_entries: int
    first_broken_seq: Optional[int] = None
    message: str
