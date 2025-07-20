from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import models
from database import get_db
from .auth import get_current_user
from services.analytics_service import AnalyticsService

analytics_router = APIRouter()

@analytics_router.get("/dashboard/sales-data-optimized")
def get_optimized_sales_data(
    start_date: str,
    end_date: str,
    time_frame: str,  # 1d, 7d, 1m, 6m, 1yr
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Optimized endpoint that returns aggregated sales data based on time frame.
    Aggregates on the backend to minimize data transfer.
    """
    analytics_service = AnalyticsService(db)
    return analytics_service.get_optimized_sales_data(start_date, end_date, time_frame, current_user.id)





@analytics_router.get("/dashboard/product-performance-optimized")
def get_optimized_product_performance(
    time_frame: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get product performance data optimized for the specified time frame.
    """
    analytics_service = AnalyticsService(db)
    return analytics_service.get_optimized_product_performance(time_frame, current_user.id)