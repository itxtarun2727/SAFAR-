# SAFAR System Review Report
**Smart AICTE FDR Automation & Registry**
*Document Version: 2.2 | Scope: Architecture, Security, Workflow, API Catalog, and Deployment Readiness*

---

## 1. Executive Summary & Core Invariants

SAFAR (**Smart AICTE FDR Automation & Registry**) is an institutional Fixed Deposit Receipt (FDR) and regulatory deposit management portal engineered for the All India Council for Technical Education (AICTE). It automates deposit submission, multi-tenant scrutiny, simulated bank verification, milestone alerting, and dual-code release authorization.

### Fundamental System Invariants
1. **Restored Scrutiny Flow (AICTE Review):** A bank record match does **not** activate a deposit. Instead, matching deposits enter `AICTE_REVIEW`, where approval by a University Officer scoped to that college's university is required (with recorded reason) before reaching `ACTIVE`. A bank mismatch routes to `NEEDS_CORRECTION` (visible to the college only, never appearing in officer queues). A temporary bank outage leaves the instrument pending with automatic backoff retry. If an officer rejects a submission, the instrument enters `REJECTED` (with the rejection reason displayed to the college), and the college can correct deficiencies to trigger a `resubmit` transition back to `SUBMITTED`.
2. **University Officer Scoping & Separation of Duties:** University officers (`role: aicte_officer`) are strictly scoped by `university_id`—they approve submissions and recommend release for colleges affiliated with their specific university. The Senior Manager (`role: aicte_senior`) maintains national jurisdiction and approves release; the Senior Manager must differ from the recommending officer (`maker_id != checker_id`).
3. **Multi-Tenant Data Isolation:** Enforced strictly at the SQL query level on every transaction. Colleges inspect only their own instruments and documents. University officers inspect only affiliated colleges. Bank checkers inspect only branch records.
4. **Bank Integration Model:** All bank connectivity passes through simulated adapters (`DemoBankAdapter`). Every bank payload, status response, and console UI carries prominent `[SIMULATED]` labeling with fictional banking partners (`Demo Bank A`, `Demo Bank B`, `Demo Bank C`). The production evolution path is a **nodal-bank API or daily bank file**.
5. **Dual-Code Release Privacy:** Senior officer approval creates a release authorization containing **only the bank code**, dispatched to the partner bank inbox. The college release code is **never** generated or exposed to AICTE staff. The college claims its code on-demand via a dedicated endpoint; only its SHA-256 hash is retained.
6. **Code Abuse & Rate Limiting:** Release authorizations lock automatically after $N = 3$ failed code presentations (`release.max_failed_attempts`). Failed bank checks are audited, counted per instrument, and at threshold (default 3) trigger an alert visible **strictly to Senior and Auditor**.
7. **Ephemeral Hosting & Storage Backend:** Document storage does not rely on local container disks. Storage is decoupled into a pluggable interface:
   - `DatabaseStorageBackend` (stores file bytes in PostgreSQL `bytea` column, safe on ephemeral hosts like Render).
   - `S3StorageBackend` (stores in S3-compatible cloud object storage configured via `S3_BUCKET`).
8. **Tamper-Evident Audit Ledger:** Every state change, scrutiny note, document upload, and security event is committed to a SHA-256 hash-chained append-only ledger.
9. **Monetary Precision:** All currency is tracked and stored as 64-bit integer paise (INR $1.00 = 100$ paise).
10. **Strict Secrets Policy:** No default secrets in code or docs outside demo mode. `JWT_SECRET` and `DATABASE_URL` are strictly required from the environment when `DEMO_MODE=false`.

---

## 2. System Architecture & Component Design

