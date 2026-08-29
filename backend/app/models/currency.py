from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class Currency(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(5), nullable=False)


class ExchangeRate(Base, TimestampMixin):
    """Rate to convert 1 unit of currency_code into the branch's base currency.

    Stored as a dated snapshot so historical transactions never drift when
    the rate changes later.
    """

    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    rate_to_base: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
