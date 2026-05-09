from pydantic import BaseModel
from typing import Optional


class OrderStatusCount(BaseModel):
    status: str
    count: int


class TopProduct(BaseModel):
    product_id: str
    product_name: str
    units_sold: int
    revenue: float


class SalesOrderBrief(BaseModel):
    id: int
    customer_id: Optional[int]
    total_amount: float
    status: str
    order_date: Optional[str]


class PurchaseOrderBrief(BaseModel):
    id: int
    supplier_id: Optional[int]
    total_amount: float
    status: str
    issue_date: Optional[str]


class LowStockItem(BaseModel):
    product_id: str
    product_name: str
    quantity: float
    min_stock: float


class DashboardSummary(BaseModel):
    monthly_revenue: float
    monthly_orders_count: int
    pending_orders_count: int
    active_products_count: int
    customers_count: int
    low_stock_count: int
    sales_by_status: list[OrderStatusCount]
    top_products: list[TopProduct]
    recent_sales: list[SalesOrderBrief]
    recent_purchases: list[PurchaseOrderBrief]
    low_stock_items: list[LowStockItem]


class SalesChartPoint(BaseModel):
    month: str
    revenue: float
    order_count: int


class SalesHistoryResponse(BaseModel):
    data: list[SalesChartPoint]


class PredictionPoint(BaseModel):
    month: str
    predicted_revenue: float
    lower_bound: float
    upper_bound: float


class PredictionsResponse(BaseModel):
    predictions: list[PredictionPoint]
    model_info: str
    history_months: int
