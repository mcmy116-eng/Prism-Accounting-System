# Project Journal

A running log of what happened on this project, in plain language, session by session.

---

## 2026-08-02 — Staff expense claims, audit trail, smarter AI

**Why:** Prism is now live and trading, and the brief asked for staff expense
claims, a proper audit trail, AI that gives a confidence level and learns, easy
exports, and comfortable mobile receipt capture. The core books already existed —
this round filled the gaps.

**What we built:**
- **Staff Expense Claims** — a whole new module. Staff (a new role) log in on their
  phone, create a claim, snap a receipt (the camera opens automatically), AI reads
  it and suggests a category with a **confidence bar**, and they submit. The admin
  approves / rejects / requests clarification / marks paid. Full lifecycle:
  Draft → Submitted → AI Reviewed → Pending Approval → Approved/Rejected → Paid.
  Approval posts a real, balanced ledger entry; "mark paid" reimburses from a bank
  account. Staff can only ever see their own claims (enforced, tested — others get 403).
- **AI category learning** — every time you approve a categorisation, the system
  remembers the vendor → account mapping and is more confident next time.
- **Audit trail** — an append-only log of who did what and when, on its own admin
  page. Nothing financial is ever hard-deleted.
- **Anomaly flags** — claims get flagged for missing receipts, unusually large
  amounts, and possible duplicates, on the list and the dashboard.
- **CSV export** for expense claims; **dashboard** now shows claims pending approval
  and amounts awaiting reimbursement.
- **Mobile polish** — the sidebar collapses to a top strip, tables reflow, tap
  targets and file inputs are enlarged on small screens.
- **Auto-migration** — added `app/schema.py::ensure_schema()` so new tables/columns
  appear on deploy with no manual migration step (works on SQLite and Postgres).

**Tested end-to-end:** full claim lifecycle posts a balanced journal entry, the
trial balance still balances, the learning loop improves suggestions, staff
isolation returns 403, and every page renders (14/14 smoke-tested).

**Also written:** `docs/PROPOSAL.md` — the full 9-part system proposal (architecture,
data model, roles, screens, AI workflow, reporting, security, phased plan, and the
open decisions to confirm before the next phase).

**Decisions still to confirm** (see the end of `docs/PROPOSAL.md`): reimbursement vs
corporate-card handling, VAT/GST regimes, Google login / 2FA, approval thresholds,
staff onboarding method, Excel vs CSV priority, backup cadence, which sales
integrations, and notification channels.

---

## 2026-07-12 — Built and deployed the whole system

**What we built:** A complete accounting web app for Prism Group International Limited —
double-entry ledger underneath everything, so the books can never silently go
out of balance.

- Chart of accounts, set up for an e-commerce + digital marketing business
- Customers & vendors
- Invoicing — line items, tax, PDF export, recurring schedules, payment tracking
- Bills & expenses — upload a photo or PDF and AI reads the vendor/dates/amounts
  for you, you just confirm and approve
- Bank accounts — CSV statement import and reconciliation
- Multi-currency, and segments to compare E-commerce vs Digital Marketing vs G&A
- Multiple user logins with different permission levels (admin / bookkeeper / viewer)
- Reports: Profit & Loss (overall and by segment), Balance Sheet, Cash Flow,
  Trial Balance, AR/AP Aging, Tax Summary, Budget vs Actual

**What we deployed:**
- Code pushed to GitHub: [github.com/mcmy116-eng/Prism-Accounting-System](https://github.com/mcmy116-eng/Prism-Accounting-System)
- Live on Railway, with its own database and permanent file storage for uploaded bills
- Set up from scratch: Homebrew, GitHub CLI, Railway CLI, all authenticated

**Problems we hit and fixed along the way** (so future-us remembers):
- Homebrew installed but wasn't on the PATH yet — needed one extra command to link it
- The app was hardcoded to a fixed port; fixed to use whatever port Railway assigns
- Having both a `Dockerfile` and a `Procfile` confused Railway about which start
  command to use — removed the Procfile
- A `PORT` variable had gotten added with the literal text `$PORT` as its value
  instead of being left out — this is the one to check first if the app ever
  refuses to start again (deploy logs will say `Error: '$PORT' is not a valid
  port number`)

**Reference guides made along the way** (kept up to date with everything above):
- Using the app day-to-day + deploying to Railway, step by step
- Absolute-beginner Terminal/GitHub walkthrough, plus where to get the AI key

---

## Next up (not started yet)

Requested 2026-07-12. Some of this already exists — noted below.

1. **Multiple login** — *already built.* Settings → Users. Might just need to be
   easier to find, or you might want something specific (e.g. Google login) —
   worth clarifying.
2. **Upload invoices/receipts from phone or computer** — *mostly already works*
   from any device's browser today. Likely needs a pass to make the upload
   screen more comfortable on a small phone screen.
3. **Easy access to saved data** — needs more detail on what this means in
   practice (search? filters? a way to export everything?).
4. **Shopify sales integration** — *not built.* Would pull orders from Shopify
   automatically instead of entering them by hand. Real scoping needed:
   one store or several, orders only or also fees/refunds, how often it syncs.
5. **Generate financial statements** — *reports already exist* on-screen for
   all the standard statements. This might mean: exportable PDF/Excel versions
   of those (right now only invoices export to PDF).
6. **Daily P&L dashboard** — dashboard currently shows month-to-date, not a
   single day. Would add a "today" view, possibly a small trend chart.

Next session: turn this list into a real plan — confirm what each item actually
means, then build.
