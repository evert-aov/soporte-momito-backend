from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


# --- Purchase Orders ---

class PurchaseOrderLineCreate(BaseModel):
    product_id: str
    quantity: int
    unit_price: Decimal


class PurchaseOrderLineResponse(BaseModel):
    id: int
    product_id: Optional[str] = None
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    class Config:
        from_attributes = True


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    estimated_arrival_date: Optional[datetime] = None
    lines: List[PurchaseOrderLineCreate]


class PurchaseOrderResponse(BaseModel):
    id: int
    supplier_id: Optional[int] = None
    user_id: Optional[int] = None
    issue_date: Optional[datetime] = None
    estimated_arrival_date: Optional[datetime] = None
    status: str
    total_amount: Optional[Decimal] = None

    class Config:
        from_attributes = True


class PurchaseOrderDetailResponse(PurchaseOrderResponse):
    lines: List[PurchaseOrderLineResponse] = []

    class Config:
        from_attributes = True


# --- Sales Orders ---

class SalesOrderLineCreate(BaseModel):
    product_id: str
    quantity: int
    unit_price: Decimal


class SalesOrderLineResponse(BaseModel):
    id: int
    product_id: Optional[str] = None
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    class Config:
        from_attributes = True


class SalesOrderCreate(BaseModel):
    customer_id: Optional[int] = None
    payment_terms: Optional[str] = None
    source_channel: Optional[str] = None
    total_discount: Optional[Decimal] = Decimal("0")
    lines: List[SalesOrderLineCreate]


class SalesOrderResponse(BaseModel):
    id: int
    customer_id: Optional[int] = None
    user_id: Optional[int] = None
    order_date: Optional[datetime] = None
    status: str
    subtotal: Optional[Decimal] = None
    total_discount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    payment_terms: Optional[str] = None
    source_channel: Optional[str] = None
    payment_method: Optional[str] = None
    paypal_order_id: Optional[str] = None
    guest_email: Optional[str] = None
    delivery_type: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    delivery_address: Optional[str] = None

    class Config:
        from_attributes = True


class SalesOrderDetailResponse(SalesOrderResponse):
    lines: List[SalesOrderLineResponse] = []

    class Config:
        from_attributes = True


# --- Invoice ---

class InvoiceCreate(BaseModel):
    sales_order_id: int
    invoice_number: str
    total_amount: Optional[Decimal] = None
    payment_status: Optional[str] = "pending"


class InvoiceResponse(BaseModel):
    id: int
    sales_order_id: Optional[int] = None
    invoice_number: str
    issue_date: Optional[datetime] = None
    total_amount: Optional[Decimal] = None
    payment_status: Optional[str] = None
    xml_file_url: Optional[str] = None
    html_file_path: Optional[str] = None

    class Config:
        from_attributes = True


# --- Shipment ---

class ShipmentCreate(BaseModel):
    sales_order_id: int
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    estimated_delivery_date: Optional[datetime] = None
    delivery_status: Optional[str] = "pending"


class ShipmentResponse(BaseModel):
    id: int
    sales_order_id: Optional[int] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    dispatch_date: Optional[datetime] = None
    estimated_delivery_date: Optional[datetime] = None
    delivery_status: Optional[str] = None

    class Config:
        from_attributes = True


# --- Checkout (Public) ---

class CheckoutLineCreate(BaseModel):
    product_id: str
    quantity: int
    unit_price: Decimal


class CheckoutCreate(BaseModel):
    payment_method: str  # "paypal" | "qr"
    guest_email: Optional[str] = None
    customer_id: Optional[int] = None
    source_channel: Optional[str] = "ecommerce"
    total_discount: Optional[Decimal] = Decimal("0")
    delivery_type: Optional[str] = None  # "delivery" | "pickup"
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    delivery_address: Optional[str] = None
    lines: List[CheckoutLineCreate]


class CheckoutResponse(BaseModel):
    order_id: int
    status: str
    total_amount: Decimal
    payment_method: str
    paypal_approval_url: Optional[str] = None
    qr_image_url: Optional[str] = None


# --- PayPal Confirm ---

class PayPalConfirmRequest(BaseModel):
    paypal_order_id: str


# --- Payment Settings ---

class PaymentSettingsResponse(BaseModel):
    id: int
    paypal_email: Optional[str] = None
    qr_image_url: Optional[str] = None

    class Config:
        from_attributes = True


class PaymentSettingsUpdate(BaseModel):
    paypal_email: Optional[str] = None
    qr_image_url: Optional[str] = None


# --- Admin Security ---

class CompanyInfoResponse(BaseModel):
    id: int
    name: Optional[str] = None
    legal_name: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None

    class Config:
        from_attributes = True


class CompanyInfoUpdate(BaseModel):
    name: Optional[str] = None
    legal_name: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None


class VerifyPasswordRequest(BaseModel):
    password: str


class VerifyPasswordResponse(BaseModel):
    valid: bool
    access_granted: bool
