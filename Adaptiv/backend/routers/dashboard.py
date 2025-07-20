from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from database import get_db
import models
from datetime import datetime, timedelta
import traceback
import logging
from .auth import get_current_user
from services.dashboard_service import DashboardService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dashboard_router = APIRouter()

@dashboard_router.get("/sales-data")
def get_sales_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    time_frame: Optional[str] = None,
    include_item_details: Optional[bool] = False,
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get sales data for the dashboard in SalesAnalytics format
    """
    user_id = account_id if account_id else current_user.id
    dashboard_service = DashboardService(db)
    
    # Get sales data
    sales_analytics = dashboard_service.get_sales_data(start_date, end_date, user_id, time_frame)
    
    # If item details are requested, add top selling items
    if include_item_details:
        top_selling_items = dashboard_service.get_product_performance(time_frame, user_id)
        sales_analytics["topSellingItems"] = top_selling_items
    
    return sales_analytics


@dashboard_router.get("/product-performance")
def get_product_performance(
    time_frame: Optional[str] = None,
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get performance data for all products
    """
    user_id = account_id if account_id else current_user.id
    dashboard_service = DashboardService(db)
    return dashboard_service.get_product_performance(time_frame, user_id)

