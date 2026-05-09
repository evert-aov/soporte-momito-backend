import math
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.modules.products.models import Product, ProductCategory, Supplier


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int | None = None):
        q = self.db.query(Product).filter(Product.active == True).offset(skip)
        return q.limit(limit).all() if limit is not None else q.all()

    def get_paginated(self, skip: int, limit: int, search: str = "", low_stock: bool = False) -> tuple[list, int]:
        from app.modules.inventory.models import BranchInventory
        q = self.db.query(Product).filter(Product.active.is_(True))
        if search:
            q = q.filter(or_(
                Product.name.ilike(f"%{search}%"),
                Product.default_code.ilike(f"%{search}%"),
            ))
        if low_stock:
            low_subq = (
                self.db.query(BranchInventory.product_id)
                .filter(BranchInventory.min_stock > 0, BranchInventory.quantity <= BranchInventory.min_stock)
                .subquery()
            )
            q = q.filter(Product.id.in_(low_subq))
        total = q.count()
        return q.order_by(Product.name.asc()).offset(skip).limit(limit).all(), total

    def get_by_id(self, product_id: str):
        return self.db.query(Product).filter(Product.id == product_id).first()

    def create(self, data: dict):
        product = Product(**data)
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def update(self, product_id: str, data: dict):
        product = self.get_by_id(product_id)
        if not product:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(product, key, value)
        self.db.commit()
        self.db.refresh(product)
        return product

    def delete(self, product_id: str):
        product = self.get_by_id(product_id)
        if product:
            product.active = False
            self.db.commit()
        return product


class CategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self):
        return self.db.query(ProductCategory).all()

    def get_by_id(self, cat_id: int):
        return self.db.query(ProductCategory).filter(ProductCategory.id == cat_id).first()

    def create(self, data: dict):
        cat = ProductCategory(**data)
        self.db.add(cat)
        self.db.commit()
        self.db.refresh(cat)
        return cat

    def update(self, cat_id: int, data: dict):
        cat = self.get_by_id(cat_id)
        if not cat:
            return None
        for key, value in data.items():
            setattr(cat, key, value)
        self.db.commit()
        self.db.refresh(cat)
        return cat

    def delete(self, cat_id: int):
        cat = self.get_by_id(cat_id)
        if cat:
            self.db.delete(cat)
            self.db.commit()
        return cat


class SupplierRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self):
        return self.db.query(Supplier).all()

    def get_by_id(self, supplier_id: int):
        return self.db.query(Supplier).filter(Supplier.id == supplier_id).first()

    def create(self, data: dict):
        supplier = Supplier(**data)
        self.db.add(supplier)
        self.db.commit()
        self.db.refresh(supplier)
        return supplier
