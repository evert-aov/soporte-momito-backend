from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from app.modules.users.schemas import UserCreate, UserResponse, UserUpdate, RoleCreate, RoleUpdate, RoleResponse, CustomerCreate, CustomerResponse, PaginatedCustomers
from app.modules.users.service import UserService, RoleService, CustomerService
from app.core.dependencies import require_admin

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/", response_model=List[UserResponse])
def list_users(skip: int = 0, limit: int | None = None, db: Session = Depends(get_db),
               current_user=Depends(require_admin)):
    return UserService(db).list_users(skip, limit)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db),
             current_user=Depends(require_admin)):
    return UserService(db).get_user(user_id)


@router.post("/", response_model=UserResponse)
def create_user(data: UserCreate, db: Session = Depends(get_db),
                current_user=Depends(require_admin)):
    return UserService(db).create_user(data)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db),
                current_user=Depends(require_admin)):
    return UserService(db).update_user(user_id, data)


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db),
                current_user=Depends(require_admin)):
    return UserService(db).delete_user(user_id)


roles_router = APIRouter(prefix="/api/roles", tags=["roles"])


@roles_router.get("/", response_model=List[RoleResponse])
def list_roles(db: Session = Depends(get_db), current_user=Depends(require_admin)):
    return RoleService(db).list_roles()


@roles_router.get("/{role_id}", response_model=RoleResponse)
def get_role(role_id: int, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    return RoleService(db).get_role(role_id)


@roles_router.post("/", response_model=RoleResponse)
def create_role(data: RoleCreate, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    return RoleService(db).create_role(data)


@roles_router.put("/{role_id}", response_model=RoleResponse)
def update_role(role_id: int, data: RoleUpdate, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    return RoleService(db).update_role(role_id, data)


@roles_router.delete("/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    return RoleService(db).delete_role(role_id)


customers_router = APIRouter(prefix="/api/customers", tags=["customers"])


@customers_router.get("/", response_model=PaginatedCustomers)
def list_customers(page: int = 1, page_size: int = 20, search: str = "",
                   db: Session = Depends(get_db), current_user=Depends(require_admin)):
    return CustomerService(db).list_paginated(page, page_size, search)


@customers_router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db),
                 current_user=Depends(require_admin)):
    return CustomerService(db).get_customer(customer_id)


@customers_router.post("/", response_model=CustomerResponse)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db),
                    current_user=Depends(require_admin)):
    return CustomerService(db).create_customer(data)
