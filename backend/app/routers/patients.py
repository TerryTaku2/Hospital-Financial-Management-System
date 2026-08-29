from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import require_role, verify_csrf
from app.models.enums import RoleEnum
from app.models.insurance import PatientCover
from app.models.patient import Patient
from app.schemas.patient import PatientCoverCreate, PatientCoverOut, PatientCreate, PatientOut

router = APIRouter(prefix="/api/patients", tags=["patients"], dependencies=[Depends(verify_csrf)])

CAN_REGISTER_PATIENTS = require_role(RoleEnum.ADMIN, RoleEnum.CASHIER, RoleEnum.ACCOUNTANT)


@router.get("", response_model=list[PatientOut])
async def list_patients(
    q: str | None = None,
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[Patient]:
    stmt = select(Patient)
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(Patient.branch_id == effective_branch_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(Patient.first_name.ilike(like), Patient.last_name.ilike(like), Patient.national_id.ilike(like))
        )
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id: int, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> Patient:
    patient = await db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    scope.check_access(patient.branch_id)
    return patient


@router.post("", response_model=PatientOut, dependencies=[Depends(CAN_REGISTER_PATIENTS)])
async def create_patient(
    patient_in: PatientCreate, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> Patient:
    scope.check_write(patient_in.branch_id)
    patient = Patient(**patient_in.model_dump())
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


@router.post("/covers", response_model=PatientCoverOut, dependencies=[Depends(CAN_REGISTER_PATIENTS)])
async def add_patient_cover(
    cover_in: PatientCoverCreate, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> PatientCover:
    patient = await db.get(Patient, cover_in.patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    scope.check_access(patient.branch_id)
    cover = PatientCover(**cover_in.model_dump())
    db.add(cover)
    await db.commit()
    await db.refresh(cover)
    return cover
