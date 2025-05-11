from sqlalchemy.orm import Session
from database import get_db, engine
import models
from datetime import datetime, timedelta
import random
from passlib.context import CryptContext
import argparse

# Password hashing utility
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def seed_test_account(target_email: str):
    db = next(get_db())
    
    print("Seeding database with test account data...")
    
    # Create / fetch account for the requested email
    test_email = target_email.lower()
    
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == test_email).first()
    if existing_user:
        print(f"User {test_email} already exists with ID: {existing_user.id}")
        user_id = existing_user.id
    else:
        # Create new user
        test_user = models.User(
            email=test_email,
            hashed_password=get_password_hash("adaptiv123"),
            is_active=True
        )
        db.add(test_user)
        db.flush()
        user_id = test_user.id
        print(f"Created test user with ID: {user_id}")
        
        # Create business profile
        business = models.BusinessProfile(
            user_id=user_id,
            business_name="Coffee Haven",
            industry="Food & Beverage",
            company_size="Small (1-10 employees)",
            founded_year=2020,
            description="A cozy coffee shop serving specialty coffee and pastries."
        )
        db.add(business)
    
    # Define menu categories specific to a coffee shop
    categories = ["Hot Coffee", "Cold Coffee", "Tea", "Pastries", "Sandwiches", "Breakfast"]
    
    # Create menu items
    items_data = [
        # Hot Coffee
        {"name": "House Blend", "description": "Our signature blend with notes of chocolate and nuts", "category": "Hot Coffee", "current_price": 3.49, "cost": 0.85},
        {"name": "Americano", "description": "Espresso diluted with hot water", "category": "Hot Coffee", "current_price": 3.99, "cost": 0.75},
        {"name": "Cappuccino", "description": "Equal parts espresso, steamed milk, and foam", "category": "Hot Coffee", "current_price": 4.49, "cost": 1.20},
        {"name": "Latte", "description": "Espresso with steamed milk and a light layer of foam", "category": "Hot Coffee", "current_price": 4.99, "cost": 1.30},
        {"name": "Mocha", "description": "Espresso with chocolate and steamed milk", "category": "Hot Coffee", "current_price": 5.49, "cost": 1.50},
        
        # Cold Coffee
        {"name": "Cold Brew", "description": "Slow-steeped for 12 hours for a smooth finish", "category": "Cold Coffee", "current_price": 4.49, "cost": 0.95},
        {"name": "Iced Latte", "description": "Espresso and cold milk over ice", "category": "Cold Coffee", "current_price": 5.29, "cost": 1.35},
        {"name": "Iced Mocha", "description": "Espresso, chocolate, cold milk, and ice", "category": "Cold Coffee", "current_price": 5.79, "cost": 1.55},
        {"name": "Vanilla Sweet Cream Cold Brew", "description": "Cold brew topped with vanilla sweet cream", "category": "Cold Coffee", "current_price": 5.99, "cost": 1.65},
        
        # Tea
        {"name": "Green Tea", "description": "Light and refreshing green tea", "category": "Tea", "current_price": 3.29, "cost": 0.65},
        {"name": "Earl Grey", "description": "Black tea with bergamot oil", "category": "Tea", "current_price": 3.29, "cost": 0.65},
        {"name": "Chai Latte", "description": "Spiced tea concentrate with steamed milk", "category": "Tea", "current_price": 4.79, "cost": 1.20},
        
        # Pastries
        {"name": "Butter Croissant", "description": "Flaky buttery pastry", "category": "Pastries", "current_price": 3.49, "cost": 1.10},
        {"name": "Blueberry Muffin", "description": "Moist muffin with fresh blueberries", "category": "Pastries", "current_price": 3.29, "cost": 1.00},
        {"name": "Chocolate Chip Cookie", "description": "Freshly baked cookie with chocolate chips", "category": "Pastries", "current_price": 2.49, "cost": 0.75},
        
        # Sandwiches
        {"name": "Turkey & Cheese", "description": "Smoked turkey with cheddar on whole grain", "category": "Sandwiches", "current_price": 7.99, "cost": 3.25},
        {"name": "Veggie Wrap", "description": "Seasonal vegetables and hummus in a wheat wrap", "category": "Sandwiches", "current_price": 6.99, "cost": 2.75},
        
        # Breakfast
        {"name": "Avocado Toast", "description": "Smashed avocado on artisan toast with red pepper flakes", "category": "Breakfast", "current_price": 8.49, "cost": 3.00},
        {"name": "Breakfast Sandwich", "description": "Egg, cheese, and choice of bacon or sausage", "category": "Breakfast", "current_price": 5.99, "cost": 2.50}
    ]
    
    # Add items to database with user_id
    db_items = []
    # First check if items already exist for this user
    existing_items = db.query(models.Item).filter(models.Item.user_id == user_id).count()
    
    if existing_items > 0:
        print(f"User already has {existing_items} menu items. Skipping item creation.")
        db_items = db.query(models.Item).filter(models.Item.user_id == user_id).all()
    else:
        print("Creating menu items for user...")
        for item_data in items_data:
            db_item = models.Item(
                **item_data,
                user_id=user_id
            )
            db.add(db_item)
            db_items.append(db_item)
        
        db.flush()  # To get IDs for the items
        
        # Create price history for each item
        print("Creating price history...")
        for db_item in db_items:
            # Generate 1-3 price history entries per item
            num_entries = random.randint(1, 3)
            
            for i in range(num_entries):
                # Calculate a previous price (slightly different from current)
                price_diff = random.uniform(-0.50, 0.30)
                previous_price = round(max(db_item.current_price + price_diff, 1.99), 2)
                
                # Create a price history entry with different dates
                changed_days_ago = random.randint(5, 90)
                change_date = datetime.now() - timedelta(days=changed_days_ago)
                
                reasons = ["Seasonal adjustment", "Cost increase", "Promotion", "Menu redesign", "Competitive pricing"]
                
                price_history = models.PriceHistory(
                    item_id=db_item.id,
                    user_id=user_id,
                    previous_price=previous_price,
                    new_price=db_item.current_price,
                    change_reason=random.choice(reasons),
                    changed_at=change_date
                )
                
                db.add(price_history)
    
    # Create competitors with locations
    competitors = [
        {
            "name": "Bean & Brew",
            "distance": 0.5,  # miles away
            "location": "123 Market St, Same City",
            "categories": ["Hot Coffee", "Cold Coffee", "Tea", "Pastries"]
        },
        {
            "name": "Morning Grind",
            "distance": 0.8,
            "location": "456 Main St, Same City",
            "categories": ["Hot Coffee", "Cold Coffee", "Breakfast", "Sandwiches"]
        },
        {
            "name": "Espresso Express",
            "distance": 1.2,
            "location": "789 Oak Ave, Same City",
            "categories": ["Hot Coffee", "Cold Coffee", "Tea", "Pastries"]
        },
        {
            "name": "City Cafe",
            "distance": 1.5,
            "location": "321 Elm St, Same City",
            "categories": ["Hot Coffee", "Cold Coffee", "Breakfast", "Sandwiches", "Pastries"]
        }
    ]
    
    # Check if competitor items already exist
    existing_competitors = db.query(models.CompetitorItem).count()
    
    if existing_competitors > 0:
        print(f"Already have {existing_competitors} competitor items. Skipping competitor creation.")
    else:
        print("Creating competitors and their items...")
        for competitor in competitors:
            # Add comparable items for each competitor
            # Focus on categories this competitor has
            for category in competitor["categories"]:
                # Get user's items in this category
                user_items_in_category = [item for item in db_items if item.category == category]
                
                # For each user item, possibly create a competitor item (70% chance)
                for user_item in user_items_in_category:
                    if random.random() < 0.7:  # 70% chance
                        # Calculate price with some variance
                        price_variance = random.uniform(-0.70, 1.20)
                        competitor_price = round(max(user_item.current_price + price_variance, 1.99), 2)
                        
                        # Calculate similarity score based on:
                        # - Price similarity (40%): how close the prices are
                        # - Menu similarity (40%): same category and similar name
                        # - Distance (20%): how close they are geographically
                        
                        price_similarity = 100 - min(abs(user_item.current_price - competitor_price) / user_item.current_price * 100, 30)
                        menu_similarity = random.uniform(70, 95)  # Simulate menu similarity
                        distance_score = 100 - min(competitor["distance"] * 10, 30)  # Lower distance = higher score
                        
                        # Weighted similarity score
                        similarity_score = round(
                            price_similarity * 0.4 + 
                            menu_similarity * 0.4 + 
                            distance_score * 0.2, 
                            1
                        )
                        
                        competitor_item = models.CompetitorItem(
                            competitor_name=competitor["name"],
                            item_name=f"{competitor['name']} {user_item.name}",
                            description=f"Similar to {user_item.name}. {competitor['location']}",
                            category=category,
                            price=competitor_price,
                            similarity_score=similarity_score,
                            url=f"https://example.com/{competitor['name'].lower().replace(' ', '-')}/menu"
                        )
                        
                        db.add(competitor_item)
    
    # Create orders for the past 60 days
    # Check if orders already exist
    existing_orders = db.query(models.Order).filter(models.Order.user_id == user_id).count()
    
    if existing_orders > 0:
        print(f"User already has {existing_orders} orders. Skipping order creation.")
    else:
        print("Creating orders for user...")
        # Create a realistic pattern with:
        # - Weekends busier than weekdays
        # - Morning and lunch rushes
        # - Certain items more popular at certain times
        
        # Track the start date
        current_date = datetime.now()
        start_date = current_date - timedelta(days=60)
        
        # Loop through each day
        for day_offset in range(60):
            date = start_date + timedelta(days=day_offset)
            day_of_week = date.weekday()  # 0=Monday, 6=Sunday
            
            # Weekends get more orders
            if day_of_week >= 5:  # Weekend
                num_orders = random.randint(25, 40)
            else:  # Weekday
                num_orders = random.randint(15, 30)
            
            # Create orders for this day
            for _ in range(num_orders):
                # Assign a realistic time
                # Morning rush: 7-10 AM, Lunch: 11-2 PM, Afternoon: 2-5 PM, Evening: 5-8 PM
                hour_weights = [1, 1, 1, 1, 1, 1, 3, 5, 7, 6, 4, 6, 8, 7, 5, 4, 4, 5, 4, 3, 2, 1, 1, 1]
                hour = random.choices(range(24), weights=hour_weights)[0]
                minute = random.randint(0, 59)
                
                order_datetime = datetime(date.year, date.month, date.day, hour, minute)
                
                # Create order
                order = models.Order(
                    order_date=order_datetime,
                    total_amount=0,
                    user_id=user_id
                )
                db.add(order)
                db.flush()  # To get order ID
                
                # Add 1-4 items to the order
                # Morning orders (before 11) tend to be coffee and pastries
                # Lunch orders (11-2) tend to include sandwiches and coffee
                # Afternoon orders tend to be coffee and pastries again
                
                if hour < 11:  # Morning
                    possible_categories = ["Hot Coffee", "Cold Coffee", "Tea", "Pastries"]
                elif hour < 14:  # Lunch
                    possible_categories = ["Hot Coffee", "Cold Coffee", "Tea", "Sandwiches", "Pastries"]
                else:  # Afternoon/Evening
                    possible_categories = ["Hot Coffee", "Cold Coffee", "Tea", "Pastries"]
                
                # Get items from possible categories
                items_in_categories = [item for item in db_items if item.category in possible_categories]
                
                # If it's a weekend, more variety
                if day_of_week >= 5:
                    num_items = random.randint(1, 4)
                else:
                    num_items = random.randint(1, 3)
                
                # Make sure we don't try to select more items than available
                num_items = min(num_items, len(items_in_categories))
                
                if num_items > 0:
                    selected_items = random.sample(items_in_categories, num_items)
                    
                    total_amount = 0
                    for item in selected_items:
                        quantity = random.randint(1, 2)  # Most orders have 1-2 of each item
                        unit_price = item.current_price
                        
                        order_item = models.OrderItem(
                            order_id=order.id,
                            item_id=item.id,
                            quantity=quantity,
                            unit_price=unit_price
                        )
                        
                        db.add(order_item)
                        total_amount += quantity * unit_price
                    
                    # Update order total
                    order.total_amount = total_amount
    
    db.commit()
    print("Account data seeded successfully!")
    print(f"Login with email: {test_email} and password: adaptiv123")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed menu / order data for a given account e-mail")
    parser.add_argument("--email", default="test@adaptiv.com", help="Target account email")
    args = parser.parse_args()

    # If running locally and using the remote DATABASE_URL, switch to SQLite temporarily
    import os

    if 'dpg-' in os.getenv("DATABASE_URL", "") and not os.getenv("RENDER"):
        print("Detected Render PostgreSQL URL but running locally.")
        print("Run on Render or point DATABASE_URL to a local DB.")
    else:
        models.Base.metadata.create_all(bind=engine)
        seed_test_account(args.email)
