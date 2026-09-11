from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin
from app.models.enums import AssetStatus


class Asset(Base, TimestampMixin):
    """A fixed-asset register entry. Cost is the historical acquisition
    cost; netbook_value is carried and updated directly rather than
    computed off a depreciation schedule."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    asset_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    asset_name: Mapped[str] = mapped_column(String(200), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    netbook_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[AssetStatus] = mapped_column(Enum(AssetStatus), nullable=False, default=AssetStatus.ACTIVE)
