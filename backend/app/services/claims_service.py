import secrets
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit_log
from app.models.billing import Invoice, InvoiceLine
from app.models.enums import AuditAction, ClaimStatus, PayerType, PaymentMethod
from app.models.insurance import Claim, ClaimLine
from app.models.user import User
from app.schemas.billing import PaymentCreate
from app.schemas.insurance import ClaimCreate, ClaimDecision
from app.services.payment_service import record_payment
from app.services.posting_service import PostingError


def _generate_claim_number() -> str:
    return f"CLM-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(4).upper()}"


async def create_claim(db: AsyncSession, claim_in: ClaimCreate, user: User) -> Claim:
    invoice = await db.get(Invoice, claim_in.invoice_id)
    if invoice is None:
        raise PostingError(f"Unknown invoice_id {claim_in.invoice_id}")
    if invoice.payer_type != PayerType.MEDICAL_AID:
        raise PostingError("Only invoices billed to a medical aid provider can have claims")

    if not claim_in.invoice_line_ids:
        raise PostingError("A claim needs at least one invoice line")

    submitted_amount = Decimal("0")
    claim = Claim(
        branch_id=invoice.branch_id,
        invoice_id=invoice.id,
        patient_id=invoice.patient_id,
        medical_aid_provider_id=claim_in.medical_aid_provider_id,
        claim_number=_generate_claim_number(),
        status=ClaimStatus.DRAFT,
        submitted_amount=Decimal("0"),
        currency_code=invoice.currency_code,
    )
    db.add(claim)
    await db.flush()

    for line_id in claim_in.invoice_line_ids:
        line = await db.get(InvoiceLine, line_id)
        if line is None or line.invoice_id != invoice.id:
            raise PostingError(f"Invoice line {line_id} does not belong to invoice {invoice.id}")
        submitted_amount += line.amount
        db.add(ClaimLine(claim_id=claim.id, invoice_line_id=line.id, amount=line.amount))

    claim.submitted_amount = submitted_amount
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=claim.branch_id,
        table_name="claims",
        record_id=claim.id,
        action=AuditAction.CREATE,
        after={"claim_number": claim.claim_number, "submitted_amount": str(submitted_amount)},
    )
    await db.refresh(claim, attribute_names=["lines"])
    return claim


async def submit_claim(db: AsyncSession, claim: Claim, user: User) -> Claim:
    if claim.status != ClaimStatus.DRAFT:
        raise PostingError(f"Claim {claim.id} is {claim.status.value} — cannot submit")
    claim.status = ClaimStatus.SUBMITTED
    claim.submitted_at = datetime.now(timezone.utc)
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=claim.branch_id,
        table_name="claims",
        record_id=claim.id,
        action=AuditAction.UPDATE,
        after={"status": claim.status.value},
    )
    return claim


async def decide_claim(db: AsyncSession, claim: Claim, decision: ClaimDecision, user: User) -> Claim:
    if claim.status != ClaimStatus.SUBMITTED:
        raise PostingError(f"Claim {claim.id} is {claim.status.value} — cannot decide")

    claim.decided_at = datetime.now(timezone.utc)

    if not decision.approve:
        claim.status = ClaimStatus.REJECTED
        claim.rejection_reason = decision.rejection_reason or "No reason given"
        await db.flush()
        await write_audit_log(
            db,
            actor_id=user.id,
            branch_id=claim.branch_id,
            table_name="claims",
            record_id=claim.id,
            action=AuditAction.UPDATE,
            after={"status": claim.status.value, "reason": claim.rejection_reason},
        )
        return claim

    approved_amount = decision.approved_amount if decision.approved_amount is not None else claim.submitted_amount
    if approved_amount <= 0 or approved_amount > claim.submitted_amount:
        raise PostingError(f"Approved amount {approved_amount} must be between 0 and {claim.submitted_amount}")

    claim.approved_amount = approved_amount
    claim.status = ClaimStatus.APPROVED
    await db.flush()

    payment_in = PaymentCreate(
        branch_id=claim.branch_id,
        invoice_id=claim.invoice_id,
        payer_type=PayerType.MEDICAL_AID,
        medical_aid_provider_id=claim.medical_aid_provider_id,
        method=PaymentMethod.MEDICAL_AID,
        currency_code=claim.currency_code,
        amount=approved_amount,
    )
    await record_payment(db, payment_in, user, idempotency_key=f"claim-payment-{claim.id}")

    claim.status = ClaimStatus.PAID
    await db.flush()

    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=claim.branch_id,
        table_name="claims",
        record_id=claim.id,
        action=AuditAction.UPDATE,
        after={"status": claim.status.value, "approved_amount": str(approved_amount)},
    )
    return claim