```
+-----------------------------------------------------------------------------------+
|                                  USER TIERS                                       |
|  +--------------------+  +----------------------+  +---------------------------+  |
|  | College Institute  |  |  University Officer  |  |  AICTE Senior Manager     |  |
|  | (inst_user, DIT)   |  | (Priya / Rajan, Univ)|  | (Dr. Anita Rao, National) |  |
|  +---------+----------+  +----------+-----------+  +-------------+-------------+  |
+------------|------------------------|----------------------------|----------------+
             |                        |                            |
             v                        v                            v
+-----------------------------------------------------------------------------------+
|                        FRONTEND SINGLE PAGE APP (React + Vite)                    |
|  - Role Switcher & Preloaded Personas      - Interactive College Submission Portal|
|  - Scrutiny Approval & Rejection Drawers   - Document Upload & Verification Vault |
|  - Bank Console with Dual-Code Presentation- Tamper-Evident Ledger & Repair Demo  |
+-----------------------------------------------------------------------------------+
                                      |
                               REST API (JSON over HTTP)
                                      |
                                      v
+-----------------------------------------------------------------------------------+
|                           FASTAPI APPLICATION BACKEND                             |
|  +---------------------+  +----------------------+  +--------------------------+  |
|  |  auth.py (JWT RBAC) |  | crud.py (Scoped I/O) |  | workflow.py (Pure FSM)   |  |
|  +---------------------+  +----------------------+  +--------------------------+  |
|  | storage.py (Bytea/S3|  | rules.py (Thresholds)|  | audit.py (Hash Chain)   |  |
|  +---------------------+  +----------------------+  +--------------------------+  |
+-----------------------------------------------------------------------------------+
                                      |
                               SQLAlchemy 2.0
                                      |
                                      v
+-----------------------------------------------------------------------------------+
|                      POSTGRESQL RELATIONAL DATABASE (Port 5433)                   |
|  - institutions / universities / banks   - instruments & documents (bytea)        |
|  - release_authorizations (with hashes)  - alerts, disputes, scrutiny_notes       |
|  - audit_log (seq, payload_hash, chain)  - system_rules                           |
+-----------------------------------------------------------------------------------+
```

---

## 3. Real Endpoint Catalog (Generated from OpenAPI Schema)

