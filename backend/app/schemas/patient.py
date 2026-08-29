from datetime import date

from pydantic import BaseModel


class PatientCreate(BaseModel):
    branch_id: int
    first_name: str
    last_name: str
    date_of_birth: date | None = None
    sex: str | None = None
    national_id: str | None = None
    phone: str | None = None
    address: str | None = None


class PatientOut(PatientCreate):
    id: int

    model_config = {"from_attributes": True}


class PatientCoverCreate(BaseModel):
    patient_id: int
    medical_aid_provider_id: int
    membership_number: str
    scheme_name: str | None = None


class PatientCoverOut(PatientCoverCreate):
    id: int

    model_config = {"from_attributes": True}
