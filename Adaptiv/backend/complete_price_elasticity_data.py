"""
Script to ensure complete price history and order data for elasticity calculations.
This script:
1. Ensures each item has at least 5 price changes for accurate elasticity calculation
2. Generates order data that reflects expected elasticity behavior around each price change
3. Creates a complete dataset for testing elasticity features in the frontend
"""

import sys
import os
import random
import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, asc
from models import Base, Item, PriceHistory, User, Order, OrderItem
from database import get_db
import logging
from dateutil.relativedelta import relativedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants for data generation
MIN_PRICE_CHANGES = 5  # Minimum number of price changes needed for elasticity calculation
MAX_PRICE_CHANGE_PERCENT = 0.20  # Maximum price change of 20% up or down
BASE_ELASTICITY = -1.2  # Base elasticity for simulation (negative as price increases lower demand)
ELASTICITY_VARIANCE = 0.3  # Variance in elasticity between items
MIN_DAYS_BETWEEN_CHANGES = 30  # At least a month between price changes
MAX_DAYS_BETWEEN_CHANGES = 45  # At most a month and a half between price changes

# Order generation constants
WEEKS_BEFORE_PRICE_CHANGE = 2  # Generate 2 weeks of orders before a price change
WEEKS_AFTER_PRICE_CHANGE = 2   # Generate 2 weeks of orders after a price change
MIN_DAILY_ORDERS = 5           # Minimum number of orders per day
MAX_DAILY_ORDERS = 15          # Maximum number of orders per day

def get_test_user(db: Session):
    """Get the test professional user"""
    test_user = db.query(User).filter(User.email == "testprofessional@test.com").first()
    
    if not test_user:
        logger.error("Test professional user not found! Run seed_test_account.py first.")
        sys.exit(1)
    
    return test_user

def get_price_history_count(db: Session, item_id: int, user_id: int):
    """Get the count of price changes for an item"""
    return db.query(PriceHistory).filter(
        PriceHistory.item_id == item_id,
        PriceHistory.user_id == user_id
    ).count()

def generate_price_changes(db: Session, item: Item, user_id: int, min_changes: int):
    """Generate price change history for an item if needed"""
    existing_changes = get_price_history_count(db, item.id, user_id)
    
    if existing_changes >= min_changes:
        logger.info(f"Item {item.id} already has {existing_changes} price changes - skipping")
        return
    
    # Get existing price history ordered by date
    existing_history = db.query(PriceHistory).filter(
        PriceHistory.item_id == item.id,
        PriceHistory.user_id == user_id
    ).order_by(desc(PriceHistory.changed_at)).all()
    
    # Generate a unique elasticity value for this item
    item_elasticity = BASE_ELASTICITY + (random.random() * ELASTICITY_VARIANCE - ELASTICITY_VARIANCE/2)
    
    # Start with the current price if no history, otherwise use oldest price
    current_price = item.current_price
    
    # If there's existing history, start from the oldest entry
    if existing_history:
        # Sort by date ascending to get the oldest first
        oldest_first = sorted(existing_history, key=lambda x: x.changed_at)
        earliest_date = oldest_first[0].changed_at
        current_price = oldest_first[0].previous_price
    else:
        # Start from a year ago if no history
        earliest_date = datetime.datetime.now() - relativedelta(years=1)
    
    # Calculate how many more changes we need
    changes_needed = min_changes - existing_changes
    
    # Generate more price changes as needed
    logger.info(f"Generating {changes_needed} additional price changes for item {item.id}")
    
    change_date = earliest_date
    
    for i in range(changes_needed):
        # Move back in time by a random interval
        days_back = random.randint(MIN_DAYS_BETWEEN_CHANGES, MAX_DAYS_BETWEEN_CHANGES)
        change_date = change_date - datetime.timedelta(days=days_back)
        
        # Determine the previous price (random change within limits)
        price_change_pct = random.uniform(-MAX_PRICE_CHANGE_PERCENT, MAX_PRICE_CHANGE_PERCENT)
        previous_price = round(current_price * (1 - price_change_pct), 2)
        
        # Ensure price doesn't go below $1.00
        previous_price = max(previous_price, 1.00)
        
        # Create price history record
        price_history = PriceHistory(
            item_id=item.id,
            user_id=user_id,
            previous_price=previous_price,
            new_price=current_price,
            change_reason=random.choice([
                "Cost increase", 
                "Seasonal adjustment", 
                "Competitive pricing", 
                "Promotion", 
                "Demand optimization"
            ]),
            changed_at=change_date
        )
        
        db.add(price_history)
        
        # For next iteration
        current_price = previous_price
    
    db.commit()

