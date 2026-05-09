import math
import httpx
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.modules.orders.repository import (
    PurchaseOrderRepository, SalesOrderRepository,
    InvoiceRepository, ShipmentRepository, PaymentSettingsRepository,
    CompanyInfoRepository,
)
from app.modules.inventory.repository import InventoryRepository
from app.modules.orders.schemas import (
    PurchaseOrderCreate, SalesOrderCreate,
    InvoiceCreate, ShipmentCreate, CheckoutCreate,
    PaymentSettingsUpdate, CompanyInfoUpdate,
)
from app.core.config import settings
from app.core.security import verify_password


PURCHASE_FLOW = ["draft", "confirmed", "received"]
SALES_FLOW    = ["draft", "pending_payment", "paid", "confirmed", "picking", "dispatched", "delivered"]
FINAL_STATES  = {"delivered", "cancelled", "received"}


class PurchaseOrderService:
    def __init__(self, db: Session):
        self.repo = PurchaseOrderRepository(db)
        self.inv_repo = InventoryRepository(db)

    def list_orders(self, skip: int = 0, limit: int | None = None):
        return self.repo.get_all(skip, limit)

    def list_paginated(self, page: int, page_size: int, search: str = "", status: str = "") -> dict:
        skip = (page - 1) * page_size
        items, total = self.repo.get_paginated(skip, page_size, search, status)
        return {"items": items, "total": total, "page": page, "page_size": page_size,
                "total_pages": max(1, math.ceil(total / page_size))}

    def get_order(self, order_id: int):
        order = self.repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        return order

    def create_order(self, data: PurchaseOrderCreate, user_id: int = None):
        lines = [line.model_dump() for line in data.lines]
        order_data = data.model_dump(exclude={"lines"})
        order_data["user_id"] = user_id
        return self.repo.create(order_data, lines)

    def confirm_order(self, order_id: int):
        order = self.get_order(order_id)
        if order.status != "draft":
            raise HTTPException(status_code=400, detail="La orden no está en borrador")
        return self.repo.update_status(order_id, "confirmed")

    def receive_order(self, order_id: int):
        order = self.get_order(order_id)
        if order.status != "confirmed":
            raise HTTPException(status_code=400, detail="La orden no está confirmada")
        updated = self.repo.update_status(order_id, "received")
        # Increment inventory when purchase order is received
        order_with_lines = self.repo.get_by_id(order_id)
        if order_with_lines and order_with_lines.lines:
            self.inv_repo.adjust_stock_for_lines(order_with_lines.lines, delta=+1)
        return updated

    def cancel_order(self, order_id: int):
        order = self.get_order(order_id)
        if order.status in FINAL_STATES:
            raise HTTPException(status_code=400, detail="No se puede cancelar una orden finalizada")
        return self.repo.update_status(order_id, "cancelled")


