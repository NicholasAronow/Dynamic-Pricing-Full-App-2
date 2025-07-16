"""
Import Square Data Script

This script imports data from a connected Square account into the Adaptiv database.
It will:
1. Import catalog items from Square
2. Import orders from Square 
3. Update the timestamps to match when they were created in Square

Usage:
    python import_square_data.py [user_id] [days_back]
    
    user_id: The user ID to import data for (default: 2)
    days_back: How many days of order history to import (default: 30)
"""

import os
import sys
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
from decimal import Decimal

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
SQUARE_ENV = os.getenv("SQUARE_ENV", "sandbox")
SQUARE_ACCESS_TOKEN = os.getenv("SQUARE_ACCESS_TOKEN", "")
SQUARE_API_BASE = "https://connect.squareupsandbox.com" if SQUARE_ENV == "sandbox" else "https://connect.squareup.com"

def get_square_locations() -> List[Dict[str, Any]]:
    """Get locations from Square"""
    try:
        locations_response = requests.get(
            f"{SQUARE_API_BASE}/v2/locations",
            headers={
                "Authorization": f"Bearer {SQUARE_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
        )
        
        if locations_response.status_code != 200:
            logger.error(f"Failed to get locations: {locations_response.json().get('errors', [])}")
            return []
        
        locations_data = locations_response.json()
        locations = locations_data.get("locations", [])
        
        if not locations:
            logger.warning("No locations found in Square account")
            
        return locations
    
    except Exception as e:
        logger.exception(f"Error getting Square locations: {str(e)}")
        return []

def import_square_catalog(user_id: int, db: Session) -> Dict[str, str]:
    """
    Import Square catalog items into the database
    
    Returns:
        Dict mapping Square catalog IDs to local item IDs
    """
    catalog_mapping = {}  # Maps Square catalog IDs to local item IDs
    items_created = 0
    items_updated = 0
    
    try:
        # Get catalog from Square
        catalog_response = requests.get(
            f"{SQUARE_API_BASE}/v2/catalog/list?types=ITEM",
            headers={
                "Authorization": f"Bearer {SQUARE_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
        )
        
        if catalog_response.status_code != 200:
            logger.error(f"Failed to get catalog: {catalog_response.json().get('errors', [])}")
            return catalog_mapping
        
        catalog_data = catalog_response.json()
        items = catalog_data.get("objects", [])
        
        logger.info(f"Found {len(items)} items in Square catalog")
        
        # Process each catalog item
        for item_obj in items:
            if item_obj.get("type") != "ITEM":
                continue
            
            square_item_id = item_obj.get("id")
            item_data = item_obj.get("item_data", {})
            name = item_data.get("name", "")
            description = item_data.get("description", "")
            
            # Skip items without name
            if not name:
                continue
            
            # Get price from first variation
            variations = item_data.get("variations", [])
            price = None
            square_variation_id = None
            
            if variations:
                variation = variations[0]
                square_variation_id = variation.get("id")
                variation_data = variation.get("item_variation_data", {})
                price_money = variation_data.get("price_money", {})
                if price_money:
                    # Convert cents to dollars
                    price = price_money.get("amount", 0) / 100.0
            
            # Skip items without price
            if price is None:
                continue
            
            # Check if item already exists
            existing_item = db.query(models.Item).filter(
                models.Item.name == name,
                models.Item.user_id == user_id
            ).first()
            
            if existing_item:
                # Update existing item
                if existing_item.current_price != price:
                    # Create price history
                    price_history = models.PriceHistory(
                        item_id=existing_item.id,
                        user_id=user_id,
                        previous_price=existing_item.current_price,
                        new_price=price,
                        change_reason="Updated from Square"
                    )
                    db.add(price_history)
                
                # Update item
                existing_item.current_price = price
                existing_item.description = description or existing_item.description
                existing_item.updated_at = datetime.datetime.now()
                existing_item.pos_id = square_item_id  # Store Square ID
                items_updated += 1
                
                # Add to mapping
                catalog_mapping[square_item_id] = existing_item.id
                if square_variation_id:
                    catalog_mapping[square_variation_id] = existing_item.id
            else:
                # Create new item
                new_item = models.Item(
                    name=name,
                    description=description,
                    category="From Square",  # Default category
                    current_price=price,
                    user_id=user_id,
                    pos_id=square_item_id  # Store Square ID
                )
                db.add(new_item)
                db.flush()  # Get ID
                
                items_created += 1
                
                # Add to mapping
                catalog_mapping[square_item_id] = new_item.id
                if square_variation_id:
                    catalog_mapping[square_variation_id] = new_item.id
        
        # Commit changes
        db.commit()
        
        logger.info(f"Catalog import complete. Created: {items_created}, Updated: {items_updated}")
        return catalog_mapping
    
    except Exception as e:
        logger.exception(f"Error importing Square catalog: {str(e)}")
        db.rollback()
        return catalog_mapping

def import_square_orders(user_id: int, db: Session, catalog_mapping: Dict[str, int], days_back: int = 30) -> int:
    """
    Import Square orders into the database
    
    Args:
        user_id: User ID to import orders for
        db: Database session
        catalog_mapping: Mapping of Square catalog IDs to local item IDs
        days_back: Number of days back to import orders from
        
    Returns:
        Number of orders imported
    """
    from models import Recipe
    from sqlalchemy.orm import joinedload
    orders_created = 0
    
    try:
        # Get locations
        locations = get_square_locations()
        if not locations:
            return 0
        
        # Calculate date filter (Square API expects RFC 3339 format)
        start_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
        start_date_str = start_date.replace(microsecond=0).isoformat() + "Z"
        
        # Process each location
        for location in locations:
            location_id = location.get("id")
            location_name = location.get("name", "Unknown Location")
            
            logger.info(f"Importing orders from location: {location_name} ({location_id})")
            
            # Get orders from Square with date filter
            orders_response = requests.post(
                f"{SQUARE_API_BASE}/v2/orders/search",
                headers={
                    "Authorization": f"Bearer {SQUARE_ACCESS_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={
                    "location_ids": [location_id],
                    "query": {
                        "filter": {
                            "date_time_filter": {
                                "created_at": {
                                    "start_at": start_date_str
                                }
                            },
                            "state_filter": {"states": ["COMPLETED", "OPEN"]}
                        },
                        "sort": {
                            "sort_field": "CREATED_AT",
                            "sort_order": "ASC"
                        }
                    },
                    "limit": 100  # Square limits to 100 orders per request
                }
            )
            
            if orders_response.status_code != 200:
                logger.error(f"Failed to get orders: {orders_response.json().get('errors', [])}")
                continue
            
            orders_data = orders_response.json()
            orders = orders_data.get("orders", [])
            
            logger.info(f"Found {len(orders)} orders in location {location_name}")
            
            # Process each order
            for order in orders:
                # Get order date and ID
                created_at = order.get("created_at")
                if not created_at:
                    continue
                
                order_date = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                square_order_id = order.get("id")
                
                # Check if order already exists
                existing_order = db.query(models.Order).filter(
                    models.Order.user_id == user_id,
                    models.Order.pos_id == square_order_id
                ).first()
                
                if existing_order:
                    logger.debug(f"Order {square_order_id} already exists, skipping")
                    continue
                
                # Calculate total from line items
                total_amount = 0
                total_cost = 0
                order_items = []

                # Calculate fixed costs using the same method as in Recipe model
                fixed_costs = Recipe.calculate_fixed_costs(db, user_id)
                fixed_cost_per_item = fixed_costs.get('fixed_cost_per_item', 0)
                
                line_items = order.get("line_items", [])
                for line_item in line_items:
                    # Get item details
                    name = line_item.get("name", "")
                    quantity = int(line_item.get("quantity", 1))
                    
                    # Get catalog ID from variation ID if available
                    catalog_object_id = line_item.get("catalog_object_id")
                    
                    # Extract price
                    base_price_money = line_item.get("base_price_money", {})
                    unit_price = base_price_money.get("amount", 0) / 100.0  # Convert cents to dollars
                    
                    # Calculate line item total
                    item_total = unit_price * quantity
                    total_amount += item_total
                    
                    # Find matching item in our database through the catalog mapping
                    item_id = None
                    if catalog_object_id and catalog_object_id in catalog_mapping:
                        item_id = catalog_mapping[catalog_object_id]
                    
                    if not item_id:
                        # Try to find by name if not in mapping
                        item = db.query(models.Item).filter(
                            models.Item.name == name,
                            models.Item.user_id == user_id
                        ).first()
                        
                        if item:
                            item_id = item.id
                        else:
                            # Create new item if not exists
                            new_item = models.Item(
                                name=name,
                                description=f"Imported from Square - {location_name}",
                                category="From Square",  # Default category
                                current_price=unit_price,
                                user_id=user_id,
                                pos_id=catalog_object_id  # Store Square ID if available
                            )
                            db.add(new_item)
                            db.flush()  # Get ID
                            
                            item_id = new_item.id
                            if catalog_object_id:
                                catalog_mapping[catalog_object_id] = item_id
                    
                    # Get recipe cost data for this item if available
                    unit_cost = None
                    subtotal_cost = None
                    recipe = db.query(Recipe).filter(Recipe.item_id == item_id).first()
                    
                    if recipe:
                        # Calculate cost from recipe
                        recipe_ingredients = db.query(models.RecipeIngredient)\
                            .options(joinedload(models.RecipeIngredient.ingredient))\
                            .filter(models.RecipeIngredient.recipe_id == recipe.id)\
                            .all()
                        
                        unit_cost = sum(ri.quantity * ri.ingredient.price for ri in recipe_ingredients if ri.ingredient)
                        subtotal_cost = unit_cost * quantity
                        
                        logger.debug(f"Item {name} has recipe with cost {unit_cost} per unit")
                    
                    # Add to order items list
                    order_items.append({
                        "item_id": item_id,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "unit_cost": unit_cost,
                        "subtotal_cost": subtotal_cost
                    })
                    
                    # Add to total cost if available
                    if subtotal_cost is not None:
                        total_cost += subtotal_cost
                
                # Create order with cost and margin data
                gross_margin = None
                net_margin = None
                
                # Calculate margins if we have cost data
                if total_cost > 0 and total_amount > 0:
                    # Gross margin percentage
                    gross_margin = ((total_amount - total_cost) / total_amount) * 100
                    
                    # For net margin, calculate using fixed costs from the Recipe model
                    from models import Recipe
                    
                    # Calculate total fixed costs for this order (fixed cost per item * quantity)
                    total_fixed_cost = fixed_cost_per_item * total_items
                    
                    # Calculate net margin using the same formula as Recipe.calculate_net_margin
                    if total_amount > 0:
                        total_cost_with_fixed = total_cost + total_fixed_cost
                        net_margin = ((total_amount - total_cost_with_fixed) / total_amount) * 100
                    
                    logger.debug(f"Order {square_order_id} has gross margin {gross_margin:.2f}% and net margin {net_margin:.2f}%")
                    logger.debug(f"Order details: total_amount=${total_amount:.2f}, ingredient_cost=${total_cost:.2f}, fixed_cost=${total_fixed_cost:.2f}")
                
                # Create order
                new_order = models.Order(
                    order_date=order_date,
                    total_amount=total_amount,
                    user_id=user_id,
                    pos_id=square_order_id,  # Store Square order ID
                    created_at=order_date,  # Use Square creation date
                    updated_at=order_date,
                    total_cost=total_cost if total_cost > 0 else None,
                    gross_margin=gross_margin,
                    net_margin=net_margin
                )
                db.add(new_order)
                db.flush()  # Get ID
                
                # Add order items
                for item_data in order_items:
                    order_item = models.OrderItem(
                        order_id=new_order.id,
                        item_id=item_data["item_id"],
                        quantity=item_data["quantity"],
                        unit_price=item_data["unit_price"],
                        unit_cost=item_data["unit_cost"],
                        subtotal_cost=item_data["subtotal_cost"]
                    )
                    db.add(order_item)
                
                orders_created += 1
                
                # Commit each order individually to avoid losing all on error
                db.commit()
                
                logger.info(f"Imported order {square_order_id} from {order_date}")
            
            # Check if we need to handle pagination
            cursor = orders_data.get("cursor")
            if cursor:
                logger.info(f"More orders available for location {location_name}, but pagination not implemented in this script")
        
        # Verify imported orders
        if orders_created > 0:
            logger.info(f"Successfully imported {orders_created} orders from Square")
            
            # Update integration with last sync time
            integration = db.query(models.POSIntegration).filter(
                models.POSIntegration.user_id == user_id,
                models.POSIntegration.provider == "square"
            ).first()
            
            if integration:
                integration.last_sync_at = datetime.datetime.now()
                db.commit()
                logger.info(f"Updated integration last_sync_at timestamp")
        else:
            logger.warning("No new orders imported from Square")
        
        return orders_created
    
    except Exception as e:
        logger.exception(f"Error importing Square orders: {str(e)}")
        db.rollback()
        return orders_created

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
    
    # Check if access token is available
    if not SQUARE_ACCESS_TOKEN:
        print("❌ SQUARE_ACCESS_TOKEN not set in environment variables")
        return 1
    
    print(f"Importing Square data for user {user_id} for the last {days_back} days...")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Check if user exists
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            print(f"❌ User with ID {user_id} not found")
            return 1
        
        # Step 1: Import catalog items
        print("📦 Importing Square catalog items...")
        catalog_mapping = import_square_catalog(user_id, db)
        
        if not catalog_mapping:
            print("⚠️  No catalog items imported from Square")
        else:
            print(f"✅ Imported {len(catalog_mapping)} catalog items from Square")
        
        # Step 2: Import orders
        print(f"🧾 Importing Square orders from the last {days_back} days...")
        orders_imported = import_square_orders(user_id, db, catalog_mapping, days_back)
        
        if orders_imported > 0:
            print(f"✅ Successfully imported {orders_imported} orders from Square")
        else:
            print("⚠️  No new orders imported from Square")
        
        return 0
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1
    
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())
