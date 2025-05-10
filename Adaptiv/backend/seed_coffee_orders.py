"""
Script to seed a full year of realistic coffee shop order data for the Adaptiv Pricing app.
This generates data with realistic seasonal, weekly, and intraday patterns.
"""

import sys
import os
import random
import datetime
import math
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
NUM_DAYS = 365  # Generate orders for a full year
MIN_ORDERS_PER_DAY = 100
MAX_ORDERS_PER_DAY = 300
MIN_ITEMS_PER_ORDER = 1
MAX_ITEMS_PER_ORDER = 4
MIN_QUANTITY_PER_ITEM = 1
MAX_QUANTITY_PER_ITEM = 2

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
    22: 10,
    # Late night & early morning
    23: 5, 
    0: 0,
    1: 0,
    2: 0,
    3: 0,
    4: 0,
    5: 10  # Early risers
}

# Seasonal patterns - multiplier by month
MONTH_WEIGHTS = {
    1: 0.75,   # January - Post-holiday slump
    2: 0.80,   # February
    3: 0.90,   # March
    4: 1.00,   # April - Spring boost
    5: 1.05,   # May
    6: 1.10,   # June - Summer begins
    7: 1.05,   # July - Hot summer
    8: 1.00,   # August
    9: 1.15,   # September - Back to school/work
    10: 1.10,  # October - Fall flavors
    11: 1.20,  # November - Holiday season begins
    12: 1.30   # December - Peak holiday season
}

# Day of week patterns - multiplier by day
DAY_WEIGHTS = {
    0: 1.10,  # Monday
    1: 1.05,  # Tuesday
    2: 1.00,  # Wednesday
    3: 1.05,  # Thursday
    4: 1.15,  # Friday
    5: 1.25,  # Saturday
    6: 1.20   # Sunday
}

# Coffee shop item category popularity by time of day
CATEGORY_TIME_WEIGHTS = {
    # Category: {hour: weight}
    "Hot Drinks": {
        6: 90, 7: 100, 8: 100, 9: 90, 10: 80, 
        11: 70, 12: 60, 13: 60, 14: 70, 
        15: 70, 16: 60, 17: 50, 
        18: 40, 19: 40, 20: 30, 21: 30, 22: 20,
        23: 10, 0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 80
    },
    "Cold Drinks": {
        6: 20, 7: 30, 8: 30, 9: 40, 10: 60, 
        11: 70, 12: 80, 13: 90, 14: 100, 
        15: 100, 16: 90, 17: 80, 
        18: 70, 19: 60, 20: 50, 21: 40, 22: 30,
        23: 10, 0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 10
    },
    "Bakery": {
        6: 70, 7: 100, 8: 100, 9: 90, 10: 80, 
        11: 70, 12: 90, 13: 70, 14: 60, 
        15: 50, 16: 40, 17: 40, 
        18: 30, 19: 30, 20: 20, 21: 20, 22: 10,
        23: 5, 0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 50
    },
    "Specialty Drinks": {
        6: 30, 7: 40, 8: 50, 9: 70, 10: 80, 
        11: 70, 12: 50, 13: 60, 14: 70, 
        15: 80, 16: 90, 17: 100, 
        18: 90, 19: 80, 20: 70, 21: 60, 22: 30,
        23: 10, 0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 20
    }
}

# Seasonal item popularity
SEASONAL_ITEM_BOOSTS = {
    # "Item name": {month: boost_factor}
    "Pumpkin Spice Latte": {9: 3.0, 10: 5.0, 11: 4.0, 12: 2.0},  # Fall months
    "Hot Chocolate": {11: 2.0, 12: 3.0, 1: 3.0, 2: 2.5},  # Winter months
    "Iced Coffee": {5: 2.0, 6: 3.0, 7: 4.0, 8: 3.0},  # Summer months
    "Cold Brew": {5: 2.0, 6: 3.0, 7: 4.0, 8: 3.0},  # Summer months
    "Nitro Cold Brew": {5: 2.0, 6: 3.0, 7: 3.5, 8: 3.0},  # Summer months
    "Frappuccino": {5: 2.0, 6: 3.0, 7: 4.0, 8: 3.0},  # Summer months
    "Matcha Latte": {3: 1.5, 4: 2.0, 5: 2.0}  # Spring months
}

def get_biased_time(date, bias_weights=HOUR_WEIGHTS):
    """Generate a time with a bias towards certain hours based on weights"""
    # Convert weights to a probability distribution
    total_weight = sum(bias_weights.values())
    hour_probs = {hour: weight/total_weight for hour, weight in bias_weights.items()}
    
    # Choose an hour based on the probability distribution
    hour_choice = random.choices(
        list(hour_probs.keys()), 
        weights=list(hour_probs.values()), 
        k=1
    )[0]
    
    # Random minute and second
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    
    return datetime.datetime.combine(date, datetime.time(hour_choice, minute, second))

