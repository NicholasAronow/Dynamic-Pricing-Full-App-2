#!/usr/bin/env python3
"""
Test Order Generator Script

This script generates realistic test orders for a specific user over a 12-month period,
using only their existing menu items.
"""

import os
import sys
import random
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

# Import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import models
from database import SessionLocal, engine, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_user_items(db: Session, user_id: int) -> List[models.Item]:
    """Get all menu items for a user"""
    items = db.query(models.Item).filter(models.Item.user_id == user_id).all()
    logger.info(f"Found {len(items)} menu items for user {user_id}")
    return items

def generate_order_date(start_date, end_date):
    """Generate a random date between start_date and end_date"""
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    random_date = start_date + timedelta(days=random_number_of_days)
    
    # Add random hour (more orders during lunch and dinner time)
    peak_hours = [11, 12, 13, 18, 19, 20]  # Lunch and dinner hours
    off_peak_hours = [9, 10, 14, 15, 16, 17, 21]  # Other business hours
    
    # 70% chance to be during peak hours
    if random.random() < 0.7:
        hour = random.choice(peak_hours)
    else:
        hour = random.choice(off_peak_hours)
    
    minutes = random.randint(0, 59)
    seconds = random.randint(0, 59)
    
    return random_date.replace(hour=hour, minute=minutes, second=seconds)

def generate_order_items(items: List[models.Item], min_items=1, max_items=5):
    """Generate a random selection of order items with quantities"""
    
    # If there are fewer than min_items, use all available items
    if len(items) < min_items:
        selected_count = len(items)
    else:
        # Select a random number of unique items between min_items and max_items
        selected_count = min(random.randint(min_items, max_items), len(items))
    
    # Randomly select items without replacement
    selected_items = random.sample(items, selected_count)
    
    order_items = []
    for item in selected_items:
        # Most items have quantity 1, but sometimes more
        quantity = 1
        if random.random() < 0.25:  # 25% chance for multiple items
            quantity = random.randint(2, 5)
        
        order_items.append({
            "item": item,
            "quantity": quantity,
            "unit_price": item.current_price
        })
    
    return order_items

def create_test_order(db: Session, user_id: int, order_date: datetime, order_items: List[Dict[str, Any]]):
    """Create a test order with the given items"""
    
    # Calculate total amount
    total_amount = sum(item["quantity"] * item["unit_price"] for item in order_items)
    
    # Create order
    new_order = models.Order(
        order_date=order_date,
        total_amount=total_amount,
        user_id=user_id,
        pos_id=f"test-{str(uuid.uuid4())[:8]}",
        created_at=order_date,
        updated_at=order_date
    )
    
    db.add(new_order)
    db.flush()  # Flush to get the order ID
    
    # Create order items
    for item_data in order_items:
        order_item = models.OrderItem(
            order_id=new_order.id,
            item_id=item_data["item"].id,
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"]
        )
        db.add(order_item)
    
    return new_order

def seed_test_orders(user_id: int, months: int = 12, orders_per_month_avg: int = 30):
    """
    Generate test orders for a user over a specified period
    
    Args:
        user_id: The user ID to generate orders for
        months: Number of months to go back from today
        orders_per_month_avg: Average number of orders to generate per month
    """
    logger.info(f"Generating test orders for user {user_id} over {months} months")
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30 * months)
    
    logger.info(f"Date range: {start_date.date()} to {end_date.date()}")
    
    db = SessionLocal()
    try:
        # Get user's menu items
        items = get_user_items(db, user_id)
        
        if not items:
            logger.error(f"No menu items found for user {user_id}. Cannot generate orders.")
            return
        
        # Determine total number of orders to create
        # Add some variability to the orders per month (±20%)
        total_orders = 0
        monthly_orders = []
        
        for i in range(months):
            variance_factor = random.uniform(0.8, 1.2)  # ±20% variance
            month_orders = int(orders_per_month_avg * variance_factor)
            monthly_orders.append(month_orders)
            total_orders += month_orders
        
        logger.info(f"Will generate approximately {total_orders} orders in total")
        
        # Create orders month by month to ensure proper distribution
        for month in range(months):
            month_start = start_date + timedelta(days=30 * month)
            month_end = month_start + timedelta(days=30)
            
            if month_end > end_date:
                month_end = end_date
                
            num_orders = monthly_orders[month]
            
            logger.info(f"Generating {num_orders} orders for month {month+1} ({month_start.strftime('%Y-%m')})")
            
            for _ in range(num_orders):
                # Generate order date within the month
                order_date = generate_order_date(month_start, month_end)
                
                # Generate order items
                order_items = generate_order_items(items)
                
                # Create the order
                create_test_order(db, user_id, order_date, order_items)
                
        # Commit all changes
        db.commit()
        logger.info(f"Successfully generated {total_orders} test orders for user {user_id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating test orders: {str(e)}")
    finally:
        db.close()

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python seed_test_orders.py USER_ID [MONTHS] [ORDERS_PER_MONTH]")
        sys.exit(1)
    
    user_id = int(sys.argv[1])
    
    months = 12  # Default
    if len(sys.argv) > 2:
        months = int(sys.argv[2])
    
    orders_per_month = 30  # Default
    if len(sys.argv) > 3:
        orders_per_month = int(sys.argv[3])
    
    seed_test_orders(user_id, months, orders_per_month)

if __name__ == "__main__":
    main()
