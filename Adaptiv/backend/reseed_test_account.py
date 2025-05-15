#!/usr/bin/env python3
"""
Re-seed script for testprofessional@test.com account on Render

This script:
1. Clears existing order data and price history for testprofessional@test.com
2. Re-seeds with new data that properly reflects price changes and sales patterns
3. Updates COGS data to match the current model

Use this script to refresh the test account data after making structural changes
to the application logic.
"""

import sys
import os
import random
import datetime
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, delete
from sqlalchemy.sql import text
from models import Base, Item, PriceHistory, User, Order, OrderItem, COGS, ActionItem
from database import get_db
from action_items import seed_default_action_items

# Adding this helper function to replace relativedelta functionality
def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
    return sourcedate.replace(year=year, month=month, day=day)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants for price change generation
NUM_PRICE_CHANGES_PER_ITEM = 12  # Increased to cover a full year (approximately monthly)
MAX_PRICE_CHANGE_PERCENT = 0.20  # Maximum price change of 20% up or down
BASE_ELASTICITY = -1.5  # Base elasticity for simulation (negative as price increases lower demand)
ELASTICITY_VARIANCE = 0.7  # Increased variance to create more realistic patterns
DAYS_BETWEEN_PRICE_CHANGES = 30  # Monthly changes
ORDER_VARIANCE_PCT = 0.3  # Variance in order quantities (30% up or down)
MIN_ORDERS_PER_PERIOD = 12  # Minimum number of orders in each price period
MAX_ORDERS_PER_PERIOD = 25  # Maximum number of orders in each price period
# Additional constants for daily orders
DAILY_ORDERS_PER_MONTH = 90  # Approximately 3 orders per day
RECENT_DAYS_WITH_MORE_ORDERS = 7  # Last 7 days will have more orders

# Target email
TARGET_EMAIL = "testprofessional@test.com"

def get_test_user(db: Session):
    """Get the test professional user"""
    test_user = db.query(User).filter(User.email == TARGET_EMAIL).first()
    
    if not test_user:
        logger.error(f"Test user {TARGET_EMAIL} not found! Please ensure this user exists before reseeding.")
        sys.exit(1)
    
    return test_user

def clear_existing_data(db: Session, user_id: int):
    """Clear existing orders, price history, COGS data, and action items for this user"""
    logger.info(f"Clearing existing data for user ID {user_id}")
    
    # Get all items for this user to identify related orders
    items = db.query(Item).filter(Item.user_id == user_id).all()
    item_ids = [item.id for item in items]
    
    if not items:
        logger.error(f"No items found for user {user_id}. Cannot proceed with reseeding.")
        sys.exit(1)
    
    logger.info(f"Found {len(items)} items for user {user_id}")
    
    # Delete order items first (foreign key constraints)
    order_items_deleted = db.query(OrderItem).filter(
        OrderItem.item_id.in_(item_ids)
    ).delete(synchronize_session=False)
    
    logger.info(f"Deleted {order_items_deleted} order items")
    
    # Find orders that belong to this user
    orders = db.query(Order).filter(Order.user_id == user_id).all()
    order_ids = [order.id for order in orders]
    
    # Delete orders
    orders_deleted = db.query(Order).filter(
        Order.id.in_(order_ids)
    ).delete(synchronize_session=False)
    
    logger.info(f"Deleted {orders_deleted} orders")
    
    # Delete price history
    price_history_deleted = db.query(PriceHistory).filter(
        PriceHistory.user_id == user_id
    ).delete(synchronize_session=False)
    
    logger.info(f"Deleted {price_history_deleted} price history records")
    
    # Delete COGS data
    cogs_deleted = db.query(COGS).filter(
        COGS.user_id == user_id
    ).delete(synchronize_session=False)
    
    logger.info(f"Deleted {cogs_deleted} COGS records")
    
    # Delete existing action items
    action_items_deleted = db.query(ActionItem).filter(
        ActionItem.user_id == user_id
    ).delete(synchronize_session=False)
    
    logger.info(f"Deleted {action_items_deleted} action items")
    
    # Commit the deletions
    db.commit()
    logger.info("Successfully cleared existing data")

