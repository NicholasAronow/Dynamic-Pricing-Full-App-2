"""
Script to seed hourly sales data for a SPECIFIC PRODUCT.
This ensures the product detail page will show hourly data for the selected product.
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

def create_product_intraday_data(db: Session, user_id: int, product_id: int):
    """Create detailed hourly sales data specifically for one product"""
    # Get the specific item to ensure it exists
    item = db.query(Item).filter(Item.id == product_id, Item.user_id == user_id).first()
    
    if not item:
        logger.error(f"Product ID {product_id} not found for user {user_id}. Cannot proceed.")
        sys.exit(1)
        
    logger.info(f"Creating intraday data for product: {item.name} (ID: {product_id})")
    
    # Get today's date with midnight time
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Current hour
    current_hour = datetime.datetime.now().hour
    
    # Delete any existing orders for this specific item from today
    start_of_day = today
    end_of_day = today + datetime.timedelta(days=1)
    
    # Find existing orders with this item
    existing_order_items = db.query(OrderItem).join(
        Order, OrderItem.order_id == Order.id
    ).filter(
        OrderItem.item_id == product_id,
        Order.order_date >= start_of_day,
        Order.order_date < end_of_day
    ).all()
    
    # Delete them
    if existing_order_items:
        order_ids = set([item.order_id for item in existing_order_items])
        logger.info(f"Deleting {len(existing_order_items)} existing order items for product {product_id}")
        
        # Delete order items first
        for order_item in existing_order_items:
            db.query(OrderItem).filter(OrderItem.id == order_item.id).delete(synchronize_session=False)
        
        # Delete orphaned orders
        for order_id in order_ids:
            # Check if there are any other items in this order
            remaining_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).count()
            if remaining_items == 0:
                db.query(Order).filter(Order.id == order_id).delete(synchronize_session=False)
    
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
        
        # Create 2-5 orders per hour with this specific item (more in busy hours)
        busy_hours = [8, 12, 13, 17, 18, 19]  # Morning, lunch, and after work are busy
        order_multiplier = 2.0 if hour in busy_hours else 1.0
        num_orders = int(random.randint(2, 5) * order_multiplier)
        
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
            
            # Add our specific product to this order
            # More realistic quantity distribution
            quantity = random.choices([1, 2, 3, 4], weights=[60, 25, 10, 5])[0]
            
            order_item = OrderItem(
                order_id=order.id,
                item_id=product_id,
                quantity=quantity,
                unit_price=item.current_price
            )
            db.add(order_item)
            
            item_subtotal = quantity * item.current_price
            order_total = item_subtotal
            
            # Optionally add 0-2 other random items to this order for realism
            if random.random() > 0.3:  # 70% chance of having other items
                other_items = db.query(Item).filter(
                    Item.user_id == user_id,
                    Item.id != product_id
                ).limit(10).all()
                
                num_other_items = random.randint(1, min(2, len(other_items)))
                selected_other_items = random.sample(other_items, num_other_items)
                
                for other_item in selected_other_items:
                    other_quantity = random.choices([1, 2], weights=[80, 20])[0]
                    other_order_item = OrderItem(
                        order_id=order.id,
                        item_id=other_item.id,
                        quantity=other_quantity,
                        unit_price=other_item.current_price
                    )
                    db.add(other_order_item)
                    order_total += other_quantity * other_item.current_price
            
            # Update order total
            order.total_amount = order_total
            hour_total_units += quantity
            hour_total_sales += item_subtotal  # Only counting our target product's sales
        
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
    logger.info("=== Hourly Sales Summary for Product ID " + str(product_id) + " ===")
    for stat in hourly_stats:
        logger.info(f"Hour {stat['hour']}: {stat['orders']} orders, {stat['units']} units, ${stat['sales']} sales")
    
    logger.info(f"Successfully created intraday sales data for product {product_id}")

def main():
    """Main function to seed intraday data"""
    if len(sys.argv) < 2:
        logger.error("Usage: python seed_product_intraday.py <product_id>")
        sys.exit(1)
    
    try:
        product_id = int(sys.argv[1])
        logger.info(f"Starting intraday seeding for product ID {product_id}")
    except ValueError:
        logger.error("Product ID must be a number")
        sys.exit(1)
    
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
        
        # Create intraday data for specific product
        create_product_intraday_data(db, user_id, product_id)
        
        logger.info(f"Product intraday data seeding completed successfully for product ID {product_id}")
    except Exception as e:
        logger.error(f"Error during intraday seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
