# 🏛️ SAFAR — Smart AICTE FDR Automation & Registry
### *A Sovereign, Double-Verified, Tamper-Evident Regulatory Compliance Portal*

[![SIH 2024 / 2026](https://img.shields.io/badge/SIH-Problem%20Statement%2026265-orange?style=for-the-badge&logo=gov.uk)](https://www.sih.gov.in/)
[![AICTE Regulation Bureau](https://img.shields.io/badge/Ministry-AICTE%20Regulation%20Bureau-blue?style=for-the-badge)](https://www.aicte-india.org/)
[![Team: Code Blooded](https://img.shields.io/badge/Team-Code%20Blooded-red?style=for-the-badge)](https://github.com/itxtarun2727/SAFAR-)
[![Frontend: Live on Vercel](https://img.shields.io/badge/Frontend-Live%20on%20Vercel-black?style=for-the-badge&logo=vercel)](https://safar-portal.vercel.app/)
[![Backend: Live on Render](https://img.shields.io/badge/Backend-Live%20on%20Render-46E3B7?style=for-the-badge&logo=render)](https://safar-backend-kqnf.onrender.com/docs)
[![Test Suite: 31 Passing](https://img.shields.io/badge/Tests-31%20Passed%20(100%25)-brightgreen?style=for-the-badge&logo=pytest)](https://docs.pytest.org/)

---

> [!IMPORTANT]
> ### ⚠️ Mandatory Regulatory & Simulation Disclosure
> **Bank confirmation in SAFAR is SIMULATED.**  
> In compliance with the Smart India Hackathon (SIH Problem Statement 26265) guidelines and Indian banking security norms:
> 1. No live Indian core banking systems (SFMS, RBI gateways, or commercial bank nodal APIs) are connected to this prototype.
> 2. All bank confirmations, ISO 20022 simulated message envelopes, and two-column reconciliation checks use isolated deterministic mock adapters (`backend/adapters.py`).
> 3. All participating banks are strictly fictional: **Demo Bank A**, **Demo Bank B**, and **Demo Bank C**.
> 4. Zero real funds are touched. Every mock response and ledger confirmation is explicitly stamped with `[SIMULATED]`.

---

## 🚀 Live Demo & Deployment

| Resource | Target Deployment URL | Status / Notes |
| :--- | :--- | :--- |
| **🌐 Live Frontend Portal** | [https://safar-portal.vercel.app](https://safar-portal.vercel.app/) | Production React 19 SPA with Role Switcher & Live Vault |
| **⚡ FastAPI Swagger Docs** | [https://safar-backend-kqnf.onrender.com/docs](https://safar-backend-kqnf.onrender.com/docs) | Interactive OpenAPI console with "Try it out" buttons |
| **📖 Alternative ReDoc** | [https://safar-backend-kqnf.onrender.com/redoc](https://safar-backend-kqnf.onrender.com/redoc) | Clean API reference specification |
| **🩺 Health & Liveness** | [https://safar-backend-kqnf.onrender.com/health](https://safar-backend-kqnf.onrender.com/health) | Live container health, DB heartbeat, clock status |
| **📋 System Review Report** | [SYSTEM_REVIEW_REPORT.md](SYSTEM_REVIEW_REPORT.md) | Comprehensive 10-invariant compliance audit |
| **🛡️ Security Architecture** | [SECURITY.md](SECURITY.md) | STRIDE Threat Model & Cryptographic Specification |

---

## 📌 Problem Context & The SAFAR Solution

Under the **AICTE Approval Process Handbook (APH)**, thousands of technical institutes (Engineering, Management, Pharmacy, Architecture) across India are legally required to maintain **Security Deposits** (ranging from ₹15 Lakhs to ₹50 Lakhs per program) as **Fixed Deposit Receipts (FDRs)** registered under joint title with AICTE for 8 to 10 years.

### The Operational Challenge Faced by AICTE:
* ❌ **Ghost FDRs & Single-Name Certificates:** Colleges opening deposits in their own name without AICTE's mandatory joint lien, allowing unilateral early withdrawal.
* ❌ **Matured Deposit Blind Spots:** Billions of rupees in institutional deposits mature and slip past renewal deadlines without automated alerts.
* ❌ **Physical Discrepancies:** Paper receipts submitted to regional offices do not match real bank ledger values (differing tenures or amounts).
* ❌ **Premature Release Risks:** Lack of multi-tenant maker-checker separation allowing unauthorized fund returns without resolving faculty salary disputes or student grievances.

### The SAFAR Solution:
SAFAR replaces spreadsheets and paper archives with a sovereign GovTech platform featuring:
1. **Hierarchical Multi-Tenant Scoping:** Clean isolation across `AICTE HQ` $\rightarrow$ `State Technical Universities` $\rightarrow$ `Affiliated Colleges`.
2. **Two-Column Trust Reconciliation:** College submissions are compared side-by-side with bank records before any certificate can be activated.
3. **Restored Scrutiny Flow:** A bank match routes to University Scrutiny (`AICTE_REVIEW`), requiring formal officer sign-off before entering `ACTIVE`.
4. **Two-Part Zero-Knowledge Release Authorization:** Neither AICTE nor the college can release funds alone. The Senior Manager issues the bank code to the bank; the college independently claims their own code; both must be presented at the bank branch.
5. **Cryptographic SHA-256 Hash Chaining:** Every action is linked in a tamper-evident audit ledger with live bit-level tamper detection.

---

## 🏗️ System Architecture & Governance Hierarchy

```mermaid
graph TD
    subgraph Tier1 [National Tier - AICTE Headquarters]
        Senior[AICTE Senior Manager - Dr. Anita Rao]
        Auditor[External Auditor / Vigilance]
    end

    subgraph Tier2 [Scrutiny Tier - State Technical Universities]
        UnivA[Demo University A - Priya Sharma]
        UnivB[Demo University B - Rajan Mehta]
    end

    subgraph Tier3 [Institutional Tier - Affiliated Colleges]
        Col1[Delhi Institute of Technology - inst-001]
        Col2[Apex Engineering College - inst-002]
        Col3[Sunrise Tech Institute - inst-003]
    end

    subgraph BankingTier [Banking Tier - ISO 20022 Simulated]
        BankA[Demo Bank A Branch Inbox]
        BankB[Demo Bank B Branch Inbox]
        BankC[Demo Bank C Branch Inbox]
    end

    Senior -->|National Release Clearance & Code 1 Issuance| BankA
    Senior -->|National Release Clearance & Code 1 Issuance| BankB
    Senior -->|National Release Clearance & Code 1 Issuance| BankC
    Senior -.->|Dispute Resolution & Rule Updates| UnivA
    Senior -.->|Dispute Resolution & Rule Updates| UnivB

    UnivA -->|Scrutiny & Submission Review| Col1
    UnivA -->|Scrutiny & Submission Review| Col2
    UnivB -->|Scrutiny & Submission Review| Col3

    Col1 -->|Presents Code 2 at Branch| BankA
    Col2 -->|Presents Code 2 at Branch| BankB
    Col3 -->|Presents Code 2 at Branch| BankC

    Auditor -->|Verifies SHA-256 Hash Chain| Ledger[(PostgreSQL Tamper-Evident Ledger)]
```

---

## 🔄 End-to-End FDR Lifecycle Flowchart

```mermaid
flowchart TD
    Start([College Submits FDR]) --> SUBMITTED[Status: SUBMITTED]
    
    SUBMITTED -->|Auto Bank Dispatch| BANK_CHECK[Status: BANK_CHECK]
    
    BANK_CHECK -->|Bank Record Matches| AICTE_REVIEW[Status: AICTE_REVIEW<br/>Scoped University Officer Review]
    BANK_CHECK -->|Discrepancy / Mismatch| NEEDS_CORR[Status: NEEDS_CORRECTION<br/>Visible ONLY to College]
    
    NEEDS_CORR -->|College Fixes Values| SUBMITTED
    
    AICTE_REVIEW -->|University Officer Approves| ACTIVE[Status: ACTIVE<br/>Lien Marked Jointly with AICTE]
    AICTE_REVIEW -->|University Officer Rejects| REJECTED[Status: REJECTED<br/>Reason Displayed to College]
    
    REJECTED -->|College Resubmits Correction| SUBMITTED

    ACTIVE -->|Maturity Date Approaching| STAGES[Stage-Gate Countdown<br/>180D ➔ 90D ➔ 60D ➔ 30D ➔ Due Today]
    
    ACTIVE -->|College Initiates Encashment| REL_REQ[Status: RELEASE_REQUESTED]
    
    REL_REQ -->|University Scrutiny Checklist| COMPLIANCE[Status: COMPLIANCE_CHECK<br/>No Dues, Affiliation, 7th CPC Cleared]
    
    COMPLIANCE -->|University Officer Recommends| SENIOR_APPR{Senior Manager Approval<br/>Maker != Checker}
    
    SENIOR_APPR -->|Approved| REL_APPR[Status: RELEASE_APPROVED<br/>Bank Code Created ➔ Sent to Bank Inbox]
    
    REL_APPR -->|College Claims Code Online| CLAIM[College Claims Code 2<br/>One-Time View, Only Hash Stored]
    
    CLAIM --> PRESENT[Dual-Code Presentation at Bank<br/>Code 1 Bank Inbox + Code 2 College Voucher]
    
    PRESENT -->|Match within 3 Attempts| CLOSED([Status: CLOSED / RELEASED<br/>Funds Credited to College])
    PRESENT -->|3 Failed Attempts| LOCKED([AUTHORIZATION LOCKED<br/>Senior Security Alert Dispatched])
```

---

## 🎮 Interactive Evaluator Walkthrough Guide

The frontend features a quick **Persona Role Switcher** at the top right of the navigation bar with standard demo password **`demo1234`**. Follow these steps to experience the complete workflow:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   SAFAR EVALUATOR WALKTHROUGH CHECKLIST                          │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 1. [College Admin]        Submit a new FDR certificate with PDF upload          │
│ 2. [System Automatic]     Instant ISO 20022 STP verification moves to Scrutiny   │
│ 3. [University Officer]   Inspect Two-Column Trust drawer and Approve to ACTIVE │
│ 4. [System Admin]         Fast-Forward Demo Clock (+365 Days) to reach Maturity │
│ 5. [College Admin]        Initiate Release Request for matured deposit           │
│ 6. [University Officer]   Verify 4-point compliance checklist & Recommend       │
│ 7. [Senior Manager]       Approve release (Issues Code 1 to Bank Inbox)         │
│ 8. [College Admin]        Claim one-time independent Code 2                     │
│ 9. [Bank Checker]         Open Bank Console & verify matching Dual Codes        │
│ 10. [Auditor]             Verify SHA-256 ledger integrity & simulate tamper     │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Detailed Step-by-Step Instructions:

1. **Submit Deposit (`inst_user` - Delhi Institute of Technology)**:
   - Select **College Admin** in the role switcher.
   - Click **"Submit New FDR"**, enter FDR details (e.g. ₹20 Lakhs, Demo Bank A), upload a PDF receipt, and submit.
   - Status updates to `SUBMITTED` and triggers automated bank verification (`BANK_CHECK`).
2. **University Scrutiny (`priya` - Demo University A Scrutinizer)**:
   - Switch role to **University Officer (Priya Sharma)**.
   - Notice that you only see colleges affiliated with Demo University A (multi-tenant isolation).
   - Open the submitted FDR. Click **"Review Scrutiny"**, inspect the side-by-side bank confirmation, enter an approval remark, and click **"Approve FDR"**. Status becomes `ACTIVE`.
3. **Time-Travel Demo Clock (`admin`)**:
   - Switch role to **System Admin**.
   - Use the **Demo Clock** controls in the navigation bar to advance system time by `+365 Days`.
   - Refresh the dashboard to see stage-gate alert counters advance to `DUE_TODAY` or `OVERDUE`.
4. **Initiate Release (`inst_user`)**:
   - Switch back to **College Admin**.
   - Navigate to the matured FDR (`DEMOA00554433`) and click **"Request Release"**. Status moves to `RELEASE_REQUESTED`.
5. **Clearance Checklist (`priya`)**:
   - Switch to **University Officer**. Open the release request, complete the 4-point clearance checklist (No-Dues, Faculty Salary Clearance under Clause 14.8, Affiliation NOC), and click **"Recommend Release"**.
6. **Senior Manager Dual-Code Clearance (`anita` - Dr. Anita Rao)**:
   - Switch role to **Senior Manager**.
   - Review the recommendation. Enforces strict **Maker $\neq$ Checker** separation (Dr. Anita Rao $\neq$ Priya Sharma).
   - Click **"Approve Release"**. This generates **only the bank code**, which is automatically dispatched to the partner bank branch inbox.
7. **Claim College Code (`inst_user`)**:
   - Switch to **College Admin**.
   - Open the release case file and click **"Claim Release Code"**. The one-time college authorization voucher is revealed. Only its SHA-256 hash is retained on the server.
8. **Bank Branch Dual-Code Presentation (`bank_a` - Demo Bank A Checker)**:
   - Switch role to **Bank Checker (Demo Bank A)**.
   - Navigate to the **Bank Console Inbox**. Click **"Present Release Codes"**.
   - Enter the Bank Code (from the bank screen) and College Code (from the college voucher). Click **"Confirm Release"**.
   - Status updates to `CLOSED` and the security deposit is formally released.
9. **Tamper-Evident Audit Verification (`auditor`)**:
   - Switch role to **Auditor Observer**.
   - Open the **Audit Ledger**. Click **"Verify Cryptographic Integrity"** — all SHA-256 hashes recompute from genesis block sequence 1 to head.
   - To demonstrate fraud detection: Switch to Admin, click **"Simulate Tamper"** to alter a bit in the database, and run verification again — the system flags the exact modified sequence! Click **"Repair Ledger"** to restore.

---

## 👥 Pre-Seeded Personas & Evaluation Scenarios

### Demo User Personas (`POST /auth/login`)
Standard password for all demo personas: **`demo1234`**

| Username | Role | Persona & Jurisdiction | Key Responsibilities |
|---|---|---|---|
| **`priya`** | `aicte_officer` | Priya Sharma (Demo University A) | Scrutiny approval/rejection, clearance checklist recommendation |
| **`rajan`** | `aicte_officer` | Rajan Mehta (Demo University B) | Scrutiny scoped strictly to Maharashtra / Demo Univ B colleges |
| **`anita`** | `aicte_senior` | Dr. Anita Rao (Senior AICTE Director) | National release approval, bank code generation, dispute clearance |
| **`bank_a`** | `bank_checker`| Demo Bank A Branch Officer [SIMULATED] | Branch inbox verification, dual-code presentation confirmation |
| **`bank_b`** | `bank_checker`| Demo Bank B Branch Officer [SIMULATED] | Branch inbox verification, dual-code presentation confirmation |
| **`bank_c`** | `bank_checker`| Demo Bank C Branch Officer [SIMULATED] | Branch inbox verification, dual-code presentation confirmation |
| **`inst_user`** | `institution` | Delhi Institute of Technology Admin | Greenfield college: uploads FDRs, claims one-time release code |
| **`inst_apex`** | `institution` | Apex Engineering College Admin | College under Demo Univ A; isolated FDR portfolio |
| **`inst_sunrise`**| `institution`| Sunrise Institute Admin | College under Demo Univ B; isolated FDR portfolio |
| **`auditor`** | `auditor` | Audit Observer | Read-only ledger inspection, cryptographic verification & incident reports |
| **`admin`** | `admin` | Portal Administrator | Regulatory rules threshold config, demo clock time-travel, ledger repair |

### Pre-Seeded Test Scenarios

| Reference No. | Institution | Bank | Amount | Initial State | Evaluation Scenario Goal |
|---|---|---|---|---|---|
| **`DEMOA00112233`** | Delhi Inst. of Technology | Demo Bank A | ₹20 Lakhs | `SUBMITTED` | Ready for automated bank match $\rightarrow$ University Scrutiny |
| **`DEMOB00918273`** | Apex Engineering College | Demo Bank B | ₹15 Lakhs | `NEEDS_CORRECTION` | Discrepancy test: Submitted 10 yrs vs Bank confirmed 5 yrs |
| **`DEMOA00269910`** | Delhi Inst. of Technology | Demo Bank A | ₹25 Lakhs | `ACTIVE` | Happy path: Fully verified active joint deposit |
| **`DEMOC00771239`** | Sunrise Institute | Demo Bank C | ₹20 Lakhs | `ACTIVE` (30D) | Stage-gate test: Matures in 30 days; triggers alert notice |
| **`DEMOA00554433`** | Delhi Inst. of Technology | Demo Bank A | ₹30 Lakhs | `ACTIVE` (Matured) | Release candidate: Ready for release request & dual-code payout |
| **`DEMOC00441188`** | Sunrise Institute | Demo Bank C | ₹35 Lakhs | `DISPUTED` | Guard lock test: Blocked by active 7th CPC unpaid salary dispute |

---

## 🛠️ Local Development & Quickstart

### Prerequisites
* Docker & Docker Compose
* Python 3.11+ / 3.12+
* Node.js 18+ & npm

### Step 1: Clone Repository
```bash
git clone https://github.com/itxtarun2727/SAFAR-.git
cd SAFAR-
```

### Step 2: Start PostgreSQL Database & Backend via Docker
```bash
docker-compose up -d
```
* PostgreSQL runs on port **`5433`** (`postgresql://safar:safar_secure_password@localhost:5433/safar_db`).
* FastAPI backend starts on **`http://localhost:8000`**.

### Step 3: Run the Frontend
```bash
cd frontend
npm install
npm run dev
```
* Open **`http://localhost:5173`** in your browser.

---

## 🧪 Automated Testing

SAFAR includes an automated test suite verifying all state transitions, security guards, multi-tenant isolation rules, and cryptographic ledger hashing.

```bash
# Run the test suite inside the backend container
docker exec safar_backend pytest -v

# Or run locally from backend/
cd backend
pytest -v
```

**Results:**
```text
======================= 31 passed in 18.25s =======================
- test_change_request.py: 17 passed (Hierarchy, Scrutiny, Release Privacy, Rate Limits)
- test_workflow.py:        9 passed (State transitions, guard enforcement)
- test_audit.py:           5 passed (SHA-256 chaining, bit-tamper detection, repair)
```

---

## ☁️ Cloud Deployment Blueprint

SAFAR is engineered for zero-data-loss ephemeral container hosting:
* **Pluggable Storage**: Uses `DatabaseStorageBackend` (storing PDF bytes in PostgreSQL `bytea`) on ephemeral cloud platforms (Render, Railway), or `S3StorageBackend` (AWS S3 / Cloudflare R2) when configured via `S3_BUCKET`.
* **Render Blueprint (`render.yaml`)**:
  - Web Service: Python FastAPI ASGI server with auto-healthcheck at `/health`.
  - Managed PostgreSQL: Automated connection string injection.
* **Vercel Frontend**: Vite static bundle deployed with proxy routing to the FastAPI backend.

---

## 🏆 Project & Hackathon Credentials

* **Hackathon:** Smart India Hackathon (SIH 2024 / 2026)
* **Problem Statement:** 26265 — *"Streamline of security deposit / FDR portal"*
* **Organization:** All India Council for Technical Education (AICTE Regulation Bureau)
* **Team:** Code Blooded
* **Repository:** [https://github.com/itxtarun2727/SAFAR-](https://github.com/itxtarun2727/SAFAR-)