def get_item_probability(item, current_datetime):
    """Calculate the probability of an item being ordered based on time, season, and category"""
    hour = current_datetime.hour
    month = current_datetime.month
    base_probability = 1.0
    
    # Apply category time-of-day weighting
    if item.category in CATEGORY_TIME_WEIGHTS:
        category_time_weight = CATEGORY_TIME_WEIGHTS[item.category][hour] / 100.0
        base_probability *= category_time_weight
    
    # Apply seasonal item boosts
    if item.name in SEASONAL_ITEM_BOOSTS and month in SEASONAL_ITEM_BOOSTS[item.name]:
        seasonal_boost = SEASONAL_ITEM_BOOSTS[item.name][month]
        base_probability *= seasonal_boost
    
    return base_probability

def select_items_for_order(all_items, order_time, num_items):
    """Select items with probability based on time of day and seasonal factors"""
    # Calculate probabilities for each item
    item_probs = [get_item_probability(item, order_time) for item in all_items]
    
    # Ensure probabilities sum to 1
    total_prob = sum(item_probs)
    normalized_probs = [p/total_prob for p in item_probs]
    
    # Select items based on probabilities
    selected_indices = random.choices(
        range(len(all_items)), 
        weights=normalized_probs, 
        k=min(num_items, len(all_items))
    )
    
    # Ensure no duplicates
    selected_indices = list(set(selected_indices))
    
    # If we lost items due to duplicate removal, add more
    while len(selected_indices) < num_items and len(selected_indices) < len(all_items):
        new_index = random.choices(
            range(len(all_items)), 
            weights=normalized_probs, 
            k=1
        )[0]
        if new_index not in selected_indices:
            selected_indices.append(new_index)
    
    return [all_items[i] for i in selected_indices]

def generate_orders(db_session, num_days=NUM_DAYS):
    """Generate a full year of orders with realistic patterns"""
    
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
    
    # For each day in the range
    for day_offset in range(num_days, 0, -1):
        current_date = today - datetime.timedelta(days=day_offset)
        
        # Apply seasonal and day of week factors
        month_factor = MONTH_WEIGHTS.get(current_date.month, 1.0)
        day_factor = DAY_WEIGHTS.get(current_date.weekday(), 1.0)
        daily_factor = month_factor * day_factor
        
        # Random number of orders for this day, influenced by all factors
        num_orders = random.randint(
            int(MIN_ORDERS_PER_DAY * daily_factor * 0.9),
            int(MAX_ORDERS_PER_DAY * daily_factor * 1.1)
        )
        
        logger.info(f"Generating {num_orders} orders for {current_date} (factors: month={month_factor}, day={day_factor})")
        
        # Create orders for this day
        for _ in range(num_orders):
            # Generate order time with realistic pattern
            order_time = get_biased_time(current_date)
            
            # Create order
            new_order = Order(
                order_date=order_time,
                total_amount=0,  # Will calculate after adding items
                created_at=order_time
            )
            db_session.add(new_order)
            db_session.flush()  # Get the order ID
            
            # Random number of different items in this order
            # People tend to order fewer items per order during busy hours
            hour_business_factor = HOUR_WEIGHTS[order_time.hour] / 100.0
            max_items_adjusted = max(1, int(MAX_ITEMS_PER_ORDER * (1.5 - hour_business_factor)))
            num_items = random.randint(MIN_ITEMS_PER_ORDER, max_items_adjusted)
            
            # Select items based on time-of-day and seasonal preferences
            selected_items = select_items_for_order(items, order_time, num_items)
            
            # If we don't have enough items, adjust
            if not selected_items:
                logger.warning(f"No items selected for order at {order_time}, using random selection")
                selected_items = random.sample(items, min(num_items, len(items)))
            
            total_amount = 0
            
            # Add items to the order
            for item in selected_items:
                # Random quantity, with time-of-day influence
                # During rush hours, people tend to order simpler (fewer items)
                max_quantity_adjusted = max(1, int(MAX_QUANTITY_PER_ITEM * (1.2 - hour_business_factor)))
                quantity = random.randint(MIN_QUANTITY_PER_ITEM, max_quantity_adjusted)
                
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
            
            # Commit every 1000 orders to avoid huge transactions
            if total_orders % 1000 == 0:
                db_session.commit()
                logger.info(f"Committed {total_orders} orders so far")
    
    # Final commit
    db_session.commit()
    logger.info(f"Successfully generated {total_orders} orders across {num_days} days")
    return True

def main():
    """Main function to seed orders"""
    try:
        # Get db session
        db = next(get_db())
        
        # Generate coffee shop orders
        generate_orders(db)
        
        logger.info("Order data generation completed successfully")
    except Exception as e:
        logger.error(f"Error generating orders: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    return True

if __name__ == "__main__":
    main()
