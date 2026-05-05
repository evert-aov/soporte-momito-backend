from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from database import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    issue_date = Column(DateTime, nullable=True)
    estimated_arrival_date = Column(DateTime, nullable=True)
    status = Column(String, default="draft")
    total_amount = Column(Numeric, nullable=True)

    supplier = relationship("Supplier")
    user = relationship("User")
    lines = relationship("PurchaseOrderLine", back_populates="purchase_order")


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    id = Column(Integer, primary_key=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=True)
    quantity = Column(Integer)
    unit_price = Column(Numeric)
    subtotal = Column(Numeric)

    purchase_order = relationship("PurchaseOrder", back_populates="lines")
    product = relationship("Product")


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    order_date = Column(DateTime, nullable=True)
    status = Column(String, default="pending_payment")
    subtotal = Column(Numeric, nullable=True)
    total_discount = Column(Numeric, nullable=True)
    total_amount = Column(Numeric, nullable=True)
    payment_terms = Column(String, nullable=True)
    source_channel = Column(String, nullable=True)
    payment_method = Column(String, nullable=True)
    paypal_order_id = Column(String, nullable=True)
    guest_email = Column(String, nullable=True)
    delivery_type = Column(String, nullable=True)  # 'delivery' | 'pickup'
    contact_name = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    delivery_address = Column(String, nullable=True)

    customer = relationship("Customer")
    user = relationship("User")
    lines = relationship("SalesOrderLine", back_populates="sales_order")
    invoices = relationship("Invoice", back_populates="sales_order")
    shipments = relationship("Shipment", back_populates="sales_order")


class SalesOrderLine(Base):
    __tablename__ = "sales_order_lines"

    id = Column(Integer, primary_key=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=True)
    quantity = Column(Integer)
    unit_price = Column(Numeric)
    subtotal = Column(Numeric)

    sales_order = relationship("SalesOrder", back_populates="lines")
    product = relationship("Product")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=True)
    invoice_number = Column(String, unique=True)
    issue_date = Column(DateTime, nullable=True)
    total_amount = Column(Numeric, nullable=True)
    payment_status = Column(String, nullable=True)
    xml_file_url = Column(String, nullable=True)
    html_file_path = Column(String, nullable=True)

    sales_order = relationship("SalesOrder", back_populates="invoices")


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=True)
    carrier = Column(String, nullable=True)
    tracking_number = Column(String, nullable=True)
    dispatch_date = Column(DateTime, nullable=True)
    estimated_delivery_date = Column(DateTime, nullable=True)
    delivery_status = Column(String, nullable=True)

    sales_order = relationship("SalesOrder", back_populates="shipments")


class PaymentSettings(Base):
    __tablename__ = "payment_settings"

    id = Column(Integer, primary_key=True)
    paypal_email = Column(String, nullable=True)
    qr_image_url = Column(String, nullable=True)


class CompanyInfo(Base):
    __tablename__ = "company_info"

    id = Column(Integer, primary_key=True)
    name = Column(String, default="TUMOMITO S.A.")
    legal_name = Column(String, nullable=True)
    tax_id = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    country = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
