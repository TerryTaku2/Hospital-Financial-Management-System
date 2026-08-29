from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import get_current_user, require_role, verify_csrf
from app.models.billing import Invoice, Payment
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.billing import PaymentCreate, PaymentOut
from app.services.payment_service import record_payment
from app.services.posting_service import PostingError

router = APIRouter(prefix="/api/payments", tags=["payments"], dependencies=[Depends(verify_csrf)])

CAN_TAKE_PAYMENT = require_role(RoleEnum.ADMIN, RoleEnum.CASHIER, RoleEnum.ACCOUNTANT)


@router.get("", response_model=list[PaymentOut])
async def list_payments(
    invoice_id: int | None = None,
    patient_id: int | None = None,
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[Payment]:
    stmt = select(Payment).order_by(Payment.id.desc())
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(Payment.branch_id == effective_branch_id)
    if invoice_id is not None:
        stmt = stmt.where(Payment.invoice_id == invoice_id)
    if patient_id is not None:
        stmt = stmt.join(Invoice, Payment.invoice_id == Invoice.id).where(Invoice.patient_id == patient_id)
    return list((await db.execute(stmt)).scalars().all())


@router.post("", response_model=PaymentOut, dependencies=[Depends(CAN_TAKE_PAYMENT)])
async def create_payment(
    payment_in: PaymentCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> Payment:
    scope.check_write(payment_in.branch_id)
    invoice = await db.get(Invoice, payment_in.invoice_id)
    if invoice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found")
    scope.check_access(invoice.branch_id)
    try:
        payment, _created = await record_payment(db, payment_in, user, idempotency_key)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(payment)
    return payment
