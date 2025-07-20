from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import models
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class PricingService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_pricing_recommendations(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get pricing recommendations for all items belonging to a user.
        """
        try:
            # Get all items for the user
            items = self.db.query(models.Item).filter(models.Item.user_id == user_id).all()
            
            recommendations = []
            for item in items:
                # Get recent sales data for this item (last 30 days)
                thirty_days_ago = datetime.now() - timedelta(days=30)
                
                sales_data = self.db.query(
                    func.sum(models.OrderItem.quantity).label('total_quantity'),
                    func.sum(models.OrderItem.quantity * models.OrderItem.unit_price).label('total_revenue'),
                    func.avg(models.OrderItem.unit_price).label('avg_price')
                ).join(
                    models.Order, models.OrderItem.order_id == models.Order.id
                ).filter(
                    and_(
                        models.OrderItem.item_id == item.id,
                        models.Order.user_id == user_id,
                        models.Order.order_date >= thirty_days_ago
                    )
                ).first()
                
                # Get competitor data if available
                competitor_data = self.db.query(models.CompetitorItem).filter(
                    models.CompetitorItem.item_name.ilike(f"%{item.name}%")
                ).first()
                
                # Calculate recommendation
                recommendation = self._calculate_pricing_recommendation(
                    item, sales_data, competitor_data
                )
                
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting pricing recommendations: {str(e)}")
            raise
    
    def _calculate_pricing_recommendation(
        self, 
        item: models.Item, 
        sales_data: Any, 
        competitor_data: Optional[models.CompetitorItem]
    ) -> Dict[str, Any]:
        """
        Calculate pricing recommendation for a single item.
        """
        current_price = float(item.current_price or 0)
        
        # Base recommendation
        recommendation = {
            'item_id': item.id,
            'item_name': item.name,
            'current_price': current_price,
            'recommended_price': current_price,
            'confidence': 'medium',
            'reasoning': 'Maintain current price',
            'expected_impact': {
                'revenue_change': '0%',
                'volume_change': '0%'
            }
        }
        
        # Analyze sales performance
        if sales_data and sales_data.total_quantity:
            total_quantity = int(sales_data.total_quantity)
            avg_price = float(sales_data.avg_price or current_price)
            
            # High sales volume - consider price increase
            if total_quantity > 50:  # Threshold for high volume
                recommended_price = current_price * 1.05  # 5% increase
                recommendation.update({
                    'recommended_price': round(recommended_price, 2),
                    'confidence': 'high',
                    'reasoning': 'High demand suggests room for price increase',
                    'expected_impact': {
                        'revenue_change': '+3-7%',
                        'volume_change': '-2-5%'
                    }
                })
            
            # Low sales volume - consider price decrease
            elif total_quantity < 10:  # Threshold for low volume
                recommended_price = current_price * 0.95  # 5% decrease
                recommendation.update({
                    'recommended_price': round(recommended_price, 2),
                    'confidence': 'medium',
                    'reasoning': 'Low sales suggest price may be too high',
                    'expected_impact': {
                        'revenue_change': '-2-5%',
                        'volume_change': '+5-15%'
                    }
                })
        
        # Factor in competitor pricing
        if competitor_data and competitor_data.price:
            competitor_price = float(competitor_data.price)
            price_diff = (current_price - competitor_price) / competitor_price * 100
            
            # If significantly higher than competitors
            if price_diff > 15:
                recommended_price = competitor_price * 1.10  # 10% above competitor
                recommendation.update({
                    'recommended_price': round(recommended_price, 2),
                    'confidence': 'high',
                    'reasoning': f'Price is {price_diff:.1f}% above competitor average',
                    'expected_impact': {
                        'revenue_change': '-5-10%',
                        'volume_change': '+10-25%'
                    }
                })
            
            # If significantly lower than competitors
            elif price_diff < -15:
                recommended_price = competitor_price * 0.95  # 5% below competitor
                recommendation.update({
                    'recommended_price': round(recommended_price, 2),
                    'confidence': 'medium',
                    'reasoning': f'Price is {abs(price_diff):.1f}% below competitor average - opportunity to increase',
                    'expected_impact': {
                        'revenue_change': '+8-15%',
                        'volume_change': '-3-8%'
                    }
                })
        
        return recommendation
    
    def get_price_history(self, item_id: int, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get price history for an item over the specified number of days.
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            price_history = self.db.query(models.PriceHistory).filter(
                and_(
                    models.PriceHistory.item_id == item_id,
                    models.PriceHistory.user_id == user_id,
                    models.PriceHistory.changed_at >= start_date
                )
            ).order_by(models.PriceHistory.changed_at.desc()).all()
            
            return [
                {
                    'date': history.changed_at.isoformat(),
                    'old_price': float(history.old_price or 0),
                    'new_price': float(history.new_price or 0),
                    'reason': history.reason or 'Manual update'
                }
                for history in price_history
            ]
            
        except Exception as e:
            logger.error(f"Error getting price history for item {item_id}: {str(e)}")
            raise
    
    def update_item_price(self, item_id: int, new_price: float, user_id: int, reason: str = None) -> bool:
        """
        Update an item's price and record the change in price history.
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
            
            old_price = item.current_price
            
            # Update the item price
            item.current_price = new_price
            
            # Create price history record
            price_history = models.PriceHistory(
                item_id=item_id,
                user_id=user_id,
                old_price=old_price,
                new_price=new_price,
                changed_at=datetime.now(),
                reason=reason or 'Price recommendation accepted'
            )
            
            self.db.add(price_history)
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating price for item {item_id}: {str(e)}")
            self.db.rollback()
            raise
    
    def get_pricing_analytics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get pricing analytics including price changes impact and trends.
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get recent price changes
            price_changes = self.db.query(models.PriceHistory).filter(
                and_(
                    models.PriceHistory.user_id == user_id,
                    models.PriceHistory.changed_at >= start_date
                )
            ).count()
            
            # Get items with recent sales
            items_with_sales = self.db.query(
                models.Item.id,
                models.Item.name,
                models.Item.current_price,
                func.sum(models.OrderItem.quantity).label('total_quantity'),
                func.sum(models.OrderItem.quantity * models.OrderItem.unit_price).label('total_revenue')
            ).join(
                models.OrderItem, models.Item.id == models.OrderItem.item_id
            ).join(
                models.Order, models.OrderItem.order_id == models.Order.id
            ).filter(
                and_(
                    models.Order.user_id == user_id,
                    models.Order.order_date >= start_date
                )
            ).group_by(models.Item.id).all()
            
            # Calculate average price and revenue
            total_revenue = sum(float(item.total_revenue or 0) for item in items_with_sales)
            total_items = len(items_with_sales)
            avg_price = sum(float(item.current_price or 0) for item in items_with_sales) / total_items if total_items > 0 else 0
            
            return {
                'recent_price_changes': price_changes,
                'total_revenue': total_revenue,
                'average_price': round(avg_price, 2),
                'items_analyzed': total_items,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Error getting pricing analytics: {str(e)}")
            raise
