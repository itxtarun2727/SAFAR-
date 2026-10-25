# SAFAR — Project Memory & Context
**Smart India Hackathon (SIH Problem Statement 26265)**  
*AICTE Regulation Bureau — Smart Automation (Software)*  
**Team:** Code Blooded  
**Product Name:** SAFAR (Smart AICTE FDR Automation & Registry)

---

## 1. Project Background & Objective

AICTE regulates thousands of technical colleges across India. Under the AICTE Approval Process Handbook (APH), every institution must maintain a security deposit (via Fixed Deposit Receipts or Bank Guarantees) in joint title with AICTE for 8 to 10 years.

### The Operational Challenge:
- FDRs mature and slip past renewal dates unnoticed.
- Single-name FDRs are issued without AICTE's mandatory joint lien.
- Physical certificate loss, tracking discrepancies, and fraud risks.
- Lack of an immutable audit trail when funds are released or renewed.

### SAFAR Solution:
SAFAR provides an automated, tamper-evident regulatory registry that enforces maker-checker approvals, side-by-side bank reconciliation, stage-gate renewal countdowns, and cryptographic hash-chaining.

---

## 2. Non-Negotiable Engineering Rules

1. **Mandatory Simulation Notice:**  
   No live Indian banking systems (SFMS, Core Banking Systems, RBI gateways) are connected. All bank confirmations are deterministic mocks in `backend/adapters.py` explicitly labeled `[SIMULATED]`.
2. **Never Invent Rules or Statistics:**  
   Amounts, tenure norms, and clause references come from AICTE norms or are stored in the database `rules` table with default placeholders.
3. **Flat Backend Monolith:**  
   The backend layout is strictly flat (`backend/*.py`), not a multi-layered nested module hierarchy.
4. **FSM as Single Source of Truth:**  
   No direct SQL `UPDATE` to `instrument.status`. All lifecycle changes must pass through `workflow.transition()`.
5. **Maker-Checker Separation:**  
   The officer who creates, verifies, or initiates an action cannot approve it. Guard `guard_maker_differs_from_checker` blocks single-person approvals.
6. **No Release with Open Disputes:**  
   Active faculty salary disputes (Clause 14.8), legal holds, or compliance investigations lock release transitions.
7. **Append-Only Cryptographic Audit Log:**  
   Every state change records an entry in the SHA-256 hash-chain ledger.

---

## 3. Demo Persona Roster

Standard password for all demo accounts: **`demo1234`**

| Username | Name | Role | Responsibilities |
|---|---|---|---|
| `priya` | Priya Sharma | `aicte_officer` | AICTE Maker: Reviews submissions, initiates verification, attaches notes |
| `rajan` | Rajan Mehta | `aicte_officer` | AICTE Maker 2: Alternative officer for dual-maker workflows |
| `anita` | Dr. Anita Rao | `aicte_senior` | AICTE Senior Checker: Approves releases, clears disputes, signs renewals |
| `bank_maker` | Bank Officer | `bank_officer` | Bank Maker [SIMULATED]: Submits mock bank confirmation data |
| `bank_checker`| Bank Checker | `bank_checker`| Bank Checker [SIMULATED]: Validates and confirms lien marking |
| `inst_user` | Greenfield Admin | `institution` | College User: Views institution FDRs, submits receipts, requests release |
| `auditor` | Audit Observer | `auditor` | External Auditor: Read-only access to cryptographic ledger & verification |
| `admin` | Portal Admin | `admin` | System Administrator: Rules configuration, emergency maintenance |

---

## 4. Pre-Programmed Demo Test Scenarios

The database is pre-seeded in `backend/seed.py` with 4 realistic cases:

1. **`SBIN00269910` (Happy Path Verification):**
   - Greenfield Institute of Technology (₹25 Lakhs, State Bank of India).
   - Data matches bank records perfectly. Demonstrates clean STP confirmation.
2. **`HDFC00918273` (Maturity Date Mismatch):**
   - Apex College of Engineering (₹15 Lakhs, HDFC Bank).
   - Institution claimed 10-year maturity (2033); bank records confirm 5-year maturity (2028).
   - Demonstrates Two-Column Trust discrepancy detection and automatic transition to `REJECTED`.
3. **`BARB00771239` (Expiring Soon - 30D Window):**
   - Sunrise College of Pharmacy (₹20 Lakhs, Bank of Baroda).
   - Matures within 30 days. Triggers stage-gate alert chip `30D`.
4. **`ICIC00441188` (`fdr-scenario-6`, Disputed Release Candidate):**
   - National Institute of Architecture (₹35 Lakhs, ICICI Bank).
   - Already matured, but blocked by an active faculty unpaid salary dispute under AICTE Clause 14.8.
   - Demonstrates guard protection: release approval returns `400 Bad Request` until dispute is formally cleared by Dr. Anita Rao.

---

## 5. Architectural Decisions & Changelog

- **ADR-01: Flat Backend Monolith:**  
  Adopted flat backend layout (`backend/*.py`) instead of 12-subfolder micro-module layout for developer clarity and rapid SIH iteration.
- **ADR-02: Dual Database Compatibility (PostgreSQL + SQLite):**  
  Defaulted to PostgreSQL on Docker port `5433` via `.env`, with automatic fallback to local `sqlite:///./safar.db` for offline testing.
- **ADR-03: Modern Pydantic v2 & FastAPI Lifespan:**  
  Migrated from deprecated `class Config:` to `ConfigDict(from_attributes=True)` and replaced `@app.on_event("startup")` with `@asynccontextmanager lifespan`.
- **ADR-04: Full Governance API Expansion:**  
  Implemented scrutiny observations (`/instruments/{id}/notes`), dispute locks (`/disputes`), and release request pipelines (`/instruments/{id}/release`).