def create_price_history_with_orders(db: Session, user_id: int):
    """Create comprehensive price history with corresponding orders for a full year including today"""
    logger.info(f"Creating new price history and orders for user {user_id}")
    
    # Get all items for this user
    items = db.query(Item).filter(Item.user_id == user_id).all()
    
    # Define the date range - exactly 1 year back from today including today
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=365)
    
    logger.info(f"Creating data from {start_date.date()} to {end_date.date()}, covering a full year")
    
    # Keeping track of all orders created to ensure even distribution
    all_item_orders = []
    
    # For each item, create a series of price changes and corresponding orders
    for item in items:
        # Generate a unique elasticity value for this item
        item_elasticity = BASE_ELASTICITY + (random.random() * ELASTICITY_VARIANCE - ELASTICITY_VARIANCE/2)
        logger.info(f"Creating price history for item: {item.name} (ID: {item.id}) with elasticity {item_elasticity:.2f}")
        
        # Start from current price
        current_price = item.current_price
        
        # Price at the beginning of our history (work backwards from current)
        # Create some randomness by starting with a different price
        initial_price = current_price * (1 + random.uniform(-0.15, 0.15))
        initial_price = round(initial_price, 2)
        
        # Track price changes
        price_changes = []
        
        # Create the sequence of monthly price changes for the full year
        price = initial_price
        for i in range(NUM_PRICE_CHANGES_PER_ITEM):
            change_pct = random.uniform(-MAX_PRICE_CHANGE_PERCENT, MAX_PRICE_CHANGE_PERCENT)
            new_price = round(price * (1 + change_pct), 2)
            
            # For the last change, make sure it ends at the current price
            if i == NUM_PRICE_CHANGES_PER_ITEM - 1:
                new_price = current_price
            
            # Calculate change date - distribute evenly over the year
            month_offset = i * 30  # Approx 30 days per month
            change_date = start_date + datetime.timedelta(days=month_offset)
            
            # Ensure we don't go beyond today
            if change_date > end_date:
                change_date = end_date - datetime.timedelta(days=random.randint(1, 7))
            
            price_changes.append({
                "date": change_date,
                "old_price": price,
                "new_price": new_price
            })
            
            price = new_price
        
        # Now create price history records and corresponding orders
        for i, change in enumerate(price_changes):
            # Skip the first one as it doesn't have a previous price
            if i == 0:
                continue
                
            # Create price history record
            price_history = PriceHistory(
                item_id=item.id,
                user_id=user_id,
                previous_price=change["old_price"],
                new_price=change["new_price"],
                change_reason=random.choice([
                    "Cost increase", 
                    "Competitive adjustment", 
                    "Seasonal adjustment",
                    "Demand-based pricing",
                    "Promotion"
                ]),
                changed_at=change["date"]
            )
            db.add(price_history)
            
            # Create orders for the period after this price change
            # Find the date range for this price period
            start_period = change["date"]
            
            # End period is either the next price change or today
            end_period = None
            if i < len(price_changes) - 1:
                end_period = price_changes[i+1]["date"]
            else:
                end_period = end_date
            
            # Duration of this price period in days
            period_days = (end_period - start_period).days
            if period_days <= 0:
                continue
                
            # Create a number of orders during this period
            num_orders = random.randint(MIN_ORDERS_PER_PERIOD, MAX_ORDERS_PER_PERIOD)
            
            # Expected quantity based on elasticity and price change
            if i > 0:
                # Calculate percentage change in price
                prev_price = price_changes[i-1]["new_price"]
                current_price = change["new_price"]
                price_pct_change = (current_price - prev_price) / prev_price
                
                # Apply elasticity to determine quantity change
                # (elasticity is negative, so price increase reduces quantity)
                qty_pct_change = price_pct_change * item_elasticity
                
                # Base quantity with randomness
                base_quantity = random.randint(5, 20) * (1 + qty_pct_change)
            else:
                # Base quantity for first price period
                base_quantity = random.randint(5, 20)
                
            # Ensure base quantity is positive
            base_quantity = max(1, base_quantity)
            
            # Create orders spread throughout the period
            for j in range(num_orders):
                # Randomly select a date within this period
                days_offset = random.randint(0, period_days)
                order_date = start_period + datetime.timedelta(days=days_offset)
                
                # Track all orders created
                all_item_orders.append({
                    "item_id": item.id,
                    "date": order_date,
                    "price": change["new_price"],
                    "base_quantity": base_quantity
                })
                
                # Create a new order or find an existing one on this date
                existing_order = db.query(Order).filter(
                    Order.user_id == user_id,
                    func.date(Order.order_date) == func.date(order_date)
                ).first()
                
                if existing_order:
                    order = existing_order
                else:
                    order = Order(
                        user_id=user_id,
                        order_date=order_date,
                        total_amount=0.0
                    )
                    db.add(order)
                    db.flush()
                
                # Apply some randomness to the quantity
                quantity = int(base_quantity * (1 + random.uniform(-ORDER_VARIANCE_PCT, ORDER_VARIANCE_PCT)))
                quantity = max(1, quantity)  # Ensure at least 1 unit
                
                # Create order item
                order_item = OrderItem(
                    order_id=order.id,
                    item_id=item.id,
                    quantity=quantity,
                    unit_price=change["new_price"]
                )
                db.add(order_item)
                
                # Subtotal is automatically calculated
                subtotal = order_item.subtotal
                
                # Update order total
                order.total_amount = subtotal
    
    # Now ensure we have orders for EVERY day in the last week
    # This is crucial to make the dashboard show recent data
    logger.info("Ensuring every day in the last week has orders...")
    
    # Get the last 7 days
    today = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    last_week_dates = [today - datetime.timedelta(days=i) for i in range(7)]
    
    # Check which days have orders
    for day in last_week_dates:
        day_start = day
        day_end = day + datetime.timedelta(days=1)
        
        # Check if we have orders for this day
        existing_orders = db.query(func.count(Order.id)).filter(
            Order.user_id == user_id,
            Order.order_date >= day_start,
            Order.order_date < day_end
        ).scalar()
        
        # If no orders, create some
        if existing_orders < 3:  # Ensure at least 3 orders per day
            logger.info(f"Adding orders for {day.date()} which had {existing_orders} orders")
            
            # Create 3-5 orders for this day
            for _ in range(random.randint(3, 5)):
                # Random time during the day
                hour = random.randint(8, 21)  # Between 8am and 9pm
                minute = random.randint(0, 59)
                order_time = day.replace(hour=hour, minute=minute)
                
                # Create a new order
                order = Order(
                    user_id=user_id,
                    order_date=order_time,
                    total_amount=0.0
                )
                db.add(order)
                db.flush()
                
                # Add 1-3 random items to this order
                num_items = random.randint(1, 3)
                random_items = random.sample(items, min(num_items, len(items)))
                
                order_total = 0.0
                for item in random_items:
                    quantity = random.randint(1, 3)
                    
                    order_item = OrderItem(
                        order_id=order.id,
                        item_id=item.id,
                        quantity=quantity,
                        unit_price=item.current_price
                    )
                    db.add(order_item)
                    
                    # Add to order total
                    order_total += order_item.subtotal
                
                # Update order total
                order.total_amount = order_total
    
    # Commit all changes
    db.commit()
    logger.info("Successfully created price history and orders")