def generate_orders_for_price_change(db: Session, item: Item, user_id: int, price_change: PriceHistory):
    """Generate orders around a price change to demonstrate elasticity behavior"""
    # Get all menu items for this user to include in orders
    all_items = db.query(Item).filter(Item.user_id == user_id).all()
    
    # Calculate date ranges for before and after the price change
    change_date = price_change.changed_at
    before_start = change_date - datetime.timedelta(days=WEEKS_BEFORE_PRICE_CHANGE * 7)
    before_end = change_date - datetime.timedelta(days=1)
    after_start = change_date
    after_end = change_date + datetime.timedelta(days=WEEKS_AFTER_PRICE_CHANGE * 7)
    
    # Check if we already have orders for this item within these date ranges
    before_orders = db.query(func.count(OrderItem.id)).join(Order).filter(
        OrderItem.item_id == item.id,
        Order.user_id == user_id,
        Order.order_date.between(before_start, before_end)
    ).scalar()
    
    after_orders = db.query(func.count(OrderItem.id)).join(Order).filter(
        OrderItem.item_id == item.id,
        Order.user_id == user_id,
        Order.order_date.between(after_start, after_end)
    ).scalar()
    
    # Skip if we already have orders in both periods
    if before_orders > 0 and after_orders > 0:
        logger.info(f"Already have orders around price change on {change_date.date()} for item {item.id}")
        return
    
    # Generate a unique elasticity for this item
    item_elasticity = BASE_ELASTICITY + (random.random() * ELASTICITY_VARIANCE - ELASTICITY_VARIANCE/2)
    
    # Calculate base demand (qty per day) before price change
    base_demand = random.randint(8, 20)
    
    # Calculate how demand changed after price change based on elasticity
    price_change_pct = (price_change.new_price - price_change.previous_price) / price_change.previous_price
    demand_change_pct = item_elasticity * price_change_pct
    after_demand = base_demand * (1 + demand_change_pct)
    
    # Ensure we have some minimum demand
    after_demand = max(after_demand, 1)
    
    logger.info(f"Generating orders for price change on {change_date.date()} - "
               f"Price: ${price_change.previous_price:.2f} → ${price_change.new_price:.2f} "
               f"Elasticity: {item_elasticity:.2f}, Demand: {base_demand:.1f} → {after_demand:.1f} units/day")
    
    # Generate orders before price change
    if before_orders == 0:
        generate_daily_orders(
            db, all_items, item, user_id, before_start, before_end, 
            base_price=price_change.previous_price, base_demand=base_demand
        )
    
    # Generate orders after price change
    if after_orders == 0:
        generate_daily_orders(
            db, all_items, item, user_id, after_start, after_end, 
            base_price=price_change.new_price, base_demand=after_demand
        )

def generate_daily_orders(db: Session, all_items: list, target_item: Item, user_id: int, 
                         start_date, end_date, base_price: float, base_demand: float):
    """Generate daily orders for a date range with specified demand for target item"""
    current_date = start_date
    
    while current_date <= end_date:
        # Number of orders for this day
        num_orders = random.randint(MIN_DAILY_ORDERS, MAX_DAILY_ORDERS)
        
        # Target quantity for the item based on demand
        target_qty = round(base_demand)
        
        # Add randomness (+/- 20%)
        target_qty = max(1, round(target_qty * random.uniform(0.8, 1.2)))
        
        # Distribute this quantity across orders
        remaining_qty = target_qty
        
        # Generate orders for this day
        for i in range(num_orders):
            # Random time of day
            hour = random.randint(7, 21)
            minute = random.randint(0, 59)
            order_time = current_date.replace(hour=hour, minute=minute)
            
            # New order
            order = Order(
                order_date=order_time,
                total_amount=0,  # Will calculate after adding items
                user_id=user_id
            )
            db.add(order)
            db.flush()  # Get order ID
            
            # Add a quantity of our target item if we still have remaining
            if remaining_qty > 0:
                # How many to add to this order
                qty_for_order = min(remaining_qty, random.randint(1, 3))
                remaining_qty -= qty_for_order
                
                # Add target item
                order_item = OrderItem(
                    order_id=order.id,
                    item_id=target_item.id,
                    quantity=qty_for_order,
                    unit_price=base_price
                )
                db.add(order_item)
            
            # Add 1-3 other random items
            num_other_items = random.randint(1, 3)
            other_items = random.sample([i for i in all_items if i.id != target_item.id], 
                                       min(num_other_items, len(all_items) - 1))
            
            for other_item in other_items:
                order_item = OrderItem(
                    order_id=order.id,
                    item_id=other_item.id,
                    quantity=random.randint(1, 2),
                    unit_price=other_item.current_price
                )
                db.add(order_item)
            
            # Calculate order total
            db.flush()
            order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
            order.total_amount = sum(item.quantity * item.unit_price for item in order_items)
            
        # Move to next day
        current_date += datetime.timedelta(days=1)
    
    db.commit()

def ensure_complete_elasticity_data(db: Session):
    """Main function to ensure complete data for elasticity calculations"""
    # Get test user
    test_user = get_test_user(db)
    logger.info(f"Processing test user (ID: {test_user.id})")
    
    # Get all items for this test user
    items = db.query(Item).filter(Item.user_id == test_user.id).all()
    
    if not items:
        logger.error("No items found for test user! Run seed_coffee_shop.py first.")
        return
    
    logger.info(f"Found {len(items)} items to process")
    
    # For each item, ensure we have enough price history
    for item in items:
        # Generate price changes if needed
        generate_price_changes(db, item, test_user.id, MIN_PRICE_CHANGES)
        
        # Get the price history for this item
        price_changes = db.query(PriceHistory).filter(
            PriceHistory.item_id == item.id,
            PriceHistory.user_id == test_user.id
        ).order_by(asc(PriceHistory.changed_at)).all()
        
        # Generate orders around each price change
        for price_change in price_changes:
            generate_orders_for_price_change(db, item, test_user.id, price_change)

def main():
    """Main function"""
    logger.info("Starting elasticity data completion script")
    
    # Get database session
    db = next(get_db())
    
    try:
        ensure_complete_elasticity_data(db)
        logger.info("Elasticity data completion finished successfully")
    except Exception as e:
        logger.error(f"Error completing elasticity data: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
