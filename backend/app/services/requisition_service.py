import secrets
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit_log
from app.models.billing import ChargeItem
from app.models.enums import AuditAction, RequisitionSignatory, RequisitionStatus, RoleEnum
from app.models.procurement import PurchaseOrder, Supplier
from app.models.requisition import PurchaseRequisition, PurchaseRequisitionLine, RequisitionSignature
from app.models.user import User
from app.schemas.procurement import PurchaseOrderCreate, PurchaseOrderLineIn
from app.schemas.requisition import RequisitionCreate
from app.services.posting_service import PostingError
from app.services.procurement_service import create_purchase_order

REQUIRED_SIGNATORIES = (
    RequisitionSignatory.MEDICAL_SUPERINTENDENT,
    RequisitionSignatory.MATRON,
    RequisitionSignatory.ADMIN,
)

_ROLE_TO_SIGNATORY = {
    RoleEnum.MEDICAL_SUPERINTENDENT: RequisitionSignatory.MEDICAL_SUPERINTENDENT,
    RoleEnum.MATRON: RequisitionSignatory.MATRON,
    RoleEnum.ADMIN: RequisitionSignatory.ADMIN,
}


def _generate_number() -> str:
    return f"PR-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(4).upper()}"


def signatory_for(user: User) -> RequisitionSignatory:
    signatory = _ROLE_TO_SIGNATORY.get(user.role)
    if signatory is None:
        raise PostingError("Only the Medical Superintendent, Matron or Admin can sign a purchase requisition")
    return signatory


def _require_pending(requisition: PurchaseRequisition, action: str) -> None:
    if requisition.status != RequisitionStatus.PENDING_APPROVAL:
        raise PostingError(
            f"Requisition {requisition.requisition_number} is {requisition.status.value} — cannot {action}"
        )


async def create_requisition(db: AsyncSession, req_in: RequisitionCreate, user: User) -> PurchaseRequisition:
    if not req_in.lines:
        raise PostingError("A purchase requisition needs at least one line")
    if not req_in.department.strip():
        raise PostingError("Department is required")

    if req_in.supplier_id is not None:
        supplier = await db.get(Supplier, req_in.supplier_id)
        if supplier is None or not supplier.is_active:
            raise PostingError(f"Unknown or inactive supplier {req_in.supplier_id}")

    charge_items: dict[int, ChargeItem] = {}
    for line in req_in.lines:
        if line.quantity <= 0:
            raise PostingError("Requisition line quantity must be positive")
        if line.estimated_unit_cost < 0:
            raise PostingError("Estimated unit cost cannot be negative")
        if line.charge_item_id not in charge_items:
            item = await db.get(ChargeItem, line.charge_item_id)
            if item is None or not item.is_active:
                raise PostingError(f"Unknown or inactive charge item {line.charge_item_id}")
            if item.branch_id != req_in.branch_id:
                raise PostingError(f"Charge item {line.charge_item_id} belongs to a different branch")
            charge_items[line.charge_item_id] = item

    requisition = PurchaseRequisition(
        branch_id=req_in.branch_id,
        requisition_number=_generate_number(),
        department=req_in.department.strip(),
        supplier_id=req_in.supplier_id,
        currency_code=req_in.currency_code,
        status=RequisitionStatus.PENDING_APPROVAL,
        justification=req_in.justification,
        requested_by_id=user.id,
    )
    db.add(requisition)
    await db.flush()

    total = Decimal("0")
    for line in req_in.lines:
        amount = (line.estimated_unit_cost * line.quantity).quantize(Decimal("0.01"))
        total += amount
        db.add(
            PurchaseRequisitionLine(
                requisition_id=requisition.id,
                charge_item_id=line.charge_item_id,
                description=charge_items[line.charge_item_id].name,
                quantity=line.quantity,
                estimated_unit_cost=line.estimated_unit_cost,
                amount=amount,
            )
        )
    requisition.total = total
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=requisition.branch_id,
        table_name="purchase_requisitions",
        record_id=requisition.id,
        action=AuditAction.CREATE,
        after={"requisition_number": requisition.requisition_number, "total": str(total)},
    )
    await db.refresh(requisition, attribute_names=["lines", "signatures"])
    return requisition


async def sign_requisition(db: AsyncSession, requisition: PurchaseRequisition, user: User) -> PurchaseRequisition:
    signatory = signatory_for(user)
    _require_pending(requisition, "sign")

    if any(sig.signatory == signatory for sig in requisition.signatures):
        raise PostingError(f"The {signatory.value.replace('_', ' ')} signature has already been given")

    db.add(
        RequisitionSignature(
            requisition_id=requisition.id,
            signatory=signatory,
            signed_by_id=user.id,
            signed_by_name=user.full_name,
        )
    )
    await db.flush()
    await db.refresh(requisition, attribute_names=["signatures"])

    before_status = requisition.status
    signed = {sig.signatory for sig in requisition.signatures}
    if all(required in signed for required in REQUIRED_SIGNATORIES):
        requisition.status = RequisitionStatus.APPROVED
        await db.flush()

    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=requisition.branch_id,
        table_name="purchase_requisitions",
        record_id=requisition.id,
        action=AuditAction.UPDATE,
        before={"status": before_status.value},
        after={"status": requisition.status.value, "signed_by": signatory.value},
    )
    return requisition


async def reject_requisition(
    db: AsyncSession, requisition: PurchaseRequisition, user: User, reason: str
) -> PurchaseRequisition:
    signatory_for(user)
    _require_pending(requisition, "reject")
    if not reason.strip():
        raise PostingError("A reason is required to reject a requisition")

    before_status = requisition.status
    requisition.status = RequisitionStatus.REJECTED
    requisition.rejection_reason = reason.strip()
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=requisition.branch_id,
        table_name="purchase_requisitions",
        record_id=requisition.id,
        action=AuditAction.UPDATE,
        before={"status": before_status.value},
        after={"status": requisition.status.value, "reason": requisition.rejection_reason},
    )
    return requisition


async def cancel_requisition(
    db: AsyncSession, requisition: PurchaseRequisition, user: User, reason: str
) -> PurchaseRequisition:
    _require_pending(requisition, "cancel")
    if not reason.strip():
        raise PostingError("A reason is required to cancel a requisition")

    before_status = requisition.status
    requisition.status = RequisitionStatus.CANCELLED
    requisition.rejection_reason = reason.strip()
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=requisition.branch_id,
        table_name="purchase_requisitions",
        record_id=requisition.id,
        action=AuditAction.VOID,
        before={"status": before_status.value},
        after={"status": requisition.status.value, "reason": requisition.rejection_reason},
    )
    return requisition


async def raise_purchase_order(
    db: AsyncSession, requisition: PurchaseRequisition, user: User, supplier_id: int | None
) -> PurchaseOrder:
    if requisition.status != RequisitionStatus.APPROVED:
        raise PostingError(
            f"Requisition {requisition.requisition_number} is {requisition.status.value} — "
            "it needs all three signatures before a purchase order can be raised"
        )
    chosen_supplier_id = supplier_id or requisition.supplier_id
    if chosen_supplier_id is None:
        raise PostingError("Choose a supplier for the purchase order")

    po = await create_purchase_order(
        db,
        PurchaseOrderCreate(
            branch_id=requisition.branch_id,
            supplier_id=chosen_supplier_id,
            currency_code=requisition.currency_code,
            lines=[
                PurchaseOrderLineIn(
                    charge_item_id=line.charge_item_id, quantity=line.quantity, unit_cost=line.estimated_unit_cost
                )
                for line in requisition.lines
            ],
        ),
        user,
    )
    before_status = requisition.status
    requisition.status = RequisitionStatus.ORDERED
    requisition.purchase_order_id = po.id
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=requisition.branch_id,
        table_name="purchase_requisitions",
        record_id=requisition.id,
        action=AuditAction.UPDATE,
        before={"status": before_status.value},
        after={"status": requisition.status.value, "purchase_order_id": po.id},
    )
    return po
