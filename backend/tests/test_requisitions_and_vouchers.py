from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.accounting import Account, JournalEntry
from app.models.billing import ChargeItem
from app.models.enums import (
    AccountType,
    CashVoucherStatus,
    JournalSourceType,
    PaymentMethod,
    PurchaseOrderStatus,
    RequisitionSignatory,
    RequisitionStatus,
    RoleEnum,
)
from app.models.procurement import Supplier
from app.models.user import User
from app.schemas.procurement import PurchaseOrderCreate, PurchaseOrderLineIn
from app.schemas.requisition import RequisitionCreate, RequisitionLineIn
from app.schemas.voucher import CashVoucherCreate
from app.security import hash_password
from app.services import requisition_service, voucher_service
from app.services.posting_service import PostingError
from app.services.procurement_service import create_purchase_order, receive_purchase_order


# bcrypt is deliberately slow; hash once rather than per user per test.
_PASSWORD_HASH = hash_password("password")


@pytest_asyncio.fixture
async def ctx(db_session, seeded):
    branch = seeded["branch"]
    db_session.add_all(
        [
            Account(code="2200", name="Accounts Payable - Suppliers", type=AccountType.LIABILITY),
            Account(code="5000", name="Cost of Drugs", type=AccountType.EXPENSE),
        ]
    )

    users: dict[str, User] = {"accountant": seeded["user"]}
    for key, role in {
        "superintendent": RoleEnum.MEDICAL_SUPERINTENDENT,
        "matron": RoleEnum.MATRON,
        "admin": RoleEnum.ADMIN,
        "clerk": RoleEnum.ACCOUNTS_CLERK,
        "accountant2": RoleEnum.ACCOUNTANT,
        "cashier": RoleEnum.CASHIER,
    }.items():
        user = User(
            branch_id=branch.id,
            username=key,
            email=f"{key}@example.com",
            full_name=f"{key.title()} Person",
            hashed_password=_PASSWORD_HASH,
            role=role,
        )
        db_session.add(user)
        users[key] = user

    supplier = Supplier(code="SUP1", name="MedSupplies")
    db_session.add(supplier)
    await db_session.flush()

    item = ChargeItem(
        branch_id=branch.id,
        code="AMOX",
        name="Amoxicillin 500mg",
        category="Pharmacy",
        default_price=Decimal("5.00"),
        currency_code="USD",
        revenue_account_id=seeded["revenue"].id,
    )
    db_session.add(item)
    await db_session.flush()
    return {"branch": branch, "users": users, "supplier": supplier, "item": item}


def _requisition_in(ctx, supplier_id=None) -> RequisitionCreate:
    return RequisitionCreate(
        branch_id=ctx["branch"].id,
        department="Pharmacy",
        supplier_id=supplier_id,
        currency_code="USD",
        lines=[RequisitionLineIn(charge_item_id=ctx["item"].id, quantity=Decimal("10"), estimated_unit_cost=Decimal("2.50"))],
    )


async def _approved_requisition(db, ctx, supplier_id=None):
    requisition = await requisition_service.create_requisition(db, _requisition_in(ctx, supplier_id), ctx["users"]["cashier"])
    for key in ("superintendent", "matron", "admin"):
        requisition = await requisition_service.sign_requisition(db, requisition, ctx["users"][key])
    return requisition


async def _received_po(db, ctx, total_unit_cost="100.00"):
    po = await create_purchase_order(
        db,
        PurchaseOrderCreate(
            branch_id=ctx["branch"].id,
            supplier_id=ctx["supplier"].id,
            currency_code="USD",
            lines=[PurchaseOrderLineIn(charge_item_id=ctx["item"].id, quantity=Decimal("1"), unit_cost=Decimal(total_unit_cost))],
        ),
        ctx["users"]["cashier"],
    )
    return await receive_purchase_order(db, po, ctx["users"]["cashier"])


# ---------- purchase requisitions ----------


