# SAFAR — REST API Reference Specification
**Smart India Hackathon (SIH Problem Statement 26265)**  
*AICTE Regulation Bureau — Smart Automation (Software)*  
**Team:** Code Blooded

---

## 1. Overview & Authentication

- **Base URL:** `http://localhost:8000`
- **Interactive Swagger Documentation:** `http://localhost:8000/docs`
- **Alternative ReDoc UI:** `http://localhost:8000/redoc`
- **Authentication Scheme:** HTTP Bearer JWT

To authenticate, send the `Authorization` header with your requests:
```http
Authorization: Bearer <access_token>
```

---

## 2. API Endpoints Reference

### 2.1 System & Health

#### `GET /`
- **Description:** Redirects automatically to `/docs` (Swagger UI).
- **Status:** `307 Temporary Redirect`

#### `GET /health`
- **Description:** Liveness check returning service status and simulated clock mode.
- **Response `200 OK`:**
  ```json
  {
    "status": "ok",
    "service": "safar-backend",
    "clock_simulated": false,
    "current_time": "2026-10-25T08:45:00.000000+00:00"
  }
  ```

---

### 2.2 Authentication

#### `POST /auth/login`
- **Description:** Authenticate demo persona using standard password `demo1234`.
- **Request Body:**
  ```json
  {
    "username": "priya",
    "password": "demo1234"
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "user": {
      "user_id": "u-aicte-01",
      "role": "aicte_officer",
      "name": "Priya Sharma",
      "institution_ids": []
    }
  }
  ```

#### `GET /auth/me`
- **Description:** Returns profile and role permissions of current token holder.

---

### 2.3 FDR Instruments & Two-Column Trust

#### `GET /instruments`
- **Description:** List FDR certificates with optional filtering.
- **Query Parameters:**
  - `institution_id` *(optional, string)*
  - `status` *(optional, string)*: `SUBMITTED`, `BANK_CHECK`, `ACTIVE`, `REJECTED`, `DISPUTED`, etc.
  - `stage` *(optional, string)*: `180D`, `90D`, `60D`, `30D`, `7D`, `DUE_TODAY`, `OVERDUE`.

#### `POST /instruments`
- **Description:** Submit a new FDR certificate record.
- **Request Body:**
  ```json
  {
    "institution_id": "inst-001",
    "type": "bank_fdr",
    "bank_name": "State Bank of India",
    "branch": "Connaught Place, New Delhi",
    "reference_no": "SBIN00269910",
    "amount_paise": 250000000,
    "issue_date": "2024-01-15",
    "maturity_date": "2034-01-15",
    "tenure_years": 10,
    "joint_holder": "AICTE and Greenfield Society",
    "lien_marked": true
  }
  ```
- **Response `200 OK`:** Returns created instrument with initial status `SUBMITTED`.

#### `GET /instruments/{instrument_id}`
- **Description:** 360-degree case file containing:
  - Instrument metadata
  - Two-Column confirmations (`confirmations`)
  - Attached documents (`documents`)
  - Scrutiny notes (`notes`)
  - Active disputes (`disputes`)
  - Release requests (`release_requests`)

#### `GET /instruments/{instrument_id}/lineage`
- **Description:** Returns the chronological renewal history (predecessor to successors).

---

### 2.4 Bank Verification & State Machine

#### `POST /instruments/{instrument_id}/verify-bank`
- **Description:** Triggers simulated STP core banking verification.
- **Effects:**
  - Updates `FieldConfirmation` table side-by-side.
  - Transitions `SUBMITTED` → `BANK_CHECK` → `ACTIVE` (if matched) or `REJECTED` (if mismatched).

#### `POST /instruments/{instrument_id}/transition`
- **Description:** Executes a guarded state transition through `workflow.py`.
- **Request Body:**
  ```json
  {
    "event": "approve",
    "reason": "Clearance checklist verified by Senior Officer.",
    "payload": {
      "checklist": {"no_dues": true, "audit_cleared": true}
    }
  }
  ```
- **Response `200 OK`:** `{"status": "success", "new_state": "APPROVED", "effects": [...]}`
- **Response `400 Bad Request`:** Raised if guard fails (e.g. open dispute or maker == checker).

---

### 2.5 Governance: Notes, Disputes & Release

#### `POST /instruments/{instrument_id}/notes`
- **Description:** Officer records formal scrutiny observation.
- **Request Body:** `{"text": "Original hard-copy receipt verified against bank letter."}`

#### `POST /instruments/{instrument_id}/disputes`
- **Description:** Open a compliance hold or legal grievance, locking release.
- **Request Body:** `{"reason": "Faculty 7th CPC unpaid salary grievance under Clause 14.8"}`

#### `POST /disputes/{dispute_id}/clear`
- **Description:** Formally resolve and clear a dispute hold (Senior Officer / Admin only).

#### `POST /instruments/{instrument_id}/release`
- **Description:** Submit deposit release request with multi-point clearance checklist.

---

### 2.6 Automation: Scheduler & Demo Clock

#### `GET /dashboard/stats`
- **Description:** Returns counts for Dashboard cards: `active`, `expiring`, `matured`, `renewed`, `released`, `pending`.

#### `GET /alerts`
- **Description:** List active countdown and overdue stage alerts.

#### `POST /scheduler/run-now`
- **Description:** Manually trigger idempotent daily alert calculation.

#### `GET /clock`
- **Description:** Inspect current system time and simulation override status.

#### `POST /clock/advance?days=90`
- **Description:** Fast-forward demo time by $N$ days to test renewal countdowns.

#### `POST /clock/reset`
- **Description:** Reset clock back to real system time.

---

### 2.7 Cryptographic Audit Ledger

#### `GET /audit/entries?skip=0&limit=50`
- **Description:** Fetch append-only audit trail in chronological order.

#### `GET /audit/verify`
- **Description:** Recompute SHA-256 hash chain and report ledger integrity status.

#### `POST /audit/simulate-tamper`
- **Description:** Deliberately alter an audit row in the database to demonstrate tamper detection to evaluators.

#### `POST /audit/repair`
- **Description:** Restore ledger verification by recomputing valid hashes after a tamper demo.
