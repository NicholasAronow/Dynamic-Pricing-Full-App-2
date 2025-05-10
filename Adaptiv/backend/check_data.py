#!/usr/bin/env python3
"""
Script to check the order data in the database.
"""
from database import get_db
import models
from sqlalchemy import func

def main():
    # Get database session
    db = next(get_db())
    
    # Check total orders
    total_orders = db.query(models.Order).count()
    print(f"Total orders in database: {total_orders}")
    
    # Check order totals
    total_amount = db.query(func.sum(models.Order.total_amount)).scalar()
    print(f"Total order amount: ${total_amount:.2f}")
    
    # Check top items
    top_items = db.query(
        models.Item.id,
        models.Item.name,
        func.count(models.OrderItem.id).label('order_count'),
        models.Item.current_price
    ).join(
        models.OrderItem,
        models.Item.id == models.OrderItem.item_id
    ).group_by(
        models.Item.id
    ).order_by(func.count(models.OrderItem.id).desc()).limit(5).all()
    
    print("\nTop selling items:")
    for item in top_items:
        print(f"ID: {item.id}, Name: {item.name}, Orders: {item.order_count}, Price: ${item.current_price:.2f}")
    
    # Check relationship between orders and items
    order_items = db.query(models.OrderItem).limit(5).all()
    print("\nSample order items:")
    for item in order_items:
        print(f"Order ID: {item.order_id}, Item ID: {item.item_id}, Quantity: {item.quantity}, Unit Price: ${item.unit_price:.2f}")
        # Also get the related order
        order = db.query(models.Order).filter(models.Order.id == item.order_id).first()
        print(f"  -> Order date: {order.order_date}, Total amount: ${order.total_amount:.2f}")
    
    # Check for orders with zero amounts
    zero_orders = db.query(models.Order).filter(models.Order.total_amount == 0).count()
    print(f"\nOrders with zero amount: {zero_orders}")

if __name__ == "__main__":
    main()
