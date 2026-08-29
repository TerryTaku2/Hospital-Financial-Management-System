from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import Account, JournalEntry, JournalLine
from app.models.billing import Invoice
from app.models.enums import AccountType, InvoiceStatus, PayerType
from app.models.insurance import MedicalAidProvider
from app.models.patient import Patient
from app.schemas.reports import (
    ArAgingOut,
    ArAgingRow,
    IncomeStatementLine,
    IncomeStatementOut,
    TrialBalanceLine,
    TrialBalanceOut,
)


async def trial_balance(db: AsyncSession, branch_id: int | None = None) -> TrialBalanceOut:
    stmt = (
        select(
            Account.id,
            Account.code,
            Account.name,
            func.coalesce(func.sum(JournalLine.base_amount_debit), 0).label("total_debit"),
            func.coalesce(func.sum(JournalLine.base_amount_credit), 0).label("total_credit"),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(JournalEntry.is_posted.is_(True))
    )
    if branch_id is not None:
        stmt = stmt.where(JournalEntry.branch_id == branch_id)
    stmt = stmt.group_by(Account.id, Account.code, Account.name).order_by(Account.code)

    rows = (await db.execute(stmt)).all()
    lines = [
        TrialBalanceLine(
            account_id=row.id,
            account_code=row.code,
            account_name=row.name,
            total_debit=Decimal(row.total_debit),
            total_credit=Decimal(row.total_credit),
        )
        for row in rows
    ]
    total_debit = sum((line.total_debit for line in lines), Decimal("0"))
    total_credit = sum((line.total_credit for line in lines), Decimal("0"))
    return TrialBalanceOut(
        lines=lines, total_debit=total_debit, total_credit=total_credit, is_balanced=total_debit == total_credit
    )


async def income_statement(db: AsyncSession, branch_id: int | None = None) -> IncomeStatementOut:
    stmt = (
        select(
            Account.id,
            Account.code,
            Account.name,
            Account.type,
            func.coalesce(func.sum(JournalLine.base_amount_credit), 0).label("total_credit"),
            func.coalesce(func.sum(JournalLine.base_amount_debit), 0).label("total_debit"),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(JournalEntry.is_posted.is_(True), Account.type.in_([AccountType.INCOME, AccountType.EXPENSE]))
    )
    if branch_id is not None:
        stmt = stmt.where(JournalEntry.branch_id == branch_id)
    stmt = stmt.group_by(Account.id, Account.code, Account.name, Account.type).order_by(Account.code)

    rows = (await db.execute(stmt)).all()
    income_lines: list[IncomeStatementLine] = []
    expense_lines: list[IncomeStatementLine] = []
    for row in rows:
        if row.type == AccountType.INCOME:
            amount = Decimal(row.total_credit) - Decimal(row.total_debit)
            income_lines.append(IncomeStatementLine(account_id=row.id, account_code=row.code, account_name=row.name, amount=amount))
        else:
            amount = Decimal(row.total_debit) - Decimal(row.total_credit)
            expense_lines.append(IncomeStatementLine(account_id=row.id, account_code=row.code, account_name=row.name, amount=amount))

    total_income = sum((line.amount for line in income_lines), Decimal("0"))
    total_expense = sum((line.amount for line in expense_lines), Decimal("0"))
    return IncomeStatementOut(
        income_lines=income_lines,
        expense_lines=expense_lines,
        total_income=total_income,
        total_expense=total_expense,
        net_income=total_income - total_expense,
    )


async def ar_aging(db: AsyncSession, branch_id: int | None = None) -> ArAgingOut:
    stmt = select(Invoice).where(Invoice.status.in_([InvoiceStatus.FINALIZED, InvoiceStatus.PARTIALLY_PAID]))
    if branch_id is not None:
        stmt = stmt.where(Invoice.branch_id == branch_id)
    invoices = (await db.execute(stmt)).scalars().all()

    today = datetime.now(timezone.utc).date()
    buckets: dict[tuple[str, int], dict[str, Decimal]] = {}
    debtor_names: dict[tuple[str, int], str] = {}

    for invoice in invoices:
        outstanding = invoice.total - invoice.amount_paid
        if outstanding <= 0:
            continue

        if invoice.payer_type == PayerType.MEDICAL_AID and invoice.medical_aid_provider_id is not None:
            key = ("medical_aid", invoice.medical_aid_provider_id)
            if key not in debtor_names:
                provider = await db.get(MedicalAidProvider, invoice.medical_aid_provider_id)
                debtor_names[key] = provider.name if provider else f"Medical Aid #{invoice.medical_aid_provider_id}"
        else:
            key = ("patient", invoice.patient_id)
            if key not in debtor_names:
                patient = await db.get(Patient, invoice.patient_id)
                debtor_names[key] = f"{patient.first_name} {patient.last_name}" if patient else f"Patient #{invoice.patient_id}"

        bucket = buckets.setdefault(
            key,
            {"bucket_0_30": Decimal("0"), "bucket_31_60": Decimal("0"), "bucket_61_90": Decimal("0"), "bucket_90_plus": Decimal("0")},
        )
        age_days = (today - invoice.created_at.date()).days
        if age_days <= 30:
            bucket["bucket_0_30"] += outstanding
        elif age_days <= 60:
            bucket["bucket_31_60"] += outstanding
        elif age_days <= 90:
            bucket["bucket_61_90"] += outstanding
        else:
            bucket["bucket_90_plus"] += outstanding

    rows = [
        ArAgingRow(
            debtor_type=key[0],
            debtor_id=key[1],
            debtor_name=debtor_names[key],
            bucket_0_30=b["bucket_0_30"],
            bucket_31_60=b["bucket_31_60"],
            bucket_61_90=b["bucket_61_90"],
            bucket_90_plus=b["bucket_90_plus"],
            total_outstanding=sum(b.values(), Decimal("0")),
        )
        for key, b in buckets.items()
    ]
    grand_total = sum((row.total_outstanding for row in rows), Decimal("0"))
    return ArAgingOut(rows=rows, grand_total=grand_total)