def create_cogs_data(db: Session, user_id: int):
    """Create COGS data for the test user"""
    logger.info(f"Creating COGS data for user {user_id}")
    
    # Generate 52 weeks of historical data
    cogs_data = []
    
    # Current week (don't seed this to allow the user to enter it themselves)
    end_date = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # Go back to the previous Sunday
    while end_date.weekday() != 6:  # Sunday is 6
        end_date = end_date - datetime.timedelta(days=1)
    
    # Start 52 weeks ago
    start_date = end_date - datetime.timedelta(weeks=52)
    current_date = start_date
    
    # Get all items for this user to calculate reasonable COGS values
    items = db.query(Item).filter(Item.user_id == user_id).all()
    
    # Calculate average item cost
    total_cost = sum([item.cost for item in items if item.cost is not None])
    total_price = sum([item.current_price for item in items])
    avg_cost_ratio = total_cost / total_price if total_price > 0 else 0.6
    
    # Generate weekly COGS data
    week_number = 1
    while current_date < end_date:
        # Get orders for this week
        week_start = current_date
        week_end = current_date + datetime.timedelta(days=7)
        
        # Query to get total sales for this week
        total_sales = db.query(func.sum(Order.total_amount)).filter(
            Order.user_id == user_id,
            Order.order_date >= week_start,
            Order.order_date < week_end
        ).scalar() or 0
        
        # Calculate COGS based on sales
        cogs_value = round(total_sales * avg_cost_ratio, 2)
        
        # Add some randomness to COGS
        cogs_value = cogs_value * (1 + random.uniform(-0.1, 0.1))
        
        # Create COGS record
        cogs = COGS(
            user_id=user_id,
            week_start_date=week_start,
            week_end_date=week_end,
            amount=cogs_value
        )
        db.add(cogs)
        
        # Move to next week
        current_date = week_end
        week_number += 1
    
    # Commit COGS data
    db.commit()
    logger.info(f"Successfully created {week_number-1} weeks of COGS data")

