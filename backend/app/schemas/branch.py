from pydantic import BaseModel


class BranchCreate(BaseModel):
    code: str
    name: str
    address: str | None = None
    base_currency_code: str = "USD"


class BranchOut(BaseModel):
    id: int
    code: str
    name: str
    address: str | None
    base_currency_code: str
    is_active: bool
    is_main: bool

    model_config = {"from_attributes": True}
