# SAFAR: DESIGN.md (UI and UX design system)

SAFAR = Smart AICTE FDR Automation & Registry. This file tells the frontend how the product should look, read and behave. Follow it for every screen. Where it conflicts with a quick guess, follow this file. Read it with `IDE_SYSTEM_PROMPT` / the project brief, which defines the rules and data.

Stack: React + Vite + TypeScript + Tailwind. Icons: Lucide. Charts: Recharts (simple bars and counts only).

---

## 1. Design intent

SAFAR is a regulator's working tool. It must feel calm, exact and trustworthy, not flashy.

- **Trust first.** The most important thing on any case screen is who vouched for each fact: the institution (submitted) or the bank (confirmed). Show it every time.
- **Honest about the simulation.** The bank is simulated. Say so visibly, always, without apology.
- **Next action is obvious.** Every list and case shows what is pending and who must act next.
- **Dense but readable.** Officers scan queues all day. Use tables, tight spacing and clear status badges, not large cards.
- **Government-appropriate.** Plain language, high contrast, no decorative animation, no gradients or glass effects.

Three words for the feel: **steady, precise, accountable.**

## 2. Design tokens

Define as Tailwind theme values and CSS variables. Use tokens only; no raw hex in components.

### Colour

| Token | Hex | Use |
| --- | --- | --- |
| `ink` | `#0F1B2D` | Primary text |
| `ink-soft` | `#4A5568` | Secondary text |
| `navy-700` | `#12355B` | Primary brand, app bar, primary buttons |
| `navy-600` | `#1B4A7A` | Hover and active |
| `navy-50` | `#EAF1F8` | Selected rows, soft fills |
| `surface` | `#FFFFFF` | Cards, tables |
| `canvas` | `#F5F7FA` | App background |
| `line` | `#D8DEE6` | Borders, dividers |
| `saffron-500` | `#E58A1F` | Accent for the demo clock and highlights only |
| `ok-600` | `#1E7F5C` | Bank-confirmed, match, active |
| `ok-50` | `#E6F4EE` | Soft fill for ok |
| `warn-600` | `#B7791F` | Pending, due soon, manual review |
| `warn-50` | `#FDF3E1` | Soft fill for warn |
| `bad-600` | `#B42318` | Mismatch, overdue, blocked |
| `bad-50` | `#FDECEA` | Soft fill for bad |
| `info-600` | `#2563A8` | Informational, simulated notices |
| `info-50` | `#E8F0FA` | Soft fill for info |

Rules:
- Never use colour alone to carry status. Always pair it with an icon and a text label.
- Text on any fill must meet at least 4.5:1 contrast. Check before shipping.
- Saffron is a rare accent, not a brand colour for buttons.

### Typography

- **Font:** Noto Sans (covers Devanagari, so Hindi labels can be added later). Fallback: system sans-serif.
- **Mono:** JetBrains Mono for FDR reference numbers, hashes and amounts in tables.
- Scale: 12 (meta) / 14 (body and tables) / 16 (inputs) / 20 (section title) / 24 (page title) / 32 (dashboard numbers).
- Weights: 400 body, 500 labels, 600 titles. Line height 1.5 for text, 1.3 for headings.
- Show amounts in Indian grouping (for example Rs 12,50,000) from integer paise. Dates as `24 Oct 2026` in IST.

### Spacing, shape, elevation

- 4 px base grid. Common steps: 4, 8, 12, 16, 24, 32.
- Radius: 6 px for inputs and buttons, 8 px for cards and panels.
- Borders over shadows: 1 px `line` borders. One soft shadow only for menus and dialogs.
- Page max content width 1280 px; tables may use full width.

### Motion

Minimal. 150 ms fades for menus and toasts. No page transitions, no bouncing. Respect `prefers-reduced-motion`.

## 3. Layout

