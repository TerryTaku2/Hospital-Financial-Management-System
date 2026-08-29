from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import require_role, verify_csrf
from app.models.encounter import Encounter
from app.models.enums import EncounterStatus, RoleEnum
from app.schemas.encounter import EncounterClose, EncounterCreate, EncounterOut

router = APIRouter(prefix="/api/encounters", tags=["encounters"], dependencies=[Depends(verify_csrf)])

CAN_MANAGE_ENCOUNTERS = require_role(RoleEnum.ADMIN, RoleEnum.CASHIER, RoleEnum.ACCOUNTANT, RoleEnum.CLINICIAN)


@router.get("", response_model=list[EncounterOut])
async def list_encounters(
    patient_id: int | None = None,
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[Encounter]:
    stmt = select(Encounter)
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(Encounter.branch_id == effective_branch_id)
    if patient_id is not None:
        stmt = stmt.where(Encounter.patient_id == patient_id)
    return list((await db.execute(stmt)).scalars().all())


@router.post("", response_model=EncounterOut, dependencies=[Depends(CAN_MANAGE_ENCOUNTERS)])
async def create_encounter(
    encounter_in: EncounterCreate, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> Encounter:
    scope.check_write(encounter_in.branch_id)
    encounter = Encounter(**encounter_in.model_dump())
    db.add(encounter)
    await db.commit()
    await db.refresh(encounter)
    return encounter


@router.post("/{encounter_id}/close", response_model=EncounterOut, dependencies=[Depends(CAN_MANAGE_ENCOUNTERS)])
async def close_encounter(
    encounter_id: int,
    close_in: EncounterClose,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> Encounter:
    encounter = await db.get(Encounter, encounter_id)
    if encounter is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Encounter not found")
    scope.check_access(encounter.branch_id)
    encounter.status = EncounterStatus.CLOSED
    encounter.discharge_date = close_in.discharge_date
    await db.commit()
    await db.refresh(encounter)
    return encounter
