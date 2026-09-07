from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role, verify_csrf
from app.models.enums import RoleEnum
from app.models.procurement import Supplier
from app.models.user import User
from app.schemas.procurement import SupplierCreate, SupplierOut

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"], dependencies=[Depends(verify_csrf)])


@router.get("", response_model=list[SupplierOut])
async def list_suppliers(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> list[Supplier]:
    return list((await db.execute(select(Supplier).order_by(Supplier.name))).scalars().all())


@router.post(
    "", response_model=SupplierOut, dependencies=[Depends(require_role(RoleEnum.ADMIN, RoleEnum.ACCOUNTANT))]
)
async def create_supplier(supplier_in: SupplierCreate, db: AsyncSession = Depends(get_db)) -> Supplier:
    supplier = Supplier(**supplier_in.model_dump())
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier
