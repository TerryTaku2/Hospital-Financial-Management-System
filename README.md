# Hospital Financial Management System

A v1 hospital finance backend and admin UI: patient billing/invoicing, deposits and refunds, medical aid (insurance) claims, pharmacy procurement (suppliers, purchase orders, stock levels), employee registration and payroll runs, a double-entry General Ledger, accounts receivable aging, multi-currency (USD/ZWG), role-based access control, and a full audit trail. Built with **FastAPI + SQLAlchemy (async) + PostgreSQL** and a **plain HTML/CSS/JS** frontend (no build step).

Deferred to a later phase: budgeting, fixed asset register, and general (non-pharmacy) Accounts Payable.

## How it's put together

- Every billing, payment, deposit, and claim event posts through one function — `app/services/posting_service.py` — so the books can never go out of balance.
- Every financial mutation writes an append-only row to `audit_logs` (see `app/audit.py`).
- Money is `NUMERIC(18,2)` / `Decimal` everywhere — never float.
- Payments, deposits, and refunds require an `Idempotency-Key` header so a retried request can't double-post.
- Auth is JWT-in-httpOnly-cookie (access + refresh) plus a CSRF cookie/header pair for state-changing requests — not `localStorage`.

See `backend/app/services/` for the money-flow logic and `backend/app/models/` for the schema.

## Pharmacy procurement (Suppliers & Purchase Orders)

Where the pharmacy orders stock from:

- **Suppliers** (`/suppliers.html`) — the stores/vendors pharmacy buys from (name, contact info).
- **Charge Items** (`/charge-items.html`) — the price list invoices are billed from; a Pharmacy-category item also carries `quantity_on_hand` and an optional `reorder_level`.
- **Purchase Orders** (`/purchase-orders.html`) — raised against a supplier for one or more charge items. A draft PO has no accounting or stock impact.
  - **Receive** → increments `quantity_on_hand` for each line and posts `Dr Cost of Drugs & Consumables (5000) / Cr Accounts Payable - Suppliers (2200)`. This is expense-on-receipt costing (not perpetual/COGS-on-sale inventory valuation — see limitations below).
  - **Pay supplier** → posts `Dr Accounts Payable - Suppliers / Cr Cash or Bank`, same partial/full payment mechanics as patient payments.
- **Dispensing**: when a Pharmacy-category invoice line is finalized, `quantity_on_hand` decrements automatically (and restores if the invoice is later voided). This is **soft** tracking — it never blocks billing on low or negative stock, it's informational (pair it with `reorder_level` to know when to reorder).

## Running it locally (no Docker required)

