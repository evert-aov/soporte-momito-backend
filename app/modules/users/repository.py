import math
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.modules.users.models import User, Role, Customer


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()

    def get_by_id(self, user_id: int):
        return self.db.query(User).filter(User.id == user_id).first()

    def get_all(self, skip: int = 0, limit: int | None = None):
        q = self.db.query(User).offset(skip)
        return q.limit(limit).all() if limit is not None else q.all()

    def create(self, full_name: str, email: str, password_hash: str,
               role_id: int = None, branch_id: int = None):
        user = User(
            full_name=full_name,
            email=email,
            password_hash=password_hash,
            role_id=role_id,
            branch_id=branch_id
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user_id: int, data: dict):
        user = self.get_by_id(user_id)
        if not user:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user_id: int):
        user = self.get_by_id(user_id)
        if user:
            user.is_active = False
            self.db.commit()
        return user


class RoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self):
        return self.db.query(Role).all()

    def get_by_id(self, role_id: int):
        return self.db.query(Role).filter(Role.id == role_id).first()

    def create(self, data: dict) -> Role:
        role = Role(**data)
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def update(self, role_id: int, data: dict) -> Role:
        role = self.get_by_id(role_id)
        for k, v in data.items():
            setattr(role, k, v)
        self.db.commit()
        self.db.refresh(role)
        return role

    def delete(self, role_id: int):
        role = self.get_by_id(role_id)
        self.db.delete(role)
        self.db.commit()


class CustomerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int | None = None):
        q = self.db.query(Customer).offset(skip)
        return q.limit(limit).all() if limit is not None else q.all()

    def get_paginated(self, skip: int, limit: int, search: str = "") -> tuple[list, int]:
        q = self.db.query(Customer).order_by(Customer.id.desc())
        if search:
            q = q.filter(or_(
                Customer.commercial_name.ilike(f"%{search}%"),
                Customer.legal_name.ilike(f"%{search}%"),
                Customer.tax_id.ilike(f"%{search}%"),
            ))
        total = q.count()
        return q.offset(skip).limit(limit).all(), total

    def get_by_id(self, customer_id: int):
        return self.db.query(Customer).filter(Customer.id == customer_id).first()

    def create(self, data: dict):
        customer = Customer(**data)
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer
