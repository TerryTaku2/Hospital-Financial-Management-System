from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
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
    reports,
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
app.include_router(reports.router)
app.include_router(audit_logs.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Mounted last: StaticFiles("/") is a catch-all prefix match, so every API
# route above must already be registered or it would shadow them.
_frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