class SalesOrderService:
    def __init__(self, db: Session):
        self.repo = SalesOrderRepository(db)
        self.invoice_repo = InvoiceRepository(db)
        self.inv_repo = InventoryRepository(db)

    def list_orders(self, skip: int = 0, limit: int | None = None):
        return self.repo.get_all(skip, limit)

    def list_paginated(self, page: int, page_size: int, search: str = "", status: str = "", channel: str = "") -> dict:
        skip = (page - 1) * page_size
        items, total = self.repo.get_paginated(skip, page_size, search, status, channel)
        return {"items": items, "total": total, "page": page, "page_size": page_size,
                "total_pages": max(1, math.ceil(total / page_size))}

    def get_order(self, order_id: int):
        order = self.repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Sales order not found")
        return order

    def create_order(self, data: SalesOrderCreate, user_id: int = None):
        lines = [line.model_dump() for line in data.lines]
        order_data = data.model_dump(exclude={"lines"})
        # Presential orders created from admin start as draft
        if not order_data.get("source_channel"):
            order_data["source_channel"] = "presencial"
        order_data["status"] = "draft"
        return self.repo.create(order_data, lines, user_id=user_id)

    def mark_paid(self, order_id: int):
        """Mark a presential or QR order as paid and auto-generate invoice."""
        order = self.get_order(order_id)
        if order.status in FINAL_STATES or order.status == "paid":
            raise HTTPException(status_code=400, detail="La orden ya está pagada o finalizada")
        self.repo.update_status(order_id, "paid")
        order = self.repo.get_by_id(order_id)
        invoice = self.invoice_repo.auto_generate(order)
        return {"order": order, "invoice": invoice}

    def advance_status(self, order_id: int):
        """Move the order to the next step in SALES_FLOW."""
        order = self.get_order(order_id)
        if order.status in FINAL_STATES:
            raise HTTPException(status_code=400, detail="La orden está finalizada")
        try:
            idx = SALES_FLOW.index(order.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Estado desconocido: {order.status}")
        if idx >= len(SALES_FLOW) - 1:
            raise HTTPException(status_code=400, detail="La orden ya está en el último estado")
        next_status = SALES_FLOW[idx + 1]
        self.repo.update_status(order_id, next_status)
        order = self.repo.get_by_id(order_id)
        if next_status == "paid":
            self.invoice_repo.auto_generate(order)
        # Deduct inventory when order is dispatched
        if next_status == "dispatched" and order.lines:
            self.inv_repo.adjust_stock_for_lines(order.lines, delta=-1)
        return order

    def confirm_order(self, order_id: int):
        order = self.get_order(order_id)
        if order.status not in ("draft", "pending_payment", "paid"):
            raise HTTPException(status_code=400, detail="Estado no permite confirmación")
        return self.repo.update_status(order_id, "confirmed")

    def cancel_order(self, order_id: int):
        order = self.get_order(order_id)
        if order.status in FINAL_STATES:
            raise HTTPException(status_code=400, detail="No se puede cancelar una orden finalizada")
        return self.repo.update_status(order_id, "cancelled")


class PayPalClient:
    """Thin wrapper around PayPal REST API v2."""

    def __init__(self):
        self.base = settings.paypal_base_url
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.secret = settings.PAYPAL_SECRET

    def _get_access_token(self) -> str:
        resp = httpx.post(
            f"{self.base}/v1/oauth2/token",
            auth=(self.client_id, self.secret),
            data={"grant_type": "client_credentials"},
            timeout=15,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="PayPal auth failed")
        return resp.json()["access_token"]

    def create_order(self, amount: str, currency: str = "USD",
                     return_url: str = "", cancel_url: str = "") -> dict:
        token = self._get_access_token()
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{"amount": {"currency_code": currency, "value": amount}}],
            "application_context": {
                "return_url": return_url,
                "cancel_url": cancel_url,
                "brand_name": "TUMOMITO S.A.",
                "landing_page": "BILLING",
                "user_action": "PAY_NOW",
            },
        }
        resp = httpx.post(
            f"{self.base}/v2/checkout/orders",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail=f"PayPal order creation failed: {resp.text}")
        return resp.json()

    def capture_order(self, paypal_order_id: str) -> dict:
        token = self._get_access_token()
        resp = httpx.post(
            f"{self.base}/v2/checkout/orders/{paypal_order_id}/capture",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={},
            timeout=15,
        )
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail=f"PayPal capture failed: {resp.text}")
        return resp.json()


