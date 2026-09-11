"""Idempotent seed data: currencies, a default branch, Chart of Accounts,
an admin user, sample medical aid providers, and a sample charge-item price
list. Safe to run multiple times.

Usage: python -m app.seed
"""

import asyncio
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.accounting import Account
from app.models.billing import ChargeItem
from app.models.branch import Branch
from app.models.currency import Currency, ExchangeRate
from app.models.enums import AccountType, RoleEnum
from app.models.insurance import MedicalAidProvider
from app.models.user import User
from app.security import hash_password
from app.services import coa_codes

DEFAULT_ACCOUNTS = [
    (coa_codes.CASH, "Cash on Hand", AccountType.ASSET),
    (coa_codes.BANK, "Bank Account", AccountType.ASSET),
    (coa_codes.AR_PATIENTS, "Accounts Receivable - Patients", AccountType.ASSET),
    (coa_codes.AR_MEDICAL_AID, "Accounts Receivable - Medical Aid", AccountType.ASSET),
    (coa_codes.DEPOSITS_HELD, "Deposits Held (Liability)", AccountType.LIABILITY),
    (coa_codes.AP_SUPPLIERS, "Accounts Payable - Suppliers", AccountType.LIABILITY),
    (coa_codes.PAYROLL_PAYABLE, "Payroll Payable", AccountType.LIABILITY),
    (coa_codes.PAYROLL_DEDUCTIONS_PAYABLE, "Payroll Deductions Payable", AccountType.LIABILITY),
    ("3000", "Owner's Equity", AccountType.EQUITY),
    ("4000", "Revenue - Consultations", AccountType.INCOME),
    ("4010", "Revenue - Pharmacy", AccountType.INCOME),
    ("4020", "Revenue - Procedures", AccountType.INCOME),
    ("4030", "Revenue - Ward/Bed Fees", AccountType.INCOME),
    (coa_codes.REVENUE_GENERAL, "Revenue - General/Miscellaneous", AccountType.INCOME),
    (coa_codes.COGS_DRUGS, "Cost of Drugs & Consumables", AccountType.EXPENSE),
    (coa_codes.SALARIES_EXPENSE, "Salaries & Wages", AccountType.EXPENSE),
]


async def seed_core(db: AsyncSession) -> None:
    """The actual seeding logic, operating on a caller-provided session.

    Split out from `seed()` so callers that already have a request-scoped
    session (e.g. the demo-login flow) can reuse this instead of opening a
    second, independent session/transaction mid-request.
    """
    if (await db.execute(select(Currency).where(Currency.code == "USD"))).scalars().first() is None:
        db.add(Currency(code="USD", name="US Dollar", symbol="$"))
    if (await db.execute(select(Currency).where(Currency.code == "ZWG"))).scalars().first() is None:
        db.add(Currency(code="ZWG", name="Zimbabwe Gold", symbol="ZWG"))
    await db.flush()

    if (await db.execute(select(ExchangeRate).where(ExchangeRate.currency_code == "ZWG"))).scalars().first() is None:
        db.add(ExchangeRate(currency_code="ZWG", rate_to_base=Decimal("1"), effective_date=date.today()))

    branch = (await db.execute(select(Branch).where(Branch.code == "MAIN"))).scalars().first()
    if branch is None:
        branch = Branch(code="MAIN", name="Main Hospital", base_currency_code="USD", is_main=True)
        db.add(branch)
        await db.flush()

    for code, name, acc_type in DEFAULT_ACCOUNTS:
        if (await db.execute(select(Account).where(Account.code == code))).scalars().first() is None:
            db.add(Account(code=code, name=name, type=acc_type))
    await db.flush()

    if (await db.execute(select(User).where(User.username == "admin"))).scalars().first() is None:
        db.add(
            User(
                branch_id=branch.id,
                username="admin",
                email="admin@example.com",
                full_name="System Administrator",
                hashed_password=hash_password("ChangeMe123!"),
                role=RoleEnum.ADMIN,
            )
        )

    provider_defs = [
        ("PSMAS", "Premier Service Medical Aid Society"),
        ("CIMAS", "CIMAS Medical Aid Society"),
        ("FIRSTMUTUAL", "First Mutual Health"),
    ]
    for code, name in provider_defs:
        if (await db.execute(select(MedicalAidProvider).where(MedicalAidProvider.code == code))).scalars().first() is None:
            db.add(MedicalAidProvider(code=code, name=name))
    await db.flush()

    revenue_account_id = (
        await db.execute(select(Account.id).where(Account.code == "4000"))
    ).scalar_one()
    pharmacy_account_id = (
        await db.execute(select(Account.id).where(Account.code == "4010"))
    ).scalar_one()
    procedures_account_id = (
        await db.execute(select(Account.id).where(Account.code == "4020"))
    ).scalar_one()

    charge_item_defs = [
        ("CONSULT-GEN", "General Consultation", "Consultation", Decimal("25.00"), revenue_account_id),
        ("CONSULT-SPEC", "Specialist Consultation", "Consultation", Decimal("50.00"), revenue_account_id),
        ("PROC-DRESSING", "Wound Dressing", "Procedure", Decimal("15.00"), procedures_account_id),
        ("PHARM-PARACETAMOL", "Paracetamol 500mg (strip)", "Pharmacy", Decimal("2.00"), pharmacy_account_id),
    ]
    for code, name, category, price, acct_id in charge_item_defs:
        if (await db.execute(select(ChargeItem).where(ChargeItem.code == code))).scalars().first() is None:
            db.add(
                ChargeItem(
                    branch_id=branch.id,
                    code=code,
                    name=name,
                    category=category,
                    default_price=price,
                    currency_code="USD",
                    revenue_account_id=acct_id,
                )
            )

    await db.commit()


async def seed() -> None:
    """Assumes `alembic upgrade head` has already created the schema."""
    async with AsyncSessionLocal() as db:
        await seed_core(db)

    print("Seed complete. Admin login: username=admin password=ChangeMe123!")


if __name__ == "__main__":
    asyncio.run(seed())