- **App shell:** top bar (navy-700) + left sidebar (240 px, collapsible on tablet) + content area on `canvas`.
- **Top bar:** SAFAR wordmark, current role and user name, notification bell, user menu, and (demo mode) the Demo Clock chip.
- **Persistent simulation banner** directly under the top bar on every authenticated page, `info-50` fill:
  "Bank confirmation is simulated in this prototype. Synthetic data only."
- **Sidebar items by role** (show only what the role can use):
  - Institution: My deposits, Submit FDR, Alerts, Release requests.
  - AICTE officer / senior: Dashboard, Queues, Release requests, Instruments, Reports.
  - Bank officer (simulated): Verification inbox, Daily feed.
  - Auditor: Audit log, Evidence packs, Instruments (read-only).
  - Admin: Users, Rules, Demo controls.
- **Responsive:** designed for desktop first. At tablet width the sidebar collapses to icons. Forms and tables must still work at 768 px. Phones need only to be readable, not optimised.
- **Page anatomy:** page title + one-line purpose, filters row, main content, and a right-hand "Next action" panel on case screens.

## 4. Status language (one mapping used everywhere)

Every state uses the same badge: icon + label + colour. Do not invent new labels.

| State | Label | Colour | Icon (Lucide) |
| --- | --- | --- | --- |
| SUBMITTED | Submitted | info | `FileUp` |
| BANK_CHECK | With bank (simulated) | warn | `Landmark` |
| ACTIVE | Active, bank-confirmed | ok | `ShieldCheck` |
| RENEWAL_PENDING | Renewal pending | warn | `RefreshCw` |
| REJECTED | Rejected by bank | bad | `XCircle` |
| DISPUTED | Disputed, release blocked | bad | `Ban` |
| RELEASE_REQUESTED | Release requested | info | `Send` |
| COMPLIANCE_CHECK | Compliance check | warn | `ClipboardCheck` |
| APPROVED | Approved | ok | `CheckCircle2` |
| BANK_RELEASE_PENDING | Awaiting bank release | warn | `Hourglass` |
| CLOSED | Closed | neutral (`ink-soft`) | `Archive` |

Verification result badges: **Match** (ok), **Mismatch** (bad, with reason code), **Pending** (warn), **Source unavailable** (warn, with retry), **Manual review required** (warn).

Alert stage chips: 180d, 90d, 60d, 30d, 7d, Due today, Overdue. Colour moves from info to warn to bad as the date nears. Never show "Verified" without saying by whom.

## 5. Core components

Build these once in `src/components` and reuse.

1. **StatusBadge** (state and verification variants, per section 4).
2. **TwoColumnTrustView** (the signature component).
   - Two columns: "Submitted by institution" and "Confirmed by bank (simulated)".
   - One row per field: reference number, bank, amount, issue date, maturity date, holder, lien in favour of AICTE.
   - A result badge per row. A mismatching row has a `bad-50` fill, the reason code (for example MATURITY_MISMATCH) and the two values side by side.
   - Header shows an overall trust summary: "5 of 7 fields confirmed, 1 mismatch, 1 pending".
   - Rows with no bank value yet show "Not yet confirmed" in `ink-soft`, never a blank.
3. **QueueTable** (sortable, filterable, paginated; row click opens the case; columns: institution, reference, amount, maturity date, days left, status, next action, assignee).
4. **StatCard** (large number, label, optional trend). Used for the six dashboard counts: Active, Expiring, Matured, Renewed, Released, Pending.
5. **Timeline** (vertical; each event has actor, role, action, reason, time, and a small hash chip `a3f9…c21`).
6. **AlertList** (stage chip, due date, channel, sent, acknowledged; an Acknowledge button for the right role).
7. **LineageChain** (horizontal chain of FDR cards: old reference to new reference, with dates and the bank re-confirmation status).
8. **ReleaseStepper** (Request, Scrutiny, Clearances, Approval, Bank release, Closed; checklist items with owner and tick state; a blocking banner when a dispute is open).
9. **AuditChainViewer** (list of entries with prev-hash to row-hash links; an "Verify integrity" button; a broken link is shown in `bad` with the sequence number).
10. **DemoClockChip** (shows the current simulated date; click opens a small panel to move the clock forward by 30 / 90 / 180 days and a "Run scheduler now" button; only visible in demo mode; saffron outline).
11. **SimulatedBankBanner** (the persistent notice in section 3).
12. **EvidencePackButton** (exports case history, document hashes and audit entries; shows a small progress state, then a download).
13. **EmptyState, ErrorState, Skeleton** (see section 8).
14. **ConfirmDialog** (for any approve, reject, release or dispute action; requires a reason text; shows who is acting and in which role).

## 6. Screens

### Login
Simple centred card on `canvas`. Fields: username, password. Below the form, in demo mode only, a "Demo users" list with one-click fill for each role. Plain notice: "Role-based access with demo users."

### Institution: My deposits
Table of the institution's instruments with status badge, maturity date, days left and next action. A "Submit FDR" primary button. A strip at the top shows alerts due soon.

### Institution: Submit FDR
One page form in two groups: Instrument details (bank, reference number, amount, issue date, maturity date, Trust/Society, linked institution) and Evidence (drag-and-drop upload, file name, size, SHA-256 shown after upload). Inline validation on blur. On submit, show the case page with status "With bank (simulated)".

### Instrument detail (shared by all roles)
Header: reference number (mono), institution, trust, status badge, maturity date and days left. Tabs:
1. **Overview** (key facts, next action panel, open flags).
2. **Trust view** (TwoColumnTrustView).
3. **Documents** (versions, hash, uploaded by and when, download).
4. **Lineage** (LineageChain).
5. **Alerts** (AlertList).
6. **History** (Timeline plus scrutiny notes).
The right-hand "Next action" panel always says who must do what, for example "Waiting for bank checker" or "Needs senior approval".

### AICTE: Dashboard
Six StatCards (Active, Expiring, Matured, Renewed, Released, Pending), then three compact lists: Pending verification, Upcoming maturities (next 90 days), Overdue and disputed. Filters by state, bank, date range and assignee. Clicking a number or list item opens the matching queue.

### AICTE: Queues
Tabs: Pending verification, Upcoming maturity, Overdue renewal, Disputes, Release requests. Each is a QueueTable with bulk assign.

### Bank console (simulated)
Clearly framed with the simulation banner in a stronger style. Inbox of instruments awaiting confirmation. Case view lists each field with Confirm, Mismatch (choose a reason code) and Cannot confirm actions. A second bank user acts as checker; the maker cannot approve their own entry (disable the button and say why). Also a "Daily feed" page to upload or generate the CSV feed.

### Release workflow
ReleaseStepper at the top; below it, the checklist (three placeholder items from the rules table, marked "placeholder"), scrutiny notes, and the approval panel. If a dispute is open, a `bad-50` banner states "Release is blocked: dispute open" and disables approval. Approval needs a different user from the maker and a written reason. Final screen shows the bank release confirmation and the Evidence Pack button.

### Audit log (auditor and admin)
AuditChainViewer with filters by entity, actor, date range. "Verify integrity" runs the check and shows a clear pass or fail with the first broken sequence number.

### Admin: Rules
Table of rules with key, value, clause reference and effective date. Edit in place with a reason; each change is itself audited. Rows with `TODO(confirm)` show a warning chip.

## 7. Content and tone

- Plain English. Short sentences. No jargon without a tooltip.
- Honest wording: "Confirmed by bank (simulated)", "Not yet confirmed", "Source unavailable, retrying", "Manual review required".
- Never say "fraud" or "fake" about a document. Say "Mismatch with bank record" or "Needs manual review".
- Never say "verified" without naming the source.
- Button labels are verbs: Submit FDR, Confirm, Request release, Approve release, Acknowledge.
- Destructive or irreversible actions use a ConfirmDialog with a required reason.
- Numbers shown on any "impact" screen must be measured values labelled "synthetic data".