async def test_requisition_needs_all_three_signatures(db_session, ctx):
    users = ctx["users"]
    requisition = await requisition_service.create_requisition(db_session, _requisition_in(ctx), users["cashier"])
    assert requisition.status == RequisitionStatus.PENDING_APPROVAL
    assert requisition.total == Decimal("25.00")

    requisition = await requisition_service.sign_requisition(db_session, requisition, users["superintendent"])
    requisition = await requisition_service.sign_requisition(db_session, requisition, users["matron"])
    assert requisition.status == RequisitionStatus.PENDING_APPROVAL

    requisition = await requisition_service.sign_requisition(db_session, requisition, users["admin"])
    assert requisition.status == RequisitionStatus.APPROVED
    assert {s.signatory for s in requisition.signatures} == set(requisition_service.REQUIRED_SIGNATORIES)


async def test_signing_order_does_not_matter(db_session, ctx):
    users = ctx["users"]
    requisition = await requisition_service.create_requisition(db_session, _requisition_in(ctx), users["cashier"])
    for key in ("admin", "superintendent", "matron"):
        requisition = await requisition_service.sign_requisition(db_session, requisition, users[key])
    assert requisition.status == RequisitionStatus.APPROVED


async def test_same_signatory_cannot_sign_twice(db_session, ctx):
    users = ctx["users"]
    requisition = await requisition_service.create_requisition(db_session, _requisition_in(ctx), users["cashier"])
    await requisition_service.sign_requisition(db_session, requisition, users["matron"])
    with pytest.raises(PostingError, match="already been given"):
        await requisition_service.sign_requisition(db_session, requisition, users["matron"])


@pytest.mark.parametrize("key", ["accountant", "clerk", "cashier"])
async def test_only_the_three_signatories_can_sign(db_session, ctx, key):
    requisition = await requisition_service.create_requisition(db_session, _requisition_in(ctx), ctx["users"]["cashier"])
    with pytest.raises(PostingError, match="Only the Medical Superintendent"):
        await requisition_service.sign_requisition(db_session, requisition, ctx["users"][key])


async def test_reject_blocks_further_signing(db_session, ctx):
    users = ctx["users"]
    requisition = await requisition_service.create_requisition(db_session, _requisition_in(ctx), users["cashier"])
    await requisition_service.reject_requisition(db_session, requisition, users["matron"], "Over budget")
    assert requisition.status == RequisitionStatus.REJECTED
    with pytest.raises(PostingError, match="rejected"):
        await requisition_service.sign_requisition(db_session, requisition, users["admin"])


async def test_reject_needs_a_reason(db_session, ctx):
    requisition = await requisition_service.create_requisition(db_session, _requisition_in(ctx), ctx["users"]["cashier"])
    with pytest.raises(PostingError, match="reason"):
        await requisition_service.reject_requisition(db_session, requisition, ctx["users"]["matron"], "  ")


async def test_purchase_order_only_from_approved_requisition(db_session, ctx):
    requisition = await requisition_service.create_requisition(
        db_session, _requisition_in(ctx, ctx["supplier"].id), ctx["users"]["cashier"]
    )
    await requisition_service.sign_requisition(db_session, requisition, ctx["users"]["matron"])
    with pytest.raises(PostingError, match="three signatures"):
        await requisition_service.raise_purchase_order(db_session, requisition, ctx["users"]["cashier"], None)


async def test_approved_requisition_becomes_purchase_order(db_session, ctx):
    requisition = await _approved_requisition(db_session, ctx, ctx["supplier"].id)
    po = await requisition_service.raise_purchase_order(db_session, requisition, ctx["users"]["cashier"], None)

    assert po.status == PurchaseOrderStatus.DRAFT
    assert po.supplier_id == ctx["supplier"].id
    assert po.total == Decimal("25.00")
    assert [(l.charge_item_id, l.quantity, l.unit_cost) for l in po.lines] == [
        (ctx["item"].id, Decimal("10.00"), Decimal("2.50"))
    ]
    assert requisition.status == RequisitionStatus.ORDERED
    assert requisition.purchase_order_id == po.id

    with pytest.raises(PostingError, match="ordered"):
        await requisition_service.raise_purchase_order(db_session, requisition, ctx["users"]["cashier"], None)


