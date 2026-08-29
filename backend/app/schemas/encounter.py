from datetime import datetime

from pydantic import BaseModel

from app.models.enums import EncounterStatus, EncounterType


class EncounterCreate(BaseModel):
    branch_id: int
    patient_id: int
    type: EncounterType
    attending_doctor_name: str | None = None
    admission_date: datetime


class EncounterOut(EncounterCreate):
    id: int
    status: EncounterStatus
    discharge_date: datetime | None

    model_config = {"from_attributes": True}


class EncounterClose(BaseModel):
    discharge_date: datetime
