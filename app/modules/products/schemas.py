from pydantic import BaseModel
from typing import Optional
from decimal import Decimal


class ProductBase(BaseModel):
    id: str
    default_code: Optional[str] = None
    name: str
    active: bool = True
    type: Optional[str] = None
    category_id: Optional[int] = None
    uom_id: Optional[int] = None
    uom_po_id: Optional[int] = None
    list_price: Optional[Decimal] = None
    standard_price: Optional[Decimal] = None
    purchase_ok: bool = True
    sale_ok: bool = True
    taxes_id: Optional[int] = None
    supplier_taxes_id: Optional[int] = None
    image_url: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None
    list_price: Optional[Decimal] = None
    standard_price: Optional[Decimal] = None
    image_url: Optional[str] = None


class ProductResponse(ProductBase):
    class Config:
        from_attributes = True


class CategoryCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None

    class Config:
        from_attributes = True


class SupplierCreate(BaseModel):
    name: str
    country_of_origin: Optional[str] = None
    email: Optional[str] = None


class SupplierResponse(BaseModel):
    id: int
    name: str
    country_of_origin: Optional[str] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True
