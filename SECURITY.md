# SAFAR — Security Architecture & Threat Mitigation Model
**Smart India Hackathon (SIH Problem Statement 26265)**  
*AICTE Regulation Bureau — Smart Automation (Software)*  
**Team:** Code Blooded

---

## 1. Security Overview

SAFAR is designed to handle high-value regulatory financial instruments (deposits ranging from ₹15 Lakhs to ₹50 Lakhs per college). Because institutional deposits are vulnerable to unauthorized release, falsified documents, and collusion, SAFAR embeds strict security controls directly into the architectural core.

---

## 2. STRIDE Threat Model & Mitigations

| Threat Category | Potential Attack Vector | SAFAR Mitigation |
|---|---|---|
| **Spoofing** | Attacker impersonates an AICTE officer or bank representative to falsify deposit confirmations. | Signed JWT tokens with HS256 algorithm. In production, tokens are signed with RS256/ECDSA private keys. |
| **Tampering** | Rogue actor or database administrator alters an audit entry or marks an FDR as "Released" directly in SQL. | **Cryptographic SHA-256 Hash Chaining:** Every entry's hash depends on the preceding row's hash. Tampering breaks the chain, detected immediately by `/audit/verify`. |
| **Repudiation** | An officer approves a premature deposit release and denies having authorized it. | Immutable audit entries record `actor_id`, `role`, UTC timestamp (`at`), exact JSON payload hash, and formal reason. |
| **Information Disclosure** | An institution inspects competing colleges' security deposit details. | **Institutional Scoping:** When role is `institution`, `GET /instruments` automatically restricts results to `user.institution_ids`. |
| **Denial of Service** | Malicious script triggers repetitive alert runs or overwhelms database connections. | Idempotent daily alert jobs; SQLAlchemy connection pooling with `pool_pre_ping=True`. |
| **Elevation of Privilege** | An officer creates an FDR release request and approves their own payout. | **Maker-Checker Guard:** `guard_maker_differs_from_checker` strictly aborts approval with HTTP 400 if `maker_id == checker_id`. |

---

## 3. Cryptographic Hash-Chain Specification

The audit system in `backend/audit.py` implements an append-only, tamper-evident hash chain.

### Hash Calculation Standard
1. **Canonical JSON Serialization:**  
   To prevent hash variations due to dictionary key ordering or whitespace differences, all JSON payloads are sorted and serialized with zero whitespace:
   ```python
   def canonical_json(data: Any) -> str:
       return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
   ```
2. **Payload Hash:**
   $$\text{PayloadHash} = \text{SHA256}(\text{CanonicalJSON}(\text{payload}))$$
3. **Row Hash:**
   $$\text{RowHash}_n = \text{SHA256}(\text{PrevHash}_n \parallel \text{CanonicalJSON}(\text{hash\_data}))$$
4. **Genesis Block:**
   The initial row links to 64 zeroes: `0000000000000000000000000000000000000000000000000000000000000000`.

### Live Verification & Demonstration Endpoints
- `GET /audit/verify`: Traverses sequence 1 to $N$, recomputing hashes. Returns `ok: true` or highlights the exact broken sequence number.
- `POST /audit/simulate-tamper`: Deliberately mutates a historical row to prove the verifier immediately flags unauthorized modifications.
- `POST /audit/repair`: Recomputes valid hashes across the chain to restore verification for evaluation continuity.

---

## 4. Role-Based Access Control (RBAC) Permissions Matrix

| Resource / Endpoint | `aicte_officer` (Maker) | `aicte_senior` (Checker) | `bank_officer` | `bank_checker` | `institution` | `auditor` | `admin` |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `POST /instruments` (Submit FDR) | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ |
| `POST /instruments/{id}/verify-bank` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `POST /instruments/{id}/transition` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| `POST /instruments/{id}/notes` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `POST /instruments/{id}/disputes` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `POST /disputes/{id}/clear` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `POST /instruments/{id}/release` | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ |
| `POST /rules` (Update Norms) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `GET /audit/entries` & `/verify` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |

---

## 5. Simulation Boundary Disclosures

- **No SFMS / RBI Connections:** Real banking interfaces require dedicated leased lines, SFMS sub-membership, and hardware HSMs. In this prototype, banking operations are mocked deterministically in `backend/adapters.py`.
- **Demo Passwords:** All demo accounts use the convenience password `demo1234` for rapid evaluation during the hackathon. In production, authentication would integrate with AICTE Single Sign-On (DigiLocker / MeriPehchaan).
