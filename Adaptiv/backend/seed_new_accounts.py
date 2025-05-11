"""
Script to automatically seed new user accounts with sample data.
This script should be run after registering a new user to give them isolated sample data.
"""

import sys
import os
from sqlalchemy.orm import Session
from database import get_db, engine, Base
import models
from sqlalchemy import func, select
import random
from datetime import datetime, timedelta

# Sample item data
SAMPLE_ITEMS = [
    {"name": "Cappuccino", "description": "Italian coffee drink", "category": "Coffee", "current_price": 4.99, "cost": 1.50},
    {"name": "Latte", "description": "Coffee with steamed milk", "category": "Coffee", "current_price": 5.49, "cost": 1.70},
    {"name": "Espresso", "description": "Concentrated coffee shot", "category": "Coffee", "current_price": 3.49, "cost": 1.20},
    {"name": "Mocha", "description": "Chocolate flavored coffee", "category": "Coffee", "current_price": 5.99, "cost": 1.80},
    {"name": "Croissant", "description": "Buttery, flaky pastry", "category": "Bakery", "current_price": 3.49, "cost": 1.10},
    {"name": "Blueberry Muffin", "description": "Muffin with blueberries", "category": "Bakery", "current_price": 3.99, "cost": 1.30},
    {"name": "Chocolate Chip Cookie", "description": "Fresh baked cookie", "category": "Bakery", "current_price": 2.49, "cost": 0.80},
    {"name": "Avocado Toast", "description": "Toast topped with avocado", "category": "Food", "current_price": 7.99, "cost": 2.50},
    {"name": "Breakfast Sandwich", "description": "Egg, cheese, and bacon on a roll", "category": "Food", "current_price": 6.99, "cost": 2.20},
    {"name": "Caesar Salad", "description": "Classic salad with romaine lettuce", "category": "Food", "current_price": 8.99, "cost": 3.00},
]

def seed_user_data(user_id: int):
    """Seed a new user account with sample items and orders."""
    print(f"Seeding data for user ID: {user_id}")
    
    # Create a session
    db = next(get_db())
    
    try:
        # First check if user already has items to avoid duplicates
        existing_items = db.query(models.Item).filter(models.Item.user_id == user_id).count()
        if existing_items > 0:
            print(f"User {user_id} already has {existing_items} items. Skipping data seeding.")
            return
        
        # Create sample items for the user
        created_items = []
        for item_data in SAMPLE_ITEMS:
            db_item = models.Item(
                **item_data,
                user_id=user_id
            )
            db.add(db_item)
            db.flush()  # Get the ID without committing
            created_items.append(db_item)
            
            # Add some price history for each item
            previous_price = item_data["current_price"] * 0.9  # 10% lower initial price
            price_history = models.PriceHistory(
                item_id=db_item.id,
                user_id=user_id,
                previous_price=previous_price,
                new_price=item_data["current_price"],
                change_reason="Initial price set",
                changed_at=datetime.now() - timedelta(days=30)
            )
            db.add(price_history)
        
        # Create some sample orders
        today = datetime.now()
        for day_offset in range(1, 31):  # Create 30 days of order history
            order_date = today - timedelta(days=day_offset)
            # Create 1-3 orders per day
            for _ in range(random.randint(1, 3)):
                # Calculate total amount and create order
                total_amount = 0
                order = models.Order(
                    order_date=order_date,
                    total_amount=0,  # Temporary, will update after adding items
                    user_id=user_id
                )
                db.add(order)
                db.flush()  # Get the order ID
                
                # Add 1-5 random items to each order
                order_items = []
                for _ in range(random.randint(1, 5)):
                    item = random.choice(created_items)
                    quantity = random.randint(1, 3)
                    unit_price = item.current_price
                    subtotal = quantity * unit_price
                    total_amount += subtotal
                    
                    order_item = models.OrderItem(
                        order_id=order.id,
                        item_id=item.id,
                        quantity=quantity,
                        unit_price=unit_price
                    )
                    db.add(order_item)
                
                # Update order with correct total
                order.total_amount = total_amount
        
        # Commit all changes
        db.commit()
        print(f"Successfully seeded data for user {user_id}!")
        print(f"Created {len(created_items)} items and multiple orders with history.")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    # Check arguments
    if len(sys.argv) != 2:
        print("Usage: python seed_new_accounts.py <user_id>")
        sys.exit(1)
    
    try:
        user_id = int(sys.argv[1])
        seed_user_data(user_id)
    except ValueError:
        print("Error: user_id must be an integer")
        sys.exit(1)
