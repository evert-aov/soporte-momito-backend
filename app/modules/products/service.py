from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.modules.products.repository import ProductRepository, CategoryRepository, SupplierRepository
from app.modules.products.schemas import ProductCreate, ProductUpdate, CategoryCreate, CategoryUpdate, SupplierCreate


class ProductService:
    def __init__(self, db: Session):
        self.repo = ProductRepository(db)

    def list_products(self, skip: int = 0, limit: int = 100):
        return self.repo.get_all(skip, limit)

    def get_product(self, product_id: str):
        product = self.repo.get_by_id(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    def create_product(self, data: ProductCreate):
        existing = self.repo.get_by_id(data.id)
        if existing:
            raise HTTPException(status_code=400, detail="Product ID already exists")
        return self.repo.create(data.model_dump())

    def update_product(self, product_id: str, data: ProductUpdate):
        product = self.repo.update(product_id, data.model_dump(exclude_none=True))
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    def delete_product(self, product_id: str):
        return self.repo.delete(product_id)


class CategoryService:
    def __init__(self, db: Session):
        self.repo = CategoryRepository(db)

    def list_categories(self):
        return self.repo.get_all()

    def get_category(self, cat_id: int):
        cat = self.repo.get_by_id(cat_id)
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
        return cat

    def create_category(self, data: CategoryCreate):
        return self.repo.create(data.model_dump())

    def update_category(self, cat_id: int, data: CategoryUpdate):
        cat = self.repo.update(cat_id, data.model_dump(exclude_none=True))
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
        return cat

    def delete_category(self, cat_id: int):
        self.get_category(cat_id)
        return self.repo.delete(cat_id)


class SupplierService:
    def __init__(self, db: Session):
        self.repo = SupplierRepository(db)

    def list_suppliers(self):
        return self.repo.get_all()

    def create_supplier(self, data: SupplierCreate):
        return self.repo.create(data.model_dump())
