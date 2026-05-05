from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.modules.inventory.repository import InventoryRepository
from app.modules.inventory.schemas import InventoryCreate, InventoryUpdate


class InventoryService:
    def __init__(self, db: Session):
        self.repo = InventoryRepository(db)

    def list_inventory(self, skip: int = 0, limit: int = 100):
        return self.repo.get_all(skip, limit)

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
