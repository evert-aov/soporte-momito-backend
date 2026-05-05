from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    role_id: Optional[int] = None
    branch_id: Optional[int] = None
    customer_id: Optional[int] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role_id: Optional[int] = None
    branch_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class CustomerCreate(BaseModel):
    segment: Optional[str] = None
    commercial_name: Optional[str] = None
    legal_name: Optional[str] = None
    tax_id: Optional[str] = None
    credit_limit: Optional[float] = None
    pricing_profile: Optional[int] = None
    phone: Optional[str] = None
    delivery_address: Optional[str] = None


class CustomerResponse(CustomerCreate):
    id: int
    registration_date: Optional[datetime] = None

    class Config:
        from_attributes = True
