"""
Script to seed coffee shop menu items and a full year of order data for the Adaptiv Pricing app.
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

# Coffee shop menu items
COFFEE_ITEMS = [
    # Hot Drinks
    {"name": "Espresso", "category": "Hot Drinks", "price": 2.75, "cost": 0.65, "description": "Single shot of rich espresso"},
    {"name": "Double Espresso", "category": "Hot Drinks", "price": 3.50, "cost": 1.10, "description": "Double shot of rich espresso"},
    {"name": "Americano", "category": "Hot Drinks", "price": 3.25, "cost": 0.70, "description": "Espresso with hot water"},
    {"name": "Cappuccino", "category": "Hot Drinks", "price": 4.50, "cost": 1.25, "description": "Espresso with steamed milk and foam"},
    {"name": "Latte", "category": "Hot Drinks", "price": 4.75, "cost": 1.35, "description": "Espresso with lots of steamed milk"},
    {"name": "Flat White", "category": "Hot Drinks", "price": 4.50, "cost": 1.30, "description": "Espresso with velvety steamed milk"},
    {"name": "Mocha", "category": "Hot Drinks", "price": 5.25, "cost": 1.55, "description": "Espresso with chocolate and steamed milk"},
    {"name": "Hot Chocolate", "category": "Hot Drinks", "price": 4.25, "cost": 1.15, "description": "Rich chocolate with steamed milk"},
    {"name": "Chai Latte", "category": "Hot Drinks", "price": 4.95, "cost": 1.45, "description": "Spiced tea with steamed milk"},
    {"name": "Drip Coffee", "category": "Hot Drinks", "price": 2.95, "cost": 0.55, "description": "Freshly brewed coffee"},
    {"name": "Macchiato", "category": "Hot Drinks", "price": 3.75, "cost": 0.95, "description": "Espresso marked with a dollop of foam"},
    
    # Cold Drinks
    {"name": "Iced Coffee", "category": "Cold Drinks", "price": 3.75, "cost": 0.85, "description": "Chilled coffee over ice"},
    {"name": "Iced Latte", "category": "Cold Drinks", "price": 5.25, "cost": 1.45, "description": "Espresso and milk over ice"},
    {"name": "Cold Brew", "category": "Cold Drinks", "price": 4.95, "cost": 1.10, "description": "Slow-steeped cold coffee"},
    {"name": "Nitro Cold Brew", "category": "Cold Drinks", "price": 5.75, "cost": 1.35, "description": "Cold brew infused with nitrogen"},
    {"name": "Iced Americano", "category": "Cold Drinks", "price": 3.95, "cost": 0.85, "description": "Chilled espresso with water over ice"},
    {"name": "Iced Mocha", "category": "Cold Drinks", "price": 5.75, "cost": 1.65, "description": "Chilled espresso with chocolate and milk over ice"},
    {"name": "Frappuccino", "category": "Cold Drinks", "price": 5.95, "cost": 1.85, "description": "Blended coffee drink with ice"},
    {"name": "Vanilla Frappuccino", "category": "Cold Drinks", "price": 6.25, "cost": 2.00, "description": "Blended vanilla coffee drink with ice"},
    {"name": "Caramel Frappuccino", "category": "Cold Drinks", "price": 6.50, "cost": 2.10, "description": "Blended caramel coffee drink with ice"},
    {"name": "Iced Tea", "category": "Cold Drinks", "price": 3.50, "cost": 0.60, "description": "Fresh brewed tea over ice"},
    
    # Bakery Items
    {"name": "Croissant", "category": "Bakery", "price": 3.25, "cost": 1.05, "description": "Buttery flaky pastry"},
    {"name": "Blueberry Muffin", "category": "Bakery", "price": 3.50, "cost": 1.15, "description": "Moist muffin with fresh blueberries"},
    {"name": "Chocolate Chip Cookie", "category": "Bakery", "price": 2.95, "cost": 0.85, "description": "Classic chocolate chip cookie"},
    {"name": "Bagel", "category": "Bakery", "price": 2.75, "cost": 0.75, "description": "Fresh baked bagel"},
    {"name": "Bagel with Cream Cheese", "category": "Bakery", "price": 3.95, "cost": 1.25, "description": "Bagel with a side of cream cheese"},
    {"name": "Breakfast Sandwich", "category": "Bakery", "price": 5.95, "cost": 2.35, "description": "Egg and cheese on a croissant"},
    {"name": "Cinnamon Roll", "category": "Bakery", "price": 4.25, "cost": 1.45, "description": "Sweet roll with cinnamon and icing"},
    {"name": "Banana Bread", "category": "Bakery", "price": 3.75, "cost": 1.20, "description": "Moist bread made with ripe bananas"},
    {"name": "Scone", "category": "Bakery", "price": 3.50, "cost": 1.10, "description": "Buttery pastry in various flavors"},
    
    # Specialty Drinks
    {"name": "Caramel Macchiato", "category": "Specialty Drinks", "price": 5.50, "cost": 1.65, "description": "Vanilla, steamed milk, espresso, and caramel"},
    {"name": "Pumpkin Spice Latte", "category": "Specialty Drinks", "price": 5.95, "cost": 1.85, "description": "Seasonal favorite with pumpkin and spices"},
    {"name": "Vanilla Latte", "category": "Specialty Drinks", "price": 5.25, "cost": 1.55, "description": "Espresso with vanilla and steamed milk"},
    {"name": "Hazelnut Latte", "category": "Specialty Drinks", "price": 5.25, "cost": 1.55, "description": "Espresso with hazelnut and steamed milk"},
    {"name": "White Chocolate Mocha", "category": "Specialty Drinks", "price": 5.75, "cost": 1.75, "description": "Espresso with white chocolate and steamed milk"},
    {"name": "Matcha Latte", "category": "Specialty Drinks", "price": 5.50, "cost": 1.75, "description": "Japanese green tea with steamed milk"}
]

def seed_coffee_items(db_session):
    """Seed the database with coffee shop menu items"""
    
    # First, check if items already exist
    existing_items = db_session.query(Item).count()
    if existing_items > 0:
        logger.info(f"Found {existing_items} existing items in the database")
        
        # Delete existing items
        logger.info("Deleting existing items...")
        db_session.query(OrderItem).delete()
        db_session.query(Order).delete()
        db_session.query(Item).delete()
        db_session.commit()
    
    logger.info(f"Seeding {len(COFFEE_ITEMS)} coffee shop menu items")
    
    # Insert coffee items
    for item_data in COFFEE_ITEMS:
        new_item = Item(
            name=item_data["name"],
            description=item_data["description"],
            category=item_data["category"],
            current_price=item_data["price"],
            cost=item_data["cost"]
        )
        db_session.add(new_item)
    
    # Commit changes
    db_session.commit()
    logger.info(f"Successfully seeded {len(COFFEE_ITEMS)} coffee shop menu items")
    return True

def main():
    """Main function to seed the database"""
    try:
        # Get db session
        db = next(get_db())
        
        # Seed coffee shop items
        seed_coffee_items(db)
        
        logger.info("Database seeding completed successfully")
    except Exception as e:
        logger.error(f"Error seeding database: {str(e)}")
        return False
    return True

if __name__ == "__main__":
    main()
