from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import AsyncSessionLocal
from app.demo_data import ensure_demo_data
from app.routers import (
    accounts,
    audit_logs,
    auth,
    branches,
    charge_items,
    claims,
    currencies,
    deposits,
    encounters,
    invoices,
    journal,
    medical_aid_providers,
    patients,
    payments,
    purchase_orders,
    reports,
    suppliers,
    users,
)

app = FastAPI(title="Hospital Financial Management System", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(branches.router)
app.include_router(users.router)
app.include_router(patients.router)
app.include_router(encounters.router)
app.include_router(medical_aid_providers.router)
app.include_router(currencies.router)
app.include_router(accounts.router)
app.include_router(journal.router)
app.include_router(charge_items.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(deposits.router)
app.include_router(claims.router)
app.include_router(suppliers.router)
app.include_router(purchase_orders.router)
app.include_router(reports.router)
app.include_router(audit_logs.router)


@app.get("/api/health")
async def health() -> dict[str, object]:
    return {"status": "ok", "demo_mode": settings.demo_mode}


@app.on_event("startup")
async def _seed_demo_on_startup() -> None:
    """Only when DEMO_MODE=true: reset the whole database to a fresh demo
    state on every boot (mirroring what /api/auth/demo-login does on every
    visitor login). Off by default — see Settings.demo_mode."""
    if not settings.demo_mode:
        return
    async with AsyncSessionLocal() as db:
        await ensure_demo_data(db)


# Mounted last: StaticFiles("/") is a catch-all prefix match, so every API
# route above must already be registered or it would shadow them.
_frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
