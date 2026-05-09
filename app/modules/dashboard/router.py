from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from app.modules.dashboard.schemas import (
    DashboardSummary,
    SalesHistoryResponse,
    PredictionsResponse,
)
from app.modules.dashboard.service import DashboardService
from app.core.dependencies import require_seller

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    db: Session = Depends(get_db),
    current_user=Depends(require_seller),
):
    return DashboardService(db).get_summary()


@router.get("/sales-history", response_model=SalesHistoryResponse)
def get_sales_history(
    db: Session = Depends(get_db),
    current_user=Depends(require_seller),
):
    return DashboardService(db).get_sales_history()


@router.get("/predictions", response_model=PredictionsResponse)
def get_predictions(
    db: Session = Depends(get_db),
    current_user=Depends(require_seller),
):
    return DashboardService(db).get_predictions()
