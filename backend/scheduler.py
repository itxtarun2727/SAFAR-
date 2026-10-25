"""
scheduler.py — Idempotent Daily Alert & Escalation Engine.

RULES:
- Scans active deposits against maturity thresholds (180, 90, 60, 30, 7, 0, overdue).
- Idempotent: UNIQUE (instrument_id, stage, channel) guarantees no duplicate spam.
- Picks the largest threshold crossed if runs are missed (catch-up guarantee).
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
import uuid

import models
from clock import Clock
import rules

ALERT_THRESHOLDS = [180, 90, 60, 30, 7, 0]


def determine_stage(days_left: int) -> str:
    """Return stage label based on remaining days to maturity."""
    if days_left < 0:
        return "OVERDUE"
    elif days_left == 0:
        return "DUE_TODAY"
    elif days_left <= 7:
        return "7D"
    elif days_left <= 30:
        return "30D"
    elif days_left <= 60:
        return "60D"
    elif days_left <= 90:
        return "90D"
    elif days_left <= 180:
        return "180D"
    return "NORMAL"


def run_daily_alert_job(db: Session) -> Dict[str, Any]:
    """
    Evaluates all active/renewal-pending instruments and dispatches alerts idempotently.
    """
    today = Clock.today()
    instruments = (
        db.query(models.Instrument)
        .filter(models.Instrument.status.in_(["ACTIVE", "RENEWAL_PENDING"]))
        .all()
    )

    alerts_created = 0
    stages_updated = 0

    for inst in instruments:
        days_left = (inst.maturity_date - today).days
        stage = determine_stage(days_left)

        if stage != "NORMAL":
            if inst.current_stage != stage:
                inst.current_stage = stage
                stages_updated += 1

            # Check if alert already sent for this (instrument, stage, channel)
            existing_alert = (
                db.query(models.Alert)
                .filter(
                    models.Alert.instrument_id == inst.id,
                    models.Alert.stage == stage,
                    models.Alert.channel == "in_app"
                )
                .first()
            )

            if not existing_alert:
                new_alert = models.Alert(
                    id=str(uuid.uuid4()),
                    instrument_id=inst.id,
                    stage=stage,
                    channel="in_app",
                    due_at=inst.maturity_date,
                    sent_at=Clock.now(),
                )
                db.add(new_alert)
                alerts_created += 1

    db.commit()

    return {
        "status": "success",
        "evaluated_instruments": len(instruments),
        "alerts_created": alerts_created,
        "stages_updated": stages_updated,
        "simulated_date": today.isoformat(),
    }
