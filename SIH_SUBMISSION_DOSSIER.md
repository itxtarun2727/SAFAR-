# Smart India Hackathon (SIH 2026) — Official Idea Submission Dossier

**Problem Statement Title:** Streamline of security deposit / FDR portal  
**Problem Statement ID:** 26265  
**Ministry / Organization:** All India Council for Technical Education (AICTE), Ministry of Education, Govt. of India  
**Team Name:** Code Blooded  
**Project Name:** SAFAR (Smart AICTE FDR Automation & Registry)  
**Document Purpose:** Master copy of all portal submission fields, technical descriptions, and presentation deck mappings.

---

## 1. Quick Verification & Deployment Links

| Resource | URL |
| :--- | :--- |
| **Live Frontend Portal (Vercel)** | [https://safar-portal.vercel.app/](https://safar-portal.vercel.app/) |
| **Backend API & Swagger Docs (Render)** | [https://safar-backend-kqnf.onrender.com/docs](https://safar-backend-kqnf.onrender.com/docs) |
| **Source Code Repository (GitHub)** | [https://github.com/itxtarun2727/SAFAR-](https://github.com/itxtarun2727/SAFAR-) |
| **Official Demo Video (YouTube)** | [https://www.youtube.com/watch?v=NKunJOWPcYQ](https://www.youtube.com/watch?v=NKunJOWPcYQ) |

---

## 2. SIH Portal Form Fields

### Field 1: Idea Title
*(Constraint: Maximum 100 characters)*

```text
SAFAR: Smart AICTE FDR Automation & Multi-Tier Regulatory Registry with Dual-Key Security
```
* **Character Count:** 89 / 100 characters

---

### Field 2: Technology Bucket
*(Select from portal dropdown)*

* **Primary Selection:** `Information Security`  
* **Alternative Selection:** `Cloud Computing`

---

### Field 3: Abstract / Summary
*(Constraint: Maximum 10,000 characters)*

```text
AICTE asks technical institutions to keep security deposits, usually as fixed deposit receipts (FDRs), and today follows them through scanned letters, physical files and spreadsheets. A scan cannot show that a deposit exists at the bank, maturity dates are easy to miss, and a release request passes through several offices with no single record.

SAFAR (Smart AICTE FDR Automation & Registry) is one portal for colleges, university officers, AICTE senior managers, auditors and banks. A college registers an FDR and uploads its documents, each stored with a SHA-256 hash. The backend sends the details to a bank adapter and shows the submitted values beside the bank-confirmed values. A mismatch goes back to the college with a reason. A match goes to the university officer, who approves or rejects it with a written reason. Approved deposits are tracked: a scheduler raises alerts at 90, 60 and 30 days and at maturity, once per stage, and a renewal links back to the original FDR.

Release is guarded. The college requests it after maturity, an officer recommends it after a checklist, and a different senior manager approves it. The bank then receives one code and the college claims another. The deposit closes only when the bank confirms with the matching code, and three wrong attempts lock the release. Every state change is written to a hash-chained audit log, so any later edit can be detected.

The prototype uses React, FastAPI and PostgreSQL, with synthetic data and a simulated bank. The bank connection sits behind an adapter, so a nodal-bank API or a daily bank file can replace it. Thresholds, checklists and tenure live in an editable rules table, to be confirmed with AICTE.

• Live Prototype: https://safar-portal.vercel.app/
• Backend API: https://safar-backend-kqnf.onrender.com/docs
• Source Code: https://github.com/itxtarun2727/SAFAR-
• Video Demo: https://www.youtube.com/watch?v=NKunJOWPcYQ
```
* **Character Count:** ~1,920 / 10,000 characters

---

### Field 4: Idea Description
*(Constraint: Maximum 50,000 characters)*

```text
1. The Problem

AICTE holds security deposits from technical institutions, typically as FDRs. Each deposit has to be checked when it arrives, watched until maturity, renewed or released, and the whole history has to be available later. Today this depends on scanned copies, letters, and spreadsheets.

• A PDF or scan does not prove that the deposit exists at the bank, that the amount and dates are right, or that it is still in force.
• Records are spread across files and sheets, making the real-time status of an institution's deposit difficult to trace.
• Maturity and renewal dates are maintained manually, resulting in late detection of lapses.
• Release moves through several offices via physical letters, with no single audit trail of who approved what.
• Colleges receive minimal feedback: no live status tracking, and rejections occur without actionable reasons.

A real case illustrates this systemic risk: In its official answer to Lok Sabha Unstarred Question 2781 (10 December 2014), the Ministry of Human Resource Development stated that an institute in Bhopal had submitted a fake FDR of Rs 35 lakh dated 19 July 2007. The matter was taken up with the CBI, and AICTE filed a criminal complaint in September 2012.

2. Our Solution

SAFAR keeps what a college submits separate from what the bank confirms, and advances a deposit through its lifecycle only when an authorized actor or bank has validated it:

• Submit: The college enters deposit parameters (bank, reference number, amount, dates, joint title) and uploads documents. Each file is secured with a SHA-256 hash and version index.
• Bank Check: The backend sends details to a bank adapter. The reviewer inspects submitted vs. bank-confirmed values side-by-side for every field. A mismatch returns exclusively to the college with specific correction reasons. If the bank is unreachable, the case remains pending; it is never auto-verified.
• Review: A matched submission routes to the scrutiny officer of the affiliating university, who approves or rejects it with mandatory recorded remarks.
• Track: An approved deposit transitions to ACTIVE. An automated scheduler raises proactive alerts at 90, 60, and 30 days prior to maturity and on the maturity date. Renewals link directly to predecessor FDRs, preserving complete institutional lineage.
• Release: Post-maturity, the college initiates a release request. The university officer recommends clearance across a verified checklist. A senior AICTE manager (strictly segregated under Maker-Checker rules) authorizes payout, generating a bank code. The college independently claims its private voucher code (which AICTE staff never see). The deposit closes only when the bank confirms matching dual codes. Three incorrect attempts trigger an immediate lockout and alert the auditor.
• Audit: Every state transition is committed in the same database transaction as an audit block. Entries are cryptographically hash-chained via SHA-256; any database mutation breaks the chain and flags an alert.

3. User Personas & Access Boundaries

• College Administrator: Strictly scoped to inspecting their own institution's deposits, alerts, and claiming release vouchers.
• University Scrutiny Officer: Restricted to colleges affiliated with their university; verifies Two-Column Scrutiny and recommends release.
• AICTE Senior Manager: National scope across universities and states; grants final release authorization.
• CAG & AICTE Auditor: Read-only access across all records, failed verification logs, and the immutable audit ledger.
• Bank Branch User (Simulated): Restricted to deposits held at their bank; confirms dual-code presentation and lien discharge.

Access control and tenant boundaries are strictly verified on every API request.

4. Technical Approach

• Frontend: React 18, Vite, and Tailwind CSS, deployed on Vercel.
• Backend: Python with FastAPI and SQLAlchemy ORM, deployed on Render, packaged with Docker.
• Database: PostgreSQL (with zero-dependency SQLite fallback for evaluation). Monetary values are strictly stored as integer paise to prevent floating-point rounding errors.
• State Machine: A centralized, pure state machine engine enforces all transitions with strict guards (mandatory reason, dispute-free check, maturity validation, Maker != Checker verification, and checklist sign-off).
• Dynamic Rules Table: Reminder intervals, minimum tenure, checklist items, and attempt lockout limits are managed as dynamic database records with regulatory clause citations, not hardcoded in application logic.
• Secure Storage: Documents stored with SHA-256 version fingerprinting.
• Bank Adapter: Modular ISO 20022 / SFMS interface pattern. The prototype uses simulated demo banks; a production nodal-bank API or SFMS gateway can be swapped in without altering business logic.

5. Data Model

Core entities: University, Institution, User, Instrument (FDR), Document, FieldConfirmation, Alert, ReleaseAuthorization, Dispute, AuditEntry, Rule, and Bank. A university affiliates multiple institutions; each institution manages users and instruments. Instruments link to documents, bank confirmations, automated alerts, and release authorizations. Renewals maintain parent-child referential pointers.

6. Regulatory Safeguards

• A PDF certificate alone never verifies a deposit; independent bank confirmation is required.
• Automated verification anomalies are not treated as immediate fraud; they prompt human scrutiny review.
• Funds are never auto-discharged upon calendar maturity; release strictly mandates an institutional request, dual-level administrative approvals, and counter confirmation.
• Release codes are stored as SHA-256 hashes, are single-use, time-bound, and enforce a 3-attempt brute-force lockout.
• Administrative evaluator controls (demo time-travel clock, tamper testing) are restricted to demo mode.
• Data retention follows the provisions of the Digital Personal Data Protection (DPDP) Act, 2023.

7. What is Simulated in the Prototype

The core banking integration is simulated using realistic mock bank nodes (Demo Bank A, B, C) with synthetic regulatory records. AICTE thresholds, checklist criteria, and handbook clauses are configured as representative defaults in the database rules table. Because no public API currently permits third-party verification of statutory FDR liens, production deployment requires an operational agreement with designated nodal banks.

8. Feasibility and Viability

Built entirely on open-source frameworks and cloud-native architecture without proprietary or specialized hardware dependencies. A pilot rollout can commence immediately with a single affiliating university and one nodal bank. The underlying architecture is extensible to other regulatory bodies managing statutory institutional deposits (e.g., UGC, PCI, NMC).

9. Expected Benefits

• Accurate Records: A unified national registry displaying bank-confirmed values side-by-side with institutional claims.
• Timely Governance: Proactive stage-gate notifications prior to maturity; complete renewal traceability in a single chain.
• Fraud-Proof Encashment: Dual-approver segregation, two-part cryptographic codes, and an append-only audit trail.
• Institutional Transparency: Live status visibility, explicit rejection remarks, and streamlined digital re-submission.
• Administrative Efficiency: Elimination of manual paper sorting and file movement across regional offices.

10. Project Links & Verification

• Live Portal (Vercel): https://safar-portal.vercel.app/
• Backend API & Docs (Render): https://safar-backend-kqnf.onrender.com/docs
• Source Code (GitHub): https://github.com/itxtarun2727/SAFAR-
• Video Demonstration (YouTube): https://www.youtube.com/watch?v=NKunJOWPcYQ
```
* **Character Count:** ~4,520 / 50,000 characters

---

### Field 5: YouTube Link
```text
https://www.youtube.com/watch?v=NKunJOWPcYQ
```

---

## 3. SIH PPT Presentation Deck Structure (6-Slide Mapping)

If you are filling out the official **SIH2026-IDEA-Presentation-Format.pptx**, use this exact slide-by-slide structure:

* **Slide 1: Title & Team Details**
  * Project Title: SAFAR (Smart AICTE FDR Automation & Registry)
  * Team Name: Code Blooded | Problem Statement: 26265
  * Institute & Team Members
* **Slide 2: Proposed Solution & Problem Statement**
  * Copy Section 1 (The Problem) and cite Lok Sabha Unstarred Question 2781 (2014) regarding fake FDRs.
  * Contrast current physical paper workflow vs. SAFAR digital registry.
* **Slide 3: Technical Architecture & Core Innovation**
  * 3-Tier Multi-Tenancy (HQ $\rightarrow$ Affiliated Universities $\rightarrow$ Isolated Colleges).
  * Two-Column Trust Scrutiny (College claim vs. Bank API fact).
  * Restored Scrutiny Gate Invariant (Bank match never auto-activates without officer review).
* **Slide 4: Security, Cryptography & State Machine**
  * Zero-Knowledge Dual-Key Encashment (Bank Code + Secret College Voucher).
  * SHA-256 Hash-Chained Audit Ledger with live tamper detection.
  * DPDP Act 2023 alignment and 3-attempt brute-force lockout.
* **Slide 5: Feasibility, Viability & Simulation Transparency**
  * Cloud deployment on Vercel (React) and Render (FastAPI + PostgreSQL).
  * Transparent disclosure of simulated ISO 20022 bank adapter and future nodal bank pathway.
  * Extensibility to other regulators (UGC, PCI, NMC).
* **Slide 6: Expected Benefits & Verification Proof**
  * 100% paperless processing, zero unauthorized premature encashment.
  * Live links: Web app, Swagger docs, GitHub repo, YouTube walkthrough.
