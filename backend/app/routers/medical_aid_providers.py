from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role, verify_csrf
from app.models.enums import RoleEnum
from app.models.insurance import MedicalAidProvider
from app.models.user import User
from app.schemas.insurance import MedicalAidProviderCreate, MedicalAidProviderOut

router = APIRouter(prefix="/api/medical-aid-providers", tags=["medical-aid-providers"], dependencies=[Depends(verify_csrf)])


@router.get("", response_model=list[MedicalAidProviderOut])
async def list_providers(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> list[MedicalAidProvider]:
    return list((await db.execute(select(MedicalAidProvider))).scalars().all())


@router.post(
    "",
    response_model=MedicalAidProviderOut,
    dependencies=[Depends(require_role(RoleEnum.ADMIN, RoleEnum.ACCOUNTANT))],
)
async def create_provider(provider_in: MedicalAidProviderCreate, db: AsyncSession = Depends(get_db)) -> MedicalAidProvider:
    provider = MedicalAidProvider(**provider_in.model_dump())
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider
