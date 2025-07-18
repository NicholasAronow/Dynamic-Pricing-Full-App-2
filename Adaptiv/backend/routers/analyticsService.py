from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import models
from database import get_db
from .auth import get_current_user

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
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Determine aggregation level based on time frame
    if time_frame in ['1d', '7d', '1m']:
        # Daily aggregation
        return get_daily_aggregated_data(start, end, current_user.id, db)
    else:  # 6m, 1yr
        # Monthly aggregation
        return get_monthly_aggregated_data(start, end, current_user.id, db)

def get_daily_aggregated_data(start: datetime, end: datetime, user_id: int, db: Session):
    """
    Get daily aggregated sales data with pre-calculated margins.
    """
    # Use SQL to aggregate at the database level
    daily_data = db.query(
        func.date(models.Order.order_date).label('date'),
        func.sum(models.Order.total_amount).label('revenue'),
        func.count(models.Order.id).label('orders'),
        func.sum(models.Order.total_cost).label('cogs'),
        func.avg(models.Order.gross_margin).label('avg_margin')
    ).filter(
        and_(
            models.Order.user_id == user_id,
            models.Order.order_date >= start,
            models.Order.order_date <= end
        )
    ).group_by(
        func.date(models.Order.order_date)
    ).all()
    
    # Transform to expected format
    result = []
    for row in daily_data:
        revenue = float(row.revenue or 0)
        cogs = float(row.cogs or 0)
        
        # Calculate profit margin if we have revenue and COGS
        profit_margin = None
        if revenue > 0 and cogs is not None:
            profit_margin = ((revenue - cogs) / revenue) * 100
        
        result.append({
            'date': row.date.strftime('%Y-%m-%d'),
            'revenue': revenue,
            'orders': row.orders,
            'cogs': cogs,
            'profitMargin': profit_margin,
            'hasMarginData': cogs is not None
        })
    
    # Get top selling items for the period (limit to top 10 for performance)
    top_items = get_top_selling_items(start, end, user_id, db, limit=10)
    
    return {
        'salesByDay': result,
        'topSellingItems': top_items
    }

def get_monthly_aggregated_data(start: datetime, end: datetime, user_id: int, db: Session):
    """
    Get monthly aggregated sales data for longer time frames.
    """
    # Use SQL to aggregate at the database level
    monthly_data = db.query(
        func.date_trunc('month', models.Order.order_date).label('month'),
        func.sum(models.Order.total_amount).label('revenue'),
        func.count(models.Order.id).label('orders'),
        func.sum(models.Order.total_cost).label('cogs')
    ).filter(
        and_(
            models.Order.user_id == user_id,
            models.Order.order_date >= start,
            models.Order.order_date <= end
        )
    ).group_by(
        func.date_trunc('month', models.Order.order_date)
    ).order_by(
        func.date_trunc('month', models.Order.order_date)
    ).all()
    
    # Transform to daily format but aggregated by month
    result = []
    for row in monthly_data:
        revenue = float(row.revenue or 0)
        cogs = float(row.cogs or 0)
        
        profit_margin = None
        if revenue > 0 and cogs > 0:
            profit_margin = ((revenue - cogs) / revenue) * 100
        
        result.append({
            'date': row.month.strftime('%Y-%m-01'),  # First day of month
            'revenue': revenue,
            'orders': row.orders,
            'cogs': cogs,
            'profitMargin': profit_margin,
            'hasMarginData': cogs is not None
        })
    
    # Get top selling items for the period
    top_items = get_top_selling_items(start, end, user_id, db, limit=20)
    
    return {
        'salesByDay': result,  # Actually by month, but keeping same structure
        'topSellingItems': top_items
    }

