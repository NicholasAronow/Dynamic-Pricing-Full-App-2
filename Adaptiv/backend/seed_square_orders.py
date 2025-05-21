"""
Script to seed Square orders using existing orders in the local database.

This script:
1. Finds existing orders in the database
2. Creates corresponding orders in Square
3. Updates the orders with Square IDs for proper syncing

Usage:
    python seed_square_orders.py [user_id] [days_back]
    
    user_id: The user ID to create orders for (default: 2)
    days_back: How many days of orders to convert (default: 30)
"""

import os
import sys
import random
import datetime
import time
import requests
import json
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
import models
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
SQUARE_ENV = os.getenv("SQUARE_ENV", "sandbox")
SQUARE_ACCESS_TOKEN = os.getenv("SQUARE_ACCESS_TOKEN", "")
SQUARE_API_BASE = "https://connect.squareupsandbox.com" if SQUARE_ENV == "sandbox" else "https://connect.squareup.com"

def get_square_location(access_token: str) -> Optional[str]:
    """Get the first location ID from Square"""
    try:
        locations_response = requests.get(
            f"{SQUARE_API_BASE}/v2/locations",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )
        
        locations_data = locations_response.json()
        
        if locations_response.status_code != 200 or "locations" not in locations_data:
            logger.error(f"Failed to get locations: {locations_data.get('errors', [])}")
            return None
        
        if not locations_data.get("locations"):
            logger.error("No locations found")
            return None
        
        # Use first location
        location_id = locations_data["locations"][0]["id"]
        logger.info(f"Using Square location: {location_id}")
        return location_id
    
    except Exception as e:
        logger.exception(f"Error getting Square location: {str(e)}")
        return None

