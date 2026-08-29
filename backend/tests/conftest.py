from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.accounting import Account
from app.models.branch import Branch
from app.models.currency import Currency
from app.models.enums import AccountType, RoleEnum
from app.models.user import User
from app.security import hash_password


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def seeded(db_session: AsyncSession):
    db_session.add(Currency(code="USD", name="US Dollar", symbol="$"))
    branch = Branch(code="MAIN", name="Main Hospital", base_currency_code="USD")
    db_session.add(branch)
    await db_session.flush()

    cash = Account(code="1000", name="Cash", type=AccountType.ASSET)
    ar = Account(code="1100", name="AR - Patients", type=AccountType.ASSET)
    revenue = Account(code="4000", name="Revenue", type=AccountType.INCOME)
    db_session.add_all([cash, ar, revenue])

    user = User(
        branch_id=branch.id,
        username="tester",
        email="tester@example.com",
        full_name="Test User",
        hashed_password=hash_password("password"),
        role=RoleEnum.ACCOUNTANT,
    )
    db_session.add(user)
    await db_session.flush()

    return {
        "branch": branch,
        "cash": cash,
        "ar": ar,
        "revenue": revenue,
        "user": user,
    }