Every route below is verified and active in [`backend/main.py`](file:///d:/SIH'26/SAFAR/backend/main.py):

| Method | Endpoint Path | Tag | Description & Access Scope |
|---|---|---|---|
| `GET` | `/health` | System | Container health, database heartbeat, demo clock state |
| `POST` | `/auth/login` | Auth | Issues JWT bearer token for demo personas |
| `GET` | `/auth/me` | Auth | Returns currently active user persona profile |
| `GET` | `/universities` | Hierarchy | Lists affiliating State Technical Universities |
| `GET` | `/banks` | Hierarchy | Lists fictional partner banks [SIMULATED] |
| `GET` | `/institutions` | Institutions | Lists technical colleges with university/tenant scoping |
| `GET` | `/dashboard/stats` | Dashboard | Scoped 6-metric summary: Active, Expiring, Matured, Renewed, Released, Pending |
| `GET` | `/instruments` | Instruments | Scoped list of FDR instruments |
| `POST` | `/instruments` | Instruments | College submits FDR; triggers automatic bank verification |
| `GET` | `/instruments/{id}` | Instruments | Scoped retrieval of single FDR |
| `POST` | `/instruments/{id}/approve` | Scrutiny | University Officer approves submitted FDR (`AICTE_REVIEW -> ACTIVE`) |
| `POST` | `/instruments/{id}/reject` | Scrutiny | University Officer rejects submitted FDR (`AICTE_REVIEW -> REJECTED`) |
| `POST` | `/instruments/{id}/resubmit` | Instruments | College resubmits corrected FDR (`REJECTED -> SUBMITTED`) |
| `POST` | `/instruments/{id}/verify-bank`| Verification| Manual/system trigger for simulated bank verification check |
| `POST` | `/instruments/{id}/transition` | Workflow | Generic guarded transition evaluator |
| `GET` | `/instruments/{id}/lineage` | Instruments | Predecessor/successor instrument renewal ancestry |
| `POST` | `/instruments/{id}/renew` | Instruments | Initiates renewal linked to predecessor deposit |
| `POST` | `/instruments/{id}/documents` | Documents | Uploads document to Database bytea or S3 with SHA-256 digest |
| `GET` | `/instruments/{id}/documents` | Documents | Lists document versions for scoped instrument |
| `GET` | `/instruments/{id}/documents/{doc_id}` | Documents | Retrieves document metadata |
| `GET` | `/instruments/{id}/documents/{doc_id}/download` | Documents | Downloads file content bytes with SHA-256 verification |
| `GET` | `/instruments/{id}/evidence-pack` | Compliance | Comprehensive compliance evidence bundle with audit proof |
| `POST` | `/instruments/{id}/notes` | Scrutiny | Adds scrutiny observation note |
| `GET` | `/instruments/{id}/notes` | Scrutiny | Lists scrutiny note history |
| `POST` | `/instruments/{id}/disputes` | Disputes | Opens dispute hold on instrument |
| `POST` | `/disputes/{id}/clear` | Disputes | Senior/Admin formally clears dispute |
| `POST` | `/instruments/{id}/release-request` | Release | College initiates release request |
| `POST` | `/release/{id}/recommend` | Release | University Officer records checklist and recommends release |
| `POST` | `/release/{id}/approve` | Release | Senior Manager approves release; issues bank code only |
| `POST` | `/release/{release_ref}/claim-code` | Release | College claims one-time release code |
| `POST` | `/release/{release_ref}/reissue` | Release | Senior reissues expired authorization |
| `GET` | `/bank/inbox` | Bank Console | Pending release authorizations for bank branch [SIMULATED] |
| `POST` | `/bank/release/{release_ref}/confirm` | Bank Console | Dual-code presentation confirmation ($N=3$ rate-limited) |
| `GET` | `/reports/failed-verifications` | Reports | Incident report of failed bank checks (**Senior & Auditor only**) |
| `GET` | `/alerts` | Alerts | Scoped alert feed (`90D`, `60D`, `30D`, `MATURED`, failed checks) |
| `POST` | `/alerts/{id}/acknowledge` | Alerts | Formal acknowledgment of alert notice |
| `POST` | `/scheduler/run-now` | Scheduler | Admin trigger for daily alert sweep |
| `GET` | `/audit/entries` | Audit | Scoped append-only ledger entries |
| `GET` | `/audit/verify` | Audit | Cryptographic SHA-256 chain validation |
| `POST` | `/audit/simulate-tamper` | Audit | Bit manipulation demo (Admin, `DEMO_MODE=true`) |
| `POST` | `/audit/tamper-demo` | Audit | Alias for simulate-tamper |
| `POST` | `/audit/repair` | Audit | Cryptographic chain repair with audit logging |
| `POST` | `/audit/repair-demo` | Audit | Alias for repair |
| `GET` | `/clock` | Clock | Evaluator demo clock status |
| `GET` | `/clock/current` | Clock | Current active system clock time |
| `POST` | `/clock/advance` | Clock | Time-travel clock advance (+30D, +90D; Admin, `DEMO_MODE=true`) |
| `POST` | `/clock/reset` | Clock | Reset clock to UTC wall time (Admin, `DEMO_MODE=true`) |
| `GET` | `/rules` | Rules | Lists regulatory configuration parameters |
| `POST` | `/rules` | Rules | Updates regulatory rule threshold (Admin only) |

---

## 4. Finite State Machine (FSM) & Lifecycle Flow

```
                           +---------------+
                           |     DRAFT     |
                           +-------+-------+
                                   | submit
                                   v
                           +---------------+
              +----------->|   SUBMITTED   |<------------+
              |            +-------+-------+             |
              |                    | send_to_bank        |
              |                    v                     |
              |            +---------------+             |
              |            |  BANK_CHECK   |             |
              |            +---+-------+---+             |
              |                |       |                 |
  mismatch    |     bank match |       | bank mismatch   |
  resubmit    |                v       v                 |
              |        +---------------+ +------------------+
              |        | AICTE_REVIEW  | | NEEDS_CORRECTION |
              |        +---+-------+---+ +--------+---------+
              |            |       |              |
              |    approve |       | reject       +------+
              |            v       v
              |    +---------------+  +--------------+
              |    |    ACTIVE     |  |   REJECTED   |
              |    +---+---+---+---+  +-------+------+
              |        |   |   |              |
              +--------|---|---|--------------+ (College resubmits)
                       |   |   |
     renewal_detected  |   |   | dispute_opened
     +-----------------+   |   +-------------------+
     |                     |                       |
     v                     v request_release       v
   +-----------------+   +-------------------+   +--------------------+
   | RENEWAL_PENDING |   | RELEASE_REQUESTED |   |     IN_DISPUTE     |
   +-----------------+   +---------+---------+   +---------+----------+
                                   |                       |
                   recommend_release |                     | clear_dispute
                  (University Officer)                     v
                                   v             +--------------------+
                         +-------------------+   |       ACTIVE       |
                         | COMPLIANCE_CHECK  |   +--------------------+
                         +---------+---------+
                                   |
                      senior_approve (AICTE Senior Manager, maker != checker)
                                   v
                         +-------------------+
                         |     APPROVED      |
                         +---------+---------+
                                   | issue_authorization (bank code only)
                                   v
                         +-------------------+
                         |BANK_RELEASE_PENDNG|
                         +---------+---------+
                                   | bank_confirm_release (matching college code)
                                   v
                         +-------------------+
                         |      CLOSED       |
                         +-------------------+
```

---

## 5. Security & Isolation Matrix

| Tenant Role | Jurisdiction Scope | Actions Permitted | Restrictions & Invariants |
|---|---|---|---|
| **College Institute (`inst_user`)** | Own college instruments only | Submits FDR; uploads documents; resubmits; claims one-time release code | Cannot view officer queues; cannot read other colleges (`404`/`403`) |
| **University Officer (`priya`, `rajan`)** | Affiliated colleges under same `university_id` | Approves/rejects submissions (`AICTE_REVIEW`); completes clearance checklist; recommends release | Cannot approve across universities (`403`); cannot approve release as senior |
| **AICTE Senior Manager (`anita`)** | National jurisdiction across all universities | Approves deposit release; issues bank authorization; clears disputes | **Strict separation of duties**: cannot approve release if also recommending officer |
| **Auditor Observer (`auditor`)** | National oversight | Reads all instruments, ledgers, verification histories, failed reports | Read-only; cannot mutate state or approve releases |
| **Bank Checker (`bank_a`, etc.)** | Own branch instruments only [SIMULATED] | Confirms verification; confirms release using presented dual codes | Receives bank code via inbox; cannot access college code; locked after 3 failures |
| **Portal Administrator (`admin`)** | System administration | Updates rules; runs scheduler; executes tamper demo and repair | Clock and tamper actions strictly gated by `DEMO_MODE=true` |

---

## 6. Candid Design Trade-offs & TODOs

| Component | Current Implementation | Production Evolution Path | Classification |
|---|---|---|---|
| **Checklist Items** | Single standardized clearance checklist (grievances, 7th CPC norms, regional NOC) | Stakeholder review with AICTE legal and approval bureaus | `TODO(confirm)` |
| **Release Expiry Window** | 72 hours from senior manager approval | Formally specify in official AICTE approval guidelines | `SAFAR design parameter; TODO(confirm)` |
| **Max Failed Attempts** | Lockout after 3 incorrect dual-code attempts | Institutional unlock protocol by Regional Director (proposal) | `SAFAR design parameter; TODO(confirm)` |
| **Document Vault** | Pluggable storage interface: PostgreSQL bytea for demo/ephemeral hosting; S3 bucket via env config | AWS S3 / Azure Blob Storage with write-once-read-many (WORM) | Ephemeral host ready |
| **Bank Adapter** | In-memory simulated response generator (`[SIMULATED]`) | nodal-bank API or daily bank file | External integration |
| **Demo Clock** | `/clock/advance` and `/clock/reset` gated by `DEMO_MODE=true` and admin | Inactive in production; replaced by system UTC wall clock | Demo utility |
