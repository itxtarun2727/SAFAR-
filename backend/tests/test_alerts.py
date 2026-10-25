"""
test_alerts.py — Unit tests for alert threshold calculations and idempotency.
"""

import sys
import os
import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import scheduler
from database import Base
import models


def test_determine_stage_thresholds():
    """Verify correct alert chips mapped from days remaining."""
    assert scheduler.determine_stage(200) == "NORMAL"
    assert scheduler.determine_stage(180) == "180D"
    assert scheduler.determine_stage(85) == "90D"
    assert scheduler.determine_stage(55) == "60D"
    assert scheduler.determine_stage(25) == "30D"
    assert scheduler.determine_stage(5) == "7D"
    assert scheduler.determine_stage(0) == "DUE_TODAY"
    assert scheduler.determine_stage(-3) == "OVERDUE"


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_idempotent_alert_job(test_db):
    """Running the alert job multiple times must never create duplicate alert entries."""
    today = date.today()
    inst = models.Instrument(
        id="fdr-test-alert",
        institution_id="inst-01",
        bank_name="Test Bank",
        reference_no="TEST999",
        amount_paise=150000000,
        issue_date=today - timedelta(days=3650),
        maturity_date=today + timedelta(days=20),  # In 30D stage
        status="ACTIVE",
    )
    test_db.add(inst)
    test_db.commit()

    # Run 1
    res1 = scheduler.run_daily_alert_job(test_db)
    assert res1["alerts_created"] == 1

    # Run 2 on same day -> must create 0 new alerts!
    res2 = scheduler.run_daily_alert_job(test_db)
    assert res2["alerts_created"] == 0

    total_alerts = test_db.query(models.Alert).filter(models.Alert.instrument_id == inst.id).count()
    assert total_alerts == 1
