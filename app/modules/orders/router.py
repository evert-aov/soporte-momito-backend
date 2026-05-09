from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os
from database import get_db
from app.modules.orders.schemas import (
    PurchaseOrderCreate, PurchaseOrderResponse, PurchaseOrderDetailResponse,
    SalesOrderCreate, SalesOrderResponse, SalesOrderDetailResponse,
    InvoiceCreate, InvoiceResponse,
    ShipmentCreate, ShipmentResponse,
    CheckoutCreate, CheckoutResponse,
    PayPalConfirmRequest,
    PaymentSettingsResponse, PaymentSettingsUpdate,
    VerifyPasswordRequest, VerifyPasswordResponse,
    CompanyInfoResponse, CompanyInfoUpdate,
    PaginatedPurchaseOrders, PaginatedSalesOrders, PaginatedInvoices, PaginatedShipments,
)
from app.modules.orders.service import (
    PurchaseOrderService, SalesOrderService,
    InvoiceService, ShipmentService,
    CheckoutService, PaymentSettingsService, AdminSecurityService,
    CompanyInfoService,
)
from app.core.dependencies import (
    get_current_user, get_optional_user,
    require_admin, require_seller, is_seller_or_above,
)

# ── Purchase Orders ────────────────────────────────────────────────────────────

purchase_router = APIRouter(prefix="/api/purchase-orders", tags=["purchase-orders"])


@purchase_router.get("/", response_model=PaginatedPurchaseOrders)
def list_purchase_orders(page: int = 1, page_size: int = 20, search: str = "", status: str = "",
                         db: Session = Depends(get_db), current_user=Depends(require_seller)):
    return PurchaseOrderService(db).list_paginated(page, page_size, search, status)


@purchase_router.get("/{order_id}", response_model=PurchaseOrderDetailResponse)
def get_purchase_order(order_id: int, db: Session = Depends(get_db),
                       current_user=Depends(require_seller)):
    return PurchaseOrderService(db).get_order(order_id)


@purchase_router.post("/", response_model=PurchaseOrderResponse)
def create_purchase_order(data: PurchaseOrderCreate, db: Session = Depends(get_db),
                          current_user=Depends(require_seller)):
    return PurchaseOrderService(db).create_order(data, user_id=current_user.id)


@purchase_router.post("/{order_id}/confirm", response_model=PurchaseOrderResponse)
def confirm_purchase_order(order_id: int, db: Session = Depends(get_db),
                           current_user=Depends(require_seller)):
    return PurchaseOrderService(db).confirm_order(order_id)


@purchase_router.post("/{order_id}/receive", response_model=PurchaseOrderResponse)
def receive_purchase_order(order_id: int, db: Session = Depends(get_db),
                           current_user=Depends(require_seller)):
    return PurchaseOrderService(db).receive_order(order_id)


@purchase_router.post("/{order_id}/cancel", response_model=PurchaseOrderResponse)
def cancel_purchase_order(order_id: int, db: Session = Depends(get_db),
                          current_user=Depends(require_seller)):
    return PurchaseOrderService(db).cancel_order(order_id)


# ── Sales Orders ───────────────────────────────────────────────────────────────

sales_router = APIRouter(prefix="/api/sales-orders", tags=["sales-orders"])


@sales_router.get("/", response_model=PaginatedSalesOrders)
def list_sales_orders(page: int = 1, page_size: int = 20, search: str = "", status: str = "", channel: str = "",
                      db: Session = Depends(get_db), current_user=Depends(require_seller)):
    return SalesOrderService(db).list_paginated(page, page_size, search, status, channel)


@sales_router.get("/{order_id}", response_model=SalesOrderDetailResponse)
def get_sales_order(order_id: int, db: Session = Depends(get_db),
                    current_user=Depends(require_seller)):
    return SalesOrderService(db).get_order(order_id)


@sales_router.post("/", response_model=SalesOrderResponse)
def create_sales_order(data: SalesOrderCreate, db: Session = Depends(get_db),
                       current_user=Depends(require_seller)):
    return SalesOrderService(db).create_order(data, user_id=current_user.id)


@sales_router.post("/{order_id}/confirm", response_model=SalesOrderResponse)
def confirm_sales_order(order_id: int, db: Session = Depends(get_db),
                        current_user=Depends(require_seller)):
    return SalesOrderService(db).confirm_order(order_id)


@sales_router.post("/{order_id}/mark-paid")
def mark_sales_order_paid(order_id: int, db: Session = Depends(get_db),
                          current_user=Depends(require_seller)):
    result = SalesOrderService(db).mark_paid(order_id)
    return {
        "order": result["order"],
        "invoice_number": result["invoice"].invoice_number,
        "status": result["order"].status,
    }


@sales_router.post("/{order_id}/advance", response_model=SalesOrderResponse)
def advance_sales_order(order_id: int, db: Session = Depends(get_db),
                        current_user=Depends(require_seller)):
    return SalesOrderService(db).advance_status(order_id)


@sales_router.post("/{order_id}/cancel", response_model=SalesOrderResponse)
def cancel_sales_order(order_id: int, db: Session = Depends(get_db),
                       current_user=Depends(require_seller)):
    return SalesOrderService(db).cancel_order(order_id)


# ── Checkout (PUBLIC — no JWT required) ───────────────────────────────────────

checkout_router = APIRouter(prefix="/api/orders", tags=["checkout"])


