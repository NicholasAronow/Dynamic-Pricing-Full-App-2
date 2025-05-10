"""
Script to seed order data for the Adaptiv Pricing app.
This generates 30 days of order data with realistic patterns.
"""

import sys
import os
import random
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from models import Base, Order, OrderItem, Item, User
from database import get_db
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants for order generation
NUM_DAYS = 30  # Generate orders for the last 30 days
MIN_ORDERS_PER_DAY = 15
MAX_ORDERS_PER_DAY = 50
MIN_ITEMS_PER_ORDER = 1
MAX_ITEMS_PER_ORDER = 5
MIN_QUANTITY_PER_ITEM = 1
MAX_QUANTITY_PER_ITEM = 3

def get_random_time(date):
    """Generate a random time during business hours (7am-10pm)"""
    hour = random.randint(7, 22)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return datetime.datetime.combine(date, datetime.time(hour, minute, second))

def generate_orders(db_session, num_days=NUM_DAYS):
    """Generate orders with realistic patterns for the given number of days"""
    
    # Get all items from the database
    items = db_session.query(Item).all()
    if not items:
        logger.error("No items found in the database. Please seed items first.")
        return False
    
    # Check if we have items to create orders for
    item_count = db_session.query(Item).count()
    logger.info(f"Found {item_count} items in the database")
    
    logger.info(f"Generating orders for the last {num_days} days")
    
    # Delete existing orders to avoid duplication
    db_session.query(OrderItem).delete()
    db_session.query(Order).delete()
    db_session.commit()
    
    today = datetime.date.today()
    total_orders = 0
    
    # Different day patterns (weekday vs weekend)
    weekday_multiplier = 1.0
    weekend_multiplier = 1.5
    
    # For each day in the range
    for day_offset in range(num_days, 0, -1):
        current_date = today - datetime.timedelta(days=day_offset)
        
        # More orders on weekends
        is_weekend = current_date.weekday() >= 5  # 5,6 = Saturday, Sunday
        daily_multiplier = weekend_multiplier if is_weekend else weekday_multiplier
        
        # Random number of orders for this day, influenced by weekday/weekend
        num_orders = random.randint(
            int(MIN_ORDERS_PER_DAY * daily_multiplier),
            int(MAX_ORDERS_PER_DAY * daily_multiplier)
        )
        
        logger.info(f"Generating {num_orders} orders for {current_date}")
        
        # Create orders for this day
        for _ in range(num_orders):
            # Generate order time
            order_time = get_random_time(current_date)
            
            # Create order
            new_order = Order(
                order_date=order_time,
                total_amount=0,  # Will calculate after adding items
                created_at=order_time
            )
            db_session.add(new_order)
            db_session.flush()  # Get the order ID
            
            # Random number of different items in this order
            num_items = random.randint(MIN_ITEMS_PER_ORDER, MAX_ITEMS_PER_ORDER)
            
            # Select random items (ensure no duplicates)
            selected_items = random.sample(items, min(num_items, len(items)))
            total_amount = 0
            
            # Add items to the order
            for item in selected_items:
                # Random quantity
                quantity = random.randint(MIN_QUANTITY_PER_ITEM, MAX_QUANTITY_PER_ITEM)
                
                # Calculate subtotal
                subtotal = quantity * item.current_price
                total_amount += subtotal
                
                # Create order item
                order_item = OrderItem(
                    order_id=new_order.id,
                    item_id=item.id,
                    quantity=quantity,
                    unit_price=item.current_price
                )
                db_session.add(order_item)
            
            # Update order total
            new_order.total_amount = total_amount
            total_orders += 1
            
            # Commit in batches to avoid overwhelming the database
            if total_orders % 100 == 0:
                db_session.commit()
        
        # Commit remaining orders for this day
        db_session.commit()
    
    logger.info(f"Successfully generated {total_orders} orders over {num_days} days")
    return True

def main():
    """Main function to run the seed script"""
    try:
        db = next(get_db())
        success = generate_orders(db)
        if success:
            logger.info("Order seeding completed successfully!")
        else:
            logger.error("Order seeding failed.")
    except Exception as e:
        logger.error(f"Error seeding orders: {str(e)}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
