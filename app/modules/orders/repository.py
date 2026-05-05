import os
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from app.modules.orders.models import (
    PurchaseOrder, PurchaseOrderLine,
    SalesOrder, SalesOrderLine,
    Invoice, Shipment, PaymentSettings,
)


class PurchaseOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100):
        return self.db.query(PurchaseOrder).offset(skip).limit(limit).all()

    def get_by_id(self, order_id: int):
        return self.db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()

    def create(self, data: dict, lines: list) -> PurchaseOrder:
        total = sum(Decimal(str(line["quantity"])) * Decimal(str(line["unit_price"])) for line in lines)
        order = PurchaseOrder(
            supplier_id=data["supplier_id"],
            user_id=data.get("user_id"),
            estimated_arrival_date=data.get("estimated_arrival_date"),
            issue_date=datetime.utcnow(),
            status="draft",
            total_amount=total,
        )
        self.db.add(order)
        self.db.flush()

        for line_data in lines:
            subtotal = Decimal(str(line_data["quantity"])) * Decimal(str(line_data["unit_price"]))
            line = PurchaseOrderLine(
                purchase_order_id=order.id,
                product_id=line_data["product_id"],
                quantity=line_data["quantity"],
                unit_price=line_data["unit_price"],
                subtotal=subtotal,
            )
            self.db.add(line)

        self.db.commit()
        self.db.refresh(order)
        return order

    def update_status(self, order_id: int, status: str):
        order = self.get_by_id(order_id)
        if order:
            order.status = status
            self.db.commit()
            self.db.refresh(order)
        return order


class SalesOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100):
        return self.db.query(SalesOrder).offset(skip).limit(limit).all()

    def get_by_id(self, order_id: int):
        return self.db.query(SalesOrder).filter(SalesOrder.id == order_id).first()

    def create(self, data: dict, lines: list, user_id: int = None) -> SalesOrder:
        subtotal = sum(Decimal(str(l["quantity"])) * Decimal(str(l["unit_price"])) for l in lines)
        discount = Decimal(str(data.get("total_discount") or 0))
        total = subtotal - discount

        order = SalesOrder(
            customer_id=data.get("customer_id"),
            user_id=user_id,
            order_date=datetime.utcnow(),
            status=data.get("status", "pending_payment"),
            subtotal=subtotal,
            total_discount=discount,
            total_amount=total,
            payment_terms=data.get("payment_terms"),
            source_channel=data.get("source_channel"),
            payment_method=data.get("payment_method"),
            paypal_order_id=data.get("paypal_order_id"),
            guest_email=data.get("guest_email"),
            delivery_type=data.get("delivery_type"),
            contact_name=data.get("contact_name"),
            contact_phone=data.get("contact_phone"),
            delivery_address=data.get("delivery_address"),
        )
        self.db.add(order)
        self.db.flush()

        for line_data in lines:
            subtotal_line = Decimal(str(line_data["quantity"])) * Decimal(str(line_data["unit_price"]))
            line = SalesOrderLine(
                sales_order_id=order.id,
                product_id=line_data["product_id"],
                quantity=line_data["quantity"],
                unit_price=line_data["unit_price"],
                subtotal=subtotal_line,
            )
            self.db.add(line)

        self.db.commit()
        self.db.refresh(order)
        return order

    def update_status(self, order_id: int, status: str):
        order = self.get_by_id(order_id)
        if order:
            order.status = status
            self.db.commit()
            self.db.refresh(order)
        return order

    def set_paypal_order_id(self, order_id: int, paypal_order_id: str):
        order = self.get_by_id(order_id)
        if order:
            order.paypal_order_id = paypal_order_id
            self.db.commit()
            self.db.refresh(order)
        return order


class InvoiceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100):
        return self.db.query(Invoice).offset(skip).limit(limit).all()

    def get_all_for_user(self, user_id: int, customer_id: int | None, skip: int = 0, limit: int = 100):
        from app.modules.orders.models import SalesOrder
        from sqlalchemy import or_
        conditions = [SalesOrder.user_id == user_id]
        if customer_id:
            conditions.append(SalesOrder.customer_id == customer_id)
        return (
            self.db.query(Invoice)
            .join(SalesOrder, Invoice.sales_order_id == SalesOrder.id)
            .filter(or_(*conditions))
            .offset(skip).limit(limit).all()
        )

    def get_by_id(self, invoice_id: int):
        return self.db.query(Invoice).filter(Invoice.id == invoice_id).first()

    def get_by_id_for_user(self, invoice_id: int, user_id: int, customer_id: int | None):
        from app.modules.orders.models import SalesOrder
        from sqlalchemy import or_
        conditions = [SalesOrder.user_id == user_id]
        if customer_id:
            conditions.append(SalesOrder.customer_id == customer_id)
        return (
            self.db.query(Invoice)
            .join(SalesOrder, Invoice.sales_order_id == SalesOrder.id)
            .filter(Invoice.id == invoice_id, or_(*conditions))
            .first()
        )

    def get_by_sales_order(self, sales_order_id: int):
        return self.db.query(Invoice).filter(Invoice.sales_order_id == sales_order_id).first()

    def create(self, data: dict) -> Invoice:
        data["issue_date"] = datetime.utcnow()
        invoice = Invoice(**data)
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def auto_generate(self, sales_order: SalesOrder, db: Session = None) -> Invoice:
        """Generate invoice automatically from a paid sales order."""
        existing = self.get_by_sales_order(sales_order.id)
        if existing:
            return existing
        _db = db if db is not None else self.db
        invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{sales_order.id:05d}"

        issue_dt = datetime.utcnow()

        # Fetch company info
        from app.modules.orders.models import CompanyInfo
        company = _db.query(CompanyInfo).first()
        if not company:
            company = CompanyInfo(name="TUMOMITO S.A.")
            _db.add(company)
            _db.commit()
            _db.refresh(company)

        # Build lines HTML
        lines_html = ""
        if hasattr(sales_order, 'lines') and sales_order.lines:
            for line in sales_order.lines:
                lines_html += (
                    f"<tr>"
                    f"<td>{line.product_id}</td>"
                    f"<td class='text-right'>{line.quantity}</td>"
                    f"<td class='text-right'>Bs. {float(line.unit_price or 0):.2f}</td>"
                    f"<td class='text-right'>Bs. {float(line.subtotal or 0):.2f}</td>"
                    f"</tr>"
                )
        else:
            lines_html = "<tr><td colspan='4' style='text-align:center;color:#94a3b8;'>Sin detalle de líneas</td></tr>"

        issue_date_str = issue_dt.strftime("%d/%m/%Y %H:%M")
        subtotal_val = float(sales_order.subtotal or sales_order.total_amount or 0)
        total_val = float(sales_order.total_amount or 0)

        # Build XML lines
        xml_lines = ""
        if hasattr(sales_order, 'lines') and sales_order.lines:
            for line in sales_order.lines:
                xml_lines += (
                    f"    <Line>"
                    f"<ProductId>{line.product_id}</ProductId>"
                    f"<Quantity>{line.quantity}</Quantity>"
                    f"<UnitPrice>{float(line.unit_price or 0):.2f}</UnitPrice>"
                    f"<Subtotal>{float(line.subtotal or 0):.2f}</Subtotal>"
                    f"</Line>\n"
                )

        xml_content = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<Invoice>\n'
            f'  <Header>\n'
            f'    <Number>{invoice_number}</Number>\n'
            f'    <IssueDate>{issue_dt.isoformat()}</IssueDate>\n'
            f'    <Status>paid</Status>\n'
            f'    <SalesOrderId>{sales_order.id}</SalesOrderId>\n'
            f'    <DeliveryType>{sales_order.delivery_type or ""}</DeliveryType>\n'
            f'  </Header>\n'
            f'  <Company>\n'
            f'    <Name>{company.name or "TUMOMITO S.A."}</Name>\n'
            f'    <LegalName>{company.legal_name or ""}</LegalName>\n'
            f'    <TaxId>{company.tax_id or ""}</TaxId>\n'
            f'    <Address>{company.address or ""}</Address>\n'
            f'    <City>{company.city or ""}</City>\n'
            f'    <Country>{company.country or ""}</Country>\n'
            f'    <Phone>{company.phone or ""}</Phone>\n'
            f'    <Email>{company.email or ""}</Email>\n'
            f'    <Website>{company.website or ""}</Website>\n'
            f'  </Company>\n'
            f'  <Customer>\n'
            f'    <Name>{sales_order.contact_name or ""}</Name>\n'
            f'    <Email>{sales_order.guest_email or ""}</Email>\n'
            f'    <Phone>{sales_order.contact_phone or ""}</Phone>\n'
            f'    <Address>{sales_order.delivery_address or ""}</Address>\n'
            f'  </Customer>\n'
            f'  <Lines>\n'
            f'{xml_lines}'
            f'  </Lines>\n'
            f'  <Totals>\n'
            f'    <Subtotal>{subtotal_val:.2f}</Subtotal>\n'
            f'    <Total>{total_val:.2f}</Total>\n'
            f'  </Totals>\n'
            f'</Invoice>'
        )

        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Factura {invoice_number}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f8fafc; color: #1e293b; padding: 40px 20px; }}
  .invoice {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); overflow: hidden; }}
  .header {{ background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%); color: white; padding: 40px; }}
  .header h1 {{ font-size: 32px; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 4px; }}
  .header p {{ opacity: 0.8; font-size: 13px; }}
  .badge {{ display: inline-block; background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); border-radius: 20px; padding: 4px 14px; font-size: 12px; font-weight: 600; }}
  .body {{ padding: 40px; }}
  .meta {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px; gap: 24px; }}
  .meta-block h3 {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #94a3b8; margin-bottom: 6px; }}
  .meta-block p {{ font-size: 14px; color: #1e293b; line-height: 1.6; }}
  .meta-block .num {{ font-size: 22px; font-weight: 800; color: #2563eb; font-family: monospace; }}
  .divider {{ height: 1px; background: #e2e8f0; margin: 24px 0; }}
  table {{ width: 100%; border-collapse: collapse; margin: 24px 0; }}
  th {{ background: #f1f5f9; padding: 10px 14px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: #64748b; font-weight: 700; }}
  td {{ padding: 12px 14px; font-size: 13px; border-bottom: 1px solid #f1f5f9; }}
  tr:last-child td {{ border-bottom: none; }}
  .text-right {{ text-align: right; }}
  .totals {{ background: #f8fafc; border-radius: 8px; padding: 20px 24px; margin-top: 24px; }}
  .total-row {{ display: flex; justify-content: space-between; font-size: 13px; color: #475569; margin-bottom: 8px; }}
  .total-final {{ display: flex; justify-content: space-between; font-size: 20px; font-weight: 800; color: #1e293b; margin-top: 12px; padding-top: 12px; border-top: 2px solid #e2e8f0; }}
  .total-final span:last-child {{ color: #2563eb; }}
  .footer {{ background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 20px 40px; text-align: center; font-size: 12px; color: #94a3b8; }}
</style>
</head>
<body>
<div class="invoice">
  <div class="header">
    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
      <div>
        <h1>{company.name or 'TUMOMITO S.A.'}</h1>
        <p>{company.legal_name or ''} &bull; NIT: {company.tax_id or 'N/A'}</p>
        <p style="margin-top:6px;">{company.address or ''}, {company.city or ''}, {company.country or ''}</p>
        <p>{company.phone or ''} &bull; {company.email or ''}</p>
      </div>
      <div style="text-align:right;">
        <p style="font-size:28px; font-weight:800; font-family:monospace; letter-spacing:-1px;">FACTURA</p>
        <span class="badge">#{invoice_number}</span>
      </div>
    </div>
  </div>
  <div class="body">
    <div class="meta">
      <div class="meta-block">
        <h3>N&uacute;mero de Factura</h3>
        <p class="num">{invoice_number}</p>
      </div>
      <div class="meta-block">
        <h3>Fecha de Emisi&oacute;n</h3>
        <p>{issue_date_str}</p>
      </div>
      <div class="meta-block">
        <h3>Estado</h3>
        <p style="color:#16a34a; font-weight:700;">PAGADO</p>
      </div>
      <div class="meta-block">
        <h3>Orden de Venta</h3>
        <p>#{sales_order.id}</p>
      </div>
    </div>
    <div class="divider"></div>
    <div class="meta">
      <div class="meta-block" style="flex:1;">
        <h3>Cliente</h3>
        <p>{sales_order.contact_name or ''}</p>
        <p>{sales_order.guest_email or ''}</p>
        <p>{sales_order.contact_phone or ''}</p>
        <p>{sales_order.delivery_address or ''}</p>
      </div>
      <div class="meta-block" style="flex:1; text-align:right;">
        <h3>Tipo de Entrega</h3>
        <p>{sales_order.delivery_type or 'N/A'}</p>
      </div>
    </div>
    <div class="divider"></div>
    <table>
      <thead>
        <tr>
          <th>Producto</th>
          <th class="text-right">Cant.</th>
          <th class="text-right">P. Unit.</th>
          <th class="text-right">Subtotal</th>
        </tr>
      </thead>
      <tbody>
        {lines_html}
      </tbody>
    </table>
    <div class="totals">
      <div class="total-row"><span>Subtotal</span><span>Bs. {subtotal_val:.2f}</span></div>
      <div class="total-final"><span>TOTAL</span><span>Bs. {total_val:.2f}</span></div>
    </div>
  </div>
  <div class="footer">
    {company.website or ''} &bull; {company.name or 'TUMOMITO S.A.'} &mdash; Todos los derechos reservados
  </div>
</div>
</body>
</html>"""

        # Save HTML and XML to files
        invoices_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', '..', '..', 'invoices'
        )
        os.makedirs(invoices_dir, exist_ok=True)

        html_filename = f"{invoice_number}.html"
        with open(os.path.join(invoices_dir, html_filename), 'w', encoding='utf-8') as f:
            f.write(html_content)

        xml_filename = f"{invoice_number}.xml"
        with open(os.path.join(invoices_dir, xml_filename), 'w', encoding='utf-8') as f:
            f.write(xml_content)

        invoice = Invoice(
            sales_order_id=sales_order.id,
            invoice_number=invoice_number,
            issue_date=issue_dt,
            total_amount=sales_order.total_amount,
            payment_status="paid",
            xml_file_url=f"invoices/{xml_filename}",
            html_file_path=f"invoices/{html_filename}",
        )
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice


class ShipmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100):
        return self.db.query(Shipment).offset(skip).limit(limit).all()

    def get_by_id(self, shipment_id: int):
        return self.db.query(Shipment).filter(Shipment.id == shipment_id).first()

    def create(self, data: dict) -> Shipment:
        data["dispatch_date"] = datetime.utcnow()
        shipment = Shipment(**data)
        self.db.add(shipment)
        self.db.commit()
        self.db.refresh(shipment)
        return shipment


class PaymentSettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self) -> PaymentSettings:
        settings = self.db.query(PaymentSettings).first()
        if not settings:
            settings = PaymentSettings(paypal_email="", qr_image_url="")
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings

    def update(self, data: dict) -> PaymentSettings:
        settings = self.get()
        for key, value in data.items():
            if value is not None:
                setattr(settings, key, value)
        self.db.commit()
        self.db.refresh(settings)
        return settings


class CompanyInfoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self):
        from app.modules.orders.models import CompanyInfo
        info = self.db.query(CompanyInfo).first()
        if not info:
            info = CompanyInfo(name="TUMOMITO S.A.")
            self.db.add(info)
            self.db.commit()
            self.db.refresh(info)
        return info

    def update(self, data: dict):
        info = self.get()
        for key, value in data.items():
            if value is not None:
                setattr(info, key, value)
        self.db.commit()
        self.db.refresh(info)
        return info