@checkout_router.post("/checkout", response_model=CheckoutResponse)
def public_checkout(
    data: CheckoutCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    user_id = current_user.id if current_user else None
    origin = request.headers.get("origin", "http://localhost:4200")
    svc = CheckoutService(db)
    result = svc.checkout(data, user_id=user_id, frontend_base=origin)
    return result


@checkout_router.post("/{order_id}/confirm-paypal")
def confirm_paypal(
    order_id: int,
    body: PayPalConfirmRequest,
    db: Session = Depends(get_db),
):
    svc = CheckoutService(db)
    result = svc.confirm_paypal(order_id, body.paypal_order_id)
    return {
        "message": "Payment confirmed and invoice generated",
        "order_id": result["order"].id,
        "invoice_number": result["invoice"].invoice_number,
        "status": result["order"].status,
    }


@checkout_router.post("/{order_id}/confirm-manual")
def confirm_manual(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc = CheckoutService(db)
    result = svc.confirm_manual(order_id)
    return {
        "message": "Manual payment confirmed and invoice generated",
        "order_id": result["order"].id,
        "invoice_number": result["invoice"].invoice_number,
        "status": result["order"].status,
    }


# ── Invoices ───────────────────────────────────────────────────────────────────

invoices_router = APIRouter(prefix="/api/invoices", tags=["invoices"])


def _resolve_invoice(invoice_id: int, current_user, db: Session):
    """Returns invoice respecting ownership: sellers/admins see all, customers see only theirs."""
    svc = InvoiceService(db)
    if is_seller_or_above(current_user):
        return svc.get_invoice(invoice_id)
    return svc.get_invoice_for_user(
        invoice_id, current_user.id, getattr(current_user, "customer_id", None)
    )


@invoices_router.get("/", response_model=PaginatedInvoices)
def list_invoices(page: int = 1, page_size: int = 20, search: str = "",
                  db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    svc = InvoiceService(db)
    seller = is_seller_or_above(current_user)
    return svc.list_paginated(
        page, page_size, search,
        user_id=current_user.id,
        customer_id=getattr(current_user, "customer_id", None),
        is_seller=seller,
    )


@invoices_router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    return _resolve_invoice(invoice_id, current_user, db)


@invoices_router.post("/", response_model=InvoiceResponse)
def create_invoice(data: InvoiceCreate, db: Session = Depends(get_db),
                   current_user=Depends(require_seller)):
    return InvoiceService(db).create_invoice(data)


@invoices_router.get("/{invoice_id}/html")
def get_invoice_html(invoice_id: int, db: Session = Depends(get_db),
                     current_user=Depends(get_current_user)):
    inv = _resolve_invoice(invoice_id, current_user, db)
    if not inv.html_file_path:
        raise HTTPException(status_code=404, detail="HTML invoice not available")
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        inv.html_file_path
    )
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Invoice file not found")
    return FileResponse(path, media_type="text/html")


@invoices_router.get("/{invoice_id}/xml")
def get_invoice_xml(invoice_id: int, db: Session = Depends(get_db),
                    current_user=Depends(get_current_user)):
    inv = _resolve_invoice(invoice_id, current_user, db)
    if not inv.xml_file_url:
        raise HTTPException(status_code=404, detail="XML invoice not available")
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        inv.xml_file_url
    )
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="XML file not found")
    return FileResponse(path, media_type="application/xml", filename=f"{inv.invoice_number}.xml")


# ── Shipments ─────────────────────────────────────────────────────────────────

shipments_router = APIRouter(prefix="/api/shipments", tags=["shipments"])


@shipments_router.get("/", response_model=PaginatedShipments)
def list_shipments(page: int = 1, page_size: int = 20, search: str = "", status: str = "",
                   db: Session = Depends(get_db), current_user=Depends(require_seller)):
    return ShipmentService(db).list_paginated(page, page_size, search, status)


@shipments_router.get("/{shipment_id}", response_model=ShipmentResponse)
def get_shipment(shipment_id: int, db: Session = Depends(get_db),
                 current_user=Depends(require_seller)):
    return ShipmentService(db).get_shipment(shipment_id)


@shipments_router.post("/", response_model=ShipmentResponse)
def create_shipment(data: ShipmentCreate, db: Session = Depends(get_db),
                    current_user=Depends(require_seller)):
    return ShipmentService(db).create_shipment(data)


# ── Admin: Payment Settings & Security ────────────────────────────────────────

admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


@admin_router.post("/verify-password", response_model=VerifyPasswordResponse)
def verify_password(
    body: VerifyPasswordRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    svc = AdminSecurityService()
    valid = svc.verify_password(current_user, body.password)
    return VerifyPasswordResponse(valid=valid, access_granted=valid)


@admin_router.get("/payment-settings", response_model=PaymentSettingsResponse)
def get_payment_settings(db: Session = Depends(get_db)):
    return PaymentSettingsService(db).get()


@admin_router.put("/payment-settings", response_model=PaymentSettingsResponse)
def update_payment_settings(
    data: PaymentSettingsUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    return PaymentSettingsService(db).update(data)


@admin_router.get("/company-info", response_model=CompanyInfoResponse)
def get_company_info(db: Session = Depends(get_db)):
    return CompanyInfoService(db).get()


@admin_router.put("/company-info", response_model=CompanyInfoResponse)
def update_company_info(
    data: CompanyInfoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    return CompanyInfoService(db).update(data)
