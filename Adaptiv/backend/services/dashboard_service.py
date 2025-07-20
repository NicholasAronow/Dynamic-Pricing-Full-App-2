"""
Dashboard service for handling dashboard data operations
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import models
import traceback
import logging

logger = logging.getLogger(__name__)

class DashboardService:
    """Service for dashboard operations and data aggregation"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_sales_data(self, start_date: Optional[str] = None, end_date: Optional[str] = None, user_id: int = None):
        """
        Get sales data for the dashboard
        """
        try:
            # Parse date range or use default (last 30 days)
            end_date_obj = datetime.now()
            start_date_obj = end_date_obj - timedelta(days=30)  # Default to last 30 days
            
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
                        logger.warning(f"Failed to parse dates {start_date} and {end_date}, using default range")
                        pass

            logger.info(f"Using date range: {start_date_obj} to {end_date_obj}")

            # Get orders within the date range
            orders = self.db.query(models.Order).filter(
                models.Order.user_id == user_id,
                models.Order.order_date >= start_date_obj,
                models.Order.order_date <= end_date_obj
            ).all()

            logger.info(f"Found {len(orders)} orders for user {user_id}")

            # Get COGS data for profit margin calculations
            cogs_data = self.db.query(models.COGS).filter(
                models.COGS.user_id == user_id
            ).order_by(models.COGS.week_start_date.desc()).all()

            # Convert weekly COGS to daily values for profit margin calculation
            daily_cogs = self._convert_weekly_cogs_to_daily(cogs_data)

            # Process orders and calculate metrics
            sales_data = []
            total_revenue = 0
            total_orders = len(orders)

            # Group orders by date for daily aggregation
            daily_orders = {}
            for order in orders:
                order_date = order.order_date.date()
                if order_date not in daily_orders:
                    daily_orders[order_date] = []
                daily_orders[order_date].append(order)

            # Process each day's data
            for date, day_orders in daily_orders.items():
                daily_revenue = sum(order.total_amount or 0 for order in day_orders)
                daily_order_count = len(day_orders)
                
                # Get COGS for this date
                daily_cogs_amount = daily_cogs.get(date, 0)
                
                # Calculate profit margin
                profit_margin = 0
                if daily_revenue > 0 and daily_cogs_amount > 0:
                    profit_margin = ((daily_revenue - daily_cogs_amount) / daily_revenue) * 100

                sales_data.append({
                    "date": date.isoformat(),
                    "sales": daily_revenue,
                    "orders": daily_order_count,
                    "profit_margin": round(profit_margin, 2)
                })
                
                total_revenue += daily_revenue

            # Sort by date
            sales_data.sort(key=lambda x: x["date"])

            # Calculate average order value
            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

            logger.info(f"Processed sales data: {len(sales_data)} days, total revenue: ${total_revenue:.2f}")

            return {
                "sales_data": sales_data,
                "total_revenue": round(total_revenue, 2),
                "total_orders": total_orders,
                "avg_order_value": round(avg_order_value, 2),
                "date_range": {
                    "start": start_date_obj.isoformat(),
                    "end": end_date_obj.isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Error in get_sales_data: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def get_product_performance(self, time_frame: Optional[str] = None, user_id: int = None):
        """
        Get performance data for all products
        """
        try:
            # Calculate date range based on time frame
            end_date = datetime.now()
            if time_frame == "1d":
                start_date = end_date - timedelta(days=1)
            elif time_frame == "7d":
                start_date = end_date - timedelta(days=7)
            elif time_frame == "1m":
                start_date = end_date - timedelta(days=30)
            elif time_frame == "6m":
                start_date = end_date - timedelta(days=180)
            elif time_frame == "1yr":
                start_date = end_date - timedelta(days=365)
            else:
                start_date = end_date - timedelta(days=30)  # Default to 30 days

            logger.info(f"Getting product performance for time frame: {time_frame}, date range: {start_date} to {end_date}")

            # Get all items for the user
            items = self.db.query(models.Item).filter(models.Item.user_id == user_id).all()
            
            product_performance = []
            
            for item in items:
                # Get order items for this product within the date range
                order_items = self.db.query(models.OrderItem).join(models.Order).filter(
                    models.OrderItem.item_id == item.id,
                    models.Order.user_id == user_id,
                    models.Order.order_date >= start_date,
                    models.Order.order_date <= end_date
                ).all()
                
                # Calculate metrics
                total_quantity = sum(oi.quantity for oi in order_items)
                total_revenue = sum(oi.quantity * oi.unit_price for oi in order_items)
                total_cost = sum(oi.quantity * (oi.unit_cost or 0) for oi in order_items)
                
                # Calculate profit margin
                profit_margin = 0
                if total_revenue > 0:
                    profit_margin = ((total_revenue - total_cost) / total_revenue) * 100
                
                product_performance.append({
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "current_price": float(item.current_price) if item.current_price else 0,
                    "cost": float(item.cost) if item.cost else 0,
                    "quantity_sold": total_quantity,
                    "revenue": round(total_revenue, 2),
                    "profit_margin": round(profit_margin, 2),
                    "orders_count": len(set(oi.order_id for oi in order_items))
                })
            
            # Sort by revenue descending
            product_performance.sort(key=lambda x: x["revenue"], reverse=True)
            
            logger.info(f"Processed {len(product_performance)} products")
            
            return {
                "products": product_performance,
                "time_frame": time_frame,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error in get_product_performance: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def _convert_weekly_cogs_to_daily(self, cogs_data: List[models.COGS]) -> Dict[datetime.date, float]:
        """
        Convert weekly COGS data to daily values by distributing each week's costs evenly across days
        """
        daily_cogs = {}
        
        for cogs in cogs_data:
            if cogs.week_start_date and cogs.amount:
                # Distribute the weekly amount across 7 days
                daily_amount = float(cogs.amount) / 7
                
                # Add to each day of the week
                for i in range(7):
                    date = cogs.week_start_date + timedelta(days=i)
                    daily_cogs[date] = daily_amount
        
        return daily_cogs

    def get_dashboard_summary(self, user_id: int):
        """Get summary statistics for dashboard"""
        try:
            # Get basic counts
            total_items = self.db.query(models.Item).filter(models.Item.user_id == user_id).count()
            total_orders = self.db.query(models.Order).filter(models.Order.user_id == user_id).count()
            
            # Get revenue for last 30 days
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_orders = self.db.query(models.Order).filter(
                models.Order.user_id == user_id,
                models.Order.order_date >= thirty_days_ago
            ).all()
            
            total_revenue = sum(order.total_amount or 0 for order in recent_orders)
            avg_order_value = total_revenue / len(recent_orders) if recent_orders else 0
            
            # Get top selling item
            top_item_query = self.db.query(
                models.Item.name,
                func.sum(models.OrderItem.quantity).label('total_sold')
            ).join(
                models.OrderItem, models.Item.id == models.OrderItem.item_id
            ).join(
                models.Order, models.OrderItem.order_id == models.Order.id
            ).filter(
                models.Item.user_id == user_id,
                models.Order.order_date >= thirty_days_ago
            ).group_by(
                models.Item.id, models.Item.name
            ).order_by(
                func.sum(models.OrderItem.quantity).desc()
            ).first()
            
            top_item = top_item_query.name if top_item_query else "No sales data"
            
            return {
                "total_items": total_items,
                "total_orders": total_orders,
                "total_revenue_30d": round(total_revenue, 2),
                "avg_order_value": round(avg_order_value, 2),
                "top_selling_item": top_item,
                "recent_orders_count": len(recent_orders)
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard summary: {str(e)}")
            return {
                "total_items": 0,
                "total_orders": 0,
                "total_revenue_30d": 0,
                "avg_order_value": 0,
                "top_selling_item": "Error loading data",
                "recent_orders_count": 0
            }
