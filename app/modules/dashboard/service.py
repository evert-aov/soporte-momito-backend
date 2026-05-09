from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

from app.modules.orders.models import SalesOrder, SalesOrderLine, PurchaseOrder
from app.modules.products.models import Product
from app.modules.inventory.models import BranchInventory
from app.modules.users.models import Customer
from app.modules.dashboard.schemas import (
    DashboardSummary, OrderStatusCount, TopProduct,
    SalesOrderBrief, PurchaseOrderBrief, LowStockItem,
    SalesHistoryResponse, SalesChartPoint,
    PredictionsResponse, PredictionPoint,
)

PAID_STATUSES = ("paid", "confirmed", "picking", "dispatched", "delivered")


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_summary(self) -> DashboardSummary:
        db = self.db

        # Current-month revenue — aggregate in DB, not Python
        monthly_revenue = db.query(
            func.coalesce(func.sum(SalesOrder.total_amount), 0)
        ).filter(
            SalesOrder.status.in_(PAID_STATUSES),
            SalesOrder.order_date.isnot(None),
            func.date_trunc("month", SalesOrder.order_date)
            == func.date_trunc("month", func.now()),
        ).scalar()

        monthly_orders_count = db.query(func.count(SalesOrder.id)).filter(
            SalesOrder.status.in_(PAID_STATUSES),
            SalesOrder.order_date.isnot(None),
            func.date_trunc("month", SalesOrder.order_date)
            == func.date_trunc("month", func.now()),
        ).scalar() or 0

        pending_orders_count = db.query(func.count(SalesOrder.id)).filter(
            SalesOrder.status == "pending_payment",
        ).scalar() or 0

        active_products_count = db.query(func.count(Product.id)).filter(
            Product.active.is_(True),
        ).scalar() or 0

        customers_count = db.query(func.count(Customer.id)).scalar() or 0

        # Low-stock: single join query, no row-by-row iteration
        low_stock_rows = (
            db.query(
                BranchInventory.product_id,
                Product.name.label("product_name"),
                BranchInventory.quantity,
                BranchInventory.min_stock,
            )
            .join(Product, BranchInventory.product_id == Product.id)
            .filter(
                BranchInventory.min_stock > 0,
                BranchInventory.quantity <= BranchInventory.min_stock,
            )
            .all()
        )
        low_stock_items = [
            LowStockItem(
                product_id=r.product_id,
                product_name=r.product_name,
                quantity=float(r.quantity or 0),
                min_stock=float(r.min_stock or 0),
            )
            for r in low_stock_rows
        ]

        # Sales-order count per status — single GROUP BY
        status_rows = (
            db.query(
                SalesOrder.status,
                func.count(SalesOrder.id).label("cnt"),
            )
            .group_by(SalesOrder.status)
            .all()
        )
        sales_by_status = [
            OrderStatusCount(status=r.status, count=r.cnt) for r in status_rows
        ]

        # Top-5 products by units sold — join + aggregate entirely in DB
        top_rows = (
            db.query(
                SalesOrderLine.product_id,
                Product.name.label("product_name"),
                func.sum(SalesOrderLine.quantity).label("units_sold"),
                func.coalesce(func.sum(SalesOrderLine.subtotal), 0).label("revenue"),
            )
            .join(Product, SalesOrderLine.product_id == Product.id)
            .join(SalesOrder, SalesOrderLine.sales_order_id == SalesOrder.id)
            .filter(SalesOrder.status.in_(PAID_STATUSES))
            .group_by(SalesOrderLine.product_id, Product.name)
            .order_by(func.sum(SalesOrderLine.quantity).desc())
            .limit(5)
            .all()
        )
        top_products = [
            TopProduct(
                product_id=r.product_id,
                product_name=r.product_name,
                units_sold=int(r.units_sold or 0),
                revenue=float(r.revenue or 0),
            )
            for r in top_rows
        ]

        # Recent sales — project only needed columns
        recent_sale_rows = (
            db.query(
                SalesOrder.id,
                SalesOrder.customer_id,
                SalesOrder.total_amount,
                SalesOrder.status,
                SalesOrder.order_date,
            )
            .order_by(SalesOrder.id.desc())
            .limit(5)
            .all()
        )
        recent_sales = [
            SalesOrderBrief(
                id=r.id,
                customer_id=r.customer_id,
                total_amount=float(r.total_amount or 0),
                status=r.status,
                order_date=r.order_date.isoformat() if r.order_date else None,
            )
            for r in recent_sale_rows
        ]

        # Recent purchase orders (last 10 for bar chart)
        recent_purchase_rows = (
            db.query(
                PurchaseOrder.id,
                PurchaseOrder.supplier_id,
                PurchaseOrder.total_amount,
                PurchaseOrder.status,
                PurchaseOrder.issue_date,
            )
            .order_by(PurchaseOrder.id.desc())
            .limit(10)
            .all()
        )
        recent_purchases = [
            PurchaseOrderBrief(
                id=r.id,
                supplier_id=r.supplier_id,
                total_amount=float(r.total_amount or 0),
                status=r.status,
                issue_date=r.issue_date.isoformat() if r.issue_date else None,
            )
            for r in recent_purchase_rows
        ]

        return DashboardSummary(
            monthly_revenue=float(monthly_revenue or 0),
            monthly_orders_count=monthly_orders_count,
            pending_orders_count=pending_orders_count,
            active_products_count=active_products_count,
            customers_count=customers_count,
            low_stock_count=len(low_stock_items),
            sales_by_status=sales_by_status,
            top_products=top_products,
            recent_sales=recent_sales,
            recent_purchases=recent_purchases,
            low_stock_items=low_stock_items,
        )

    def get_sales_history(self) -> SalesHistoryResponse:
        # One GROUP BY query — DB does all the aggregation
        rows = (
            self.db.query(
                func.date_trunc("month", SalesOrder.order_date).label("month"),
                func.coalesce(func.sum(SalesOrder.total_amount), 0).label("revenue"),
                func.count(SalesOrder.id).label("order_count"),
            )
            .filter(
                SalesOrder.status.in_(PAID_STATUSES),
                SalesOrder.order_date.isnot(None),
            )
            .group_by(func.date_trunc("month", SalesOrder.order_date))
            .order_by(func.date_trunc("month", SalesOrder.order_date))
            .all()
        )
        data = [
            SalesChartPoint(
                month=r.month.strftime("%Y-%m"),
                revenue=float(r.revenue or 0),
                order_count=int(r.order_count or 0),
            )
            for r in rows
        ]
        return SalesHistoryResponse(data=data)

    def get_predictions(self) -> PredictionsResponse:
        history = self.get_sales_history()
        data = history.data

        if len(data) < 2:
            return PredictionsResponse(
                predictions=[],
                model_info="Datos insuficientes para predicción (mínimo 2 meses de historial)",
                history_months=len(data),
            )

        # Build DataFrame — only n rows (one per month), already aggregated
        df = pd.DataFrame(
            [{"month": p.month, "revenue": p.revenue} for p in data]
        )
        df["month_dt"] = pd.to_datetime(df["month"] + "-01")
        df = df.sort_values("month_dt").reset_index(drop=True)
        df["t"] = np.arange(len(df), dtype=float)

        X = df[["t"]].values
        y = df["revenue"].values.astype(float)

        model = LinearRegression()
        model.fit(X, y)

        # Residual std → 95 % confidence interval (±1.96 σ)
        residuals = y - model.predict(X)
        std_resid = float(np.std(residuals)) if len(residuals) > 1 else 0.0
        margin = std_resid * 1.96

        last_dt = df["month_dt"].iloc[-1]
        n = float(len(df))

        predictions = []
        for i in range(1, 4):
            future_dt = last_dt + pd.DateOffset(months=i)
            pred = float(model.predict([[n + i - 1]])[0])
            pred = max(0.0, pred)
            predictions.append(
                PredictionPoint(
                    month=future_dt.strftime("%Y-%m"),
                    predicted_revenue=round(pred, 2),
                    lower_bound=round(max(0.0, pred - margin), 2),
                    upper_bound=round(pred + margin, 2),
                )
            )

        r_sq = float(model.score(X, y))
        return PredictionsResponse(
            predictions=predictions,
            model_info=f"Regresión Lineal — R²={r_sq:.2f} — {len(data)} meses de histórico",
            history_months=len(data),
        )
