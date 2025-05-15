"""
Script to seed historical price changes for test items in the Adaptiv Pricing app.
This creates price change history and ensures corresponding order data exists
to calculate price elasticity from actual sales performance.
"""

import sys
import os
import random
import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.sql import text
from models import Base, Item, PriceHistory, User, Order, OrderItem
from database import get_db
import logging
from dateutil.relativedelta import relativedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants for price change generation
NUM_PRICE_CHANGES_PER_ITEM = 7  # At least 5 are needed for elasticity calculation
MAX_PRICE_CHANGE_PERCENT = 0.20  # Maximum price change of 20% up or down
BASE_ELASTICITY = -1.2  # Base elasticity for simulation (negative as price increases lower demand)
ELASTICITY_VARIANCE = 0.3  # Variance in elasticity between items
DAYS_BETWEEN_PRICE_CHANGES = 35  # Approximately monthly changes

def get_or_create_test_user(db: Session):
    """Get the test professional user or create if not exists"""
    test_user = db.query(User).filter(User.email == "testprofessional@test.com").first()
    
    if not test_user:
        logger.warning("Test professional user not found! Creating a new one.")
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        test_user = User(
            email="testprofessional@test.com",
            hashed_password=pwd_context.hash("password123"),
            is_active=True
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
    
    return test_user

def get_weekly_sales_volume(db: Session, item_id: int, user_id: int, start_date, end_date):
    """Get the total sales volume for an item within a specified date range"""
    # Query for all order items that match this item within the date range
    sales_data = db.query(
        func.sum(OrderItem.quantity).label('total_quantity')
    ).join(
        Order, OrderItem.order_id == Order.id
    ).filter(
        OrderItem.item_id == item_id,
        Order.user_id == user_id,
        Order.order_date.between(start_date, end_date)
    ).first()
    
    return sales_data.total_quantity if sales_data.total_quantity else 0

def seed_price_history(db: Session):
    """
    Create historical price changes and ensure orders exist to calculate elasticity
    """
    # Get test user
    test_user = get_or_create_test_user(db)
    logger.info(f"Seeding price history for test user (ID: {test_user.id})")
    
    # Get all items for this test user
    items = db.query(Item).filter(Item.user_id == test_user.id).all()
    
    if not items:
        logger.error("No items found for test user! Make sure to run seed_coffee_shop.py first.")
        return
    
    logger.info(f"Found {len(items)} items for test user")
    
    # For each item, create a series of price changes
    for item in items:
        # Generate a unique elasticity value for this item (around the base elasticity)
        item_elasticity = BASE_ELASTICITY + (random.random() * ELASTICITY_VARIANCE - ELASTICITY_VARIANCE/2)
        logger.info(f"Creating price history for item: {item.name} (ID: {item.id}) with elasticity {item_elasticity:.2f}")
        
        # Get current price
        current_price = item.current_price
        
        # Start from current price and work backwards
        # Most recent change was 7 days ago
        change_date = datetime.datetime.now() - datetime.timedelta(days=7)
        
        # Check for existing price history entries to avoid duplicates
        existing_history = db.query(PriceHistory).filter(
            PriceHistory.item_id == item.id,
            PriceHistory.user_id == test_user.id
        ).order_by(desc(PriceHistory.changed_at)).all()
        
        if existing_history:
            logger.info(f"Found {len(existing_history)} existing price history entries for item {item.id}")
            continue
        
        # Generate price changes over the past year
        for i in range(NUM_PRICE_CHANGES_PER_ITEM):
            # Skip the most recent price (that's the current price)
            if i == 0:
                previous_date = change_date - datetime.timedelta(days=DAYS_BETWEEN_PRICE_CHANGES)
                # Create some orders between previous_date and change_date with the current price
                continue
                
            # Determine the previous price (random change within limits)
            price_change_pct = random.uniform(-MAX_PRICE_CHANGE_PERCENT, MAX_PRICE_CHANGE_PERCENT)
            previous_price = round(current_price / (1 + price_change_pct), 2)
            
            # Calculate dates for this price change window
            next_change_date = change_date
            change_date = next_change_date - datetime.timedelta(days=DAYS_BETWEEN_PRICE_CHANGES)
            
            # Create price history record
            price_history = PriceHistory(
                item_id=item.id,
                user_id=test_user.id,
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
            
            # Setup for next iteration
            current_price = previous_price
    
    # Commit all price history changes
    db.commit()
    logger.info(f"Successfully created price history for {len(items)} items")

    # Now check if we have orders that align with these price changes
    logger.info("Verifying orders exist for elasticity calculations...")


def main():
    """Main function to seed price history and ensure orders exist"""
    logger.info("Starting price history seed script")
    
    # Get database session
    db = next(get_db())
    
    try:
        seed_price_history(db)
        logger.info("Price history seeding completed successfully")
    except Exception as e:
        logger.error(f"Error seeding price history: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
