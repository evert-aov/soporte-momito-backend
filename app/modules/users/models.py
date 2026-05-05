from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Numeric, Text
)
from sqlalchemy.orm import relationship
from database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)

    users = relationship("User", back_populates="role")
    role_permissions = relationship("RolePermission", back_populates="role")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    name = Column(String)

    role_permissions = relationship("RolePermission", back_populates="permission")


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)

    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")


class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    location = Column(String)

    users = relationship("User", back_populates="branch")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    segment = Column(String)
    commercial_name = Column(String)
    legal_name = Column(String)
    tax_id = Column(String)
    credit_limit = Column(Numeric)
    pricing_profile = Column(Integer)
    phone = Column(String)
    delivery_address = Column(String)
    registration_date = Column(DateTime)

    users = relationship("User", back_populates="customer")
    crm_interactions = relationship("CrmInteraction", back_populates="customer")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    full_name = Column(String)
    email = Column(String, unique=True)
    password_hash = Column(String)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)

    role = relationship("Role", back_populates="users")
    branch = relationship("Branch", back_populates="users")
    customer = relationship("Customer", back_populates="users")
    crm_interactions = relationship("CrmInteraction", back_populates="user")


class CrmInteraction(Base):
    __tablename__ = "crm_interactions"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    interaction_type = Column(String)
    description = Column(Text)
    interaction_date = Column(DateTime)
    status = Column(String)

    customer = relationship("Customer", back_populates="crm_interactions")
    user = relationship("User", back_populates="crm_interactions")
