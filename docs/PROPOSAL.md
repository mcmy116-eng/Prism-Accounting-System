# Prism Group International Limited — Accounting & Cash-Flow System
## System Proposal & Roadmap

_Last updated: 2026-08-02_

This document answers the nine deliverables in the brief. It is written against
the **system that already exists in this repository** — a working, deployed,
double-entry accounting platform — and marks each item as **Built**, **Built this
round**, or **Planned** so you can see exactly where we are.

> **Where we are today:** the core books (chart of accounts, invoicing, bills with
> AI receipt reading, bank reconciliation, multi-currency, segment reporting,
> multi-user roles, and the full suite of financial statements) are already live.
> This round added the **Staff Expense Claims** workflow, an **audit trail**,
> **AI category confidence + a learning loop**, **CSV export**, **anomaly flags**,
> and **mobile-friendly receipt capture** — closing the biggest gaps in the brief.

---

## 1. Recommended architecture & technology stack

**Approach: cloud-first, server-rendered web app — one codebase, every device.**
A phone browser and a desktop browser hit the same secure URL and the same
central database, so data is always in sync. No app-store installs, no separate
mobile build to maintain.

| Layer | Choice | Why |
|---|---|---|
| Backend | **Python + Flask** | Small, readable, easy to hire for and extend |
| Data | **SQLAlchemy ORM** over **PostgreSQL** (prod) / SQLite (dev) | Managed, backed-up cloud Postgres; portable locally |
| Auth | **Flask-Login**, PBKDF2-hashed passwords, role-based access | Session security handled centrally |
| Accounting core | **Double-entry ledger** (`app/ledger.py`) | Books can never silently go out of balance |
| AI | **Anthropic Claude API** (vision + text) | Reads receipts/invoices; suggests categories with a confidence score |
| Files | Object storage / persistent volume (`UPLOAD_FOLDER`) | Receipts stored durably alongside their transaction |
| UI | Server-rendered templates + responsive CSS | Works identically on desktop and mobile; nothing to install |
| Hosting | **Railway** (current), or Render/Fly.io — Docker image included | Managed Postgres + persistent disk + TLS |

**Why not a heavier SPA/mobile-native stack?** For a growing SME the priority is a
reliable record and low maintenance. A single server-rendered app gives real-time
cross-device consistency (the server is the single source of truth) without the
cost of building and syncing a separate mobile client. If a native app is wanted
later, the same backend can expose a JSON API without rework.

---

## 2. Database structure (key tables & fields)

The schema is normalised around a **general ledger** so every figure on every
report traces back to a balanced journal entry.

**Core ledger**
- `accounts` — chart of accounts: `code, name, type (asset/liability/equity/revenue/expense), subtype, is_bank, system_locked`
- `journal_entries` — `date, memo, reference, source_type, source_id, created_by, is_posted`
- `journal_lines` — `account_id, debit_cents, credit_cents, cost_center_id, contact_id, description`

**Money in / money out**
- `invoices` + `invoice_lines` (AR), `recurring_invoices`
- `bills` + `bill_lines` (AP)
- `payments` + `payment_allocations` (money received/paid, allocated to invoices/bills)
- `bank_accounts` + `bank_transactions` (CSV import + reconciliation)

**Staff expense claims** *(new this round)*
- `expense_claims` — `number, staff_id, title, business_purpose, claim_date, currency, cost_center_id, status, subtotal/tax/total_cents, amount_paid_cents, ai_confidence, ai_summary, reviewer_notes, submitted_at, decided_at, decided_by, paid_at, journal_entry_id, payment_journal_entry_id`
- `expense_claim_lines` — `merchant, expense_date, description, amount_cents, account_id, tax_rate_id, cost_center_id, category_guess, ai_confidence`

**Documents & AI**
- `documents` — `filename, filepath, mimetype, uploaded_by, extraction_status, extracted_json` — linked to a `bill_id` **or** a `claim_id`
- `category_rules` *(new)* — learned `keyword → account_id (hits)` mappings that improve AI suggestions over time

**Governance & reference**
- `audit_logs` *(new)* — append-only `at, user, action, entity_type, entity_id, summary`
- `users` (`role`), `contacts` (customers/vendors), `cost_centers` (segments), `tax_rates`, `currencies`, `exchange_rates`, `budgets`, `company_settings`

**Design rules:** all money is stored as **integer cents** (no float rounding);
records are **voided via reversing entries, never deleted**; system-locked
accounts (AR, AP, tax, reimbursements payable) are referenced by fixed code.

---

## 3. User roles & permissions

| Role | Sees | Can do |
|---|---|---|
| **Master Admin** | Everything | All accounting, approvals, user management, settings, audit log |
| **Bookkeeper** | Everything | Create/post invoices, bills, payments, reconciliations; approve claims |
| **Staff** *(new)* | **Only their own expense claims** | Submit claims, upload receipts, pick a category, add a business purpose, track status |
| **Viewer** | Read-only books | For an external accountant reviewing the records |

Staff isolation is enforced server-side: a staff user is redirected away from the
financial dashboard, their claim list is filtered to their own records, and any
attempt to open another person's claim returns **403 Forbidden** (verified by
test). Additional access can be granted later by changing a user's role.

---

## 4. Main pages / screens & the mobile user journey

**Master Admin / Bookkeeper:** Dashboard · Invoices · Customers & Vendors · Bills &
Expenses · **Expense Claims** · Bank Accounts · Payments · Chart of Accounts ·
Reports · Settings · Users · **Audit Log**.

