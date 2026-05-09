import math
from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.modules.inventory.models import BranchInventory
from app.modules.users.models import Branch


class InventoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int | None = None):
        q = self.db.query(BranchInventory).offset(skip)
        return q.limit(limit).all() if limit is not None else q.all()

    def get_paginated(self, skip: int, limit: int, search: str = "", low_stock: bool = False) -> tuple[list, int]:
        from app.modules.products.models import Product
        q = self.db.query(BranchInventory, Product.name.label("product_name")).join(
            Product, BranchInventory.product_id == Product.id
        )
        if search:
            q = q.filter(or_(
                Product.name.ilike(f"%{search}%"),
                BranchInventory.product_id.ilike(f"%{search}%"),
            ))
        if low_stock:
            q = q.filter(BranchInventory.min_stock > 0, BranchInventory.quantity <= BranchInventory.min_stock)
        total = q.count()
        rows = q.order_by(BranchInventory.id.asc()).offset(skip).limit(limit).all()
        result = [
            {
                "id": inv.id, "product_id": inv.product_id, "product_name": pname or inv.product_id,
                "branch_id": inv.branch_id, "quantity": inv.quantity, "min_stock": inv.min_stock,
                "last_updated": inv.last_updated,
            }
            for inv, pname in rows
        ]
        return result, total

    def get_by_id(self, inventory_id: int):
        return self.db.query(BranchInventory).filter(BranchInventory.id == inventory_id).first()

    def get_by_product_branch(self, product_id: str, branch_id: int):
        return (
            self.db.query(BranchInventory)
            .filter(BranchInventory.product_id == product_id, BranchInventory.branch_id == branch_id)
            .first()
        )

    def create(self, data: dict):
        data["last_updated"] = datetime.utcnow()
        inv = BranchInventory(**data)
        self.db.add(inv)
        self.db.commit()
        self.db.refresh(inv)
        return inv

    def update(self, inventory_id: int, data: dict):
        inv = self.get_by_id(inventory_id)
        if not inv:
            return None
        data["last_updated"] = datetime.utcnow()
        for key, value in data.items():
            if value is not None:
                setattr(inv, key, value)
        self.db.commit()
        self.db.refresh(inv)
        return inv

    def delete(self, inventory_id: int):
        inv = self.get_by_id(inventory_id)
        if inv:
            self.db.delete(inv)
            self.db.commit()
        return inv

    def adjust_stock_for_lines(self, lines, delta: int):
        """Adjust stock for each line. delta=+1 to add (purchase), delta=-1 to deduct (sale)."""
        for line in lines:
            product_id = str(line.product_id)
            records = (
                self.db.query(BranchInventory)
                .filter(BranchInventory.product_id == product_id)
                .all()
            )
            if records:
                rec = records[0]
                new_qty = max(0, (rec.quantity or 0) + delta * line.quantity)
                rec.quantity = new_qty
                rec.last_updated = datetime.utcnow()
            elif delta > 0:
                # New product received via purchase — create inventory entry
                default_branch = self.db.query(Branch).first()
                new_inv = BranchInventory(
                    product_id=product_id,
                    branch_id=default_branch.id if default_branch else None,
                    quantity=line.quantity,
                    last_updated=datetime.utcnow(),
                )
                self.db.add(new_inv)
        self.db.commit()
