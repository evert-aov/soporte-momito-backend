from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class InventoryCreate(BaseModel):
    product_id: str
    branch_id: int
    quantity: int
    min_stock: int = 0


class InventoryUpdate(BaseModel):
    quantity: Optional[int] = None
    min_stock: Optional[int] = None


class InventoryResponse(BaseModel):
    id: int
    product_id: str
    branch_id: Optional[int] = None
    quantity: int
    min_stock: int
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True
