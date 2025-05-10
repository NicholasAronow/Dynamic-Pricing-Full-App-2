"""
Script to seed coffee shop competitor data for the Adaptiv Pricing app.
This adds competitor shops with overlapping and unique menu items.
"""

import sys
import os
import random
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, CompetitorItem
from database import get_db
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# List of competitor coffee shops
COFFEE_COMPETITORS = [
    {
        "name": "Bean Scene",
        "logo": "🌱",
        "distance": 0.8,
        "price_modifier": 1.15,  # 15% more expensive than you
        "has_items": ["Espresso", "Cappuccino", "Latte", "Flat White", "Mocha", "Americano", 
                      "Iced Coffee", "Cold Brew", "Croissant", "Blueberry Muffin", "Scone"]
    },
    {
        "name": "Coffee Bean",
        "logo": "☕",
        "distance": 0.2,
        "price_modifier": 0.85,  # 15% cheaper than you
        "has_items": ["Espresso", "Cappuccino", "Latte", "Americano", "Hot Chocolate", 
                      "Chai Latte", "Iced Coffee", "Bagel", "Chocolate Chip Cookie", 
                      "Cinnamon Roll", "Vanilla Latte"]
    },
    {
        "name": "Java Junction",
        "logo": "☕",
        "distance": 0.5,
        "price_modifier": 1.0,  # Same prices as you
        "has_items": ["Espresso", "Cappuccino", "Latte", "Americano", "Mocha", "Drip Coffee",
                      "Iced Latte", "Cold Brew", "Croissant", "Bagel", "Breakfast Sandwich"]
    },
    {
        "name": "Brew Haven",
        "logo": "🍵",
        "distance": 1.2,
        "price_modifier": 0.9,  # 10% cheaper than you
        "has_items": ["Espresso", "Cappuccino", "Latte", "Mocha", "Drip Coffee", "Macchiato",
                      "Iced Latte", "Cold Brew", "Nitro Cold Brew", "Chocolate Chip Cookie", 
                      "Breakfast Sandwich"]
    },
    {
        "name": "Morning Cup",
        "logo": "☕",
        "distance": 1.5,
        "price_modifier": 0.8,  # 20% cheaper than you
        "has_items": ["Espresso", "Cappuccino", "Americano", "Drip Coffee", 
                      "Iced Coffee", "Bagel", "Chocolate Chip Cookie"]
    },
    {
        "name": "Star Coffee",
        "logo": "⭐",
        "distance": 1.8,
        "price_modifier": 1.2,  # 20% more expensive than you
        "has_items": ["Espresso", "Double Espresso", "Cappuccino", "Latte", "Flat White", 
                      "Mocha", "Chai Latte", "Caramel Macchiato", "Vanilla Latte", 
                      "Hazelnut Latte", "White Chocolate Mocha", "Matcha Latte", "Iced Latte", 
                      "Cold Brew", "Nitro Cold Brew", "Frappuccino", "Croissant"]
    },
    {
        "name": "The Roastery",
        "logo": "🔥",
        "distance": 2.0,
        "price_modifier": 1.3,  # 30% more expensive than you
        "has_items": ["Espresso", "Double Espresso", "Pour Over", "Chemex", "V60", "Aeropress", 
                      "Single Origin Espresso", "Cold Brew", "Nitro Cold Brew"]
    },
    {
        "name": "Cafe Delight",
        "logo": "✨",
        "distance": 2.3,
        "price_modifier": 1.1,  # 10% more expensive than you
        "has_items": ["Espresso", "Cappuccino", "Latte", "Mocha", "Chai Latte",  
                      "Iced Latte", "Cold Brew", "Croissant", "Blueberry Muffin", 
                      "Chocolate Chip Cookie", "Cinnamon Roll", "Scone"]
    },
    {
        "name": "Brew & Co",
        "logo": "🍵",
        "distance": 2.8,
        "price_modifier": 1.4,  # 40% more expensive than you
        "has_items": ["Espresso", "Cappuccino", "Latte", "Flat White", "Pour Over", 
                      "Cold Brew", "Nitro Cold Brew", "Croissant", "Avocado Toast", 
                      "Granola Bowl", "Acai Bowl"]
    }
]

