"""
Check orders for testprofessional@test.com account
"""
import sys
from database import get_db
from models import User, Order, Item, OrderItem
from sqlalchemy import func

def main():
    # Get database session
    db = next(get_db())
    
    # Find the test user
    user = db.query(User).filter(User.email == 'testprofessional@test.com').first()
    
    if not user:
        print("Test user not found!")
        return
    
    # Count orders
    order_count = db.query(func.count(Order.id)).filter(Order.user_id == user.id).scalar()
    print(f"Found {order_count} orders for testprofessional@test.com (user_id: {user.id})")
    
    # Check for recent orders
    recent_orders = db.query(Order).filter(Order.user_id == user.id).order_by(Order.order_date.desc()).limit(5).all()
    
    if recent_orders:
        print("\nMost recent orders:")
        for order in recent_orders:
            order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
            items_count = len(order_items)
            print(f"Order ID: {order.id}, Date: {order.order_date}, Amount: ${order.total_amount:.2f}, Items: {items_count}")
    
    # Count items
    item_count = db.query(func.count(Item.id)).filter(Item.user_id == user.id).scalar()
    print(f"\nFound {item_count} items for this user")

if __name__ == "__main__":
    main()
