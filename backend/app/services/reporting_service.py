from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import Account, JournalEntry, JournalLine
from app.models.billing import Deposit, Invoice, Payment, Refund
from app.models.enums import AccountType, InvoiceStatus, PayerType
from app.models.insurance import MedicalAidProvider
from app.models.patient import Patient
from app.schemas.reports import (
    ArAgingOut,
    ArAgingRow,
    DailyTransactionRow,
    DailyTransactionsOut,
    DailyTransactionsSummary,
    IncomeStatementLine,
    IncomeStatementOut,
    RevenueTrendOut,
    RevenueTrendPoint,
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


async def revenue_trend(db: AsyncSession, days: int = 90, branch_id: int | None = None) -> RevenueTrendOut:
    """Net revenue (income account credits minus debits) posted per day over
    the trailing `days` days, for the dashboard trend chart."""
    start_date = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
    stmt = (
        select(
            JournalEntry.entry_date,
            func.coalesce(func.sum(JournalLine.base_amount_credit - JournalLine.base_amount_debit), 0).label("revenue"),
        )
        .join(JournalLine, JournalLine.journal_entry_id == JournalEntry.id)
        .join(Account, Account.id == JournalLine.account_id)
        .where(JournalEntry.is_posted.is_(True), Account.type == AccountType.INCOME, JournalEntry.entry_date >= start_date)
    )
    if branch_id is not None:
        stmt = stmt.where(JournalEntry.branch_id == branch_id)
    stmt = stmt.group_by(JournalEntry.entry_date).order_by(JournalEntry.entry_date)

    rows = (await db.execute(stmt)).all()
    by_date = {row.entry_date: Decimal(row.revenue) for row in rows}

    points = [
        RevenueTrendPoint(period=start_date + timedelta(days=offset), revenue=by_date.get(start_date + timedelta(days=offset), Decimal("0")))
        for offset in range(days)
    ]
    return RevenueTrendOut(points=points)


def _add_amount(totals: dict[str, Decimal], currency_code: str, amount: Decimal) -> None:
    totals[currency_code] = totals.get(currency_code, Decimal("0")) + amount


async def daily_transactions(
    db: AsyncSession, transaction_date: date, branch_id: int | None = None
) -> DailyTransactionsOut:
    day_start = datetime.combine(transaction_date, time.min, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    async def _for_day(model):
        stmt = select(model).where(model.created_at >= day_start, model.created_at < day_end)
        if branch_id is not None:
            stmt = stmt.where(model.branch_id == branch_id)
        return list((await db.execute(stmt)).scalars().all())

    invoices = await _for_day(Invoice)
    deposits = await _for_day(Deposit)
    payments = await _for_day(Payment)
    refunds = await _for_day(Refund)

    invoice_ids = {p.invoice_id for p in payments} | {r.invoice_id for r in refunds if r.invoice_id is not None}
    invoice_ids -= {i.id for i in invoices}
    related_invoices: dict[int, Invoice] = {i.id: i for i in invoices}
    for invoice_id in invoice_ids:
        invoice = await db.get(Invoice, invoice_id)
        if invoice is not None:
            related_invoices[invoice.id] = invoice

    deposit_ids = {r.deposit_id for r in refunds if r.deposit_id is not None}
    deposit_ids -= {d.id for d in deposits}
    related_deposits: dict[int, Deposit] = {d.id: d for d in deposits}
    for deposit_id in deposit_ids:
        deposit = await db.get(Deposit, deposit_id)
        if deposit is not None:
            related_deposits[deposit.id] = deposit

    patient_ids: set[int] = {inv.patient_id for inv in related_invoices.values()}
    patient_ids |= {dep.patient_id for dep in related_deposits.values()}
    patients: dict[int, Patient] = {}
    if patient_ids:
        result = await db.execute(select(Patient).where(Patient.id.in_(patient_ids)))
        patients = {p.id: p for p in result.scalars().all()}

    def _patient_name(patient_id: int | None) -> str | None:
        if patient_id is None:
            return None
        patient = patients.get(patient_id)
        return f"{patient.first_name} {patient.last_name}" if patient else f"Patient #{patient_id}"

    rows: list[DailyTransactionRow] = []
    total_invoiced: dict[str, Decimal] = {}
    total_payments: dict[str, Decimal] = {}
    total_deposits: dict[str, Decimal] = {}
    total_refunds: dict[str, Decimal] = {}

    for invoice in invoices:
        rows.append(
            DailyTransactionRow(
                kind="invoice",
                id=invoice.id,
                time=invoice.created_at,
                patient_id=invoice.patient_id,
                patient_name=_patient_name(invoice.patient_id),
                reference=invoice.invoice_number,
                description=f"Invoice raised ({len(invoice.lines)} line{'s' if len(invoice.lines) != 1 else ''})",
                method=None,
                currency_code=invoice.currency_code,
                amount=invoice.total,
                status=invoice.status.value,
            )
        )
        if invoice.status != InvoiceStatus.VOID:
            _add_amount(total_invoiced, invoice.currency_code, invoice.total)

    for deposit in deposits:
        rows.append(
            DailyTransactionRow(
                kind="deposit",
                id=deposit.id,
                time=deposit.created_at,
                patient_id=deposit.patient_id,
                patient_name=_patient_name(deposit.patient_id),
                reference=f"DEP-{deposit.id}",
                description="Deposit received",
                method=None,
                currency_code=deposit.currency_code,
                amount=deposit.amount,
                status=deposit.status.value,
            )
        )
        _add_amount(total_deposits, deposit.currency_code, deposit.amount)

    for payment in payments:
        invoice = related_invoices.get(payment.invoice_id)
        rows.append(
            DailyTransactionRow(
                kind="payment",
                id=payment.id,
                time=payment.created_at,
                patient_id=invoice.patient_id if invoice else None,
                patient_name=_patient_name(invoice.patient_id) if invoice else None,
                reference=invoice.invoice_number if invoice else f"INV-{payment.invoice_id}",
                description="Payment received",
                method=payment.method.value,
                currency_code=payment.currency_code,
                amount=payment.amount,
                status="completed",
            )
        )
        _add_amount(total_payments, payment.currency_code, payment.amount)

    for refund in refunds:
        if refund.invoice_id is not None:
            invoice = related_invoices.get(refund.invoice_id)
            patient_id = invoice.patient_id if invoice else None
            reference = invoice.invoice_number if invoice else f"INV-{refund.invoice_id}"
        else:
            deposit = related_deposits.get(refund.deposit_id) if refund.deposit_id is not None else None
            patient_id = deposit.patient_id if deposit else None
            reference = f"DEP-{refund.deposit_id}"
        rows.append(
            DailyTransactionRow(
                kind="refund",
                id=refund.id,
                time=refund.created_at,
                patient_id=patient_id,
                patient_name=_patient_name(patient_id),
                reference=reference,
                description=f"Refund: {refund.reason}",
                method=None,
                currency_code=refund.currency_code,
                amount=refund.amount,
                status="completed",
            )
        )
        _add_amount(total_refunds, refund.currency_code, refund.amount)

    rows.sort(key=lambda r: r.time, reverse=True)

    currencies = set(total_payments) | set(total_deposits) | set(total_refunds)
    net_cash_collected = {
        code: total_payments.get(code, Decimal("0"))
        + total_deposits.get(code, Decimal("0"))
        - total_refunds.get(code, Decimal("0"))
        for code in currencies
    }

    return DailyTransactionsOut(
        transaction_date=transaction_date,
        rows=rows,
        summary=DailyTransactionsSummary(
            total_invoiced=total_invoiced,
            total_payments=total_payments,
            total_deposits=total_deposits,
            total_refunds=total_refunds,
            net_cash_collected=net_cash_collected,
        ),
    )