class CheckoutService:
    def __init__(self, db: Session):
        self.order_repo = SalesOrderRepository(db)
        self.invoice_repo = InvoiceRepository(db)
        self.settings_repo = PaymentSettingsRepository(db)
        self.paypal = PayPalClient()

    def checkout(self, data: CheckoutCreate, user_id: int = None,
                 frontend_base: str = "http://localhost:4200") -> dict:
        if data.payment_method not in ("paypal", "qr"):
            raise HTTPException(status_code=400, detail="payment_method must be 'paypal' or 'qr'")
        if data.source_channel == "ecommerce" and data.payment_method != "paypal":
            raise HTTPException(status_code=400, detail="Online checkout only supports PayPal")

        lines = [line.model_dump() for line in data.lines]
        order_data = data.model_dump(exclude={"lines"})
        order_data["status"] = "pending_payment"

        order = self.order_repo.create(order_data, lines, user_id=user_id)

        result = {
            "order_id": order.id,
            "status": order.status,
            "total_amount": order.total_amount,
            "payment_method": data.payment_method,
            "paypal_approval_url": None,
            "qr_image_url": None,
        }

        if data.payment_method == "paypal":
            amount_str = f"{float(order.total_amount):.2f}"
            return_url = f"{frontend_base}/checkout/success?order_id={order.id}"
            cancel_url = f"{frontend_base}/checkout/cancel?order_id={order.id}"
            pp_order = self.paypal.create_order(amount_str, return_url=return_url, cancel_url=cancel_url)
            paypal_order_id = pp_order.get("id")
            self.order_repo.set_paypal_order_id(order.id, paypal_order_id)
            approval_url = next(
                (link["href"] for link in pp_order.get("links", []) if link["rel"] == "approve"),
                None,
            )
            result["paypal_approval_url"] = approval_url

        elif data.payment_method == "qr":
            payment_cfg = self.settings_repo.get()
            result["qr_image_url"] = payment_cfg.qr_image_url

        return result

    def confirm_paypal(self, order_id: int, paypal_order_id: str) -> dict:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status not in ("pending_payment", "draft"):
            raise HTTPException(status_code=400, detail="Order already processed")

        capture = self.paypal.capture_order(paypal_order_id)
        capture_status = capture.get("status")
        if capture_status != "COMPLETED":
            raise HTTPException(status_code=402, detail=f"PayPal payment not completed: {capture_status}")

        self.order_repo.update_status(order_id, "paid")
        order = self.order_repo.get_by_id(order_id)
        invoice = self.invoice_repo.auto_generate(order)
        return {"order": order, "invoice": invoice}

    def confirm_manual(self, order_id: int) -> dict:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status not in ("pending_payment", "draft"):
            raise HTTPException(status_code=400, detail="Order already processed")

        self.order_repo.update_status(order_id, "paid")
        order = self.order_repo.get_by_id(order_id)
        invoice = self.invoice_repo.auto_generate(order)
        return {"order": order, "invoice": invoice}


class InvoiceService:
    def __init__(self, db: Session):
        self.repo = InvoiceRepository(db)

    def list_invoices(self, skip: int = 0, limit: int | None = None):
        return self.repo.get_all(skip, limit)

    def list_invoices_for_user(self, user_id: int, customer_id: int | None, skip: int = 0, limit: int | None = None):
        return self.repo.get_all_for_user(user_id, customer_id, skip, limit)

    def list_paginated(self, page: int, page_size: int, search: str = "",
                       user_id: int | None = None, customer_id: int | None = None,
                       is_seller: bool = True) -> dict:
        skip = (page - 1) * page_size
        if is_seller:
            items, total = self.repo.get_paginated(skip, page_size, search)
        else:
            items, total = self.repo.get_paginated_for_user(user_id, customer_id, skip, page_size, search)
        return {"items": items, "total": total, "page": page, "page_size": page_size,
                "total_pages": max(1, math.ceil(total / page_size))}

    def get_invoice(self, invoice_id: int):
        inv = self.repo.get_by_id(invoice_id)
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return inv

    def get_invoice_for_user(self, invoice_id: int, user_id: int, customer_id: int | None):
        inv = self.repo.get_by_id_for_user(invoice_id, user_id, customer_id)
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return inv

    def create_invoice(self, data: InvoiceCreate):
        return self.repo.create(data.model_dump())


class ShipmentService:
    def __init__(self, db: Session):
        self.repo = ShipmentRepository(db)

    def list_shipments(self, skip: int = 0, limit: int | None = None):
        return self.repo.get_all(skip, limit)

    def list_paginated(self, page: int, page_size: int, search: str = "", status: str = "") -> dict:
        skip = (page - 1) * page_size
        items, total = self.repo.get_paginated(skip, page_size, search, status)
        return {"items": items, "total": total, "page": page, "page_size": page_size,
                "total_pages": max(1, math.ceil(total / page_size))}

    def get_shipment(self, shipment_id: int):
        ship = self.repo.get_by_id(shipment_id)
        if not ship:
            raise HTTPException(status_code=404, detail="Shipment not found")
        return ship

    def create_shipment(self, data: ShipmentCreate):
        return self.repo.create(data.model_dump())


class PaymentSettingsService:
    def __init__(self, db: Session):
        self.repo = PaymentSettingsRepository(db)

    def get(self):
        return self.repo.get()

    def update(self, data: PaymentSettingsUpdate):
        return self.repo.update(data.model_dump(exclude_none=True))


class AdminSecurityService:
    def verify_password(self, user, password: str) -> bool:
        return verify_password(password, user.password_hash)


class CompanyInfoService:
    def __init__(self, db: Session):
        self.repo = CompanyInfoRepository(db)

    def get(self):
        return self.repo.get()

    def update(self, data: CompanyInfoUpdate):
        return self.repo.update(data.model_dump(exclude_none=True))
