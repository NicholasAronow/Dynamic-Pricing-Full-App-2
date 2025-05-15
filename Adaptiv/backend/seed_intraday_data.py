"""
Special script to specifically seed hourly intraday sales data for today's date only.
This script focuses on creating detailed hourly data using the exact format expected
by the frontend ProductDetail component.
"""
import sys
import os
import random
import datetime
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, delete
from models import Base, Item, Order, OrderItem, User
from database import get_db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Target email
TARGET_EMAIL = "testprofessional@test.com"

def create_intraday_data(db: Session, user_id: int):
    """Create detailed hourly sales data specifically for today"""
    logger.info(f"Creating intensive intraday data for user {user_id} for today")
    
    # Get all items for this user
    items = db.query(Item).filter(Item.user_id == user_id).all()
    
    if not items:
        logger.error(f"No items found for user {user_id}. Cannot proceed with seeding.")
        sys.exit(1)
        
    logger.info(f"Found {len(items)} items for user {user_id}")
    
    # Get today's date with midnight time
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # For each hour of the day until the current hour
    current_hour = datetime.datetime.now().hour
    
    # Delete any existing orders from today to avoid duplicates
    start_of_day = today
    end_of_day = today + datetime.timedelta(days=1)
    
    # Find any existing orders
    existing_orders = db.query(Order).filter(
        Order.user_id == user_id,
        Order.order_date >= start_of_day,
        Order.order_date < end_of_day
    ).all()
    
    # Delete existing order items first
    for order in existing_orders:
        db.query(OrderItem).filter(OrderItem.order_id == order.id).delete(synchronize_session=False)
    
    # Then delete the orders
    order_ids = [order.id for order in existing_orders]
    if order_ids:
        logger.info(f"Deleting {len(order_ids)} existing orders for today")
        db.query(Order).filter(Order.id.in_(order_ids)).delete(synchronize_session=False)
    
    # Create orders for each hour from 8 AM until current hour
    start_hour = 8  # Business starts at 8 AM
    end_hour = max(current_hour, start_hour + 1)  # Ensure at least one hour of data
    
    # Log what we're generating
    logger.info(f"Generating hourly data from {start_hour}:00 to {end_hour}:00")
    
    # List to track order data to print at the end
    hourly_stats = []
    
    # Loop through hours
    for hour in range(start_hour, end_hour + 1):
        hour_total_sales = 0
        hour_total_units = 0
        
        # Create 3-7 orders per hour with items (more in busy hours)
        busy_hours = [8, 12, 13, 17, 18, 19]  # Morning, lunch, and after work are busy
        order_multiplier = 2.0 if hour in busy_hours else 1.0
        num_orders = int(random.randint(3, 7) * order_multiplier)
        
        logger.info(f"Creating {num_orders} orders for hour {hour}")
        
        for _ in range(num_orders):
            # Randomize minutes within the hour for more realistic data
            minute = random.randint(0, 59)
            order_time = today.replace(hour=hour, minute=minute)
            
            # Create order
            order = Order(
                user_id=user_id,
                order_date=order_time,
                total_amount=0.0
            )
            db.add(order)
            db.flush()  # Get the order ID
            
            # Add 1-4 random items to this order
            num_items = random.randint(1, 4)
            random_items = random.sample(items, min(num_items, len(items)))
            
            order_total = 0.0
            for item in random_items:
                # More realistic quantity distribution
                quantity = random.choices([1, 2, 3, 4], weights=[60, 25, 10, 5])[0]
                
                order_item = OrderItem(
                    order_id=order.id,
                    item_id=item.id,
                    quantity=quantity,
                    unit_price=item.current_price
                )
                db.add(order_item)
                
                item_subtotal = quantity * item.current_price
                order_total += item_subtotal
                hour_total_units += quantity
                
            # Update order total
            order.total_amount = order_total
            hour_total_sales += order_total
        
        # Log stats for this hour
        hourly_stats.append({
            'hour': f"{hour:02d}:00",
            'orders': num_orders,
            'units': hour_total_units,
            'sales': round(hour_total_sales, 2)
        })
    
    # Commit transactions
    db.commit()
    
    # Print summary of created data
    logger.info("=== Hourly Sales Summary ===")
    for stat in hourly_stats:
        logger.info(f"Hour {stat['hour']}: {stat['orders']} orders, {stat['units']} units, ${stat['sales']} sales")
    
    logger.info("Successfully created intensive intraday sales data")

def main():
    """Main function to seed intraday data"""
    logger.info(f"Starting intraday seeding for {TARGET_EMAIL}")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get test user
        test_user = db.query(User).filter(User.email == TARGET_EMAIL).first()
        
        if not test_user:
            logger.error(f"Test user {TARGET_EMAIL} not found!")
            sys.exit(1)
            
        user_id = test_user.id
        logger.info(f"Found test user with ID: {user_id}")
        
        # Create intraday data
        create_intraday_data(db, user_id)
        
        logger.info(f"Intraday data seeding completed successfully for {TARGET_EMAIL}")
    except Exception as e:
        logger.error(f"Error during intraday seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
