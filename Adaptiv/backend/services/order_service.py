from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import models, schemas
import logging

logger = logging.getLogger(__name__)

class OrderService:
    def __init__(self, db: Session):
        self.db = db

    def get_orders(self, user_id: int, skip: int = 0, limit: Optional[int] = None) -> List[models.Order]:
        """
        Get all orders for a user with pagination.
        """
        query = self.db.query(models.Order).filter(models.Order.user_id == user_id)
        
        if skip > 0:
            query = query.offset(skip)
        if limit:
            query = query.limit(limit)
            
        return query.all()

    def check_has_orders(self, user_id: int) -> bool:
        """
        Check if a user has any orders in the system.
        """
        return self.db.query(func.count(models.Order.id)).filter(
            models.Order.user_id == user_id
        ).scalar() > 0

    def create_order(self, order_data: schemas.OrderCreate, user_id: int) -> models.Order:
        """
        Create a new order with items for a user.
        """
        try:
            # Calculate total amount from items
            total_amount = sum(item.unit_price * item.quantity for item in order_data.items)
            
            # Create order
            db_order = models.Order(
                order_date=order_data.order_date,
                total_amount=total_amount,
                user_id=user_id
            )
            self.db.add(db_order)
            self.db.flush()  # Flush to get the order ID
            
            # Create order items
            for item in order_data.items:
                # Verify item exists and belongs to the user
                db_item = self.db.query(models.Item).filter(
                    models.Item.id == item.item_id,
                    models.Item.user_id == user_id
                ).first()
                if not db_item:
                    raise ValueError(f"Item with ID {item.item_id} not found")
                    
                order_item = models.OrderItem(
                    order_id=db_order.id,
                    item_id=item.item_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price
                )
                self.db.add(order_item)
            
            self.db.commit()
            self.db.refresh(db_order)
            return db_order
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating order: {str(e)}")
            raise

    def get_orders_by_date_range(
        self, 
        user_id: int, 
        start_date: datetime, 
        end_date: datetime,
        skip: int = 0,
        limit: Optional[int] = None
    ) -> List[models.Order]:
        """
        Get orders within a specific date range.
        """
        query = self.db.query(models.Order).filter(
            models.Order.user_id == user_id,
            models.Order.order_date >= start_date,
            models.Order.order_date <= end_date
        )
        
        if skip > 0:
            query = query.offset(skip)
        if limit:
            query = query.limit(limit)
            
        return query.all()

    def get_order_statistics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get order statistics for a user over a specified period.
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get orders in the period
            orders = self.get_orders_by_date_range(user_id, start_date, end_date)
            
            total_orders = len(orders)
            total_revenue = sum(order.total_amount or 0 for order in orders)
            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
            
            return {
                'total_orders': total_orders,
                'total_revenue': round(total_revenue, 2),
                'avg_order_value': round(avg_order_value, 2),
                'period_days': days,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting order statistics: {str(e)}")
            raise

    def get_recent_orders(self, user_id: int, limit: int = 10) -> List[models.Order]:
        """
        Get the most recent orders for a user.
        """
        return self.db.query(models.Order).filter(
            models.Order.user_id == user_id
        ).order_by(models.Order.order_date.desc()).limit(limit).all()
