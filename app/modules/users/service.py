from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.modules.users.repository import UserRepository, RoleRepository, CustomerRepository
from app.modules.users.schemas import UserCreate, UserUpdate, CustomerCreate
from app.core.security import get_password_hash


class UserService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def list_users(self, skip: int = 0, limit: int | None = None):
        return self.repo.get_all(skip, limit)

    def get_user(self, user_id: int):
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    def create_user(self, data: UserCreate):
        existing = self.repo.get_by_email(data.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        return self.repo.create(
            full_name=data.full_name,
            email=data.email,
            password_hash=get_password_hash(data.password),
            role_id=data.role_id,
            branch_id=data.branch_id,
        )

    def update_user(self, user_id: int, data: UserUpdate):
        user = self.repo.update(user_id, data.model_dump(exclude_none=True))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    def delete_user(self, user_id: int):
        return self.repo.delete(user_id)


class RoleService:
    def __init__(self, db: Session):
        self.repo = RoleRepository(db)

    def list_roles(self):
        return self.repo.get_all()

    def get_role(self, role_id: int):
        role = self.repo.get_by_id(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        return role

    def create_role(self, data):
        return self.repo.create(data.model_dump())

    def update_role(self, role_id: int, data):
        self.get_role(role_id)
        return self.repo.update(role_id, data.model_dump(exclude_none=True))

    def delete_role(self, role_id: int):
        self.get_role(role_id)
        self.repo.delete(role_id)
        return {"ok": True}


class CustomerService:
    def __init__(self, db: Session):
        self.repo = CustomerRepository(db)

    def list_customers(self, skip: int = 0, limit: int | None = None):
        return self.repo.get_all(skip, limit)

    def list_paginated(self, page: int, page_size: int, search: str = "") -> dict:
        import math
        skip = (page - 1) * page_size
        items, total = self.repo.get_paginated(skip, page_size, search)
        return {"items": items, "total": total, "page": page, "page_size": page_size,
                "total_pages": max(1, math.ceil(total / page_size))}

    def get_customer(self, customer_id: int):
        customer = self.repo.get_by_id(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        return customer

    def create_customer(self, data: CustomerCreate):
        from datetime import datetime
        payload = data.model_dump()
        payload["registration_date"] = datetime.utcnow()
        return self.repo.create(payload)