async def test_purchase_order_needs_a_supplier(db_session, ctx):
    requisition = await _approved_requisition(db_session, ctx, supplier_id=None)
    with pytest.raises(PostingError, match="supplier"):
        await requisition_service.raise_purchase_order(db_session, requisition, ctx["users"]["cashier"], None)
    po = await requisition_service.raise_purchase_order(db_session, requisition, ctx["users"]["cashier"], ctx["supplier"].id)
    assert po.supplier_id == ctx["supplier"].id


# ---------- cash vouchers ----------


def _voucher_in(ctx, po, amount="40.00", method=PaymentMethod.CASH) -> CashVoucherCreate:
    return CashVoucherCreate(
        branch_id=ctx["branch"].id, purchase_order_id=po.id, method=method, amount=Decimal(amount)
    )


async def test_voucher_full_flow_posts_payment_only_on_disbursement(db_session, ctx):
    users = ctx["users"]
    po = await _received_po(db_session, ctx)
    voucher = await voucher_service.create_voucher(db_session, _voucher_in(ctx, po), users["clerk"])
    assert voucher.status == CashVoucherStatus.PENDING_CONFIRMATION

    voucher = await voucher_service.confirm_voucher(db_session, voucher, users["accountant"])
    assert voucher.status == CashVoucherStatus.CONFIRMED
    assert voucher.accountant_name == users["accountant"].full_name
    assert voucher.accountant_signed_at is not None
    # Confirmed is only permission to pay — no money has moved yet.
    assert po.amount_paid == Decimal("0")

    voucher = await voucher_service.disburse_voucher(db_session, voucher, users["clerk"])
    assert voucher.status == CashVoucherStatus.DISBURSED
    assert voucher.clerk_name == users["clerk"].full_name
    assert voucher.supplier_payment_id is not None
    assert po.amount_paid == Decimal("40.00")
    assert po.status == PurchaseOrderStatus.PARTIALLY_PAID

    entries = (
        await db_session.execute(
            select(JournalEntry).where(
                JournalEntry.source_type == JournalSourceType.SUPPLIER_PAYMENT,
                JournalEntry.source_id == voucher.supplier_payment_id,
            )
        )
    ).scalars().all()
    assert len(entries) == 1


async def test_clerk_cannot_disburse_before_accountant_confirms(db_session, ctx):
    po = await _received_po(db_session, ctx)
    voucher = await voucher_service.create_voucher(db_session, _voucher_in(ctx, po), ctx["users"]["clerk"])
    with pytest.raises(PostingError, match="pending_confirmation"):
        await voucher_service.disburse_voucher(db_session, voucher, ctx["users"]["clerk"])
    assert po.amount_paid == Decimal("0")


async def test_voucher_signatures_are_role_specific(db_session, ctx):
    users = ctx["users"]
    po = await _received_po(db_session, ctx)
    voucher = await voucher_service.create_voucher(db_session, _voucher_in(ctx, po), users["clerk"])

    for key in ("clerk", "admin", "cashier"):
        with pytest.raises(PostingError, match="accountant"):
            await voucher_service.confirm_voucher(db_session, voucher, users[key])

    await voucher_service.confirm_voucher(db_session, voucher, users["accountant"])
    for key in ("accountant", "accountant2", "admin"):
        with pytest.raises(PostingError, match="accounts clerk"):
            await voucher_service.disburse_voucher(db_session, voucher, users[key])


async def test_accountant_cannot_confirm_a_voucher_they_prepared(db_session, ctx):
    po = await _received_po(db_session, ctx)
    voucher = await voucher_service.create_voucher(db_session, _voucher_in(ctx, po), ctx["users"]["accountant"])
    with pytest.raises(PostingError, match="different accountant"):
        await voucher_service.confirm_voucher(db_session, voucher, ctx["users"]["accountant"])
    await voucher_service.confirm_voucher(db_session, voucher, ctx["users"]["accountant2"])


