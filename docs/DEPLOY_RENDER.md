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
- A **PostgreSQL database** that keeps your data safely (not a throwaway file).
- **Persistent storage** for uploaded receipts, bill PDFs, and your logo.
- The chart of accounts and your first admin login created automatically.

**Rough cost:** about **US$7/month** for the web service + a small database tier
(≈ HK$55–110/month total). A free tier exists for trying it out, but it sleeps when
idle and the free database is deleted after 30 days — not suitable for real books.

---

## Before you start — have these ready

1. A **Render account** — sign up free at https://render.com (log in with GitHub).
2. This GitHub repo connected to Render (Render will ask permission the first time).
3. An **Anthropic API key** (for the AI receipt reading) — from
   https://console.anthropic.com → *API Keys*. Starts with `sk-ant-...`.
4. A **password you choose** for the first admin account.

---

## Step-by-step

### 1. Create the Blueprint
- In Render: **New +** → **Blueprint**.
- Select this repository. Render detects `render.yaml` and lists what it will create:
  a web service (`prism-accounting`) and a database (`prism-accounting-db`).
- Click **Apply**.

> The `render.yaml` is set to deploy the `claude/prism-accounting-system-m97iv8`
> branch (which has all the latest features). Once that work is merged into your main
> branch, change the `branch:` line in `render.yaml` to your default branch.

### 2. Set the three secrets
Render will prompt for the values marked "sync:false" (or set them under the web
service → **Environment**):

| Key | What to put |
|---|---|
| `ADMIN_EMAIL` | The email for your first admin login (e.g. `mcmy116@gmail.com`) |
| `ADMIN_PASSWORD` | A strong password you choose for that admin |
| `ANTHROPIC_API_KEY` | Your `sk-ant-...` key from the Anthropic console |

`SECRET_KEY` and `DATABASE_URL` are filled in automatically — leave them alone.

### 3. Deploy
- Render builds the Docker image, provisions the database, runs the seeding step
  (creates the chart of accounts + your admin), and starts the site.
- First build takes a few minutes. Watch the **Logs** tab; you're looking for
  `Seed complete.` followed by gunicorn starting.

### 4. Log in
- Open the service URL Render shows (e.g. `https://prism-accounting.onrender.com`).
- Log in with the `ADMIN_EMAIL` / `ADMIN_PASSWORD` you set.
- **Change the password** and add your two staff under **Users** if you like.

### 5. (Optional) Use your own domain
- Web service → **Settings → Custom Domains** → add `accounts.yourdomain.com`.
- Add the DNS record Render gives you at your domain provider.
- If your DNS is managed through Netlify, you can also add a Netlify redirect from
  the main site to this subdomain — so everything still feels like one connected suite.

---

## After it's live

- **See the Shopify feature:** the new **Sales Channels** item now appears in the
  sidebar. Connect the Lunara store there (Admin API token with `read_orders` scope)
  and run a sync.
- **Back up your data:** Render can take automatic database backups — enable them on
  the database's page for peace of mind.

---

## Troubleshooting

- **Deploy fails at the seeding step** → you probably didn't set `ADMIN_PASSWORD`.
  Set it under Environment and click **Manual Deploy → Deploy latest commit**.
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