def create_square_catalog_item(access_token: str, item: models.Item) -> Optional[str]:
    """Create an item in Square catalog and return its ID"""
    try:
        # Check if a catalog entry already exists for this item
        search_response = requests.post(
            f"{SQUARE_API_BASE}/v2/catalog/search",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "text_filter": item.name
            }
        )
        
        if search_response.status_code == 200:
            search_data = search_response.json()
            items = search_data.get("items", [])
            for catalog_item in items:
                if catalog_item.get("type") == "ITEM":
                    item_data = catalog_item.get("item_data", {})
                    if item_data.get("name") == item.name:
                        # Item already exists, return its ID
                        logger.info(f"Item '{item.name}' already exists in Square catalog")
                        return catalog_item.get("id")
        
        # Item doesn't exist, create it
        logger.info(f"Creating Square catalog item: {item.name}")
        
        # Convert price to cents for Square API
        price_cents = int(item.current_price * 100)
        
        catalog_response = requests.post(
            f"{SQUARE_API_BASE}/v2/catalog/object",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "idempotency_key": f"item_{item.id}_{int(time.time())}",
                "object": {
                    "type": "ITEM",
                    "id": f"#{item.id}",
                    "item_data": {
                        "name": item.name,
                        "description": item.description or "",
                        "variations": [
                            {
                                "type": "ITEM_VARIATION",
                                "id": f"#{item.id}_var",
                                "item_variation_data": {
                                    "name": "Regular",
                                    "pricing_type": "FIXED_PRICING",
                                    "price_money": {
                                        "amount": price_cents,
                                        "currency": "USD"
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        )
        
        if catalog_response.status_code != 200:
            logger.error(f"Failed to create catalog item: {catalog_response.json().get('errors', [])}")
            return None
        
        catalog_data = catalog_response.json()
        return catalog_data.get("catalog_object", {}).get("id")
    
    except Exception as e:
        logger.exception(f"Error creating Square catalog item: {str(e)}")
        return None

def create_square_order(
    access_token: str, 
    location_id: str,
    order: models.Order,
    order_items: List[Dict[str, Any]],
    item_catalog_mapping: Dict[int, str]
) -> Optional[str]:
    """Create an order in Square based on an existing order in our database"""
    try:
        # Get order date in RFC 3339 format
        order_date_utc = order.order_date.replace(microsecond=0).isoformat() + "Z"
        
        # Prepare line items for the order
        line_items = []
        
        for order_item in order_items:
            item_id = order_item["item_id"]
            quantity = order_item["quantity"]
            
            # Skip if catalog item hasn't been created
            if item_id not in item_catalog_mapping:
                logger.warning(f"Item ID {item_id} not found in catalog mapping, skipping")
                continue
                
            # Create line item
            line_items.append({
                "quantity": str(quantity),
                "catalog_object_id": item_catalog_mapping[item_id],
                "base_price_money": {
                    "amount": int(order_item["unit_price"] * 100),
                    "currency": "USD"
                }
            })
        
        # Skip if no valid line items
        if not line_items:
            logger.error("No valid line items for this order")
            return None
            
        # Create order
        logger.info(f"Creating Square order for date: {order_date_utc}")
        
        order_response = requests.post(
            f"{SQUARE_API_BASE}/v2/orders",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "idempotency_key": f"order_{order.id}_{int(time.time())}",
                "order": {
                    "location_id": location_id,
                    "line_items": line_items,
                    "state": "COMPLETED",
                    "source": {
                        "name": "Adaptiv Sync"
                    },
                    # Metadata for reference
                    "metadata": {
                        "adaptiv_order_id": str(order.id),
                        "created_by": "seed_square_orders.py"
                    },
                    # Adjust creation time to match original order
                    "created_at": order_date_utc
                }
            }
        )
        
        if order_response.status_code != 200:
            logger.error(f"Failed to create order: {order_response.json().get('errors', [])}")
            return None
            
        order_data = order_response.json()
        return order_data.get("order", {}).get("id")
    
    except Exception as e:
        logger.exception(f"Error creating Square order: {str(e)}")
        return None

def seed_square_orders(user_id: int, days_back: int = 30):
    """
    Main function to seed Square orders using existing orders in the database
    
    Args:
        user_id: The user ID to process orders for
        days_back: How many days of orders to convert
    """
    # Check if access token is available
    if not SQUARE_ACCESS_TOKEN:
        logger.error("SQUARE_ACCESS_TOKEN not set in environment variables")
        return False
    
    # Get the Square location ID
    location_id = get_square_location(SQUARE_ACCESS_TOKEN)
    if not location_id:
        return False
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Check if user exists
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            logger.error(f"User with ID {user_id} not found")
            return False
        
        # Calculate date threshold
        threshold_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
        
        # Get orders to convert
        orders = db.query(models.Order).filter(
            models.Order.user_id == user_id,
            models.Order.order_date >= threshold_date
        ).order_by(models.Order.order_date.asc()).all()
        
        if not orders:
            logger.warning(f"No orders found for user {user_id} in the last {days_back} days")
            return False
        
        logger.info(f"Found {len(orders)} orders to sync to Square")
        
        # Get all unique items used in these orders
        item_ids = []
        for order in orders:
            order_items = db.query(models.OrderItem).filter(models.OrderItem.order_id == order.id).all()
            for order_item in order_items:
                if order_item.item_id not in item_ids:
                    item_ids.append(order_item.item_id)
        
        # Get item details
        items = db.query(models.Item).filter(models.Item.id.in_(item_ids)).all()
        
        # Create items in Square catalog
        item_catalog_mapping = {}  # Maps item ID to Square catalog ID
        for item in items:
            catalog_id = create_square_catalog_item(SQUARE_ACCESS_TOKEN, item)
            if catalog_id:
                item_catalog_mapping[item.id] = catalog_id
        
        logger.info(f"Created/mapped {len(item_catalog_mapping)} items in Square catalog")
        
        # Rate limiting for Square API
        orders_per_batch = 5
        batch_delay = 2  # seconds
        
        # Create orders in Square
        orders_created = 0
        orders_failed = 0
        
        for i, order in enumerate(orders):
            # Get order items
            order_items_db = db.query(models.OrderItem).filter(models.OrderItem.order_id == order.id).all()
            order_items = [
                {
                    "item_id": item.item_id,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price
                }
                for item in order_items_db
            ]
            
            # Create Square order
            square_order_id = create_square_order(
                SQUARE_ACCESS_TOKEN,
                location_id,
                order,
                order_items,
                item_catalog_mapping
            )
            
            if square_order_id:
                # Update order with Square ID
                order.pos_id = square_order_id
                # Update user's Square integration
                integration = db.query(models.POSIntegration).filter(
                    models.POSIntegration.user_id == user_id,
                    models.POSIntegration.provider == "square"
                ).first()
                
                if integration:
                    integration.last_sync_at = datetime.datetime.now()
                
                db.commit()
                orders_created += 1
                logger.info(f"Order {order.id} created in Square with ID {square_order_id}")
            else:
                orders_failed += 1
            
            # Apply rate limiting for Square API
            if (i + 1) % orders_per_batch == 0:
                logger.info(f"Processed {i + 1}/{len(orders)} orders. Pausing for rate limiting...")
                time.sleep(batch_delay)
        
        logger.info(f"Square order seeding complete. Created: {orders_created}, Failed: {orders_failed}")
        return True
    
    except Exception as e:
        logger.exception(f"Error seeding Square orders: {str(e)}")
        return False
    
    finally:
        db.close()

def main():
    """Main entry point"""
    # Get user ID and days back from command line arguments
    user_id = 2  # Default user ID
    days_back = 30  # Default days back
    
    if len(sys.argv) > 1:
        try:
            user_id = int(sys.argv[1])
        except ValueError:
            print(f"Invalid user ID: {sys.argv[1]}")
            return 1
    
    if len(sys.argv) > 2:
        try:
            days_back = int(sys.argv[2])
        except ValueError:
            print(f"Invalid days back: {sys.argv[2]}")
            return 1
    
    print(f"Seeding Square orders for user {user_id} for the last {days_back} days...")
    
    success = seed_square_orders(user_id, days_back)
    
    if success:
        print("✅ Square orders seeded successfully!")
        return 0
    else:
        print("❌ Failed to seed Square orders")
        return 1

if __name__ == "__main__":
    sys.exit(main())
