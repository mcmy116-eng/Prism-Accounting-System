# Project Journal

A running log of what happened on this project, in plain language, session by session.

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
