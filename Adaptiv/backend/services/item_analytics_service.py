from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
import models
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ItemAnalyticsService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_item_analytics(self, item_id: int, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive analytics for a specific item.
        """
        try:
            # Get the item
            item = self.db.query(models.Item).filter(
                and_(
                    models.Item.id == item_id,
                    models.Item.user_id == user_id
                )
            ).first()
            
            if not item:
                raise ValueError(f"Item {item_id} not found for user {user_id}")
            
            start_date = datetime.now() - timedelta(days=days)
            
            # Get sales data
            sales_data = self._get_sales_analytics(item_id, user_id, start_date)
            
            # Get price history
            price_history = self._get_price_history_analytics(item_id, user_id, start_date)
            
            # Get competitor data
            competitor_data = self._get_competitor_analytics(item.name)
            
            # Get performance metrics
            performance_metrics = self._get_performance_metrics(item_id, user_id, start_date)
            
            return {
                'item': {
                    'id': item.id,
                    'name': item.name,
                    'category': item.category,
                    'current_price': float(item.current_price or 0),
                    'cost': float(item.cost or 0)
                },
                'sales_analytics': sales_data,
                'price_history': price_history,
                'competitor_analysis': competitor_data,
                'performance_metrics': performance_metrics,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Error getting item analytics for item {item_id}: {str(e)}")
            raise
    
    def _get_sales_analytics(self, item_id: int, user_id: int, start_date: datetime) -> Dict[str, Any]:
        """
        Get sales analytics for an item.
        """
        # Get overall sales data
        sales_summary = self.db.query(
            func.sum(models.OrderItem.quantity).label('total_quantity'),
            func.sum(models.OrderItem.quantity * models.OrderItem.unit_price).label('total_revenue'),
            func.count(models.OrderItem.id).label('total_orders'),
            func.avg(models.OrderItem.unit_price).label('avg_price')
        ).join(
            models.Order, models.OrderItem.order_id == models.Order.id
        ).filter(
            and_(
                models.OrderItem.item_id == item_id,
                models.Order.user_id == user_id,
                models.Order.order_date >= start_date
            )
        ).first()
        
        # Get daily sales trend
        daily_sales = self.db.query(
            func.date(models.Order.order_date).label('date'),
            func.sum(models.OrderItem.quantity).label('quantity'),
            func.sum(models.OrderItem.quantity * models.OrderItem.unit_price).label('revenue')
        ).join(
            models.Order, models.OrderItem.order_id == models.Order.id
        ).filter(
            and_(
                models.OrderItem.item_id == item_id,
                models.Order.user_id == user_id,
                models.Order.order_date >= start_date
            )
        ).group_by(func.date(models.Order.order_date)).order_by('date').all()
        
        return {
            'total_quantity': int(sales_summary.total_quantity or 0),
            'total_revenue': float(sales_summary.total_revenue or 0),
            'total_orders': int(sales_summary.total_orders or 0),
            'average_price': float(sales_summary.avg_price or 0),
            'daily_trend': [
                {
                    'date': str(day.date),
                    'quantity': int(day.quantity or 0),
                    'revenue': float(day.revenue or 0)
                }
                for day in daily_sales
            ]
        }
    
    def _get_price_history_analytics(self, item_id: int, user_id: int, start_date: datetime) -> Dict[str, Any]:
        """
        Get price history analytics for an item.
        """
        price_changes = self.db.query(models.PriceHistory).filter(
            and_(
                models.PriceHistory.item_id == item_id,
                models.PriceHistory.user_id == user_id,
                models.PriceHistory.changed_at >= start_date
            )
        ).order_by(models.PriceHistory.changed_at.desc()).all()
        
        return {
            'total_changes': len(price_changes),
            'changes': [
                {
                    'date': change.changed_at.isoformat(),
                    'old_price': float(change.old_price or 0),
                    'new_price': float(change.new_price or 0),
                    'change_percent': ((float(change.new_price or 0) - float(change.old_price or 0)) / float(change.old_price or 1)) * 100,
                    'reason': change.reason or 'Manual update'
                }
                for change in price_changes
            ]
        }
    
    def _get_competitor_analytics(self, item_name: str) -> Dict[str, Any]:
        """
        Get competitor analysis for an item.
        """
        competitors = self.db.query(models.CompetitorItem).filter(
            models.CompetitorItem.item_name.ilike(f"%{item_name}%")
        ).all()
        
        if not competitors:
            return {
                'competitors_found': 0,
                'average_competitor_price': None,
                'price_range': None,
                'competitors': []
            }
        
        prices = [float(comp.price) for comp in competitors if comp.price]
        
        return {
            'competitors_found': len(competitors),
            'average_competitor_price': sum(prices) / len(prices) if prices else None,
            'price_range': {
                'min': min(prices) if prices else None,
                'max': max(prices) if prices else None
            },
            'competitors': [
                {
                    'source': comp.source or 'Unknown',
                    'name': comp.item_name,
                    'price': float(comp.price or 0),
                    'last_updated': comp.last_updated.isoformat() if comp.last_updated else None
                }
                for comp in competitors
            ]
        }
    
    def _get_performance_metrics(self, item_id: int, user_id: int, start_date: datetime) -> Dict[str, Any]:
        """
        Get performance metrics for an item.
        """
        # Get current period data
        current_data = self.db.query(
            func.sum(models.OrderItem.quantity).label('quantity'),
            func.sum(models.OrderItem.quantity * models.OrderItem.unit_price).label('revenue')
        ).join(
            models.Order, models.OrderItem.order_id == models.Order.id
        ).filter(
            and_(
                models.OrderItem.item_id == item_id,
                models.Order.user_id == user_id,
                models.Order.order_date >= start_date
            )
        ).first()
        
        # Get previous period data for comparison
        period_length = (datetime.now() - start_date).days
        previous_start = start_date - timedelta(days=period_length)
        
        previous_data = self.db.query(
            func.sum(models.OrderItem.quantity).label('quantity'),
            func.sum(models.OrderItem.quantity * models.OrderItem.unit_price).label('revenue')
        ).join(
            models.Order, models.OrderItem.order_id == models.Order.id
        ).filter(
            and_(
                models.OrderItem.item_id == item_id,
                models.Order.user_id == user_id,
                models.Order.order_date >= previous_start,
                models.Order.order_date < start_date
            )
        ).first()
        
        current_quantity = int(current_data.quantity or 0)
        current_revenue = float(current_data.revenue or 0)
        previous_quantity = int(previous_data.quantity or 0)
        previous_revenue = float(previous_data.revenue or 0)
        
        # Calculate growth rates
        quantity_growth = ((current_quantity - previous_quantity) / previous_quantity * 100) if previous_quantity > 0 else 0
        revenue_growth = ((current_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue > 0 else 0
        
        return {
            'current_period': {
                'quantity': current_quantity,
                'revenue': current_revenue
            },
            'previous_period': {
                'quantity': previous_quantity,
                'revenue': previous_revenue
            },
            'growth_rates': {
                'quantity_growth_percent': round(quantity_growth, 2),
                'revenue_growth_percent': round(revenue_growth, 2)
            }
        }
    
    def get_top_performing_items(self, user_id: int, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top performing items by revenue for a user.
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            top_items = self.db.query(
                models.Item.id,
                models.Item.name,
                models.Item.category,
                models.Item.current_price,
                func.sum(models.OrderItem.quantity).label('total_quantity'),
                func.sum(models.OrderItem.quantity * models.OrderItem.unit_price).label('total_revenue'),
                func.count(models.OrderItem.id).label('order_count')
            ).join(
                models.OrderItem, models.Item.id == models.OrderItem.item_id
            ).join(
                models.Order, models.OrderItem.order_id == models.Order.id
            ).filter(
                and_(
                    models.Order.user_id == user_id,
                    models.Order.order_date >= start_date
                )
            ).group_by(
                models.Item.id
            ).order_by(
                desc('total_revenue')
            ).limit(limit).all()
            
            return [
                {
                    'id': item.id,
                    'name': item.name,
                    'category': item.category,
                    'current_price': float(item.current_price or 0),
                    'total_quantity': int(item.total_quantity or 0),
                    'total_revenue': float(item.total_revenue or 0),
                    'order_count': int(item.order_count or 0),
                    'avg_revenue_per_order': float(item.total_revenue or 0) / int(item.order_count or 1)
                }
                for item in top_items
            ]
            
        except Exception as e:
            logger.error(f"Error getting top performing items: {str(e)}")
            raise
