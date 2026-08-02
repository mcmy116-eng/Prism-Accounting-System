# Prism Group International Limited — Accounting System

A self-hosted, full double-entry accounting system built for an e-commerce + digital
marketing services business. Upload vendor bills/receipts and AI reads them for you;
issue customer invoices; every transaction posts to a real general ledger; get proper
financial statements out the other end.

## Features

- **Double-entry ledger core** — every invoice, bill, and payment posts a balanced
  journal entry. Nothing can silently go out of balance (see Trial Balance report).
- **AI bill/receipt capture** — upload a PDF or photo of a vendor bill and Claude reads
  the vendor, dates, amounts and line items into a draft. You review, map each line to
  a GL account, and approve before anything posts.
- **Invoicing (AR)** — line items, tax, PDF generation, recurring invoice schedules,
  payment tracking, aging.
- **Bills & Expenses (AP)** — upload or manual entry, approval workflow, payment
  tracking, aging.
- **Staff expense claims** — staff submit reimbursement claims from their phone,
  snap a receipt (camera capture), AI reads it and suggests a category with a
  **confidence score**, admin approves/rejects/requests clarification/marks paid.
  Approval posts a balanced entry crediting *Employee Reimbursements Payable*;
  "mark paid" clears it against a bank account. Staff see **only their own** claims.
  Workflow: Draft → Submitted → AI Reviewed → Pending Approval → Approved/Rejected → Paid.
- **AI category learning** — every approved categorisation reinforces a
  `keyword → account` rule, so repeat vendors get more confident suggestions over time.
- **Audit trail** — append-only log of who did what and when (login, create, edit,
  submit, approve, reject, pay, void), viewable by admins under *Audit Log*.
- **Anomaly flags** — claims are flagged for missing receipts, unusually large
  amounts, and possible duplicates.
- **CSV export** — expense claims export to line-level CSV.
- **Bank accounts & reconciliation** — CSV statement import, transaction matching
  against ledger entries, quick-entry posting for fees/interest.
- **Multi-user & roles** — admin / bookkeeper / staff / viewer.
- **Multi-currency** — per-contact/invoice/bill currency, exchange rate table.
- **Cost centers / segments** — pre-seeded with E-commerce, Digital Marketing
  Services, and General & Admin so you can see P&L by business line.
- **Reports** — P&L (overall and by segment), Balance Sheet, Cash Flow (indirect
  method), Trial Balance, AR/AP Aging, Tax Summary, Budget vs Actual.

## Tech stack

Flask + SQLAlchemy + SQLite (swap to Postgres for production via `DATABASE_URL`),
server-rendered templates, no build step. AI extraction uses the Anthropic API.

## Local development

```bash
cd accounting
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env   # then edit .env
ADMIN_EMAIL=you@example.com ADMIN_PASSWORD='a-strong-password' ./venv/bin/python seed.py
./venv/bin/python run.py
```

Visit http://localhost:5050 and log in with the admin credentials you set.

## Environment variables

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask session signing key — set a long random string in production |
| `DATABASE_URL` | Defaults to a local SQLite file. Set to a Postgres URL for production. |
| `ANTHROPIC_API_KEY` | Enables AI extraction on bill upload. Without it, uploads still work but fall back to manual entry with a clear message. |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Used once by `seed.py` to create the first admin user. |
| `UPLOAD_FOLDER` | Where uploaded bill/receipt files are stored. Needs to be a **persistent** disk in production (see below). |
| `PORT` | Port to listen on (default 5050). |

## Deploying to the cloud

This app needs two things that don't exist on most "ephemeral filesystem" hosts by
default: a **persistent database** and **persistent file storage** for uploaded bills.
Two straightforward options:

### Option A — Railway / Render / Fly.io with a volume + Postgres (recommended)

1. Create a Postgres database on the platform and set `DATABASE_URL` to it (swap
   `postgres://` → `postgresql://` if needed; SQLAlchemy requires the latter).
2. Attach a persistent volume mounted at, e.g., `/data`, and set
   `UPLOAD_FOLDER=/data/uploads`.
3. Set `SECRET_KEY`, `ANTHROPIC_API_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.
4. Deploy with the included `Dockerfile` (or `Procfile` if the platform is
   buildpack-based). The release step runs `python seed.py`, which creates the chart
   of accounts and the first admin user on first deploy only.
5. **Rotate/remove `ADMIN_PASSWORD` from the environment after first deploy** — it's
   only read once (skipped if the admin user already exists), but there's no reason to
   leave a plaintext password sitting in platform env vars indefinitely.

### Option B — Single VM / Docker Compose

Run the container behind a reverse proxy (Caddy/nginx) with TLS, mount a host volume
for `/app/instance` and `/app/uploads`, and either keep SQLite (fine for a small team)
or point `DATABASE_URL` at a Postgres container.

```bash
docker build -t prism-accounting .
docker run -d -p 5050:5050 \
  -e SECRET_KEY=... -e ANTHROPIC_API_KEY=... \
  -v prism_data:/app/instance -v prism_uploads:/app/uploads \
  prism-accounting
```

Then exec into the container once to seed:
```bash
docker exec -it <container> python seed.py
```
(with `ADMIN_EMAIL`/`ADMIN_PASSWORD` passed as `-e` on the `docker run` line).

## Users & roles

- **Admin** — everything, including company settings, user management, and the audit log.
- **Bookkeeper** — can create/post invoices, bills, payments, reconciliations; approve claims.
- **Staff** — can only submit and track their own expense claims (no access to company books).
- **Viewer** — read-only, for e.g. an external accountant reviewing the books.

Add users under Users (admin only).

## Schema migrations

There is no separate migration step to run. On every start the app calls
`app.schema.ensure_schema()`, which idempotently creates any missing tables and
adds new nullable columns (and the reimbursement liability account) — safe on both
SQLite and Postgres. `seed.py` remains the one-time chart-of-accounts + first-admin
bootstrap.

## How the AI extraction works

On bill upload, the file is sent to Claude with a prompt asking for a structured
JSON draft (vendor, dates, amounts, line items, a plain-English category guess per
line). This **only ever produces a draft** — nothing posts to the ledger until you
pick a GL account for every line and click "Approve & post" on the review screen.
If `ANTHROPIC_API_KEY` isn't set, or extraction fails for any reason, the bill still
gets created — you just fill in the fields yourself on the same review screen.

## Data model notes

- All money is stored as integer cents to avoid floating-point rounding errors.
- Every posting goes through `app/ledger.py::create_journal_entry`, which refuses to
  save anything where debits ≠ credits.
- Invoices/bills are voided via a reversing journal entry, never deleted, so the
  audit trail stays intact.
- The chart of accounts seeded by `seed.py` includes system-locked accounts (AR, AP,
  tax payable/receivable, bank clearing, equity) that the ledger posting code depends
  on by account code — don't renumber them.

## Known limitations (roadmap ideas)

- Cash flow statement uses the indirect method with a simplified operating/investing/
  financing split — good enough for internal use, have an accountant sanity-check it
  before filing anything official.
- No e-commerce platform integration yet (Shopify/Stripe order sync) — revenue is
  entered via invoices or manual journal entries. A CSV/API import for daily sales
  batches would be a natural next addition.
- Single base currency for reporting; per-transaction FX rates are stored but not
  yet auto-fetched from a live rate feed.
- No automated bank feed (Plaid/Yodlee) — statements are imported via CSV.