# Unique items that only competitors have (with base pricing)
COMPETITOR_UNIQUE_ITEMS = {
    "Pour Over": {"base_price": 5.50, "category": "Hot Drinks", "description": "Hand-poured single origin coffee"},
    "Chemex": {"base_price": 6.00, "category": "Hot Drinks", "description": "Coffee brewed in a Chemex pour-over coffeemaker"},
    "V60": {"base_price": 5.75, "category": "Hot Drinks", "description": "Coffee brewed using Hario V60 pour-over method"},
    "Aeropress": {"base_price": 5.25, "category": "Hot Drinks", "description": "Coffee pressed using an Aeropress"},
    "Single Origin Espresso": {"base_price": 4.00, "category": "Hot Drinks", "description": "Espresso using single origin beans"},
    "Avocado Toast": {"base_price": 8.50, "category": "Bakery", "description": "Toasted bread topped with avocado and seasonings"},
    "Granola Bowl": {"base_price": 7.50, "category": "Bakery", "description": "House-made granola with yogurt and fresh fruit"},
    "Acai Bowl": {"base_price": 9.50, "category": "Bakery", "description": "Acai smoothie bowl with toppings"},
    "Lavender Latte": {"base_price": 5.75, "category": "Specialty Drinks", "description": "Latte infused with lavender"},
    "Honey Cinnamon Latte": {"base_price": 5.50, "category": "Specialty Drinks", "description": "Latte with honey and cinnamon"},
    "Turmeric Latte": {"base_price": 5.50, "category": "Specialty Drinks", "description": "Golden milk latte with turmeric"},
}

def get_your_items(db_session):
    """Retrieve your coffee shop menu items"""
    from models import Item
    return {item.name: item for item in db_session.query(Item).all()}

def seed_coffee_competitors(db_session):
    """Seed the database with coffee shop competitor items"""
    
    # First, check if competitor items already exist
    existing_items = db_session.query(CompetitorItem).count()
    if existing_items > 0:
        logger.info(f"Found {existing_items} existing competitor items in the database")
        
        # Delete existing competitor items
        logger.info("Deleting existing competitor items...")
        db_session.query(CompetitorItem).delete()
        db_session.commit()
    
    # Get your menu items
    your_items = get_your_items(db_session)
    
    # Track how many items we've added
    items_added = 0
    
    # For each competitor
    for competitor in COFFEE_COMPETITORS:
        competitor_name = competitor["name"]
        price_modifier = competitor["price_modifier"]
        logger.info(f"Adding items for competitor: {competitor_name}")
        
        # Add overlapping items (items they have that you also have)
        for item_name in competitor["has_items"]:
            if item_name in your_items:
                # This is an overlapping item - use your price as reference
                your_item = your_items[item_name]
                competitor_price = round(your_item.current_price * price_modifier, 2)
                
                # Calculate similarity score - exactly the same item has high similarity
                similarity_score = random.uniform(80.0, 95.0)
                
                new_item = CompetitorItem(
                    competitor_name=competitor_name,
                    item_name=item_name,
                    description=your_item.description,
                    category=your_item.category,
                    price=competitor_price,
                    similarity_score=similarity_score,
                    url=None,  # No URL needed for this example
                    updated_at=datetime.datetime.now() - datetime.timedelta(hours=random.randint(1, 72))
                )
                db_session.add(new_item)
                items_added += 1
            elif item_name in COMPETITOR_UNIQUE_ITEMS:
                # This is a unique competitor item
                unique_item = COMPETITOR_UNIQUE_ITEMS[item_name]
                competitor_price = round(unique_item["base_price"] * price_modifier, 2)
                
                # Unique items have lower similarity scores
                similarity_score = random.uniform(40.0, 70.0)
                
                new_item = CompetitorItem(
                    competitor_name=competitor_name,
                    item_name=item_name,
                    description=unique_item["description"],
                    category=unique_item["category"],
                    price=competitor_price,
                    similarity_score=similarity_score,
                    url=None,
                    updated_at=datetime.datetime.now() - datetime.timedelta(hours=random.randint(1, 72))
                )
                db_session.add(new_item)
                items_added += 1
    
    # Commit changes
    db_session.commit()
    logger.info(f"Successfully seeded {items_added} competitor items")
    return True

def main():
    """Main function to seed the database"""
    logger.info("Starting to seed coffee shop competitor data...")
    
    # Create database session
    try:
        db = next(get_db())
        success = seed_coffee_competitors(db)
        if success:
            logger.info("Coffee shop competitor data seeded successfully!")
        else:
            logger.error("Failed to seed coffee shop competitor data")
    except Exception as e:
        logger.error(f"Error seeding database: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
