from decimal import Decimal

import pytest

from app.models.billing import Invoice
from app.models.enums import InvoiceStatus, PayerType, PaymentMethod
from app.schemas.billing import PaymentCreate
from app.services.payment_service import record_payment


@pytest.mark.asyncio
async def test_duplicate_idempotency_key_does_not_double_post(db_session, seeded):
    invoice = Invoice(
        branch_id=seeded["branch"].id,
        patient_id=1,
        invoice_number="INV-TEST-0001",
        currency_code="USD",
        payer_type=PayerType.PATIENT,
        status=InvoiceStatus.FINALIZED,
        subtotal=Decimal("100.00"),
        total=Decimal("100.00"),
        created_by_id=seeded["user"].id,
    )
    db_session.add(invoice)
    await db_session.flush()

    payment_in = PaymentCreate(
        branch_id=seeded["branch"].id,
        invoice_id=invoice.id,
        payer_type=PayerType.PATIENT,
        method=PaymentMethod.CASH,
        currency_code="USD",
        amount=Decimal("40.00"),
    )

    payment1, created1 = await record_payment(db_session, payment_in, seeded["user"], idempotency_key="key-123")
    payment2, created2 = await record_payment(db_session, payment_in, seeded["user"], idempotency_key="key-123")

    assert created1 is True
    assert created2 is False
    assert payment1.id == payment2.id
    assert invoice.amount_paid == Decimal("40.00")
    assert invoice.status == InvoiceStatus.PARTIALLY_PAID


@pytest.mark.asyncio
async def test_payment_exceeding_balance_rejected(db_session, seeded):
    from app.services.posting_service import PostingError

    invoice = Invoice(
        branch_id=seeded["branch"].id,
        patient_id=1,
        invoice_number="INV-TEST-0002",
        currency_code="USD",
        payer_type=PayerType.PATIENT,
        status=InvoiceStatus.FINALIZED,
        subtotal=Decimal("50.00"),
        total=Decimal("50.00"),
        created_by_id=seeded["user"].id,
    )
    db_session.add(invoice)
    await db_session.flush()

    payment_in = PaymentCreate(
        branch_id=seeded["branch"].id,
        invoice_id=invoice.id,
        payer_type=PayerType.PATIENT,
        method=PaymentMethod.CASH,
        currency_code="USD",
        amount=Decimal("999.00"),
    )

    with pytest.raises(PostingError):
        await record_payment(db_session, payment_in, seeded["user"], idempotency_key="key-456")
