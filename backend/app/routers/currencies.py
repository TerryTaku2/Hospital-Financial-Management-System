from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role, verify_csrf
from app.models.currency import Currency, ExchangeRate
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.currency import CurrencyOut, ExchangeRateCreate, ExchangeRateOut

router = APIRouter(prefix="/api/currencies", tags=["currencies"], dependencies=[Depends(verify_csrf)])


@router.get("", response_model=list[CurrencyOut])
async def list_currencies(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> list[Currency]:
    return list((await db.execute(select(Currency))).scalars().all())


@router.get("/exchange-rates", response_model=list[ExchangeRateOut])
async def list_exchange_rates(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> list[ExchangeRate]:
    stmt = select(ExchangeRate).order_by(ExchangeRate.effective_date.desc())
    return list((await db.execute(stmt)).scalars().all())


@router.post(
    "/exchange-rates",
    response_model=ExchangeRateOut,
    dependencies=[Depends(require_role(RoleEnum.ADMIN, RoleEnum.ACCOUNTANT))],
)
async def create_exchange_rate(rate_in: ExchangeRateCreate, db: AsyncSession = Depends(get_db)) -> ExchangeRate:
    rate = ExchangeRate(**rate_in.model_dump())
    db.add(rate)
    await db.commit()
    await db.refresh(rate)
    return rate
