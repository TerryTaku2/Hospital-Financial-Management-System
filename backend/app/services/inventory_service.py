import secrets
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit_log
from app.models.billing import ChargeItem
from app.models.enums import AuditAction, StockLocation, StockRequisitionStatus
from app.models.inventory import StockAdjustment, StockBalance, StockRequisition, StockRequisitionLine
from app.models.user import User
from app.schemas.inventory import StockAdjustmentCreate, StockRequisitionCreate
from app.services.posting_service import PostingError


def _generate_requisition_number() -> str:
    return f"REQ-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(4).upper()}"


async def get_or_create_balance(db: AsyncSession, charge_item_id: int, location: StockLocation) -> StockBalance:
    stmt = select(StockBalance).where(
        StockBalance.charge_item_id == charge_item_id, StockBalance.location == location
    )
    balance = (await db.execute(stmt)).scalars().first()
    if balance is None:
        balance = StockBalance(charge_item_id=charge_item_id, location=location, quantity_on_hand=Decimal("0"))
        db.add(balance)
        await db.flush()
    return balance


async def adjust_balance(
    db: AsyncSession, charge_item_id: int, location: StockLocation, delta: Decimal
) -> StockBalance:
    balance = await get_or_create_balance(db, charge_item_id, location)
    balance.quantity_on_hand += delta
    await db.flush()
    return balance


async def create_requisition(db: AsyncSession, req_in: StockRequisitionCreate, user: User) -> StockRequisition:
    if not req_in.lines:
        raise PostingError("A stock requisition needs at least one line")

    charge_item_ids = {line.charge_item_id for line in req_in.lines}
    charge_items: dict[int, ChargeItem] = {}
    for charge_item_id in charge_item_ids:
        item = await db.get(ChargeItem, charge_item_id)
        if item is None or not item.is_active:
            raise PostingError(f"Unknown or inactive charge item {charge_item_id}")
        if item.branch_id != req_in.branch_id:
            raise PostingError(f"Charge item {charge_item_id} belongs to a different branch")
        charge_items[charge_item_id] = item

    requisition = StockRequisition(
        branch_id=req_in.branch_id,
        requisition_number=_generate_requisition_number(),
        status=StockRequisitionStatus.DRAFT,
        requested_by_id=user.id,
    )
    db.add(requisition)
    await db.flush()

    for line_in in req_in.lines:
        if line_in.quantity <= 0:
            raise PostingError("Requisition line quantity must be positive")
        item = charge_items[line_in.charge_item_id]
        db.add(
            StockRequisitionLine(
                requisition_id=requisition.id,
                charge_item_id=item.id,
                description=item.name,
                quantity=line_in.quantity,
            )
        )

    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=requisition.branch_id,
        table_name="stock_requisitions",
        record_id=requisition.id,
        action=AuditAction.CREATE,
        after={"requisition_number": requisition.requisition_number},
    )
    await db.refresh(requisition, attribute_names=["lines"])
    return requisition


async def issue_requisition(db: AsyncSession, requisition: StockRequisition, user: User) -> StockRequisition:
    if requisition.status != StockRequisitionStatus.DRAFT:
        raise PostingError(f"Requisition {requisition.id} is {requisition.status.value}, not draft — cannot issue")

    for line in requisition.lines:
        store_balance = await get_or_create_balance(db, line.charge_item_id, StockLocation.STORE)
        if store_balance.quantity_on_hand < line.quantity:
            raise PostingError(
                f"Insufficient store stock for {line.description}: have {store_balance.quantity_on_hand}, need {line.quantity}"
            )

    for line in requisition.lines:
        await adjust_balance(db, line.charge_item_id, StockLocation.STORE, -line.quantity)
        await adjust_balance(db, line.charge_item_id, StockLocation.PHARMACY, line.quantity)

    before_status = requisition.status
    requisition.status = StockRequisitionStatus.ISSUED
    requisition.issued_by_id = user.id
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=requisition.branch_id,
        table_name="stock_requisitions",
        record_id=requisition.id,
        action=AuditAction.UPDATE,
        before={"status": before_status.value},
        after={"status": requisition.status.value},
    )
    return requisition


async def cancel_requisition(db: AsyncSession, requisition: StockRequisition, user: User, reason: str) -> StockRequisition:
    if requisition.status != StockRequisitionStatus.DRAFT:
        raise PostingError(f"Requisition {requisition.id} is {requisition.status.value} — only a draft requisition can be cancelled")

    before_status = requisition.status
    requisition.status = StockRequisitionStatus.CANCELLED
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=requisition.branch_id,
        table_name="stock_requisitions",
        record_id=requisition.id,
        action=AuditAction.VOID,
        before={"status": before_status.value},
        after={"status": requisition.status.value, "reason": reason},
    )
    return requisition


async def create_adjustment(db: AsyncSession, adj_in: StockAdjustmentCreate, user: User) -> StockAdjustment:
    if adj_in.quantity_delta == 0:
        raise PostingError("Adjustment quantity delta must not be zero")

    item = await db.get(ChargeItem, adj_in.charge_item_id)
    if item is None or not item.is_active:
        raise PostingError(f"Unknown or inactive charge item {adj_in.charge_item_id}")
    if item.branch_id != adj_in.branch_id:
        raise PostingError(f"Charge item {adj_in.charge_item_id} belongs to a different branch")

    balance = await get_or_create_balance(db, item.id, adj_in.location)
    new_quantity = balance.quantity_on_hand + adj_in.quantity_delta
    if new_quantity < 0:
        raise PostingError(f"Adjustment would take {item.name} below zero (on hand {balance.quantity_on_hand}, delta {adj_in.quantity_delta})")
    balance.quantity_on_hand = new_quantity
    await db.flush()

    adjustment = StockAdjustment(
        branch_id=adj_in.branch_id,
        charge_item_id=item.id,
        location=adj_in.location,
        quantity_delta=adj_in.quantity_delta,
        reason=adj_in.reason,
        adjusted_by_id=user.id,
    )
    db.add(adjustment)
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=adj_in.branch_id,
        table_name="stock_adjustments",
        record_id=adjustment.id,
        action=AuditAction.CREATE,
        after={
            "charge_item_id": item.id,
            "location": adj_in.location.value,
            "quantity_delta": str(adj_in.quantity_delta),
            "reason": adj_in.reason,
        },
    )
    return adjustment
