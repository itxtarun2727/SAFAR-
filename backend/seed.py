"""
seed.py — Synthetic Data Seeder for Evaluation Scenarios 1 to 6.

Populates initial rules, banks, universities, institutions, users, and instruments.
Safe and idempotent to run multiple times.
"""

from datetime import timedelta
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

    # 2. Seed Fictional Banks [SIMULATED]
    banks_data = [
        ("bank-001", "Demo Bank A", "DEMOA", "DEMOBANK_A"),
        ("bank-002", "Demo Bank B", "DEMOB", "DEMOBANK_B"),
        ("bank-003", "Demo Bank C", "DEMOC", "DEMOBANK_C"),
    ]
    for b_id, b_name, ifsc, code in banks_data:
        existing = db.query(models.Bank).filter(models.Bank.id == b_id).first()
        if not existing:
            db.add(models.Bank(
                id=b_id,
                name=b_name,
                ifsc_prefix=ifsc,
                code=code,
                created_at=Clock.now(),
            ))
    db.commit()

    # 3. Seed Universities
    universities_data = [
        ("univ-001", "Demo University A", "Delhi"),
        ("univ-002", "Demo University B", "Maharashtra"),
    ]
    for u_id, u_name, u_state in universities_data:
        existing = db.query(models.University).filter(models.University.id == u_id).first()
        if not existing:
            db.add(models.University(
                id=u_id,
                name=u_name,
                state=u_state,
                created_at=Clock.now(),
            ))
    db.commit()

    # 4. Seed Trusts
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

    # 5. Seed Institutions (3 colleges across the 2 universities)
    inst_specs = [
        ("inst-001", "1-102938471", "Delhi Institute of Technology", "trust-001", "univ-001", "Engineering", "Delhi", "director@dit.ac.in"),
        ("inst-002", "1-203948572", "Apex Engineering College", "trust-001", "univ-001", "Engineering", "Delhi", "registrar@apex.edu"),
        ("inst-003", "1-304958683", "Sunrise Institute of Technology", "trust-002", "univ-002", "Management", "Maharashtra", "contact@sunrise.ac.in"),
    ]

    for i_id, aicte_id, name, trust_id, univ_id, cat, st, em in inst_specs:
        existing = db.query(models.Institution).filter(models.Institution.id == i_id).first()
        if not existing:
            inst = models.Institution(
                id=i_id,
                aicte_id=aicte_id,
                name=name,
                trust_id=trust_id,
                university_id=univ_id,
                category=cat,
                state=st,
                email=em,
                phone="011-23456789",
            )
            db.add(inst)
        else:
            existing.university_id = univ_id
            existing.state = st
    db.commit()

    # 6. Seed Users
    users_data = [
        ("u-aicte-01", "priya", "Priya Sharma", "aicte_officer", None, "univ-001", None),
        ("u-aicte-02", "rajan", "Rajan Mehta", "aicte_officer", None, "univ-002", None),
        ("u-aicte-sr-01", "anita", "Dr. Anita Rao", "aicte_senior", None, None, None),
        ("u-bank-01", "bank_a", "Demo Bank A Officer [SIMULATED]", "bank_checker", None, None, "bank-001"),
        ("u-bank-02", "bank_b", "Demo Bank B Officer [SIMULATED]", "bank_checker", None, None, "bank-002"),
        ("u-bank-03", "bank_c", "Demo Bank C Officer [SIMULATED]", "bank_checker", None, None, "bank-003"),
        ("u-inst-01", "inst_user", "Greenfield / DIT Admin", "institution", "inst-001", "univ-001", None),
        ("u-inst-02", "inst_apex", "Apex College Admin", "institution", "inst-002", "univ-001", None),
        ("u-inst-03", "inst_sunrise", "Sunrise Tech Admin", "institution", "inst-003", "univ-002", None),
        ("u-auditor-01", "auditor", "Audit Observer", "auditor", None, None, None),
        ("u-admin-01", "admin", "Portal Admin", "admin", None, None, None),
    ]

    for uid, uname, fullname, role, inst_id, univ_id, b_id in users_data:
        existing_u = db.query(models.User).filter(models.User.id == uid).first()
        if not existing_u:
            db.add(models.User(
                id=uid,
                username=uname,
                name=fullname,
                role=role,
                institution_id=inst_id,
                university_id=univ_id,
                bank_id=b_id,
                created_at=Clock.now(),
            ))
        else:
            existing_u.university_id = univ_id
            existing_u.bank_id = b_id
            existing_u.institution_id = inst_id
    db.commit()

    today = Clock.today()

    # 7. Seed Official Evaluation Scenarios
    # Scenario 1: New Submission Draft / Submitted (Delhi Institute)
    if not db.query(models.Instrument).filter(models.Instrument.id == "fdr-scenario-1").first():
        fdr1 = models.Instrument(
            id="fdr-scenario-1",
            institution_id="inst-001",
            bank_id="bank-001",
            type="bank_fdr",
            bank_name="Demo Bank A",
            branch="Connaught Place, New Delhi",
            reference_no="DEMOA00112233",
            amount_paise=200000000,  # 20 Lakh
            issue_date=today - timedelta(days=5),
            maturity_date=today + timedelta(days=365 * 10 - 5),
            tenure_years=10,
            status="SUBMITTED",
            current_stage="NORMAL",
            joint_holder="AICTE & Delhi Institute of Technology",
            lien_marked=False,
            failed_verification_count=0,
        )
        db.add(fdr1)

    # Scenario 2: Discrepancy Mismatch -> NEEDS_CORRECTION (Apex College)
    if not db.query(models.Instrument).filter(models.Instrument.id == "fdr-scenario-2").first():
        fdr2 = models.Instrument(
            id="fdr-scenario-2",
            institution_id="inst-002",
            bank_id="bank-002",
            type="bank_fdr",
            bank_name="Demo Bank B",
            branch="Nehru Place, New Delhi",
            reference_no="DEMOB00918273",
            amount_paise=150000000,  # 15 Lakh
            issue_date=today - timedelta(days=365),
            maturity_date=today + timedelta(days=365 * 9),  # Submitted: 10 years
            tenure_years=10,
            status="NEEDS_CORRECTION",
            current_stage="NORMAL",
            joint_holder="AICTE & Apex College",
            lien_marked=True,
            failed_verification_count=1,
        )
        db.add(fdr2)
        db.flush()

        db.add(models.FieldConfirmation(
            id=str(uuid.uuid4()),
            instrument_id=fdr2.id,
            field_name="maturity_date",
            submitted_value=(today + timedelta(days=365 * 9)).isoformat(),
            confirmed_value=(today + timedelta(days=365 * 4)).isoformat(),  # Bank record shows 5 years
            source="bank_console",
            result="mismatch",
            reason_code="MATURITY_MISMATCH",
            confirmed_by="Demo Bank B Checker [SIMULATED]",
            confirmed_at=Clock.now(),
        ))
        db.add(models.FailedVerificationAttempt(
            id=str(uuid.uuid4()),
            instrument_id=fdr2.id,
            institution_id="inst-002",
            reason_code="MATURITY_MISMATCH",
            attempted_at=Clock.now(),
        ))

    # Scenario 3: Valid Active FDR (Delhi Institute)
    if not db.query(models.Instrument).filter(models.Instrument.id == "fdr-scenario-3").first():
        fdr3 = models.Instrument(
            id="fdr-scenario-3",
            institution_id="inst-001",
            bank_id="bank-001",
            type="bank_fdr",
            bank_name="Demo Bank A",
            branch="Parliament Street, New Delhi",
            reference_no="DEMOA00269910",
            amount_paise=250000000,  # 25 Lakh
            issue_date=today - timedelta(days=365 * 2),
            maturity_date=today + timedelta(days=365 * 8),
            tenure_years=10,
            status="ACTIVE",
            current_stage="NORMAL",
            joint_holder="AICTE & Principal, Delhi Institute of Technology",
            lien_marked=True,
            failed_verification_count=0,
        )
        db.add(fdr3)
        db.flush()

        for f, v in [
            ("reference_no", "DEMOA00269910"),
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
                confirmed_by="Demo Bank A Checker [SIMULATED]",
                confirmed_at=Clock.now(),
            ))

    # Scenario 4: Approaching Maturity in ~30 Days (Sunrise Institute)
    if not db.query(models.Instrument).filter(models.Instrument.id == "fdr-scenario-4").first():
        fdr4 = models.Instrument(
            id="fdr-scenario-4",
            institution_id="inst-003",
            bank_id="bank-003",
            type="bank_fdr",
            bank_name="Demo Bank C",
            branch="FC Road, Pune",
            reference_no="DEMOC00771239",
            amount_paise=200000000,
            issue_date=today - timedelta(days=365 * 10 - 30),
            maturity_date=today + timedelta(days=30),  # Exactly 30 days left
            tenure_years=10,
            status="ACTIVE",
            current_stage="30D",
            joint_holder="AICTE & Sunrise Institute",
            lien_marked=True,
            failed_verification_count=0,
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

    # Scenario 5: Matured FDR Ready for Release (Delhi Institute)
    if not db.query(models.Instrument).filter(models.Instrument.id == "fdr-scenario-5").first():
        fdr5 = models.Instrument(
            id="fdr-scenario-5",
            institution_id="inst-001",
            bank_id="bank-001",
            type="bank_fdr",
            bank_name="Demo Bank A",
            branch="Dwarka, New Delhi",
            reference_no="DEMOA00554433",
            amount_paise=300000000,  # 30 Lakh
            issue_date=today - timedelta(days=365 * 10 + 10),
            maturity_date=today - timedelta(days=10),  # Matured 10 days ago!
            tenure_years=10,
            status="ACTIVE",
            current_stage="DUE_TODAY",
            joint_holder="AICTE & Delhi Institute of Technology",
            lien_marked=True,
            failed_verification_count=0,
        )
        db.add(fdr5)

    # Scenario 6: Disputed Matured Release Candidate (Sunrise Institute)
    if not db.query(models.Instrument).filter(models.Instrument.id == "fdr-scenario-6").first():
        fdr6 = models.Instrument(
            id="fdr-scenario-6",
            institution_id="inst-003",
            bank_id="bank-003",
            type="bank_fdr",
            bank_name="Demo Bank C",
            branch="Nariman Point, Mumbai",
            reference_no="DEMOC00441188",
            amount_paise=350000000,
            issue_date=today - timedelta(days=365 * 10),
            maturity_date=today - timedelta(days=15),  # Already matured 15 days ago
            tenure_years=10,
            status="DISPUTED",
            current_stage="OVERDUE",
            joint_holder="AICTE & Sunrise Institute",
            lien_marked=True,
            failed_verification_count=0,
        )
        db.add(fdr6)
        db.flush()

        db.add(models.Dispute(
            id=str(uuid.uuid4()),
            instrument_id=fdr6.id,
            reason="Unresolved faculty 7th CPC unpaid salary grievance under AICTE Regulation Clause 14.8",
            opened_by="u-aicte-02",
            opened_at=Clock.now(),
            is_active=True,
        ))

    # 7. Seed Sample Document Artifacts on Startup (Ephemerally Safe)
    import hashlib
    for fdr_id in ["fdr-scenario-1", "fdr-scenario-2", "fdr-scenario-3", "fdr-scenario-4", "fdr-scenario-5", "fdr-scenario-6"]:
        existing_doc = db.query(models.Document).filter(models.Document.instrument_id == fdr_id).first()
        if not existing_doc:
            inst_obj = db.query(models.Instrument).filter(models.Instrument.id == fdr_id).first()
            if inst_obj:
                sample_pdf_bytes = (
                    f"%PDF-1.4\n1 0 obj << /Title (AICTE Joint FDR Deposit Certificate - {inst_obj.reference_no}) >> endobj\n"
                    f"SIMULATED Bank Certificate: {inst_obj.bank_name}\n"
                    f"Joint Custody: {inst_obj.joint_holder}\n"
                    f"Principal: Rs. {inst_obj.amount_paise / 100:.2f} Paise: {inst_obj.amount_paise}\n"
                ).encode("utf-8")
                digest = hashlib.sha256(sample_pdf_bytes).hexdigest()
                sample_doc = models.Document(
                    id=str(uuid.uuid4()),
                    instrument_id=inst_obj.id,
                    version=1,
                    file_name=f"{inst_obj.reference_no}_certificate.pdf",
                    file_type="application/pdf",
                    file_size=len(sample_pdf_bytes),
                    sha256=digest,
                    storage_key=f"db://documents/{inst_obj.id}/{inst_obj.reference_no}_certificate.pdf",
                    file_data=sample_pdf_bytes,
                    uploaded_by="u-aicte-01",
                    uploaded_at=Clock.now(),
                )
                db.add(sample_doc)
    db.commit()

    # 8. Genesis Audit Entry
    if db.query(models.AuditEntry).count() == 0:
        audit.append_audit_entry(
            db=db,
            actor_id="system",
            role="system",
            entity="system",
            entity_id="genesis",
            from_state=None,
            to_state="READY",
            payload={"action": "seed_database", "app": "SAFAR Portal", "banks": 3, "universities": 2},
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
