import math
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.modules.inventory.repository import InventoryRepository
from app.modules.inventory.schemas import InventoryCreate, InventoryUpdate


class InventoryService:
    def __init__(self, db: Session):
        self.repo = InventoryRepository(db)

    def list_inventory(self, skip: int = 0, limit: int | None = None):
        return self.repo.get_all(skip, limit)

    def list_paginated(self, page: int, page_size: int, search: str = "", low_stock: bool = False) -> dict:
        skip = (page - 1) * page_size
        items, total = self.repo.get_paginated(skip, page_size, search, low_stock)
        return {"items": items, "total": total, "page": page, "page_size": page_size,
                "total_pages": max(1, math.ceil(total / page_size))}

    def get_inventory(self, inventory_id: int):
        inv = self.repo.get_by_id(inventory_id)
        if not inv:
            raise HTTPException(status_code=404, detail="Inventory record not found")
        return inv

    def create_inventory(self, data: InventoryCreate):
        existing = self.repo.get_by_product_branch(data.product_id, data.branch_id)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Inventory record for this product/branch already exists"
            )
        return self.repo.create(data.model_dump())

    def update_inventory(self, inventory_id: int, data: InventoryUpdate):
        inv = self.repo.update(inventory_id, data.model_dump(exclude_none=True))
        if not inv:
            raise HTTPException(status_code=404, detail="Inventory record not found")
        return inv

    def delete_inventory(self, inventory_id: int):
        inv = self.repo.delete(inventory_id)
        if not inv:
            raise HTTPException(status_code=404, detail="Inventory record not found")
        return {"message": "Deleted"}
