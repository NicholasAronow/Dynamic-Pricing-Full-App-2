from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from database import get_db
import models
from sqlalchemy import func, text
from datetime import datetime, timedelta
import traceback
import logging
from auth import get_current_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dashboard_router = APIRouter()

@dashboard_router.get("/sales-data")
def get_sales_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get sales data for the dashboard without strict Pydantic validation
    """
    try:
        # Parse date range or use default (last 30 days)
        end_date_obj = datetime.now()
        start_date_obj = end_date_obj - timedelta(days=30)  # Default to last 30 days
        
        # Log the incoming date parameters
        logger.info(f"Dashboard request with date range params: start_date={start_date}, end_date={end_date}")
        
        if start_date and end_date:
            try:
                # Try ISO format first
                start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                end_date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                logger.info(f"Successfully parsed ISO date range: {start_date_obj} to {end_date_obj}")
            except ValueError:
                # Fall back to simple format
                try:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                    logger.info(f"Successfully parsed simple date range: {start_date_obj} to {end_date_obj}")
                except ValueError:
                    # If all parsing fails, use default
                    logger.warning(f"Could not parse date range {start_date} - {end_date}, using default")
                    
        # We now have a full year of data
        min_date = datetime.now() - timedelta(days=365)  # Full year of data
        if start_date_obj < min_date:
            logger.info(f"Limiting start date to 365 days ago (available data constraint)")
            start_date_obj = min_date
        
        # Filter by the current user's ID unless specifically requesting another account's data
        user_id = account_id if account_id else current_user.id
        logger.info(f"Filtering dashboard data for user_id: {user_id}")
        
        # Basic stats using simpler queries with date filter
        orders_query = db.query(models.Order).filter(models.Order.user_id == user_id)
        if start_date or end_date:
            orders_query = orders_query.filter(
                models.Order.order_date >= start_date_obj,
                models.Order.order_date <= end_date_obj
            )
        
        total_orders = orders_query.count()
        
        # Use a safer approach for sum
        revenue_result = orders_query.with_entities(func.sum(models.Order.total_amount)).scalar()
        total_revenue = float(revenue_result) if revenue_result is not None else 0.0
        
        # Safely calculate average
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0.0
        
        # Get top selling items with a simpler query
        top_items = []
        try:
            # Use a basic query that's less likely to fail
            item_query = db.query(
                models.Item.id,
                models.Item.name,
                models.Item.category,
                models.Item.current_price,
                func.count(models.OrderItem.id).label('order_count'),
                func.sum(models.OrderItem.quantity * models.OrderItem.unit_price).label('revenue')
            ).join(
                models.OrderItem,
                models.Item.id == models.OrderItem.item_id
            ).join(
                models.Order,
                models.OrderItem.order_id == models.Order.id
            ).filter(
                models.Order.order_date >= start_date_obj,
                models.Order.order_date <= end_date_obj,
                models.Order.user_id == user_id  # Filter by user ID
            ).group_by(
                models.Item.id
            ).order_by(text('order_count DESC')).limit(5).all()
            
            top_items = [
                {
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "quantity": item.order_count,
                    "revenue": float(item.revenue) if item.revenue is not None else 0.0,
                    "unitPrice": float(item.current_price) if item.current_price is not None else 0.0,
                } for item in item_query
            ]
        except Exception as e:
            logger.error(f"Error getting top items: {str(e)}")
            # Continue with an empty list if this fails
            top_items = []
        
        # Get sales by day
        sales_by_day = []
        try:
            # Format the date based on the range
            date_range_days = (end_date_obj - start_date_obj).days + 1
            date_trunc_format = 'day'  # Default to daily
            
            # Apply proper binning based on time range
            if date_range_days > 300:  # For ~1 year views
                date_trunc_format = 'month'  # Group by month
                logger.info(f"Using monthly aggregation for {date_range_days} day range")
            elif date_range_days > 60:  # For ~6 month views
                date_trunc_format = 'week'  # Group by week
                logger.info(f"Using weekly aggregation for {date_range_days} day range")
            elif date_range_days > 14:
                date_trunc_format = 'day'  # Use daily for medium ranges
                logger.info(f"Using daily aggregation for {date_range_days} day range")
            
            # Build the query based on the database
            # For SQLite
            if 'sqlite' in db.bind.dialect.name:
                if date_trunc_format == 'day':
                    date_group = func.strftime('%Y-%m-%d', models.Order.order_date)
                elif date_trunc_format == 'week':
                    # Generate a date for the first day of each week
                    # SQLite week numbers start from 0
                    date_group = func.strftime('%Y-%m-%d', models.Order.order_date, 'weekday 0', '-7 days')
                else:  # month
                    date_group = func.strftime('%Y-%m-01', models.Order.order_date)  # First day of month
            else:
                # For PostgreSQL or others that support date_trunc
                date_group = func.date_trunc(date_trunc_format, models.Order.order_date)
            
            # Execute the query
            daily_sales = db.query(
                date_group.label('date'),
                func.count(models.Order.id).label('orders'),
                func.sum(models.Order.total_amount).label('revenue')
            ).filter(
                models.Order.order_date >= start_date_obj,
                models.Order.order_date <= end_date_obj,
                models.Order.user_id == user_id  # Filter by user ID
            ).group_by(date_group).order_by(date_group).all()
            
            # Format the output
            for day in daily_sales:
                date_str = day.date
                if isinstance(date_str, datetime):
                    date_str = date_str.strftime('%Y-%m-%d')
                
                sales_by_day.append({
                    "date": date_str,
                    "orders": day.orders,
                    "revenue": float(day.revenue) if day.revenue is not None else 0.0
                })
        except Exception as e:
            logger.error(f"Error getting sales by day: {str(e)}")
            logger.error(traceback.format_exc())
            # Fall back to empty array
            sales_by_day = []
        
        # Get sales by category
        sales_by_category = []
        try:
            category_sales = db.query(
                models.Item.category,
                func.count(models.OrderItem.id).label('orders'),
                func.sum(models.OrderItem.quantity * models.OrderItem.unit_price).label('revenue')
            ).join(
                models.OrderItem,
                models.Item.id == models.OrderItem.item_id
            ).join(
                models.Order,
                models.OrderItem.order_id == models.Order.id
            ).filter(
                models.Order.order_date >= start_date_obj,
                models.Order.order_date <= end_date_obj,
                models.Order.user_id == user_id  # Filter by user ID
            ).group_by(models.Item.category).all()
            
            for cat in category_sales:
                sales_by_category.append({
                    "category": cat.category,
                    "orders": cat.orders,
                    "revenue": float(cat.revenue) if cat.revenue is not None else 0.0
                })
        except Exception as e:
            logger.error(f"Error getting sales by category: {str(e)}")
            # Fall back to empty array
            sales_by_category = []
                    
        # Return comprehensive dashboard data
        return {
            "totalSales": total_revenue,
            "totalOrders": total_orders,
            "averageOrderValue": avg_order_value,
            "topSellingItems": top_items,
            "salesByDay": sales_by_day,
            "salesByCategory": sales_by_category
        }
    except Exception as e:
        # Log the full error with stack trace
        logger.error(f"Dashboard error: {str(e)}")
        logger.error(traceback.format_exc())
        # Return a helpful error
        raise HTTPException(
            status_code=500,
            detail=f"Error generating dashboard data: {str(e)}"
        )

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
    try:
        # Determine date range based on time_frame
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)  # Default to 30 days
        
        # Handle different time frames
        if time_frame:
            if time_frame == '1d':
                start_date = end_date - timedelta(days=1)
                logger.info(f"Using 1-day time frame for product performance: {start_date} to {end_date}")
            elif time_frame == '7d':
                start_date = end_date - timedelta(days=7)
                logger.info(f"Using 7-day time frame for product performance: {start_date} to {end_date}")
            elif time_frame == '1m':
                start_date = end_date - timedelta(days=30)
                logger.info(f"Using 1-month time frame for product performance: {start_date} to {end_date}")
            elif time_frame == '6m':
                start_date = end_date - timedelta(days=180)
                logger.info(f"Using 6-month time frame for product performance: {start_date} to {end_date}")
            elif time_frame == '1yr':
                start_date = end_date - timedelta(days=365)
                logger.info(f"Using 1-year time frame for product performance: {start_date} to {end_date}")
        
        # Ensure we don't exceed available data
        min_date = datetime.now() - timedelta(days=365)  # We have a full year of data
        if start_date < min_date:
            logger.info(f"Limiting start date to 365 days ago (available data constraint)")
            start_date = min_date
            
        # Filter by the current user's ID unless specifically requesting another account's data
        user_id = account_id if account_id else current_user.id
        logger.info(f"Filtering product performance data for user_id: {user_id}")
        
        # Basic query to get products and their order metrics with time range filter
        item_query = db.query(
            models.Item.id,
            models.Item.name,
            models.Item.category,
            models.Item.current_price,
            models.Item.cost,
            func.count(models.OrderItem.id).label('order_count'),
            func.sum(models.OrderItem.quantity).label('quantity_sold'),
            func.sum(models.OrderItem.quantity * models.OrderItem.unit_price).label('revenue')
        ).outerjoin(
            models.OrderItem,
            models.Item.id == models.OrderItem.item_id
        ).outerjoin(
            models.Order,
            models.OrderItem.order_id == models.Order.id
        ).filter(
            # Filter items by user_id
            models.Item.user_id == user_id,
            # Only include orders within the time frame
            (models.Order.order_date >= start_date) | (models.Order.order_date.is_(None)),
            (models.Order.order_date <= end_date) | (models.Order.order_date.is_(None)),
            # If there are orders, ensure they belong to this user too
            (models.Order.user_id == user_id) | (models.Order.id.is_(None))
        ).group_by(
            models.Item.id
        ).all()
        
        # Transform the data for the frontend
        results = []
        for item in item_query:
            # Calculate revenue (default to 0 if None)
            revenue = float(item.revenue) if item.revenue is not None else 0.0
            # Get quantity sold (default to 0 if None)
            quantity = int(item.quantity_sold) if item.quantity_sold is not None else 0
            # Calculate cost (use 60% of price as default if not provided)
            cost = float(item.cost) if item.cost is not None else (float(item.current_price) * 0.6)
            # Calculate profit and margin
            profit = revenue - (cost * quantity)
            margin = (profit / revenue * 100) if revenue > 0 else 0
            
            # Generate a simple trend based on item id (for visual variety)
            volume_trend = 'up' if item.id % 2 == 0 else 'down'
            margin_trend = 'up' if item.id % 3 == 0 else 'down'
            
            results.append({
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "currentPrice": float(item.current_price),
                "cost": cost,
                "revenue": revenue,
                "profit": profit,
                "margin": margin,
                "quantitySold": quantity,
                "volumeTrend": volume_trend,
                "marginTrend": margin_trend,
                "growth": item.id % 10  # Simple placeholder
            })
        
        return results
    except Exception as e:
        # Log the full error with stack trace
        logger.error(f"Product performance error: {str(e)}")
        logger.error(traceback.format_exc())
        # Return a helpful error
        raise HTTPException(
            status_code=500,
            detail=f"Error getting product performance data: {str(e)}"
        )
