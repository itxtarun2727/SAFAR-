"""
rules.py — Centralized configuration table service for AICTE regulatory parameters.
"""

import json
from typing import Any, Optional
from sqlalchemy.orm import Session
import uuid

from models import Rule
from clock import Clock

DEFAULT_RULES = [
    {
        "key": "deposit.tenure_years",
        "value": json.dumps(10),
        "clause_ref": "2024-27 Approval Process Handbook (10-Year Basis)",
    },
    {
        "key": "deposit.min_amount_paise",
        "value": json.dumps(150000000),  # Rs 15 Lakh
        "clause_ref": "APH Security Deposit Schedule — TODO(confirm)",
    },
    {
        "key": "deposit.max_amount_paise",
        "value": json.dumps(350000000),  # Rs 35 Lakh
        "clause_ref": "APH Security Deposit Schedule — TODO(confirm)",
    },
    {
        "key": "alert.threshold_days",
        "value": json.dumps([180, 90, 60, 30, 7, 0]),
        "clause_ref": "SIH Problem Statement 26265 §10 Alert Schedule",
    },
    {
        "key": "escalation.ladder_days",
        "value": json.dumps({
            "institution": 1,
            "regional_officer": 7,
            "senior_authority": 15,
            "bureau_head_auditor": 30
        }),
        "clause_ref": "SIH Problem Statement 26265 §10 Escalation Matrix",
    },
    {
        "key": "release.checklist_items",
        "value": json.dumps([
            {"id": "complaints_cleared", "label": "No Open Student / Faculty Grievances", "required": True},
            {"id": "faculty_salary_compliant", "label": "Faculty Salary Norms Cleared (7th CPC)", "required": True},
            {"id": "regional_noc", "label": "AICTE Regional Office Inspection NOC Issued", "required": True}
        ]),
        "clause_ref": "APH Clearance Norms for Security Deposit Discharge",
    },
]


def get_rule(db: Session, key: str, default: Any = None) -> Any:
    """Fetch parsed rule value for a given configuration key."""
    today = Clock.today()
    rule = (
        db.query(Rule)
        .filter(Rule.key == key, Rule.effective_from <= today)
        .order_by(Rule.effective_from.desc())
        .first()
    )
    if not rule:
        return default
    try:
        return json.loads(rule.value)
    except Exception:
        return rule.value


def set_rule(db: Session, key: str, value: Any, clause_ref: Optional[str] = None) -> Rule:
    """Update or insert a configuration rule with audit tracking."""
    serialized = json.dumps(value) if not isinstance(value, str) else value
    today = Clock.today()

    existing = (
        db.query(Rule)
        .filter(Rule.key == key, Rule.effective_from == today)
        .first()
    )

    if existing:
        existing.value = serialized
        if clause_ref:
            existing.clause_reference = clause_ref
        db.commit()
        db.refresh(existing)
        return existing

    new_rule = Rule(
        id=str(uuid.uuid4()),
        key=key,
        value=serialized,
        clause_reference=clause_ref,
        effective_from=today,
    )
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    return new_rule


def seed_default_rules(db: Session) -> None:
    """Idempotently seed standard rules if missing."""
    for item in DEFAULT_RULES:
        existing = db.query(Rule).filter(Rule.key == item["key"]).first()
        if not existing:
            rule = Rule(
                id=str(uuid.uuid4()),
                key=item["key"],
                value=item["value"],
                clause_reference=item["clause_ref"],
                effective_from=Clock.today(),
            )
            db.add(rule)
    db.commit()
