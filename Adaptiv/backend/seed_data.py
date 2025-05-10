from sqlalchemy.orm import Session
from database import get_db, engine
import models
from datetime import datetime, timedelta
import random

# Create mock data for testing
def seed_database():
    db = next(get_db())
    
    # First check if we already have data
    existing_items = db.query(models.Item).count()
    if existing_items > 0:
        print("Database already has data. Skipping seed operation.")
        return
    
    print("Seeding database with mock data...")
    
    # Create menu items
    categories = ["Appetizers", "Main Courses", "Desserts", "Beverages", "Sides"]
    items_data = [
        # Appetizers
        {"name": "Garlic Bread", "description": "Toasted bread with garlic butter", "category": "Appetizers", "current_price": 5.99, "cost": 1.50},
        {"name": "Mozzarella Sticks", "description": "Breaded mozzarella with marinara sauce", "category": "Appetizers", "current_price": 7.99, "cost": 2.50},
        {"name": "Chicken Wings", "description": "Spicy buffalo wings with blue cheese dip", "category": "Appetizers", "current_price": 11.99, "cost": 4.75},
        {"name": "Calamari", "description": "Fried squid rings with aioli", "category": "Appetizers", "current_price": 12.99, "cost": 5.25},
        
        # Main Courses
        {"name": "Classic Burger", "description": "Beef patty with lettuce, tomato and special sauce", "category": "Main Courses", "current_price": 13.99, "cost": 5.75},
        {"name": "Margherita Pizza", "description": "Tomato, mozzarella, and basil", "category": "Main Courses", "current_price": 14.99, "cost": 4.50},
        {"name": "Grilled Salmon", "description": "Served with roasted vegetables", "category": "Main Courses", "current_price": 22.99, "cost": 9.50},
        {"name": "Fettuccine Alfredo", "description": "Pasta in creamy parmesan sauce", "category": "Main Courses", "current_price": 16.99, "cost": 4.25},
        
        # Desserts
        {"name": "Chocolate Cake", "description": "Rich chocolate layer cake", "category": "Desserts", "current_price": 7.99, "cost": 2.25},
        {"name": "Cheesecake", "description": "New York style with berry compote", "category": "Desserts", "current_price": 8.99, "cost": 3.00},
        
        # Beverages
        {"name": "Soft Drink", "description": "Cola, lemon-lime, or root beer", "category": "Beverages", "current_price": 2.99, "cost": 0.75},
        {"name": "Iced Tea", "description": "Freshly brewed, sweetened or unsweetened", "category": "Beverages", "current_price": 3.49, "cost": 0.50},
        
        # Sides
        {"name": "French Fries", "description": "Crispy golden fries", "category": "Sides", "current_price": 4.99, "cost": 1.25},
        {"name": "Side Salad", "description": "Mixed greens with house dressing", "category": "Sides", "current_price": 5.49, "cost": 1.75}
    ]
    
    # Add items to database
    db_items = []
    for item_data in items_data:
        db_item = models.Item(**item_data)
        db.add(db_item)
        db_items.append(db_item)
    
    db.flush()  # To get IDs for the items
    
    # Create price history for each item
    for db_item in db_items:
        # Generate 1-3 price history entries per item
        num_entries = random.randint(1, 3)
        
        for i in range(num_entries):
            # Calculate a previous price (slightly different from current)
            price_diff = random.uniform(-1.5, 1.0)
            previous_price = round(max(db_item.current_price + price_diff, 1.99), 2)
            
            # Create a price history entry
            changed_days_ago = random.randint(5, 90)
            change_date = datetime.now() - timedelta(days=changed_days_ago)
            
            reasons = ["Seasonal adjustment", "Cost increase", "Promotion", "Menu redesign", "Competitive pricing"]
            
            price_history = models.PriceHistory(
                item_id=db_item.id,
                previous_price=previous_price,
                new_price=db_item.current_price,
                change_reason=random.choice(reasons),
                changed_at=change_date
            )
            
            db.add(price_history)
    
    # Create competitor items
    competitors = ["Tasty Bites", "Flavor Heaven", "Gourmet Delight", "Urban Eats"]
    
    for competitor in competitors:
        # Add 5-10 items per competitor
        num_items = random.randint(5, 10)
        
        for i in range(num_items):
            # Randomly select a category
            category = random.choice(categories)
            
            # Create a competitor item (with similar but slightly different prices)
            item_base = random.choice([item for item in items_data if item["category"] == category])
            price_variation = random.uniform(-2.0, 3.0)
            competitor_price = round(max(item_base["current_price"] + price_variation, 1.99), 2)
            
            # Calculate similarity score (random for mock data)
            similarity_score = random.uniform(60.0, 95.0)
            
            competitor_item = models.CompetitorItem(
                competitor_name=competitor,
                item_name=f"{competitor} {item_base['name']}",
                description=item_base["description"],
                category=category,
                price=competitor_price,
                similarity_score=similarity_score,
                url=f"https://example.com/{competitor.lower().replace(' ', '-')}/menu/{item_base['name'].lower().replace(' ', '-')}"
            )
            
            db.add(competitor_item)
    
    # Create orders (past 30 days)
    for day in range(30):
        # Create 1-5 orders per day
        num_orders = random.randint(1, 5)
        
        for _ in range(num_orders):
            order_date = datetime.now() - timedelta(days=day, 
                                                   hours=random.randint(0, 23), 
                                                   minutes=random.randint(0, 59))
            
            # Create order
            order = models.Order(
                order_date=order_date,
                total_amount=0  # Will calculate after adding items
            )
            db.add(order)
            db.flush()  # To get order ID
            
            # Add 1-5 items to the order
            num_items_in_order = random.randint(1, 5)
            order_items = []
            
            # Randomly select items for the order
            selected_items = random.sample(db_items, num_items_in_order)
            
            total_amount = 0
            for item in selected_items:
                quantity = random.randint(1, 3)
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
    print("Database seeded successfully with mock data!")

if __name__ == "__main__":
    # Create tables if they don't exist
    models.Base.metadata.create_all(bind=engine)
    
    # Seed database with mock data
    seed_database()
