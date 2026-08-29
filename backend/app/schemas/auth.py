from pydantic import BaseModel, EmailStr

from app.models.enums import RoleEnum


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    branch_id: int
    username: str
    email: EmailStr
    full_name: str
    role: RoleEnum
    is_active: bool
    can_view_all_branches: bool = False

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    branch_id: int
    username: str
    email: EmailStr
    full_name: str
    password: str
    role: RoleEnum
