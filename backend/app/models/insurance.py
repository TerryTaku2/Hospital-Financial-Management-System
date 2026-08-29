from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin
from app.models.enums import ClaimStatus


class MedicalAidProvider(Base, TimestampMixin):
    __tablename__ = "medical_aid_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_info: Mapped[str | None] = mapped_column(String(300))
    ar_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))


class PatientCover(Base, TimestampMixin):
    __tablename__ = "patient_covers"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    medical_aid_provider_id: Mapped[int] = mapped_column(ForeignKey("medical_aid_providers.id"), nullable=False)
    membership_number: Mapped[str] = mapped_column(String(100), nullable=False)
    scheme_name: Mapped[str | None] = mapped_column(String(200))


class Claim(Base, TimestampMixin):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    medical_aid_provider_id: Mapped[int] = mapped_column(ForeignKey("medical_aid_providers.id"), nullable=False)
    claim_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[ClaimStatus] = mapped_column(Enum(ClaimStatus), nullable=False, default=ClaimStatus.DRAFT)
    submitted_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    approved_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(String(500))

    lines: Mapped[list["ClaimLine"]] = relationship(back_populates="claim", lazy="selectin")


class ClaimLine(Base, TimestampMixin):
    __tablename__ = "claim_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id"), nullable=False)
    invoice_line_id: Mapped[int] = mapped_column(ForeignKey("invoice_lines.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    claim: Mapped["Claim"] = relationship(back_populates="lines")
