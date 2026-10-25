# 🏛️ SAFAR — Smart AICTE FDR Automation & Registry
### *A Sovereign, Double-Verified, Tamper-Evident Regulatory Compliance Portal*

[![SIH 2024](https://img.shields.io/badge/SIH-Problem%20Statement%2026265-orange?style=for-the-badge&logo=gov.uk)](https://www.sih.gov.in/)
[![AICTE Regulation Bureau](https://img.shields.io/badge/Ministry-AICTE%20Regulation%20Bureau-blue?style=for-the-badge)](https://www.aicte-india.org/)
[![Team: Code Blooded](https://img.shields.io/badge/Team-Code%20Blooded-red?style=for-the-badge)](https://github.com/itxtarun2727/SAFAR-)
[![Python 3.11+](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.11-darkgreen?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![PostgreSQL 16](https://img.shields.io/badge/Database-PostgreSQL%2016-336791?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

---

> [!IMPORTANT]
> ### ⚠️ Mandatory Regulatory & Simulation Disclosure
> **Bank confirmation in SAFAR is SIMULATED.**  
> In compliance with the SIH 26265 problem brief and RBI cybersecurity guidelines:
> 1. No live Indian banking systems (SFMS, Core Banking Systems, or RBI gateways) are connected to this prototype.
> 2. All bank confirmations, API endpoints, Straight-Through Processing (STP), and batch reconciliation feeds are executed using isolated, deterministic mock adapters (`backend/adapters.py`).
> 3. Zero real funds or live bank deposits are touched. Every mock response and ledger confirmation is explicitly stamped with `[SIMULATED]`.

---

## 📌 Executive Summary

Under the All India Council for Technical Education (AICTE) Approval Process Handbook (APH), thousands of technical universities, engineering colleges, and management institutes across India are legally mandated to maintain **Security Deposits** (ranging from ₹15 Lakhs to ₹50 Lakhs per course) in the form of **Fixed Deposit Receipts (FDRs)** or **Bank Guarantees (BGs)** registered under joint title with AICTE for 8 to 10 years.

Historically, manual spreadsheet tracking and paper certificates have led to:
- ❌ **Matured or Expired FDRs:** Billions of rupees in government security deposits maturing without timely renewal or notice.
- ❌ **Missing Joint Liens:** Colleges opening single-name FDRs without AICTE's mandatory joint lien, allowing unilateral premature encashment.
- ❌ **Physical Certificate Loss & Discrepancies:** Paper receipts mismatching actual bank records.
- ❌ **Premature Release Collusion:** Lack of maker-checker separation allowing unauthorized fund release.

**SAFAR** (Smart AICTE FDR Automation & Registry) solves this with a **sovereign GovTech platform** combining **Two-Column Trust Reconciliation**, **Deterministic Finite State Machine (FSM) Guards**, **Cryptographic SHA-256 Hash Chaining**, and an **Idempotent Stage-Gate Scheduler**.

---

## 🌟 Key Features & Innovations

```
                                  ┌────────────────────────┐
                                  │   COLLEGE SUBMISSION   │
                                  └───────────┬────────────┘
                                              │
                         ┌────────────────────▼────────────────────┐
                         │      TWO-COLUMN TRUST RECONCILIATION    │
                         │   (College Record  vs  Bank Record)     │
                         └────────────────────┬────────────────────┘
                                              │
                         ┌────────────────────▼────────────────────┐
                         │     DETERMINISTIC FSM WORKFLOW          │
                         │   • Maker != Checker Separation         │
                         │   • Dispute & Faculty Salary Locks      │
                         │   • 4-Point Clearance Checklist         │
                         └────────────────────┬────────────────────┘
                                              │
                         ┌────────────────────▼────────────────────┐
                         │   SHA-256 HASH-CHAINED AUDIT LEDGER     │
                         │   (Immutable, Live Tamper Verifier)     │
                         └────────────────────┬────────────────────┘
                                              │
                         ┌────────────────────▼────────────────────┐
                         │   STAGE-GATE COUNTDOWN & DEMO CLOCK     │
                         │   (180D ➔ 90D ➔ 60D ➔ 30D ➔ Overdue)    │
                         └─────────────────────────────────────────┘
```

### 1. 🛡️ Two-Column Trust Reconciliation
Never trust a paper receipt or single source. SAFAR captures institutional submissions in **Column 1** and pairs them side-by-side with bank-confirmed records in **Column 2** within the `FieldConfirmation` table. Both records must match before an instrument is marked `ACTIVE`.

### 2. ⚙️ Deterministic FSM State Machine (Single Source of Truth)
No direct SQL updates to status. All 14 lifecycle transitions are evaluated through a pure transition function in `backend/workflow.py`:
- **Maker-Checker Separation (`guard_maker_differs_from_checker`):** The officer who reviews an FDR cannot approve its release.
- **Dispute Locking (`guard_no_open_dispute`):** Active student grievances, court stays, or faculty salary disputes (Clause 14.8) mathematically lock the release pipeline.
- **Clearance Checklist (`guard_checklist_cleared`):** Pre-release requires verified clearances (No-Dues, Course Closure, Affiliation Check).

### 3. 🔗 Cryptographically Chained Audit Ledger
Every state transition, officer note, dispute, and release sign-off appends a SHA-256 hash-chained entry to `AuditEntry`:
$$\text{Hash}_n = \text{SHA-256}\Big(\text{Seq}_n \parallel \text{Timestamp}_n \parallel \text{Hash}_{n-1} \parallel \text{CanonicalJSON}(\text{Payload}_n)\Big)$$
- **Live Verifier:** `GET /audit/verify` audits the full chain from sequence 1 to head in milliseconds.
- **Tamper Simulation Tool:** `POST /audit/simulate-tamper` allows evaluators to maliciously edit an old database record and watch the verifier catch the exact altered row. Click `POST /audit/repair` to restore validity.

### 4. 📢 Idempotent Stage-Gate Scheduler
An automated daily job monitors maturity dates and assigns countdown stages:
$$\text{Stages: } \mathbf{180D} \longrightarrow \mathbf{90D} \longrightarrow \mathbf{60D} \longrightarrow \mathbf{30D} \longrightarrow \mathbf{7D} \longrightarrow \mathbf{DUE\_TODAY} \longrightarrow \mathbf{OVERDUE}$$
Because it is **idempotent**, running the scheduler 1 time or 100 times on the same day produces the exact same clean state without duplicate alert spam.

### 5. ⏰ Time-Travel Demo Clock
Evaluators don't have months to wait for an FDR to mature. The demo clock (`POST /clock/advance?days=90`) allows judges to fast-forward system time on demand, demonstrating alert triggers and maturity transitions in real time.

---

## 📚 Complete Engineering Documentation Suite

The repository includes a comprehensive 5-document technical suite:

| Document | Link | Key Contents |
|---|---|---|
| **System Overview & Quickstart** | [README.md](file:///d:/SIH'26/SAFAR/README.md) | Problem brief, architecture summary, quickstart guide, personas, scenarios. |
| **System Architecture** | [ARCHITECTURE.md](file:///d:/SIH'26/SAFAR/ARCHITECTURE.md) | C4 Component Model, Two-Column Trust data flow, FSM lifecycle & guards, database ER schema. |
| **Project Memory & Context** | [MEMORY.md](file:///d:/SIH'26/SAFAR/MEMORY.md) | Team Code Blooded memory, AICTE rules, non-negotiables, persona roster, changelog. |
| **Security & Threat Model** | [SECURITY.md](file:///d:/SIH'26/SAFAR/SECURITY.md) | STRIDE threat model, SHA-256 hash-chain specification, RBAC matrix, tamper detection. |
| **REST API Reference** | [API.md](file:///d:/SIH'26/SAFAR/API.md) | Complete OpenAPI specification for all 20+ endpoints, status codes, and request bodies. |

---

## 📂 Repository File Layout

```text
SAFAR-SIH26265/
├── README.md                  # Front-door documentation & evaluator guide
├── ARCHITECTURE.md            # C4 model, ER diagrams & state machine specification
├── MEMORY.md                  # Project memory, AICTE rules & persona roster
├── SECURITY.md                # STRIDE threat model, SHA-256 hash chain & RBAC
├── API.md                     # REST API reference documentation
├── .gitignore                 # Standard Python, Node, SQLite & secret ignore rules
├── .cursorrules               # Full SAFAR project brief & flat backend layout rules
├── .env.example               # Config template (PostgreSQL, JWT, Demo Clock)
├── .env                       # Local active environment variables (ignored by git)
├── docker-compose.yml         # Container orchestration (PostgreSQL 16, Backend)
├── render.yaml                # Cloud deployment blueprint
├── docs/                      # Original challenge PDFs, DESIGN.md & system prompts
│
├── backend/
│   ├── main.py                # FastAPI entrypoint, REST routers & /health
│   ├── database.py            # SQLAlchemy session, engine & dotenv auto-loader
│   ├── models.py              # 11 Domain models (Trust, Institution, Instrument, etc.)
│   ├── schemas.py             # Pydantic v2 validation & response contracts
│   ├── crud.py                # Data access queries & atomic state transaction dispatch
│   ├── workflow.py            # FSM transition table + guards (Single source of truth)
│   ├── audit.py               # SHA-256 hash-chaining, tamper detection & repair
│   ├── scheduler.py           # Daily idempotent stage-gate alert calculations
│   ├── clock.py               # Settable demo clock for evaluator time-travel
│   ├── rules.py               # Regulatory rules table (norms, amounts, alert thresholds)
│   ├── adapters.py            # Bank interface, SIMULATED mock & SFMS file feed
│   ├── auth.py                # JWT auth, demo user roster & RBAC guards
│   ├── seed.py                # Synthetic institutional seeding & demo scenarios
│   ├── walkthrough.py         # Automated API tour & educational test runner
│   ├── tests/                 # 17 automated unit & integration tests
│   │   ├── test_api.py        # REST endpoint tests
│   │   ├── test_workflow.py   # State transitions & guard enforcement
│   │   ├── test_audit.py      # Cryptographic hash-chain & tamper detection
│   │   └── test_alerts.py     # Scheduler alert calculations & idempotency
│   ├── requirements.txt       # Pinned Python dependencies
│   └── Dockerfile             # Container definition for Python 3.11
│
└── frontend/                  # React + Vite frontend dashboard
    ├── src/                   # React components and styling
    ├── package.json           # Frontend dependencies
    └── vite.config.js         # Vite configuration
```

---

## 🚀 Quickstart & Setup Guide

### Option 1: Docker PostgreSQL Setup (Active & Recommended)

SAFAR is configured to run against PostgreSQL 16 on Docker port **`5433`**:

```bash
# 1. Run PostgreSQL in Docker
docker run --name safar_postgres -e POSTGRES_USER=safar -e POSTGRES_PASSWORD=safar_password -e POSTGRES_DB=safar_db -p 5433:5432 -d postgres:16-alpine

# 2. Seed the database with AICTE colleges and demo test scenarios
cd backend
python seed.py

# 3. Start the FastAPI backend server
uvicorn main:app --reload --port 8000
```

*(Note: If Docker is not running, SAFAR automatically falls back to local `sqlite:///./safar.db` with zero configuration needed).*

---

### Option 2: Running Automated Tests & Interactive Tour

```bash
cd backend

# Run the full 17-test suite (API, Workflow, Audit, Alerts)
pytest

# Run the automated interactive API tour (prints colored step-by-step results)
python walkthrough.py
```

---

## 🌐 Live Interactive API Documentation (Swagger UI)

With `uvicorn` running, open **http://localhost:8000/** in your browser:
- It automatically redirects to **http://localhost:8000/docs** (Swagger UI).
- Interactive OpenAPI console with "Try it out" buttons for every endpoint.
- Alternative ReDoc available at **http://localhost:8000/redoc**.

---

## 👥 Evaluator Personas & Pre-Programmed Scenarios

### Demo User Personas (`POST /auth/login`)
All demo users share the standard password: **`demo1234`**

| Username | Role | Persona Description | Key Permissions |
|---|---|---|---|
| **`priya`** | `aicte_officer` | Priya Sharma (AICTE Maker) | Reviews submissions, triggers bank checks, records scrutiny notes |
| **`rajan`** | `aicte_officer` | Rajan Mehta (AICTE Maker 2) | Alternative officer for dual-maker workflows |
| **`anita`** | `aicte_senior` | Dr. Anita Rao (AICTE Checker) | Approves deposit releases, clears disputes, authorizes renewals |
| **`bank_maker`** | `bank_officer` | Bank Officer [SIMULATED] | Enters mock confirmation data into simulated console |
| **`bank_checker`**| `bank_checker`| Bank Checker [SIMULATED] | Signs off on bank confirmations and confirms lien status |
| **`inst_user`** | `institution` | Greenfield Admin | Views college FDRs, uploads certificates, requests release |
| **`auditor`** | `auditor` | Audit Observer | Read-only verification of cryptographic hash-chain ledger |
| **`admin`** | `admin` | Portal Administrator | Updates regulatory norms (`rules` table) and maintenance |

---

### 🧪 Pre-Programmed Test Scenarios (Pre-Seeded in Database)

The database comes pre-seeded with 4 realistic cases:

```
┌─────────────────┬──────────────────────────────────┬──────────────┬──────────────┬───────────────────────────────┐
│ Reference No.   │ Institution                      │ Amount       │ Initial State│ Test Scenario Goal            │
├─────────────────┼──────────────────────────────────┼──────────────┼──────────────┼───────────────────────────────┤
│ SBIN00269910    │ Greenfield Inst. of Technology   │ ₹25,00,000   │ SUBMITTED    │ Happy path: Bank match ➔ ACTIVE│
│ HDFC00918273    │ Apex College of Engineering      │ ₹15,00,000   │ SUBMITTED    │ Fraud test: Date mismatch ➔ REJ│
│ BARB00771239    │ Sunrise College of Pharmacy      │ ₹20,00,000   │ ACTIVE       │ Stage-gate: Matures in 30 days │
│ ICIC00441188    │ National Inst. of Architecture   │ ₹35,00,000   │ DISPUTED     │ Guard test: Active salary hold│
└─────────────────┴──────────────────────────────────┴──────────────┴──────────────┴───────────────────────────────┘
```

1. **`SBIN00269910` (Happy Path Verification):**
   - Call `POST /instruments/{id}/verify-bank`.
   - Result: Matches bank records. Status transitions to `ACTIVE` with `lien_marked = true`.
2. **`HDFC00918273` (Maturity Date Mismatch):**
   - College submitted 10-year tenure (2033), but bank records confirm 5-year tenure (2028).
   - Call `POST /instruments/{id}/verify-bank`.
   - Result: Two-Column discrepancy detected. Automatically transitions to `REJECTED`.
3. **`BARB00771239` (Stage-Gate 30D Window):**
   - Matures within 30 days.
   - Evaluator advances clock by 90 days (`POST /clock/advance?days=90`).
   - Result: Scheduler automatically flags the FDR as `OVERDUE` and dispatches alerts.
4. **`ICIC00441188` (`fdr-scenario-6`, Disputed Release Candidate):**
   - Blocked by an unresolved faculty 7th CPC unpaid salary grievance under AICTE Clause 14.8.
   - Call `POST /instruments/fdr-scenario-6/transition` with `event: approve`.
   - Result: Returns `400 Bad Request` ("Release is blocked: an active dispute is open").
   - Call `POST /disputes/{id}/clear` as Dr. Anita Rao to resolve the grievance.
   - Result: Dispute cleared; release pipeline unlocks!

---

## 🛡️ Security, Cryptography & Compliance

- **Immutable Ledger:** Powered by SHA-256 hash chaining in `backend/audit.py`.
- **Zero SQL Injection:** 100% parameterized SQLAlchemy ORM queries.
- **Strict Role Scoping:** Colleges can only view their own instruments via institutional scoping.
- **Live Ledger Verification:** Run `GET /audit/verify` at any time to verify mathematical chain integrity.
- **Tamper Resistance Demonstration:**
  1. Call `POST /audit/simulate-tamper` to alter a historical database row.
  2. Call `GET /audit/verify` → The verifier immediately flags: `"Tamper detected at sequence N: row hash verification failed!"`.
  3. Call `POST /audit/repair` to restore valid hashes.

---

## 🏆 SIH Team & Project Credentials

- **Event:** Smart India Hackathon (SIH 2024 / 2026)
- **Problem Statement:** 26265 — *"Streamline of security deposit / FDR portal"*
- **Ministry / Body:** All India Council for Technical Education (AICTE Regulation Bureau)
- **Category:** Smart Automation (Software)
- **Team Name:** Code Blooded
- **Repository:** [https://github.com/itxtarun2727/SAFAR-](https://github.com/itxtarun2727/SAFAR-)

*All synthetic institutional entities, simulated banking responses, and mock certificates are engineered for regulatory demonstration purposes.*