**Staff (mobile-first) journey — capture an expense in under a minute:**
1. Open the site on the phone, log in → lands directly on **My Expense Claims**.
2. Tap **New claim**, give it a title + business purpose.
3. Tap **Add a receipt** → the phone **camera opens** (`capture="environment"`).
   Snap the receipt.
4. AI reads the merchant, date, amount and **suggests a category with a confidence
   bar**. The staffer confirms or changes it.
5. Tap **Submit for approval** → tracks status live: AI Reviewed → Pending Approval
   → Approved → Paid.

The interface is responsive: the sidebar collapses to a top strip, tables reflow,
and tap targets/file inputs are enlarged on small screens.

---

## 5. AI receipt-review & category-suggestion workflow

1. **Capture** — photo or PDF uploaded from any device, linked to its claim/bill.
2. **Read (OCR + understanding)** — Claude vision extracts merchant, date,
   currency, amounts, and line items into a structured draft (`app/ai_extract.py`).
3. **Categorise with confidence** — each line is matched to a GL account and given
   a **0–100% confidence** score (`app/ai_categorize.py`), driven by:
   - **learned rules** from past human approvals (strongest signal),
   - a built-in keyword map for common SME expenses,
   - fuzzy matching against account names,
   - a low-confidence "please confirm" fallback when unsure.
4. **Human approval** — nothing posts to the ledger until a person confirms.
   Low-confidence lines are visually flagged for a second look.
5. **Learn** — on approval, the confirmed `merchant/keyword → account` mapping is
   reinforced, so repeated vendors get more confident over time (verified: an
   approved "Cafe Deco → Travel & Entertainment" immediately raised that vendor's
   next-time confidence).

---

## 6. Dashboard & reporting structure

**Dashboard:** cash on hand, MTD revenue / net income / expenses, AR, AP,
**claims pending approval**, **approved-awaiting-reimbursement**, a **claims-to-
approve queue**, overdue invoices, and recent ledger activity. Claims surface
**anomaly flags** — missing receipt, unusually large amount, possible duplicate.

**Reports (built):** Profit & Loss (overall + by segment), Balance Sheet, Cash Flow,
Trial Balance, AR/AP Aging, Tax Summary, Budget vs Actual.

**Export:** Every core statement (P&L, Balance Sheet, Cash Flow, Trial Balance,
AR/AP Aging, Tax Summary) exports to **CSV, Excel (.xlsx) and PDF** using the same
date/segment filters as the on-screen report, so the file always matches the view.
Expense claims export to line-level CSV. The Excel files use real numeric cells for
easy re-use; PDFs are formatted for accountant hand-off.

---

## 7. Data security, backup, audit-log & access control

- **Access control** — role-based, enforced on every route; staff can only reach
  their own data; admin-only areas (users, audit log, settings) are locked down.
- **Passwords** — never stored in plaintext (PBKDF2-SHA256 hashes).
- **Audit trail (new)** — an append-only `audit_logs` table records who did what
  and when (login, create, edit, submit, approve, reject, clarify, pay, void),
  viewable by the admin under **Audit Log**. Financial records are **never hard-
  deleted** — they are reversed, preserving history.
- **Transport** — served over HTTPS/TLS by the host.
- **Backup** — managed Postgres provides automated backups/point-in-time recovery;
  uploaded receipts live on a persistent volume/object store. *(Confirm backup
  cadence with the host — see decisions below.)*
- **Secrets** — API keys and the session key are environment variables, not code;
  the first-run admin password should be rotated out of the environment after
  deploy.

---

## 8. Phased development plan

- **Phase 0 — Core books _(DONE, live)_**: double-entry ledger, chart of accounts,
  invoicing, bills + AI receipt reading, bank import/reconciliation, payments,
  multi-currency, segments, roles, full financial statements.
- **Phase 1 — Staff claims, audit & AI polish _(DONE this round)_**: staff role +
  claim workflow (Draft → Submitted → AI Reviewed → Pending Approval →
  Approved/Rejected → Paid), audit log, AI confidence + learning, anomaly flags,
  CSV export, mobile receipt capture.
- **Phase 2 — Reporting & export depth** _(export done)_: **PDF/Excel/CSV export of
  every statement is now live**; still to come — saved report filters and a
  scheduled month-end management-accounts pack.
- **Phase 3 — Automation & integrations**: Shopify/Stripe daily sales sync, live FX
  rates, automated bank feeds, recurring-bill reminders, email notifications on
  claim status changes.
- **Phase 4 — Multi-company / group**: consolidation across Prism Group entities,
  inter-company transactions, per-entity permissions.

---

## 9. Decisions to confirm before the next build phase

1. **Reimbursement accounting** — confirm approved claims should credit a dedicated
   **Employee Reimbursements Payable** liability (as built), and whether corporate-
   card spend should be handled differently from out-of-pocket.
2. **Base currency & tax** — base is set to **HKD**; confirm whether Hong Kong
   (no VAT) is the only regime, or if we must handle VAT/GST for other markets.
3. **Login method** — email/password today. Do you want Google login / 2-factor
   authentication for the master account?
4. **Approval thresholds** — should some claim sizes auto-approve, or require a
   second approver above a limit?
5. **Staff onboarding** — how many staff initially, and should they self-register
   (invite link) or be created by the admin?
6. **Export format priority** — is Excel (`.xlsx`) needed before CSV is enough, and
   which reports are most urgent to export?
7. **Backup & retention** — required backup frequency and how long to retain
   receipts/records for tax/audit (e.g. 7 years).
8. **Integrations** — which sales channels (Shopify? Stripe? others) and how often
   should they sync?
9. **Notifications** — email/WhatsApp alerts on submit/approve/reject, and to whom?
