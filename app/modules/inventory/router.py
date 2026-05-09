from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from app.modules.inventory.schemas import InventoryCreate, InventoryResponse, InventoryUpdate, PaginatedInventory
from app.modules.inventory.service import InventoryService
from app.core.dependencies import require_seller

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("/", response_model=PaginatedInventory)
def list_inventory(page: int = 1, page_size: int = 20, search: str = "", low_stock: bool = False,
                   db: Session = Depends(get_db), current_user=Depends(require_seller)):
    return InventoryService(db).list_paginated(page, page_size, search, low_stock)


@router.get("/{inventory_id}", response_model=InventoryResponse)
def get_inventory(inventory_id: int, db: Session = Depends(get_db),
                  current_user=Depends(require_seller)):
    return InventoryService(db).get_inventory(inventory_id)


@router.post("/", response_model=InventoryResponse)
def create_inventory(data: InventoryCreate, db: Session = Depends(get_db),
                     current_user=Depends(require_seller)):
    return InventoryService(db).create_inventory(data)


@router.put("/{inventory_id}", response_model=InventoryResponse)
def update_inventory(inventory_id: int, data: InventoryUpdate, db: Session = Depends(get_db),
                     current_user=Depends(require_seller)):
    return InventoryService(db).update_inventory(inventory_id, data)


@router.delete("/{inventory_id}")
def delete_inventory(inventory_id: int, db: Session = Depends(get_db),
                     current_user=Depends(require_seller)):
    return InventoryService(db).delete_inventory(inventory_id)
