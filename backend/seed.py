"""
seed.py — Synthetic Data Seeder for Evaluation Scenarios 1 to 6.

Populates initial trusts, institutions, reference rules, and instruments.
Safe and idempotent to run multiple times.
"""

from datetime import date, timedelta
from sqlalchemy.orm import Session
import uuid

import models
from database import SessionLocal, engine, Base
import rules
import audit
from clock import Clock


def seed_all(db: Session) -> None:
    """Populate full synthetic demonstration database."""
    Base.metadata.create_all(bind=engine)

    # 1. Seed Rules
    rules.seed_default_rules(db)

    # 2. Seed Trusts
    t1 = db.query(models.Trust).filter(models.Trust.id == "trust-001").first()
    if not t1:
        t1 = models.Trust(
            id="trust-001",
            name="Bharatiya Technical Education Trust",
            registration_no="REG-DL-2010-8812",
            state="Delhi",
        )
        db.add(t1)

    t2 = db.query(models.Trust).filter(models.Trust.id == "trust-002").first()
    if not t2:
        t2 = models.Trust(
            id="trust-002",
            name="Universal Shiksha Prasar Society",
            registration_no="REG-MH-2014-4190",
            state="Maharashtra",
        )
        db.add(t2)
    db.commit()

    # 3. Seed Institutions
    inst_specs = [
        ("inst-001", "1-102938471", "Delhi Institute of Technology", "trust-001", "Engineering", "Delhi", "director@dit.ac.in"),
        ("inst-002", "1-203948572", "Apex Engineering College", "trust-001", "Engineering", "Delhi", "registrar@apex.edu"),
        ("inst-003", "1-304958683", "Sunrise Institute of Technology", "trust-002", "Management", "Maharashtra", "contact@sunrise.ac.in"),
        ("inst-004", "1-405968794", "National Polytechnic Institute", "trust-002", "Polytechnic", "Haryana", "principal@npi.edu.in"),
    ]

    for i_id, aicte_id, name, trust_id, cat, st, em in inst_specs:
        existing = db.query(models.Institution).filter(models.Institution.id == i_id).first()
        if not existing:
            inst = models.Institution(
                id=i_id,
                aicte_id=aicte_id,
                name=name,
                trust_id=trust_id,
                category=cat,
                state=st,
                email=em,
                phone="011-23456789",
            )
            db.add(inst)
    db.commit()

    today = Clock.today()

    # 4. Seed Official Evaluation Scenarios
    # Scenario 3: Valid Active FDR (Delhi Institute)
    if not db.query(models.Instrument).filter(models.Instrument.reference_no == "SBIN00269910").first():
        fdr3 = models.Instrument(
            id="fdr-scenario-3",
            institution_id="inst-001",
            type="bank_fdr",
            bank_name="State Bank of India",
            branch="Parliament Street, New Delhi",
            reference_no="SBIN00269910",
            amount_paise=250000000,  # 25 Lakh
            issue_date=today - timedelta(days=365 * 2),
            maturity_date=today + timedelta(days=365 * 8),
            tenure_years=10,
            status="ACTIVE",
            current_stage="NORMAL",
            joint_holder="AICTE & Principal, Delhi Institute of Technology",
            lien_marked=True,
        )
        db.add(fdr3)
        db.flush()

        # Add match confirmations
        for f, v in [
            ("reference_no", "SBIN00269910"),
            ("amount_paise", "250000000"),
            ("maturity_date", (today + timedelta(days=365 * 8)).isoformat()),
            ("lien_marked", "True"),
        ]:
            db.add(models.FieldConfirmation(
                id=str(uuid.uuid4()),
                instrument_id=fdr3.id,
                field_name=f,
                submitted_value=v,
                confirmed_value=v,
                source="bank_console",
                result="match",
                confirmed_by="Bank Checker [SIMULATED]",
                confirmed_at=Clock.now(),
            ))

    # Scenario 2: Discrepancy Mismatch (Apex College)
    if not db.query(models.Instrument).filter(models.Instrument.reference_no == "HDFC00918273").first():
        fdr2 = models.Instrument(
            id="fdr-scenario-2",
            institution_id="inst-002",
            type="bank_fdr",
            bank_name="HDFC Bank",
            branch="Connaught Place, New Delhi",
            reference_no="HDFC00918273",
            amount_paise=150000000,
            issue_date=today - timedelta(days=365),
            maturity_date=today + timedelta(days=365 * 9),  # Submitted: 10 years
            tenure_years=10,
            status="REJECTED",
            joint_holder="AICTE & Apex College",
            lien_marked=True,
        )
        db.add(fdr2)
        db.flush()

        db.add(models.FieldConfirmation(
            id=str(uuid.uuid4()),
            instrument_id=fdr2.id,
            field_name="maturity_date",
            submitted_value=(today + timedelta(days=365 * 9)).isoformat(),
            confirmed_value=(today + timedelta(days=365 * 4)).isoformat(),  # Bank says 5 years!
            source="bank_console",
            result="mismatch",
            reason_code="MATURITY_MISMATCH",
            confirmed_by="Bank Checker [SIMULATED]",
            confirmed_at=Clock.now(),
        ))

    # Scenario 4: Approaching Maturity in ~30 Days (National Polytechnic)
    if not db.query(models.Instrument).filter(models.Instrument.reference_no == "BARB00771239").first():
        fdr4 = models.Instrument(
            id="fdr-scenario-4",
            institution_id="inst-004",
            type="bank_fdr",
            bank_name="Bank of Baroda",
            branch="Civil Lines, Gurgaon",
            reference_no="BARB00771239",
            amount_paise=200000000,
            issue_date=today - timedelta(days=365 * 10 - 30),
            maturity_date=today + timedelta(days=30),  # Exactly 30 days left!
            tenure_years=10,
            status="ACTIVE",
            current_stage="30D",
            joint_holder="AICTE & National Polytechnic",
            lien_marked=True,
        )
        db.add(fdr4)
        db.flush()

        db.add(models.Alert(
            id=str(uuid.uuid4()),
            instrument_id=fdr4.id,
            stage="30D",
            channel="in_app",
            due_at=fdr4.maturity_date,
            sent_at=Clock.now(),
        ))

    # Scenario 6: Disputed Matured Release Candidate (Sunrise Institute)
    if not db.query(models.Instrument).filter(models.Instrument.reference_no == "ICIC00441188").first():
        fdr6 = models.Instrument(
            id="fdr-scenario-6",
            institution_id="inst-003",
            type="bank_fdr",
            bank_name="ICICI Bank",
            branch="Nariman Point, Mumbai",
            reference_no="ICIC00441188",
            amount_paise=350000000,
            issue_date=today - timedelta(days=365 * 10),
            maturity_date=today - timedelta(days=15),  # Already matured 15 days ago
            tenure_years=10,
            status="DISPUTED",
            current_stage="OVERDUE",
            joint_holder="AICTE & Sunrise Institute",
            lien_marked=True,
        )
        db.add(fdr6)
        db.flush()

        # Add active dispute
        db.add(models.Dispute(
            id=str(uuid.uuid4()),
            instrument_id=fdr6.id,
            reason="Unresolved faculty 7th CPC unpaid salary grievance under AICTE Regulation Clause 14.8",
            opened_by="u-aicte-01",
            opened_at=Clock.now(),
            is_active=True,
        ))

    # 5. Genesis Audit Entry
    if db.query(models.AuditEntry).count() == 0:
        audit.append_audit_entry(
            db=db,
            actor_id="system",
            role="system",
            entity="system",
            entity_id="genesis",
            from_state=None,
            to_state="READY",
            payload={"action": "seed_database", "app": "SAFAR Portal"},
            reason="Initial synthetic database seeding for SIH 26265 evaluation.",
        )

    db.commit()
    print("Database seeding completed successfully.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()
