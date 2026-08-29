from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin
from app.models.enums import EncounterStatus, EncounterType


class Encounter(Base, TimestampMixin):
    __tablename__ = "encounters"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    type: Mapped[EncounterType] = mapped_column(Enum(EncounterType), nullable=False)
    status: Mapped[EncounterStatus] = mapped_column(
        Enum(EncounterStatus), nullable=False, default=EncounterStatus.OPEN
    )
    attending_doctor_name: Mapped[str | None] = mapped_column(String(200))
    admission_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    discharge_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