```bash
cd backend
python -m venv .venv
./.venv/Scripts/activate          # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt

cp .env.example .env               # defaults to a local SQLite file, nothing to edit for a quick start

alembic upgrade head
python -m app.seed                 # creates default branch, Chart of Accounts, currencies, admin user
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 — the FastAPI app serves the `frontend/` folder directly. Log in with:

- **username:** `admin`
- **password:** `ChangeMe123!` (change this immediately in a real deployment)

## Demo data

There are two ways to get sample data: a **one-off manual seed** for local dev, or **demo mode** — a self-resetting public sandbox for showing the product to other people (investors, testers, etc.).

### One-off manual seed (local dev)

```bash
python -m app.seed_demo
```

This builds on `app.seed` and adds a second branch, one user per role, and seven patients covering every invoice/payment/deposit/claim state (draft, paid, partially paid via deposit with a refund, medical-aid billed and paid, aged unpaid balances for AR Aging, a voided invoice, and a second-branch invoice) — all posted through the real service layer, so the books stay balanced. Safe to run more than once; it does nothing if the demo data already exists.

Log in as any of:

| Username | Password | Role |
|---|---|---|
| `admin` | `ChangeMe123!` | Administrator |
| `cashier1` | `Demo1234!` | Cashier |
| `accountant1` | `Demo1234!` | Accountant |
| `auditor1` | `Demo1234!` | Auditor |
| `clinician1` | `Demo1234!` | Clinician |

There's also `python -m app.seed_investor_demo` for a much larger one-off dataset (three branches, several hundred patients each, a year of history) — see the docstring in `backend/app/seed_investor_demo.py`. Don't combine this with demo mode below: demo mode wipes the whole database, including anything this script seeded.

### Demo mode (self-resetting public sandbox)

Set `DEMO_MODE=true` (see `.env.example`) to turn this deployment into a live, always-fresh demo instance — the same pattern used in the `store ERP` sibling project. With it on:

- The **entire database** is wiped and reseeded with a fresh month of activity across three branches every time the app starts, *and* every time anyone clicks **Login to Demo Account** on the login page (`POST /api/auth/demo-login`, no credentials needed) — so a visitor who pokes around as `demo.admin` can never leave it messy for the next person.
- The dataset: three branches (Main, North, West), two suppliers, one received purchase order per branch (in `paid`/`partially_paid`/`received`-unpaid states so the AP side has variety) that stocks each branch's pharmacy items, ~50 patients total, a price list spanning consultations/pharmacy/procedures/lab/imaging/ward fees, billing episodes over the last 28 days covering every invoice state (draft, paid, partially paid, aged unpaid, voided, deposit-with-refund) and medical aid claims (approved/rejected/pending) — plus one deliberately 95-day-aged unpaid invoice per branch so AR Aging always has something in the 90+ bucket. Deterministic (fixed RNG seed), so every reset produces the same numbers. Regenerates in a few seconds.
- Log in as `demo.admin` / `Demo1234!` for the full consolidated view, or any branch's cashier/accountant (e.g. `cashier.main`, `accountant.north`) with password `Demo1234!`. This is a dedicated demo-only admin account, kept separate from the real `admin` / `ChangeMe123!` system-administrator account — clicking **Login to Demo Account** never hands a visitor the real admin identity or credentials.

**This app has no multi-tenant isolation** — unlike `store ERP`'s `Company.is_demo` sandboxing, `DEMO_MODE=true` here wipes *everything*, not a scoped-off slice. Only ever enable it on a deployment that will never hold real hospital data. It's `false` by default specifically so local dev (`uvicorn --reload`, which re-runs startup on every reload) never loses your data, and so a real deployment doesn't accidentally expose a public data-wipe endpoint — `POST /api/auth/demo-login` returns 404 unless `DEMO_MODE=true`, and the login page only shows the demo button when `/api/health` reports `demo_mode: true`.

To enable on Render: Dashboard → your web service → Environment → add `DEMO_MODE=true`, then redeploy.

## Deploying to Render

`render.yaml` (repo root) is a [Render Blueprint](https://render.com/docs/blueprint-spec) that provisions one web service running the Docker image, backed by SQLite on a persistent [Disk](https://render.com/docs/disks) mounted at `/var/data` — so the database survives redeploys and restarts instead of living on the container's ephemeral filesystem.

```bash
# In the Render dashboard: New → Blueprint → point it at this repo.
# Render reads render.yaml and creates the service + disk automatically.
```

Notes:

- **Disks require a paid plan** — the blueprint uses `starter`; Render's free tier doesn't support them. A disk also pins the service to a single instance (no horizontal autoscaling), which is fine for this app since it isn't built for multi-instance/multi-tenant use anyway.
- `JWT_SECRET_KEY` is auto-generated by Render (`generateValue: true`) — you don't need to set it.
- After the first deploy, seed the Chart of Accounts and admin user once via the Render Shell tab (or a one-off Job):
  ```bash
  python -m app.seed
  ```
  Skip this if you're turning on `DEMO_MODE=true` instead — it seeds and resets automatically on every startup.
- The build context is the **repository root**, not `backend/` — `backend/Dockerfile` copies both `backend/` and `frontend/` into the image (`dockerContext: .` in `render.yaml`; `docker compose up --build` does the same locally). If you ever change the Dockerfile, keep the two directories laid out the same way inside the image (`/app/app/...` and `/frontend`) since `app/main.py` derives the frontend path from its own location.
- To switch to Postgres instead (matching the `docker compose` setup below) — e.g. if you outgrow a single-instance SQLite deployment — drop the `disk:` block, add a Render Postgres instance, and point `DATABASE_URL` at its connection string.

## Running it with PostgreSQL / Docker

```bash
cd backend
docker compose up --build
```

This starts Postgres, runs migrations, seeds default data, and serves the API + frontend on http://localhost:8000.

To point the no-Docker setup at a real Postgres instead of SQLite, set in `.env`:

```
DATABASE_URL=postgresql+asyncpg://hospital:hospital@localhost:5432/hospital_finance
```

## Running the tests

```bash
cd backend
pytest
```

Tests cover the posting service (rejects unbalanced or single-line journal entries) and payment idempotency (a repeated `Idempotency-Key` replays the original result instead of posting twice).

## Smoke-test walkthrough

1. Log in as `admin`.
2. **Patients** → register a patient, then open their page and start an encounter (OPD/IPD).
3. **Billing** → create a draft invoice for that patient with a couple of charge items, then open it and click **Finalize** — this posts the AR/Revenue journal entry.
4. **Reports** → confirm the Trial Balance is still balanced and the new revenue shows up.
5. Back on the invoice, **record a payment** — confirm the invoice status and AR balance update.
6. **Deposits** → take a deposit, apply part of it to an invoice, then refund the remainder.
7. For a medical-aid-billed invoice: **Medical Aid Claims** → file a claim against the invoice lines, submit it, then approve it — approval posts a payment from the medical aid provider automatically.
8. **Reports** → check AR Aging reflects any remaining balances.
9. **Audit Log** (admin/auditor only) → see every mutation above recorded with before/after state.
10. **Suppliers** → add a supplier, then **Charge Items** → add a Pharmacy item with a reorder level.
11. **Purchase Orders** → raise a PO against that supplier and item, open it and **Receive goods** — confirm stock increments and the AP/COGS journal entry posts — then **Pay supplier**.
12. **Billing** → bill that same pharmacy item on a patient invoice and finalize it — confirm stock decrements on **Charge Items**.

## Roles

| Role | Can do |
|---|---|
| `admin` | Everything: manage users, branches, Chart of Accounts, void invoices |
| `accountant` | GL/journal entries, reports, void invoices, decide medical aid claims |
| `cashier` | Register patients, create/finalize invoices, take payments/deposits, file claims — cannot post manual journal entries or void invoices |
| `auditor` | Read-only everywhere, including the audit log |
| `clinician` | Read-only patients/encounters — no billing access |

## Known v1 limitations

- Refunds are implemented against deposits only (not against a standalone overpaid invoice).
- Exchange rates are a flat daily snapshot per currency (no branch-specific or intraday rates).
- No password-reset flow or account lockout — add before any real deployment.
- Pharmacy stock is soft-tracked (see above): quantity moves on receipt/dispense/void, but nothing blocks a sale on insufficient stock, and costing is expense-on-receipt rather than a per-unit COGS-on-sale valuation.
#   H o s p i t a l - F i n a n c i a l - M a n a g e m e n t - S y s t e m  
 