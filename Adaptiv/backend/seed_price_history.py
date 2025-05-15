"""
Script to seed historical price changes for test items in the Adaptiv Pricing app.
This creates enough price change and sales data to calculate price elasticity.
"""

import sys
import os
import random
import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
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


def seed_price_history_with_sales_data(db: Session):
    """
    Create historical price changes with before/after sales data for test accounts
    """
    # Find the test professional user for seeding
    test_user = db.query(User).filter(User.email == "testprofessional@test.com").first()
    
    if not test_user:
        logger.error("Test professional user not found! Make sure to run seed_test_account.py first.")
        return
    
    logger.info(f"Seeding price history for test professional user (ID: {test_user.id})")
    
    # Get all items for this test user
    items = db.query(Item).filter(Item.user_id == test_user.id).all()
    
    if not items:
        logger.error("No items found for test user! Make sure to run seed_coffee_shop.py first.")
        return
    
    logger.info(f"Found {len(items)} items for test professional user")
    
    # For each item, create a series of price changes with sales data
    for item in items:
        # Generate a unique elasticity value for this item (around the base elasticity)
        item_elasticity = BASE_ELASTICITY + (random.random() * ELASTICITY_VARIANCE - ELASTICITY_VARIANCE/2)
        
        logger.info(f"Creating price history for item: {item.name} (ID: {item.id}) with elasticity {item_elasticity:.2f}")
        
        # Start from current price and work backwards
        current_price = item.current_price
        base_sales_volume = random.randint(80, 200)  # Weekly sales volume at current price
        
        # Generate price changes over the past year
        end_date = datetime.datetime.now() - datetime.timedelta(days=7)  # Most recent change was a week ago
        
        for i in range(NUM_PRICE_CHANGES_PER_ITEM):
            # Calculate dates for this price change
            change_date = end_date - relativedelta(months=i+1)  # One month between price changes
            
            # Determine the previous price (random change within limits)
            price_change_pct = random.uniform(-MAX_PRICE_CHANGE_PERCENT, MAX_PRICE_CHANGE_PERCENT)
            previous_price = round(current_price / (1 + price_change_pct), 2)
            
            # Calculate sales volumes based on elasticity
            # Price elasticity = (% change in sales) / (% change in price)
            # Therefore: % change in sales = elasticity * % change in price
            
            price_change_pct = (current_price - previous_price) / previous_price
            sales_change_pct = item_elasticity * price_change_pct
            
            previous_sales = base_sales_volume * (1 - sales_change_pct)  # Sales before the price change
            
            # Add randomness to sales data (±10%)
            sales_randomness = random.uniform(0.9, 1.1)
            previous_sales = round(previous_sales * sales_randomness, 2)
            
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
                changed_at=change_date,
                sales_before=previous_sales,
                sales_after=base_sales_volume
            )
            
            db.add(price_history)
            
            # For the next iteration, this price becomes the current price
            current_price = previous_price
            base_sales_volume = previous_sales  # For simplicity, use previous sales as the base for next change
    
    # Commit all changes
    db.commit()
    logger.info(f"Successfully created price history with sales data for {len(items)} items")


def main():
    """Main function to seed price history"""
    logger.info("Starting price history seed script")
    
    # Get database session
    db = next(get_db())
    
    try:
        seed_price_history_with_sales_data(db)
        logger.info("Price history seeding completed successfully")
    except Exception as e:
        logger.error(f"Error seeding price history: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