## 8. States: loading, empty, error

- **Loading:** skeleton rows that match the final layout. No spinners over whole pages.
- **Empty:** a short sentence and one action, for example "No instruments yet. Submit your first FDR."
- **Error:** say what failed and what to do. Bank unavailable: "The bank source is unavailable. We will retry, and you can request manual verification."
- **Offline or slow backend (free hosting may be asleep):** show "Waking the server, this can take a minute" after 3 seconds, instead of a blank screen.

## 9. Accessibility (build to the guidelines; do not claim compliance)

- Build to GIGW 3.0 and WCAG 2.1 AA guidelines.
- Full keyboard use, visible focus ring (2 px `info-600` outline with offset), logical tab order.
- Every input has a visible label. Errors are linked to fields and announced.
- Tables use proper header cells and sortable headers announce their state.
- Status is never colour only (icon and text always).
- Minimum touch and click target 40 px.
- Language attribute set; structure allows Hindi labels later (no text inside images).

## 10. Frontend structure and conventions

```
src/
  pages/        Login, InstitutionHome, SubmitFdr, InstrumentDetail, Dashboard, Queues, BankConsole, ReleaseFlow, AuditLog, AdminRules
  components/   StatusBadge, TwoColumnTrustView, QueueTable, StatCard, Timeline, AlertList, LineageChain,
                ReleaseStepper, AuditChainViewer, DemoClockChip, SimulatedBankBanner, EvidencePackButton,
                EmptyState, ErrorState, Skeleton, ConfirmDialog
  api/          typed client, one function per endpoint, error mapping
  auth/         token storage, role guards, route protection
  theme/        tailwind tokens, status map (section 4) as one exported object
```

- One `statusMap.ts` holds the section 4 mapping. Components read from it.
- All formatting (money, dates, hashes) goes through shared helpers.
- Role guards hide what a role cannot use, and the API still enforces access.
- Components receive data as props; pages fetch.
- Add a Storybook-style demo page (`/dev/components`) in demo mode listing every component and state.

## 11. Demo mode (for judges)

- A "Demo controls" menu for Admin: move the clock, run the scheduler now, load scenario 1 to 6, reset data.
- A scenario launcher that jumps to the right screen for each of the six official test scenarios (submission, mismatch, validity, approaching maturity, renewal, authorised release).
- The simulation banner and Demo Clock chip are always visible so nobody mistakes the demo for a live bank link.

## 12. Do and don't

Do:
- Show submitted and confirmed side by side wherever a fact appears.
- Show who must act next on every case.
- Keep tables sortable, filterable and paginated.
- Use the shared status map and badge everywhere.

Don't:
- Don't use colour alone for status.
- Don't write "verified" without a source, or "fraud" about a document.
- Don't hide the simulation notice.
- Don't add blockchain or AI imagery, gradients, glass effects or decorative motion.
- Don't show unmeasured numbers on impact screens.
- Don't invent new status names, colours or button styles.

## 13. Tailwind starter

```ts
// tailwind.config.ts (theme.extend.colors)
colors: {
  ink: { DEFAULT: '#0F1B2D', soft: '#4A5568' },
  navy: { 50: '#EAF1F8', 600: '#1B4A7A', 700: '#12355B' },
  canvas: '#F5F7FA',
  line: '#D8DEE6',
  saffron: { 500: '#E58A1F' },
  ok:   { 50: '#E6F4EE', 600: '#1E7F5C' },
  warn: { 50: '#FDF3E1', 600: '#B7791F' },
  bad:  { 50: '#FDECEA', 600: '#B42318' },
  info: { 50: '#E8F0FA', 600: '#2563A8' },
},
fontFamily: {
  sans: ['"Noto Sans"', 'system-ui', 'sans-serif'],
  mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
},
borderRadius: { md: '6px', lg: '8px' },
```
