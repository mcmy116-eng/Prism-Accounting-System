# Deploying the Prism Accounting System on Render

This guide takes you from the code in GitHub to a live website your team can log
into from anywhere. No coding required — it's mostly clicking buttons and pasting
two secrets.

Render is used (rather than Netlify) because this is a **server application with a
database and file uploads**. Netlify is superb for static/JavaScript sites like the
Prism website, but it can't host an always-on Python server with a database. Render
can, and the repo already contains everything it needs (`Dockerfile` + `render.yaml`).

---

## What you'll end up with

- An always-on website, e.g. `https://prism-accounting.onrender.com`
  (you can later put it on your own subdomain like `accounts.yourdomain.com`).
- A **PostgreSQL database** (free, hosted at Neon) that keeps your data safely.
- **Persistent storage** for uploaded receipts, bill PDFs, and your logo.
- The chart of accounts and your first admin login created automatically.

**Rough cost: ~US$7.25/month** (≈ HK$56):

| Item | Where | Cost |
|---|---|---|
| Web service (Starter, always-on) | Render | US$7.00 |
| PostgreSQL database | Neon free tier | US$0.00 |
| 1 GB disk for uploads | Render | US$0.25 |

> Using Neon's free database instead of Render's managed one (US$10.50/mo) is what
> keeps this at ~US$7.25 rather than ~US$17.75. Neon's free tier is always available
> and — unlike Render's free database — is **not** deleted after 30 days.

---

## Before you start — have these ready

1. A **Render account** — sign up free at https://render.com (log in with GitHub).
2. A **Neon account** — sign up free at https://neon.tech (log in with GitHub). This
   hosts your database at no cost.
3. This GitHub repo connected to Render (Render will ask permission the first time).
4. A **password you choose** for the first admin account.
5. *(Optional, for AI receipt reading)* An **Anthropic API key** from
   https://console.anthropic.com → *API Keys* (starts with `sk-ant-...`). You can skip
   this to start and add it later — see the note in step 3.

---

## Step-by-step

### 1. Create your free database (Neon)
- Log in at https://neon.tech → **Create project** (any name, e.g. "prism-accounting").
- Pick a region close to Hong Kong (e.g. Singapore) for speed.
- On the project dashboard, find the **connection string** (labelled *Connection
  string* / *psql*). It looks like:
  `postgresql://user:password@ep-xxxx.ap-southeast-1.aws.neon.tech/dbname?sslmode=require`
- **Copy that whole string** — you'll paste it into Render as `DATABASE_URL` in the
  next step. (Use the "pooled" connection string if Neon offers a choice.)

### 2. Create the Blueprint in Render
- In Render: **New +** → **Blueprint**.
- Select this repository. Render detects `render.yaml` and lists the web service
  (`prism-accounting`) and a disk.
- Click **Apply**.

> The `render.yaml` deploys your `main` branch, which now contains all the latest
> features.

### 3. Set the secrets
Render will prompt for the values marked "sync:false" (or set them under the web
service → **Environment**):

| Key | What to put |
|---|---|
| `DATABASE_URL` | The Neon connection string you copied in step 1 |
| `ADMIN_EMAIL` | The email for your first admin login (e.g. `mcmy116@gmail.com`) |
| `ADMIN_PASSWORD` | A strong password you choose for that admin |
| `ANTHROPIC_API_KEY` | Your `sk-ant-...` key — **or** a placeholder like `sk-ant-placeholder` for now |

`SECRET_KEY` is generated automatically — leave it alone.

> **About `ANTHROPIC_API_KEY`:** it only powers the "AI reads your uploaded receipt"
> feature. Everything else works without it. Put a placeholder now and add a real key
> later (Environment → edit → Save) whenever you want that feature.

### 4. Deploy
- Render builds the Docker image, runs the seeding step against your Neon database
  (creates the chart of accounts + your admin), and starts the site.
- First build takes a few minutes. Watch the **Logs** tab; you're looking for
  `Seed complete.` followed by gunicorn starting.

### 5. Log in
- Open the service URL Render shows (e.g. `https://prism-accounting.onrender.com`).
- Log in with the `ADMIN_EMAIL` / `ADMIN_PASSWORD` you set.
- **Change the password** and add your two staff under **Users** if you like.

### 6. (Optional) Use your own domain
- Web service → **Settings → Custom Domains** → add `accounts.yourdomain.com`.
- Add the DNS record Render gives you at your domain provider.
- If your DNS is managed through Netlify, you can also add a Netlify redirect from
  the main site to this subdomain — so everything still feels like one connected suite.

---

## After it's live

- **See the Shopify feature:** the new **Sales Channels** item now appears in the
  sidebar. Connect the Lunara store there (Admin API token with `read_orders` scope)
  and run a sync.
- **Back up your data:** your data lives in Neon — it keeps automatic point-in-time
  backups on the free tier, viewable on the Neon project dashboard.

---

## Troubleshooting

- **Deploy fails at the seeding step** → either `ADMIN_PASSWORD` isn't set, or
  `DATABASE_URL` is wrong/unreachable. Re-check the Neon connection string was pasted
  in full (it must start with `postgresql://` and end with `?sslmode=require`), then
  **Manual Deploy → Deploy latest commit**.
- **`could not translate host name` / connection errors** → the `DATABASE_URL` is
  incomplete or has a typo. Copy it again from the Neon dashboard.
- **AI receipt reading doesn't work** → check `ANTHROPIC_API_KEY` is set correctly.
- **Uploaded receipts disappear** → make sure the disk is attached (it is in
  `render.yaml`); a service without a disk loses files on restart.
- **502 right after deploy** → give it a minute; the health check hits `/auth/login`
  once the server is up.

---

## Why not Netlify (the short version)

| This app needs | Netlify | Render |
|---|---|---|
| Always-on server process | ✗ (10-second functions) | ✓ |
| Persistent database | ✗ | ✓ (managed Postgres) |
| Saved file uploads | ✗ (ephemeral disk) | ✓ (persistent disk) |
| Time for AI + PDF work | ✗ (function timeouts) | ✓ (120s+ requests) |

Keep the Prism marketing site and Master Business Execution System on Netlify where
they shine; host this database-backed accounting server on Render.
