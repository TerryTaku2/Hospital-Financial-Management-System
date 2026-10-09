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
    next_of_kin_name: str | None = None
    next_of_kin_relationship: str | None = None
    next_of_kin_phone: str | None = None
    next_of_kin_address: str | None = None


class PatientUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    sex: str | None = None
    national_id: str | None = None
    phone: str | None = None
    address: str | None = None
    next_of_kin_name: str | None = None
    next_of_kin_relationship: str | None = None
    next_of_kin_phone: str | None = None
    next_of_kin_address: str | None = None


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
