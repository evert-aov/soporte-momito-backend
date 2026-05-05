from sqlalchemy import (
    Column, Integer, String, Boolean, Numeric, ForeignKey
)
from sqlalchemy.orm import relationship
from database import Base


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    parent_id = Column(Integer, ForeignKey("product_categories.id"), nullable=True)

    parent = relationship("ProductCategory", remote_side=[id], back_populates="children")
    children = relationship("ProductCategory", back_populates="parent")
    products = relationship("Product", back_populates="category")


class UnitOfMeasure(Base):
    __tablename__ = "units_of_measure"

    id = Column(Integer, primary_key=True)
    name = Column(String)

    products_uom = relationship("Product", foreign_keys="Product.uom_id", back_populates="uom")
    products_uom_po = relationship("Product", foreign_keys="Product.uom_po_id", back_populates="uom_po")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    company_id = Column(Integer, nullable=True)
    country_of_origin = Column(String, nullable=True)
    email = Column(String, nullable=True)

    product_suppliers = relationship("ProductSupplier", back_populates="supplier")


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True)
    default_code = Column(String, unique=True, nullable=True)
    name = Column(String)
    active = Column(Boolean, default=True)
    type = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("product_categories.id"), nullable=True)
    uom_id = Column(Integer, ForeignKey("units_of_measure.id"), nullable=True)
    uom_po_id = Column(Integer, ForeignKey("units_of_measure.id"), nullable=True)
    list_price = Column(Numeric, nullable=True)
    standard_price = Column(Numeric, nullable=True)
    purchase_ok = Column(Boolean, default=True)
    sale_ok = Column(Boolean, default=True)
    taxes_id = Column(Integer, nullable=True)
    supplier_taxes_id = Column(Integer, nullable=True)
    image_url = Column(String, nullable=True)

    category = relationship("ProductCategory", back_populates="products")
    uom = relationship("UnitOfMeasure", foreign_keys=[uom_id], back_populates="products_uom")
    uom_po = relationship("UnitOfMeasure", foreign_keys=[uom_po_id], back_populates="products_uom_po")
    product_suppliers = relationship("ProductSupplier", back_populates="product")
    branch_inventory = relationship("BranchInventory", back_populates="product")


class ProductSupplier(Base):
    __tablename__ = "product_supplier"

    id = Column(Integer, primary_key=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    supplier_product_name = Column(String, nullable=True)
    min_qty = Column(Integer, nullable=True)
    delay = Column(Integer, nullable=True)

    product = relationship("Product", back_populates="product_suppliers")
    supplier = relationship("Supplier", back_populates="product_suppliers")
