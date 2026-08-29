from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import get_current_user, require_role, verify_csrf
from app.models.billing import Invoice
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.billing import InvoiceCreate, InvoiceOut
from app.services.billing_service import create_invoice, finalize_invoice, void_invoice
from app.services.posting_service import PostingError

router = APIRouter(prefix="/api/invoices", tags=["invoices"], dependencies=[Depends(verify_csrf)])

CAN_BILL = require_role(RoleEnum.ADMIN, RoleEnum.CASHIER, RoleEnum.ACCOUNTANT)
CAN_VOID = require_role(RoleEnum.ADMIN, RoleEnum.ACCOUNTANT)


class VoidRequest(BaseModel):
    reason: str


@router.get("", response_model=list[InvoiceOut])
async def list_invoices(
    patient_id: int | None = None,
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[Invoice]:
    stmt = select(Invoice).order_by(Invoice.id.desc())
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(Invoice.branch_id == effective_branch_id)
    if patient_id is not None:
        stmt = stmt.where(Invoice.patient_id == patient_id)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: int, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> Invoice:
    invoice = await db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found")
    scope.check_access(invoice.branch_id)
    return invoice


@router.post("", response_model=InvoiceOut, dependencies=[Depends(CAN_BILL)])
async def create_invoice_endpoint(
    invoice_in: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> Invoice:
    scope.check_write(invoice_in.branch_id)
    try:
        invoice = await create_invoice(db, invoice_in, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(invoice, attribute_names=["lines"])
    return invoice


@router.post("/{invoice_id}/finalize", response_model=InvoiceOut, dependencies=[Depends(CAN_BILL)])
async def finalize_invoice_endpoint(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> Invoice:
    invoice = await db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found")
    scope.check_access(invoice.branch_id)
    try:
        invoice = await finalize_invoice(db, invoice, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(invoice, attribute_names=["lines"])
    return invoice


@router.post("/{invoice_id}/void", response_model=InvoiceOut, dependencies=[Depends(CAN_VOID)])
async def void_invoice_endpoint(
    invoice_id: int,
    void_in: VoidRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> Invoice:
    invoice = await db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found")
    scope.check_access(invoice.branch_id)
    try:
        invoice = await void_invoice(db, invoice, user, void_in.reason)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(invoice, attribute_names=["lines"])
    return invoice