def create_action_items(db: Session, user_id: int):
    """Create action items (to-dos) for the test user"""
    logger.info(f"Creating action items for user {user_id}")
    
    # First, use the built-in seed function to add default action items
    seed_default_action_items(user_id, db)
    
    # Add some additional action items specific to the test account
    additional_items = [
        ActionItem(
            user_id=user_id,
            title="Review price elasticity on bestsellers",
            description="Analyze price elasticity for your top 5 bestselling items to optimize pricing",
            priority="high",
            action_type="analysis",
            status="pending"
        ),
        ActionItem(
            user_id=user_id,
            title="Set up competitor price alerts",
            description="Configure alerts for when competitor prices change significantly",
            priority="medium",
            action_type="configuration",
            status="pending"
        ),
        ActionItem(
            user_id=user_id,
            title="Update seasonal menu items",
            description="Add new seasonal items to your menu as the season changes",
            priority="medium",
            action_type="data_entry",
            status="pending"
        ),
        ActionItem(
            user_id=user_id,
            title="Analyze weekly profit margins",
            description="Review the profit margin trends from the last 4 weeks and identify improvement opportunities",
            priority="medium",
            action_type="analysis",
            status="in_progress"
        )
    ]
    
    for item in additional_items:
        db.add(item)
    
    db.commit()
    logger.info(f"Successfully created action items for user {user_id}")


def main():
    """Main function to reseed the test account"""
    logger.info(f"Starting reseed process for {TARGET_EMAIL}")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get test user
        test_user = get_test_user(db)
        user_id = test_user.id
        
        # Clear existing data
        clear_existing_data(db, user_id)
        
        # Create new price history with orders
        create_price_history_with_orders(db, user_id)
        
        # Create COGS data
        create_cogs_data(db, user_id)
        
        # Create action items (to-dos)
        create_action_items(db, user_id)
        
        logger.info(f"Reseeding completed successfully for {TARGET_EMAIL}")
    except Exception as e:
        logger.error(f"Error during reseeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
