from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit_log
from app.models.employee import Employee
from app.models.enums import AuditAction, EmployeeStatus, JournalSourceType, PaymentMethod, PayrollRunStatus
from app.models.payroll import PayrollRun, PayslipItem
from app.models.user import User
from app.schemas.payroll import PayrollRunCreate
from app.services import account_lookup, coa_codes
from app.services.posting_service import LineInput, PostingError, post_journal_entry

PAYROLL_PAYMENT_METHODS = (PaymentMethod.CASH, PaymentMethod.CARD, PaymentMethod.EFT)


async def _recompute_totals(db: AsyncSession, run: PayrollRun) -> None:
    items = (await db.execute(select(PayslipItem).where(PayslipItem.payroll_run_id == run.id))).scalars().all()
    run.total_gross = sum((item.gross_pay for item in items), Decimal("0"))
    run.total_deductions = sum((item.deductions for item in items), Decimal("0"))
    run.total_net = sum((item.net_pay for item in items), Decimal("0"))
    await db.flush()


async def create_payroll_run(db: AsyncSession, run_in: PayrollRunCreate, user: User) -> PayrollRun:
    if run_in.period_end < run_in.period_start:
        raise PostingError("Period end cannot be before period start")

    employees = (
        await db.execute(
            select(Employee).where(Employee.branch_id == run_in.branch_id, Employee.status == EmployeeStatus.ACTIVE)
        )
    ).scalars().all()
    if not employees:
        raise PostingError("No active employees in this branch to run payroll for")

    run = PayrollRun(
        branch_id=run_in.branch_id,
        period_start=run_in.period_start,
        period_end=run_in.period_end,
        currency_code=run_in.currency_code,
        status=PayrollRunStatus.DRAFT,
        created_by_id=user.id,
    )
    db.add(run)
    await db.flush()

    for employee in employees:
        db.add(
            PayslipItem(
                payroll_run_id=run.id,
                employee_id=employee.id,
                employee_name=employee.full_name,
                department=employee.department,
                basic_salary=employee.basic_salary,
                allowances=Decimal("0"),
                deductions=Decimal("0"),
                gross_pay=employee.basic_salary,
                net_pay=employee.basic_salary,
            )
        )
    await db.flush()
    await _recompute_totals(db, run)

    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=run.branch_id,
        table_name="payroll_runs",
        record_id=run.id,
        action=AuditAction.CREATE,
        after={"period_start": str(run.period_start), "period_end": str(run.period_end), "total_net": str(run.total_net)},
    )
    await db.refresh(run, attribute_names=["items"])
    return run


async def update_payslip_item(
    db: AsyncSession,
    run: PayrollRun,
    item: PayslipItem,
    *,
    allowances: Decimal,
    deductions: Decimal,
    notes: str | None,
) -> PayslipItem:
    if run.status != PayrollRunStatus.DRAFT:
        raise PostingError(f"Payroll run {run.id} is {run.status.value} — only a draft run can be edited")
    if allowances < 0 or deductions < 0:
        raise PostingError("Allowances and deductions cannot be negative")

    item.allowances = allowances
    item.deductions = deductions
    item.gross_pay = item.basic_salary + allowances
    item.net_pay = item.gross_pay - deductions
    item.notes = notes
    await db.flush()
    await _recompute_totals(db, run)
    return item


async def finalize_payroll_run(db: AsyncSession, run: PayrollRun, user: User) -> PayrollRun:
    if run.status != PayrollRunStatus.DRAFT:
        raise PostingError(f"Payroll run {run.id} is {run.status.value} — only a draft run can be finalized")
    if run.total_net <= 0:
        raise PostingError("Payroll run has no net pay to finalize")

    expense_account_id = await account_lookup.get_account_id_by_code(db, coa_codes.SALARIES_EXPENSE)
    payable_account_id = await account_lookup.get_account_id_by_code(db, coa_codes.PAYROLL_PAYABLE)

    lines = [
        LineInput(account_id=expense_account_id, debit=run.total_gross),
        LineInput(account_id=payable_account_id, credit=run.total_net),
    ]
    if run.total_deductions > 0:
        deductions_account_id = await account_lookup.get_account_id_by_code(db, coa_codes.PAYROLL_DEDUCTIONS_PAYABLE)
        lines.append(LineInput(account_id=deductions_account_id, credit=run.total_deductions))

    await post_journal_entry(
        db,
        branch_id=run.branch_id,
        entry_date=datetime.now(timezone.utc).date(),
        memo=f"Payroll run {run.id} finalized ({run.period_start} to {run.period_end})",
        currency_code=run.currency_code,
        source_type=JournalSourceType.PAYROLL,
        source_id=run.id,
        created_by_id=user.id,
        lines=lines,
    )

    run.status = PayrollRunStatus.FINALIZED
    run.finalized_at = datetime.now(timezone.utc)
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=run.branch_id,
        table_name="payroll_runs",
        record_id=run.id,
        action=AuditAction.UPDATE,
        before={"status": PayrollRunStatus.DRAFT.value},
        after={"status": run.status.value, "total_net": str(run.total_net)},
    )
    return run


async def pay_payroll_run(db: AsyncSession, run: PayrollRun, user: User, method: PaymentMethod) -> PayrollRun:
    if run.status != PayrollRunStatus.FINALIZED:
        raise PostingError(f"Payroll run {run.id} is {run.status.value} — only a finalized run can be paid")
    if method not in PAYROLL_PAYMENT_METHODS:
        raise PostingError(f"Payroll cannot be disbursed via {method.value}")

    payable_account_id = await account_lookup.get_account_id_by_code(db, coa_codes.PAYROLL_PAYABLE)
    cash_account_id = await account_lookup.get_cash_account_id(db, method)

    await post_journal_entry(
        db,
        branch_id=run.branch_id,
        entry_date=datetime.now(timezone.utc).date(),
        memo=f"Payroll run {run.id} paid ({run.period_start} to {run.period_end})",
        currency_code=run.currency_code,
        source_type=JournalSourceType.PAYROLL_PAYMENT,
        source_id=run.id,
        created_by_id=user.id,
        lines=[
            LineInput(account_id=payable_account_id, debit=run.total_net),
            LineInput(account_id=cash_account_id, credit=run.total_net),
        ],
    )

    run.status = PayrollRunStatus.PAID
    run.paid_at = datetime.now(timezone.utc)
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=run.branch_id,
        table_name="payroll_runs",
        record_id=run.id,
        action=AuditAction.UPDATE,
        before={"status": PayrollRunStatus.FINALIZED.value},
        after={"status": run.status.value, "method": method.value},
    )
    return run


async def void_payroll_run(db: AsyncSession, run: PayrollRun, user: User) -> PayrollRun:
    if run.status != PayrollRunStatus.DRAFT:
        raise PostingError(f"Payroll run {run.id} is {run.status.value} — only a draft run can be voided")

    run.status = PayrollRunStatus.VOID
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=run.branch_id,
        table_name="payroll_runs",
        record_id=run.id,
        action=AuditAction.VOID,
        before={"status": PayrollRunStatus.DRAFT.value},
        after={"status": run.status.value},
    )
    return run
