from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class BranchInventory(Base):
    __tablename__ = "branch_inventory"

    id = Column(Integer, primary_key=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    quantity = Column(Integer, default=0)
    min_stock = Column(Integer, default=0)
    last_updated = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="branch_inventory")
    branch = relationship("Branch")
