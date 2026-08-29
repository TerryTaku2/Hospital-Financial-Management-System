from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import get_current_user, require_role, verify_csrf
from app.models.billing import Invoice
from app.models.enums import RoleEnum
from app.models.insurance import Claim
from app.models.user import User
from app.schemas.insurance import ClaimCreate, ClaimDecision, ClaimOut
from app.services.claims_service import create_claim, decide_claim, submit_claim
from app.services.posting_service import PostingError

router = APIRouter(prefix="/api/claims", tags=["claims"], dependencies=[Depends(verify_csrf)])

CAN_FILE_CLAIMS = require_role(RoleEnum.ADMIN, RoleEnum.CASHIER, RoleEnum.ACCOUNTANT)
CAN_DECIDE_CLAIMS = require_role(RoleEnum.ADMIN, RoleEnum.ACCOUNTANT)


async def _get_claim_or_404(db: AsyncSession, claim_id: int) -> Claim:
    claim = await db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")
    return claim


@router.get("", response_model=list[ClaimOut])
async def list_claims(
    patient_id: int | None = None,
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[Claim]:
    stmt = select(Claim).order_by(Claim.id.desc())
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(Claim.branch_id == effective_branch_id)
    if patient_id is not None:
        stmt = stmt.where(Claim.patient_id == patient_id)
    return list((await db.execute(stmt)).scalars().all())


@router.post("", response_model=ClaimOut, dependencies=[Depends(CAN_FILE_CLAIMS)])
async def create_claim_endpoint(
    claim_in: ClaimCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> Claim:
    invoice = await db.get(Invoice, claim_in.invoice_id)
    if invoice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found")
    scope.check_access(invoice.branch_id)
    try:
        claim = await create_claim(db, claim_in, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(claim, attribute_names=["lines"])
    return claim


@router.post("/{claim_id}/submit", response_model=ClaimOut, dependencies=[Depends(CAN_FILE_CLAIMS)])
async def submit_claim_endpoint(
    claim_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> Claim:
    claim = await _get_claim_or_404(db, claim_id)
    scope.check_access(claim.branch_id)
    try:
        claim = await submit_claim(db, claim, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(claim, attribute_names=["lines"])
    return claim


@router.post("/{claim_id}/decide", response_model=ClaimOut, dependencies=[Depends(CAN_DECIDE_CLAIMS)])
async def decide_claim_endpoint(
    claim_id: int,
    decision: ClaimDecision,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> Claim:
    claim = await _get_claim_or_404(db, claim_id)
    scope.check_access(claim.branch_id)
    try:
        claim = await decide_claim(db, claim, decision, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(claim, attribute_names=["lines"])
    return claim