async def test_rejected_voucher_cannot_be_disbursed_and_frees_the_balance(db_session, ctx):
    users = ctx["users"]
    po = await _received_po(db_session, ctx)
    voucher = await voucher_service.create_voucher(db_session, _voucher_in(ctx, po, "100.00"), users["clerk"])

    with pytest.raises(PostingError, match="exceeds"):
        await voucher_service.create_voucher(db_session, _voucher_in(ctx, po, "1.00"), users["clerk"])

    await voucher_service.reject_voucher(db_session, voucher, users["accountant"], "Invoice disputed")
    assert voucher.status == CashVoucherStatus.REJECTED
    with pytest.raises(PostingError, match="rejected"):
        await voucher_service.disburse_voucher(db_session, voucher, users["clerk"])

    await voucher_service.create_voucher(db_session, _voucher_in(ctx, po, "100.00"), users["clerk"])


async def test_open_vouchers_cannot_over_commit_a_purchase_order(db_session, ctx):
    users = ctx["users"]
    po = await _received_po(db_session, ctx)
    await voucher_service.create_voucher(db_session, _voucher_in(ctx, po, "60.00"), users["clerk"])
    await voucher_service.create_voucher(db_session, _voucher_in(ctx, po, "40.00"), users["clerk"])
    with pytest.raises(PostingError, match="exceeds"):
        await voucher_service.create_voucher(db_session, _voucher_in(ctx, po, "0.01"), users["clerk"])


async def test_voucher_requires_received_purchase_order(db_session, ctx):
    po = await create_purchase_order(
        db_session,
        PurchaseOrderCreate(
            branch_id=ctx["branch"].id,
            supplier_id=ctx["supplier"].id,
            currency_code="USD",
            lines=[PurchaseOrderLineIn(charge_item_id=ctx["item"].id, quantity=Decimal("1"), unit_cost=Decimal("10"))],
        ),
        ctx["users"]["cashier"],
    )
    with pytest.raises(PostingError, match="received"):
        await voucher_service.create_voucher(db_session, _voucher_in(ctx, po, "10.00"), ctx["users"]["clerk"])


async def test_voucher_rejects_bad_amount_and_medical_aid(db_session, ctx):
    po = await _received_po(db_session, ctx)
    with pytest.raises(PostingError, match="positive"):
        await voucher_service.create_voucher(db_session, _voucher_in(ctx, po, "0"), ctx["users"]["clerk"])
    with pytest.raises(PostingError, match="medical aid"):
        await voucher_service.create_voucher(
            db_session, _voucher_in(ctx, po, "5.00", PaymentMethod.MEDICAL_AID), ctx["users"]["clerk"]
        )


async def test_cancelled_voucher_cannot_be_signed(db_session, ctx):
    users = ctx["users"]
    po = await _received_po(db_session, ctx)
    voucher = await voucher_service.create_voucher(db_session, _voucher_in(ctx, po), users["clerk"])
    await voucher_service.cancel_voucher(db_session, voucher, users["clerk"], "Raised in error")
    with pytest.raises(PostingError, match="cancelled"):
        await voucher_service.confirm_voucher(db_session, voucher, users["accountant"])


async def test_disbursed_voucher_cannot_be_cancelled_or_disbursed_again(db_session, ctx):
    users = ctx["users"]
    po = await _received_po(db_session, ctx)
    voucher = await voucher_service.create_voucher(db_session, _voucher_in(ctx, po), users["clerk"])
    await voucher_service.confirm_voucher(db_session, voucher, users["accountant"])
    await voucher_service.disburse_voucher(db_session, voucher, users["clerk"])

    with pytest.raises(PostingError, match="disbursed"):
        await voucher_service.disburse_voucher(db_session, voucher, users["clerk"])
    with pytest.raises(PostingError, match="disbursed"):
        await voucher_service.cancel_voucher(db_session, voucher, users["admin"], "oops")
    assert po.amount_paid == Decimal("40.00")
