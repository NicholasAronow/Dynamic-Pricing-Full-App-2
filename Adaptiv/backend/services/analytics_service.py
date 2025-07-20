"""
Analytics service for handling sales data analysis and reporting
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import models
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service for analytics operations and data aggregation"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_optimized_sales_data(self, start_date: str, end_date: str, time_frame: str, user_id: int):
        """
        Get optimized sales data based on time frame.
        Aggregates on the backend to minimize data transfer.
        """
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
        except ValueError:
            raise ValueError("Invalid date format")
        
        # Determine aggregation level based on time frame
        if time_frame in ['1d', '7d', '1m']:
            # Daily aggregation
            return self.get_daily_aggregated_data(start, end, user_id)
        else:  # 6m, 1yr
            # Monthly aggregation
            return self.get_monthly_aggregated_data(start, end, user_id)

    def get_daily_aggregated_data(self, start: datetime, end: datetime, user_id: int):
        """
        Get daily aggregated sales data with pre-calculated margins.
        """
        # Use SQL to aggregate at the database level
        daily_data = self.db.query(
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
        ).group_by(func.date(models.Order.order_date)).all()
        
        # Convert to list of dictionaries for JSON serialization
        result = []
        for row in daily_data:
            result.append({
                'date': row.date.isoformat() if row.date else None,
                'revenue': float(row.revenue) if row.revenue else 0.0,
                'orders': int(row.orders) if row.orders else 0,
                'cogs': float(row.cogs) if row.cogs else 0.0,
                'avg_margin': float(row.avg_margin) if row.avg_margin else 0.0,
                'profit': float(row.revenue - row.cogs) if row.revenue and row.cogs else 0.0
            })
        
        return {
            'data': result,
            'aggregation_level': 'daily',
            'total_records': len(result)
        }

    def get_monthly_aggregated_data(self, start: datetime, end: datetime, user_id: int):
        """
        Get monthly aggregated sales data for longer time frames.
        """
        monthly_data = self.db.query(
            func.extract('year', models.Order.order_date).label('year'),
            func.extract('month', models.Order.order_date).label('month'),
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
            func.extract('year', models.Order.order_date),
            func.extract('month', models.Order.order_date)
        ).order_by(
            func.extract('year', models.Order.order_date),
            func.extract('month', models.Order.order_date)
        ).all()
        
        # Convert to list of dictionaries
        result = []
        for row in monthly_data:
            # Create a date string for the first day of the month
            date_str = f"{int(row.year)}-{int(row.month):02d}-01"
            result.append({
                'date': date_str,
                'revenue': float(row.revenue) if row.revenue else 0.0,
                'orders': int(row.orders) if row.orders else 0,
                'cogs': float(row.cogs) if row.cogs else 0.0,
                'avg_margin': float(row.avg_margin) if row.avg_margin else 0.0,
                'profit': float(row.revenue - row.cogs) if row.revenue and row.cogs else 0.0
            })
        
        return {
            'data': result,
            'aggregation_level': 'monthly',
            'total_records': len(result)
        }

    def get_top_selling_items(self, start: datetime, end: datetime, user_id: int, limit: int = 10):
        """
        Get top selling items with margin data for a time period.
        """
        top_items = self.db.query(
            models.Item.id,
            models.Item.name,
            models.Item.category,
            models.Item.current_price,
            models.Item.cost,
            func.sum(models.OrderItem.quantity).label('total_quantity'),
            func.sum(models.OrderItem.quantity * models.OrderItem.unit_price).label('total_revenue'),
            func.sum(models.OrderItem.quantity * models.OrderItem.unit_cost).label('total_cost'),
            func.count(models.Order.id).label('order_count')
        ).join(
            models.OrderItem, models.Item.id == models.OrderItem.item_id
        ).join(
            models.Order, models.OrderItem.order_id == models.Order.id
        ).filter(
            and_(
                models.Item.user_id == user_id,
                models.Order.order_date >= start,
                models.Order.order_date <= end
            )
        ).group_by(
            models.Item.id,
            models.Item.name,
            models.Item.category,
            models.Item.current_price,
            models.Item.cost
        ).order_by(
            func.sum(models.OrderItem.quantity).desc()
        ).limit(limit).all()
        
        # Convert to list of dictionaries
        result = []
        for row in top_items:
            total_revenue = float(row.total_revenue) if row.total_revenue else 0.0
            total_cost = float(row.total_cost) if row.total_cost else 0.0
            margin = ((total_revenue - total_cost) / total_revenue * 100) if total_revenue > 0 else 0.0
            
            result.append({
                'id': row.id,
                'name': row.name,
                'category': row.category,
                'current_price': float(row.current_price) if row.current_price else 0.0,
                'cost': float(row.cost) if row.cost else 0.0,
                'total_quantity': int(row.total_quantity) if row.total_quantity else 0,
                'total_revenue': total_revenue,
                'total_cost': total_cost,
                'margin_percent': round(margin, 2),
                'order_count': int(row.order_count) if row.order_count else 0
            })
        
        return result

    def get_optimized_product_performance(self, time_frame: str, user_id: int):
        """
        Get product performance data optimized for the specified time frame.
        """
        # Calculate date range based on time frame
        end_date = datetime.now()
        if time_frame == '1d':
            start_date = end_date - timedelta(days=1)
        elif time_frame == '7d':
            start_date = end_date - timedelta(days=7)
        elif time_frame == '1m':
            start_date = end_date - timedelta(days=30)
        elif time_frame == '6m':
            start_date = end_date - timedelta(days=180)
        elif time_frame == '1yr':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)  # Default to 30 days
        
        # Get product performance data
        performance_data = self.db.query(
            models.Item.id,
            models.Item.name,
            models.Item.category,
            models.Item.current_price,
            models.Item.cost,
            func.coalesce(func.sum(models.OrderItem.quantity), 0).label('total_sold'),
            func.coalesce(func.sum(models.OrderItem.quantity * models.OrderItem.unit_price), 0).label('revenue'),
            func.coalesce(func.sum(models.OrderItem.quantity * models.OrderItem.unit_cost), 0).label('total_cost'),
            func.count(models.Order.id).label('order_frequency')
        ).outerjoin(
            models.OrderItem, models.Item.id == models.OrderItem.item_id
        ).outerjoin(
            models.Order, and_(
                models.OrderItem.order_id == models.Order.id,
                models.Order.order_date >= start_date,
                models.Order.order_date <= end_date
            )
        ).filter(
            models.Item.user_id == user_id
        ).group_by(
            models.Item.id,
            models.Item.name,
            models.Item.category,
            models.Item.current_price,
            models.Item.cost
        ).all()
        
        # Process and format the data
        result = []
        for row in performance_data:
            revenue = float(row.revenue) if row.revenue else 0.0
            total_cost = float(row.total_cost) if row.total_cost else 0.0
            profit = revenue - total_cost
            margin = (profit / revenue * 100) if revenue > 0 else 0.0
            
            result.append({
                'id': row.id,
                'name': row.name,
                'category': row.category,
                'current_price': float(row.current_price) if row.current_price else 0.0,
                'cost': float(row.cost) if row.cost else 0.0,
                'total_sold': int(row.total_sold) if row.total_sold else 0,
                'revenue': revenue,
                'total_cost': total_cost,
                'profit': profit,
                'margin_percent': round(margin, 2),
                'order_frequency': int(row.order_frequency) if row.order_frequency else 0
            })
        
        return {
            'products': result,
            'time_frame': time_frame,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
    
    def get_sales_summary(self, user_id: int, days: int = 30):
        """Get sales summary for the specified number of days"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        summary = self.db.query(
            func.count(models.Order.id).label('total_orders'),
            func.coalesce(func.sum(models.Order.total_amount), 0).label('total_revenue'),
            func.coalesce(func.sum(models.Order.total_cost), 0).label('total_cost'),
            func.coalesce(func.avg(models.Order.total_amount), 0).label('avg_order_value')
        ).filter(
            and_(
                models.Order.user_id == user_id,
                models.Order.order_date >= start_date,
                models.Order.order_date <= end_date
            )
        ).first()
        
        total_revenue = float(summary.total_revenue) if summary.total_revenue else 0.0
        total_cost = float(summary.total_cost) if summary.total_cost else 0.0
        
        return {
            'total_orders': int(summary.total_orders) if summary.total_orders else 0,
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'total_profit': total_revenue - total_cost,
            'avg_order_value': float(summary.avg_order_value) if summary.avg_order_value else 0.0,
            'period_days': days
        }
