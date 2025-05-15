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
NUM_PRICE_CHANGES_PER_ITEM = 8  # Increased from 7 to ensure enough data for elasticity
MAX_PRICE_CHANGE_PERCENT = 0.20  # Maximum price change of 20% up or down
BASE_ELASTICITY = -1.5  # Base elasticity for simulation (negative as price increases lower demand)
ELASTICITY_VARIANCE = 0.7  # Increased variance to create more realistic patterns
DAYS_BETWEEN_PRICE_CHANGES = 28  # Approximately monthly changes
ORDER_VARIANCE_PCT = 0.3  # Variance in order quantities (30% up or down)
MIN_ORDERS_PER_PERIOD = 12  # Minimum number of orders in each price period
MAX_ORDERS_PER_PERIOD = 25  # Maximum number of orders in each price period

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
    """Create comprehensive price history with corresponding orders"""
    logger.info(f"Creating new price history and orders for user {user_id}")
    
    # Get all items for this user
    items = db.query(Item).filter(Item.user_id == user_id).all()
    
    # For each item, create a series of price changes and corresponding orders
    for item in items:
        # Generate a unique elasticity value for this item
        item_elasticity = BASE_ELASTICITY + (random.random() * ELASTICITY_VARIANCE - ELASTICITY_VARIANCE/2)
        logger.info(f"Creating price history for item: {item.name} (ID: {item.id}) with elasticity {item_elasticity:.2f}")
        
        # Start from current price
        current_price = item.current_price
        
        # Create orders and price changes going back approximately 8 months
        # Most recent change was 7 days ago
        change_date = datetime.datetime.now() - datetime.timedelta(days=7)
        start_date = change_date - datetime.timedelta(days=DAYS_BETWEEN_PRICE_CHANGES * NUM_PRICE_CHANGES_PER_ITEM)
        
        # Price at the beginning of our history (work backwards from current)
        # Create some randomness by starting with a different price
        initial_price = current_price * (1 + random.uniform(-0.15, 0.15))
        initial_price = round(initial_price, 2)
        
        # Track price changes
        price_changes = []
        
        # Create the sequence of price changes
        price = initial_price
        for i in range(NUM_PRICE_CHANGES_PER_ITEM):
            change_pct = random.uniform(-MAX_PRICE_CHANGE_PERCENT, MAX_PRICE_CHANGE_PERCENT)
            new_price = round(price * (1 + change_pct), 2)
            
            # For the last change, make sure it ends at the current price
            if i == NUM_PRICE_CHANGES_PER_ITEM - 1:
                new_price = current_price
            
            # Calculate change date
            change_date = start_date + datetime.timedelta(days=DAYS_BETWEEN_PRICE_CHANGES * i)
            
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
                    "Seasonal adjustment", 
                    "Competitive pricing", 
                    "Promotion", 
                    "Demand optimization"
                ]),
                changed_at=change["date"]
            )
            
            db.add(price_history)
            
            # Create orders for the period between this change and the previous one
            start = price_changes[i-1]["date"]
            end = change["date"]
            price = price_changes[i-1]["new_price"]  # Price during this period
            
            # Number of orders during this period
            num_orders = random.randint(MIN_ORDERS_PER_PERIOD, MAX_ORDERS_PER_PERIOD)
            
            # Base quantity affected by elasticity
            # Calculate a base quantity that seems reasonable for the item
            base_quantity = int(300 / price)  # Higher priced items sell fewer units
            base_quantity = max(5, min(50, base_quantity))  # Between 5 and 50 units
            
            # Calculate actual quantity based on elasticity and price change (if not first period)
            if i > 1:
                prev_price = price_changes[i-2]["new_price"]
                price_ratio = price / prev_price
                # Apply elasticity formula: quantity_change = price_change^elasticity
                quantity_modifier = price_ratio ** item_elasticity
                base_quantity = int(base_quantity * quantity_modifier)
            
            # Create orders spread throughout the period
            period_days = (end - start).days
            for j in range(num_orders):
                # Random date within the period
                days_offset = random.randint(0, period_days)
                order_date = start + datetime.timedelta(days=days_offset)
                
                # Create order
                order = Order(
                    user_id=user_id,
                    order_date=order_date,
                    total_amount=0  # Will update after adding items
                )
                db.add(order)
                db.flush()  # To get the order ID
                
                # Add variance to quantity
                quantity = int(base_quantity * (1 + random.uniform(-ORDER_VARIANCE_PCT, ORDER_VARIANCE_PCT)))
                quantity = max(1, quantity)  # Ensure at least 1 unit
                
                # Create order item
                order_item = OrderItem(
                    order_id=order.id,
                    item_id=item.id,
                    quantity=quantity,
                    unit_price=price
                )
                db.add(order_item)
                
                # Subtotal is automatically calculated
                subtotal = order_item.subtotal
                
                # Update order total
                order.total_amount = subtotal
    
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
