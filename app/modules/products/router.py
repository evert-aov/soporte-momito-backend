from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from app.modules.products.schemas import (
    ProductCreate, ProductResponse, ProductUpdate,
    CategoryCreate, CategoryUpdate, CategoryResponse,
    SupplierCreate, SupplierResponse, PaginatedProducts,
)
from app.modules.products.service import ProductService, CategoryService, SupplierService
from app.core.dependencies import require_seller

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("/", response_model=PaginatedProducts)
def list_products(page: int = 1, page_size: int = 20, search: str = "", low_stock: bool = False,
                  db: Session = Depends(get_db)):
    return ProductService(db).list_paginated(page, page_size, search, low_stock)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db)):
    return ProductService(db).get_product(product_id)


@router.post("/", response_model=ProductResponse)
def create_product(data: ProductCreate, db: Session = Depends(get_db),
                   current_user=Depends(require_seller)):
    return ProductService(db).create_product(data)


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: str, data: ProductUpdate, db: Session = Depends(get_db),
                   current_user=Depends(require_seller)):
    return ProductService(db).update_product(product_id, data)


@router.delete("/{product_id}")
def delete_product(product_id: str, db: Session = Depends(get_db),
                   current_user=Depends(require_seller)):
    return ProductService(db).delete_product(product_id)


cat_router = APIRouter(prefix="/api/categories", tags=["categories"])


@cat_router.get("/", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return CategoryService(db).list_categories()


@cat_router.get("/{cat_id}", response_model=CategoryResponse)
def get_category(cat_id: int, db: Session = Depends(get_db)):
    return CategoryService(db).get_category(cat_id)


@cat_router.post("/", response_model=CategoryResponse)
def create_category(data: CategoryCreate, db: Session = Depends(get_db),
                    current_user=Depends(require_seller)):
    return CategoryService(db).create_category(data)


@cat_router.put("/{cat_id}", response_model=CategoryResponse)
def update_category(cat_id: int, data: CategoryUpdate, db: Session = Depends(get_db),
                    current_user=Depends(require_seller)):
    return CategoryService(db).update_category(cat_id, data)


@cat_router.delete("/{cat_id}")
def delete_category(cat_id: int, db: Session = Depends(get_db),
                    current_user=Depends(require_seller)):
    CategoryService(db).delete_category(cat_id)
    return {"ok": True}


sup_router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@sup_router.get("/", response_model=List[SupplierResponse])
def list_suppliers(db: Session = Depends(get_db),
                   current_user=Depends(require_seller)):
    return SupplierService(db).list_suppliers()


@sup_router.post("/", response_model=SupplierResponse)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db),
                    current_user=Depends(require_seller)):
    return SupplierService(db).create_supplier(data)
