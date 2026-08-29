from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import ClaimStatus


class MedicalAidProviderCreate(BaseModel):
    code: str
    name: str
    contact_info: str | None = None
    ar_account_id: int | None = None


class MedicalAidProviderOut(MedicalAidProviderCreate):
    id: int

    model_config = {"from_attributes": True}


class ClaimLineOut(BaseModel):
    id: int
    invoice_line_id: int
    amount: Decimal

    model_config = {"from_attributes": True}


class ClaimCreate(BaseModel):
    invoice_id: int
    medical_aid_provider_id: int
    invoice_line_ids: list[int]


class ClaimOut(BaseModel):
    id: int
    branch_id: int
    invoice_id: int
    patient_id: int
    medical_aid_provider_id: int
    claim_number: str
    status: ClaimStatus
    submitted_amount: Decimal
    approved_amount: Decimal | None
    currency_code: str
    submitted_at: datetime | None
    decided_at: datetime | None
    rejection_reason: str | None
    lines: list[ClaimLineOut] = []

    model_config = {"from_attributes": True}


class ClaimDecision(BaseModel):
    approve: bool
    approved_amount: Decimal | None = None
    rejection_reason: str | None = None
