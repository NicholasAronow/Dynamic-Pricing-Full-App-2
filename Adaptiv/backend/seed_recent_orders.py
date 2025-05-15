"""
Script to seed recent order data for May 9-14, 2025 for the Adaptiv Pricing app.
This ensures we have fresh data to display in the dashboard.
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
MIN_ORDERS_PER_DAY = 150
MAX_ORDERS_PER_DAY = 350
MIN_ITEMS_PER_ORDER = 1
MAX_ITEMS_PER_ORDER = 4
MIN_QUANTITY_PER_ITEM = 1
MAX_QUANTITY_PER_ITEM = 3

# Weights for different order patterns
HOUR_WEIGHTS = {
    # Morning rush 6-10am
    6: 30,
    7: 80,
    8: 100,  # Peak morning hour
    9: 90,
    10: 70,
    # Mid-day 11am-2pm
    11: 60,
    12: 80,  # Lunch hour
    13: 70,
    14: 50,
    # Afternoon 3-5pm
    15: 40,
    16: 50,
    17: 60,
    # Evening 6-9pm
    18: 50,
    19: 40,
    20: 30,
    21: 20,
    # Other hours (lower traffic)
    0: 5,
    1: 2,
    2: 1,
    3: 1,
    4: 2,
    5: 10,
    22: 10,
    23: 5
}

# Day of week weights (0=Monday, 6=Sunday)
DAY_WEIGHTS = {
    0: 0.9,  # Monday
    1: 0.85, # Tuesday
    2: 0.9,  # Wednesday
    3: 0.95, # Thursday
    4: 1.1,  # Friday
    5: 1.3,  # Saturday
    6: 1.2   # Sunday
}

def get_biased_time(date, bias_weights=HOUR_WEIGHTS):
    """Generate a time with a bias towards certain hours based on weights"""
    # Convert weights to a cumulative distribution
    total_weight = sum(bias_weights.values())
    normalized_weights = {hour: weight / total_weight for hour, weight in bias_weights.items()}
    
    # Build cumulative distribution
    cumulative = 0
    cumulative_distribution = {}
    for hour, weight in normalized_weights.items():
        cumulative += weight
        cumulative_distribution[hour] = cumulative
    
    # Select an hour based on the distribution
    r = random.random()
    selected_hour = 0
    for hour, cumulative_prob in cumulative_distribution.items():
        if r <= cumulative_prob:
            selected_hour = hour
            break
    
    # Generate random minute and second
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    
    return datetime.datetime.combine(date, datetime.time(selected_hour, minute, second))

def select_items_for_order(all_items, num_items):
    """Select random items for an order"""
    if num_items >= len(all_items):
        return all_items
    return random.sample(all_items, num_items)

def generate_recent_orders(db_session, start_date_str, end_date_str):
    """Generate orders for a specific date range"""
    
    # Parse date strings
    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    # Get all items from the database
    items = db_session.query(Item).all()
    if not items:
        logger.error("No items found in the database. Please seed items first.")
        return False
    
    # Check if we have items to create orders for
    item_count = db_session.query(Item).count()
    logger.info(f"Found {item_count} items in the database")
    
    # Calculate days in range (inclusive)
    days_delta = (end_date - start_date).days + 1
    logger.info(f"Generating orders for {days_delta} days from {start_date} to {end_date}")
    
    # Delete existing orders in this date range to avoid duplication
    # First get IDs of orders in this range
    orders_in_range = db_session.query(Order).filter(
        Order.order_date >= datetime.datetime.combine(start_date, datetime.time.min),
        Order.order_date <= datetime.datetime.combine(end_date, datetime.time.max)
    ).all()
    
    order_ids = [order.id for order in orders_in_range]
    
    if order_ids:
        # Delete related order items first
        db_session.query(OrderItem).filter(OrderItem.order_id.in_(order_ids)).delete(synchronize_session=False)
        # Then delete the orders
        db_session.query(Order).filter(Order.id.in_(order_ids)).delete(synchronize_session=False)
        db_session.commit()
        logger.info(f"Deleted {len(order_ids)} existing orders in the date range")
    
    total_orders = 0
    current_date = start_date
    
    # For each day in the range
    while current_date <= end_date:
        # Apply day of week factors
        day_factor = DAY_WEIGHTS.get(current_date.weekday(), 1.0)
        
        # Random number of orders for this day, influenced by all factors
        num_orders = random.randint(
            int(MIN_ORDERS_PER_DAY * day_factor * 0.9),
            int(MAX_ORDERS_PER_DAY * day_factor * 1.1)
        )
        
        logger.info(f"Generating {num_orders} orders for {current_date} (day factor={day_factor})")
        
        # Create orders for this day
        for _ in range(num_orders):
            # Generate order time with realistic pattern
            order_time = get_biased_time(current_date)
            
            # Create order and link to testprofessional@test.com account (user_id=1)
            new_order = Order(
                order_date=order_time,
                total_amount=0,  # Will calculate after adding items
                created_at=order_time,
                user_id=1  # testprofessional@test.com account
            )
            db_session.add(new_order)
            db_session.flush()  # Get the order ID
            
            # Random number of different items in this order
            # People tend to order fewer items per order during busy hours
            hour_business_factor = HOUR_WEIGHTS[order_time.hour] / 100.0
            max_items_adjusted = max(1, int(MAX_ITEMS_PER_ORDER * (1.5 - hour_business_factor)))
            num_items = random.randint(MIN_ITEMS_PER_ORDER, max_items_adjusted)
            
            # Select random items for this order
            selected_items = select_items_for_order(items, num_items)
            
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
        
        # Move to next day
        current_date += datetime.timedelta(days=1)
        
        # Commit orders for this day
        db_session.commit()
        logger.info(f"Committed orders for {current_date - datetime.timedelta(days=1)}")
    
    logger.info(f"Finished generating {total_orders} orders from {start_date} to {end_date}")
    return True

def main():
    # Connect to the database
    try:
        db = next(get_db())
        
        # May 9 to May 14, 2025
        start_date = "2025-05-09"
        end_date = "2025-05-14"
        
        # Generate orders for the specified date range
        success = generate_recent_orders(db, start_date, end_date)
        
        if success:
            logger.info("Successfully generated recent orders")
        else:
            logger.error("Failed to generate recent orders")
            
    except Exception as e:
        logger.error(f"Error seeding recent orders: {e}")
        
if __name__ == "__main__":
    main()