def get_top_selling_items(start: datetime, end: datetime, user_id: int, db: Session, limit: int = 10):
    """
    Get top selling items with margin data for a time period.
    """
    # Aggregate at database level
    top_items = db.query(
        models.Item.id.label('itemId'),
        models.Item.name,
        models.Item.current_price.label('unitPrice'),
        func.sum(models.OrderItem.quantity).label('quantity'),
        func.sum(models.OrderItem.quantity * models.OrderItem.unit_price).label('revenue'),
        func.sum(models.OrderItem.subtotal_cost).label('totalCost'),
        func.avg(models.OrderItem.unit_cost).label('unitCost')
    ).join(
        models.OrderItem, models.Item.id == models.OrderItem.item_id
    ).join(
        models.Order, models.OrderItem.order_id == models.Order.id
    ).filter(
        and_(
            models.Order.user_id == user_id,
            models.Order.order_date >= start,
            models.Order.order_date <= end
        )
    ).group_by(
        models.Item.id, models.Item.name, models.Item.current_price
    ).order_by(
        func.sum(models.OrderItem.quantity * models.OrderItem.unit_price).desc()
    ).limit(limit).all()
    
    result = []
    for item in top_items:
        revenue = float(item.revenue or 0)
        total_cost = float(item.totalCost or 0) if item.totalCost is not None else None
        
        margin_percentage = None
        has_cost = total_cost is not None
        
        if has_cost and revenue > 0:
            margin_percentage = ((revenue - total_cost) / revenue) * 100
        
        result.append({
            'itemId': item.itemId,
            'name': item.name,
            'quantity': int(item.quantity or 0),
            'revenue': revenue,
            'unitPrice': float(item.unitPrice or 0),
            'unitCost': float(item.unitCost or 0) if item.unitCost is not None else None,
            'totalCost': total_cost,
            'hasCost': has_cost,
            'marginPercentage': margin_percentage
        })
    
    return result

@analytics_router.get("/dashboard/product-performance-optimized")
def get_optimized_product_performance(
    time_frame: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get product performance data optimized for the specified time frame.
    """
    # Convert time frame to date range
    end = datetime.now()
    if time_frame == '1d':
        start = end - timedelta(days=1)
    elif time_frame == '7d':
        start = end - timedelta(days=7)
    elif time_frame == '1m':
        start = end - timedelta(days=30)
    elif time_frame == '6m':
        start = end - timedelta(days=180)
    elif time_frame == '1yr':
        start = end - timedelta(days=365)
    else:
        start = end - timedelta(days=30)
    
    # Get all product performance data aggregated at DB level
    products = db.query(
        models.Item.id,
        models.Item.name,
        models.Item.current_price,
        func.sum(models.OrderItem.quantity).label('quantity_sold'),
        func.sum(models.OrderItem.quantity * models.OrderItem.unit_price).label('revenue'),
        func.sum(models.OrderItem.subtotal_cost).label('total_cost'),
        func.bool_or(models.OrderItem.subtotal_cost.isnot(None)).label('has_cost_data')
    ).join(
        models.OrderItem, models.Item.id == models.OrderItem.item_id
    ).join(
        models.Order, models.OrderItem.order_id == models.Order.id
    ).filter(
        and_(
            models.Order.user_id == current_user.id,
            models.Order.order_date >= start,
            models.Order.order_date <= end
        )
    ).group_by(
        models.Item.id, models.Item.name, models.Item.current_price
    ).all()
    
    result = []
    for product in products:
        revenue = float(product.revenue or 0)
        total_cost = float(product.total_cost or 0) if product.total_cost is not None else 0
        quantity_sold = int(product.quantity_sold or 0)
        
        profit_margin = None
        recipe_cost = 0
        
        if product.has_cost_data and revenue > 0:
            profit_margin = ((revenue - total_cost) / revenue) * 100
            if quantity_sold > 0:
                recipe_cost = total_cost / quantity_sold
        
        result.append({
            'id': str(product.id),
            'name': product.name,
            'revenue': revenue,
            'quantitySold': quantity_sold,
            'currentPrice': float(product.current_price or 0),
            'recipeCost': recipe_cost,
            'totalCOGS': total_cost,
            'profitMargin': profit_margin,
            'hasRecipe': product.has_cost_data
        })
    
    # Sort by revenue descending
    result.sort(key=lambda x: x['revenue'], reverse=True)
    
    return result