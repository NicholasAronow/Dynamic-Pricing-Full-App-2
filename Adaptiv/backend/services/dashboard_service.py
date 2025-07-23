"""
Dashboard service for handling dashboard data operations
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, text, or_, and_
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

    def get_dashboard_data(self, start_date: Optional[str] = None, end_date: Optional[str] = None, 
                      user_id: int = None, time_frame: Optional[str] = None,
                      items_time_frame: Optional[str] = None):
        """
        Get all dashboard data in a single call - both sales and product performance
        """
        try:
            # Get sales data
            sales_data = self.get_sales_data(start_date, end_date, user_id, time_frame)
        
            # Get product performance data with its own timeframe
            product_performance = self.get_product_performance(items_time_frame or time_frame, user_id)
        
            # Add product performance to the sales data
            sales_data["topSellingItems"] = product_performance
        
            return sales_data
        except Exception as e:
            logger.error(f"Error in get_dashboard_data: {str(e)}")
            raise
    
    def get_sales_data(self, start_date: Optional[str] = None, end_date: Optional[str] = None, user_id: int = None, time_frame: Optional[str] = None):
        """
        Get sales data for the dashboard - optimized version with SQLite compatibility
        """
        try:
            # Parse date range based on timeframe
            end_date_obj = datetime.now().replace(hour=23, minute=59, second=59)
            
            if time_frame:
                # Calculate start date based on timeframe
                if time_frame == "1d":
                    # For 1 day view, show yesterday's data
                    start_date_obj = (end_date_obj - timedelta(days=1)).replace(hour=0, minute=0, second=0)
                    end_date_obj = (end_date_obj - timedelta(days=1)).replace(hour=23, minute=59, second=59)
                elif time_frame == "7d":
                    start_date_obj = (end_date_obj - timedelta(days=6)).replace(hour=0, minute=0, second=0)
                elif time_frame == "1m":
                    start_date_obj = (end_date_obj - timedelta(days=29)).replace(hour=0, minute=0, second=0)
                elif time_frame == "6m":
                    start_date_obj = (end_date_obj - timedelta(days=179)).replace(hour=0, minute=0, second=0)
                elif time_frame == "1yr":
                    start_date_obj = (end_date_obj - timedelta(days=364)).replace(hour=0, minute=0, second=0)
                else:
                    start_date_obj = (end_date_obj - timedelta(days=29)).replace(hour=0, minute=0, second=0)
            elif start_date and end_date:
                # Parse provided dates
                try:
                    start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    end_date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                    except ValueError:
                        start_date_obj = (end_date_obj - timedelta(days=29)).replace(hour=0, minute=0, second=0)
            else:
                # Default to last 30 days
                start_date_obj = (end_date_obj - timedelta(days=29)).replace(hour=0, minute=0, second=0)

            logger.info(f"Using date range: {start_date_obj} to {end_date_obj} for timeframe: {time_frame}")

            # Determine if we should aggregate by month
            aggregate_by_month = time_frame in ['6m', '1yr']
            
            if aggregate_by_month:
                # For SQLite, use strftime to group by month
                query = self.db.query(
                    func.strftime('%Y-%m-01', models.Order.order_date).label('month'),
                    func.sum(models.Order.total_amount).label('revenue'),
                    func.count(models.Order.id).label('order_count')
                ).filter(
                    models.Order.user_id == user_id,
                    models.Order.order_date >= start_date_obj,
                    models.Order.order_date <= end_date_obj
                ).group_by(
                    func.strftime('%Y-%m', models.Order.order_date)
                ).order_by('month')
                
                monthly_results = query.all()
                
                # Get COGS data for the period
                cogs_data = self.db.query(models.COGS).filter(
                    models.COGS.user_id == user_id,
                    models.COGS.week_start_date >= start_date_obj.date() - timedelta(days=7),
                    models.COGS.week_start_date <= end_date_obj.date()
                ).all()
                
                daily_cogs = self._convert_weekly_cogs_to_daily(cogs_data)
                
                # Process monthly data
                sales_data = []
                total_revenue = 0
                total_orders = 0
                
                for row in monthly_results:
                    month_date_str = row.month
                    month_date = datetime.strptime(month_date_str, '%Y-%m-%d')
                    monthly_revenue = float(row.revenue or 0)
                    monthly_order_count = row.order_count or 0
                    
                    # Calculate monthly COGS
                    monthly_cogs_amount = 0
                    for date, cogs_amount in daily_cogs.items():
                        if date.year == month_date.year and date.month == month_date.month:
                            monthly_cogs_amount += cogs_amount
                    
                    # Calculate profit margin
                    profit_margin = None
                    if monthly_revenue > 0 and monthly_cogs_amount > 0:
                        profit_margin = ((monthly_revenue - monthly_cogs_amount) / monthly_revenue) * 100
                    
                    sales_data.append({
                        "date": month_date_str,
                        "revenue": round(monthly_revenue, 2),
                        "orders": monthly_order_count,
                        "totalCost": round(monthly_cogs_amount, 2),
                        "profitMargin": round(profit_margin, 2) if profit_margin is not None else None
                    })
                    
                    total_revenue += monthly_revenue
                    total_orders += monthly_order_count
                    
            else:
                # For daily aggregation, use date function for SQLite
                query = self.db.query(
                    func.date(models.Order.order_date).label('order_date'),
                    func.sum(models.Order.total_amount).label('revenue'),
                    func.count(models.Order.id).label('order_count')
                ).filter(
                    models.Order.user_id == user_id,
                    models.Order.order_date >= start_date_obj,
                    models.Order.order_date <= end_date_obj
                ).group_by(
                    func.date(models.Order.order_date)
                ).order_by('order_date')
                
                daily_results = query.all()
                
                # Get COGS data
                cogs_data = self.db.query(models.COGS).filter(
                    models.COGS.user_id == user_id,
                    models.COGS.week_start_date >= start_date_obj.date() - timedelta(days=7),
                    models.COGS.week_start_date <= end_date_obj.date()
                ).all()
                
                daily_cogs = self._convert_weekly_cogs_to_daily(cogs_data)
                
                # Create a map of actual sales data
                sales_map = {}
                for row in daily_results:
                    # Convert string date to date object if necessary
                    if isinstance(row.order_date, str):
                        order_date = datetime.strptime(row.order_date, '%Y-%m-%d').date()
                    else:
                        order_date = row.order_date
                    sales_map[order_date] = row
                
                # Generate complete date range to ensure all days are represented
                sales_data = []
                total_revenue = 0
                total_orders = 0
                
                current_date = start_date_obj.date()
                while current_date <= end_date_obj.date():
                    row = sales_map.get(current_date)
                    
                    if row:
                        daily_revenue = float(row.revenue or 0)
                        daily_order_count = row.order_count or 0
                    else:
                        daily_revenue = 0
                        daily_order_count = 0
                    
                    # Get COGS for this date
                    daily_cogs_amount = daily_cogs.get(current_date, 0)
                    
                    # Calculate profit margin
                    profit_margin = None
                    if daily_revenue > 0 and daily_cogs_amount > 0:
                        profit_margin = ((daily_revenue - daily_cogs_amount) / daily_revenue) * 100
                    
                    sales_data.append({
                        "date": current_date.isoformat(),
                        "revenue": round(daily_revenue, 2),
                        "orders": daily_order_count,
                        "totalCost": round(daily_cogs_amount, 2),
                        "profitMargin": round(profit_margin, 2) if profit_margin is not None else None
                    })
                    
                    total_revenue += daily_revenue
                    total_orders += daily_order_count
                    
                    current_date += timedelta(days=1)

            # Calculate average order value
            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

            logger.info(f"Processed sales data: {len(sales_data)} data points, total revenue: ${total_revenue:.2f}")

            # Return in SalesAnalytics format expected by frontend
            return {
                "totalSales": round(total_revenue, 2),
                "totalOrders": total_orders,
                "averageOrderValue": round(avg_order_value, 2),
                "salesByDay": sales_data,
                "topSellingItems": [],
                "salesByCategory": []
            }

        except Exception as e:
            logger.error(f"Error in get_sales_data: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def get_product_performance(self, time_frame: Optional[str] = None, user_id: int = None):
        """
        Get performance data for all products - optimized version
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
                start_date = end_date - timedelta(days=30)

            logger.info(f"Getting product performance for time frame: {time_frame}, date range: {start_date} to {end_date}")

            # Single optimized query to get all product performance data
            # Use a subquery to properly filter orders by date
            query = self.db.query(
                models.Item.id,
                models.Item.name,
                models.Item.current_price,
                models.Item.cost,
                func.coalesce(func.sum(models.OrderItem.quantity), 0).label('total_quantity'),
                func.coalesce(func.sum(models.OrderItem.quantity * models.OrderItem.unit_price), 0).label('total_revenue'),
                func.coalesce(func.sum(models.OrderItem.quantity * models.OrderItem.unit_cost), 0).label('total_cost')
            ).outerjoin(
                models.OrderItem, models.Item.id == models.OrderItem.item_id
            ).outerjoin(
                models.Order, models.OrderItem.order_id == models.Order.id
            ).filter(
                models.Item.user_id == user_id,
                or_(
                    models.Order.id == None,  # Include items with no orders
                    and_(
                        models.Order.order_date >= start_date,
                        models.Order.order_date <= end_date,
                        models.Order.user_id == user_id  # Ensure orders belong to the same user
                    )
                )
            ).group_by(
                models.Item.id, models.Item.name, models.Item.current_price, models.Item.cost
            ).all()
            
            product_performance = []
            for row in query:
                total_quantity = row.total_quantity or 0
                total_revenue = float(row.total_revenue or 0)
                total_cost = float(row.total_cost or 0)
                unit_cost = float(row.cost or 0)
                
                # Calculate profit margin
                profit_margin = 0
                if total_revenue > 0 and total_cost > 0:
                    profit_margin = ((total_revenue - total_cost) / total_revenue) * 100
                elif total_revenue > 0 and unit_cost > 0:
                    # If no order-level cost, calculate based on item cost
                    estimated_total_cost = total_quantity * unit_cost
                    profit_margin = ((total_revenue - estimated_total_cost) / total_revenue) * 100
                
                product_performance.append({
                    "id": row.id,
                    "itemId": row.id,
                    "name": row.name,
                    "quantity": total_quantity,
                    "revenue": round(total_revenue, 2),
                    "unitPrice": float(row.current_price) if row.current_price else 0,
                    "unitCost": unit_cost,
                    "totalCost": round(total_cost, 2),
                    "hasCost": bool(unit_cost > 0),
                    "marginPercentage": round(profit_margin, 2) if profit_margin > 0 else None
                })
            
            # Sort by quantity descending
            product_performance.sort(key=lambda x: x["quantity"], reverse=True)
            
            logger.info(f"Found {len(product_performance)} products with performance data")
            
            return product_performance
            
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
