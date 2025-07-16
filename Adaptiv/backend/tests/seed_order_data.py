#!/usr/bin/env python3
import sqlite3
import random
import uuid
import os
from datetime import datetime, timedelta
import json
import requests
from dotenv import load_dotenv

# Load environment variables from .env file if available
load_dotenv()

# Get Square API credentials from environment variables
SQUARE_ACCESS_TOKEN = os.getenv("SQUARE_ACCESS_TOKEN", "EAAAl8SCkmgz697PfPEbBwNY8N6Q_7k5ToHXtiSjerNBWbboUwm-ytpjbb-0SQqK")
SQUARE_LOCATION_ID = os.getenv("SQUARE_LOCATION_ID", "LP7SQ6NZH2A8M")
SQUARE_ENV = os.getenv("SQUARE_ENV", "sandbox")  # 'sandbox' or 'production'

if not SQUARE_ACCESS_TOKEN or not SQUARE_LOCATION_ID:
    print("Error: Square API credentials not found.")
    print("Please set SQUARE_ACCESS_TOKEN and SQUARE_LOCATION_ID environment variables.")
    exit(1)

# Square API base URL based on environment
SQUARE_API_BASE = "https://connect.squareupsandbox.com" if SQUARE_ENV == "sandbox" else "https://connect.squareup.com"

print(f"Using Square {SQUARE_ENV} environment")
print(f"API Base URL: {SQUARE_API_BASE}")

# Connect to your local database to get items
conn = sqlite3.connect('./Adaptiv/backend/adaptiv.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Define the date range
start_date = datetime(2025, 5, 15)
end_date = datetime(2025, 6, 19)
days = (end_date - start_date).days + 1

print(f"Preparing to seed order data to Square from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

# Get items for user_id 1
cursor.execute('SELECT id, name, current_price, category FROM items WHERE user_id = 1')
local_items = [dict(row) for row in cursor.fetchall()]

if not local_items:
    print("No items found for user_id 1. Please make sure the items exist in your local database.")
    exit(1)

print(f"Found {len(local_items)} items in local database")

# First, create items in Square if they don't exist
print("\nSyncing items with Square catalog...")
square_item_map = {}

for item in local_items:
    # Search for existing item in Square
    print(f"\nProcessing item: {item['name']}")
    
    # Search catalog by name
    search_response = requests.post(
        f"{SQUARE_API_BASE}/v2/catalog/search",
        headers={
            "Authorization": f"Bearer {SQUARE_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "Square-Version": "2024-01-18"
        },
        json={
            "object_types": ["ITEM"],
            "query": {
                "text_query": {
                    "keywords": [item['name']]
                }
            },
            "include_related_objects": True
        }
    )
    
    found_item = None
    if search_response.status_code == 200:
        search_data = search_response.json()
        objects = search_data.get("objects", [])
        
        # Look for exact name match
        for obj in objects:
            if obj.get("type") == "ITEM" and obj.get("item_data", {}).get("name") == item['name']:
                found_item = obj
                break
    
    if found_item:
        # Item exists, get its variation
        item_data = found_item.get("item_data", {})
        variations = item_data.get("variations", [])
        if variations:
            variation = variations[0]
            square_item_map[item['name']] = {
                'item_id': found_item.get('id'),
                'variation_id': variation.get('id')
            }
            print(f"  ✓ Found existing item: {item['name']} (ID: {variation.get('id')})")
        else:
            print(f"  ⚠ Warning: Item {item['name']} has no variations")
    else:
        # Create the item
        print(f"  → Creating new item: {item['name']}")
        
        # Convert price to cents (Square uses smallest currency unit)
        price_in_cents = int(float(item['current_price']) * 100)
        
        # Generate temporary IDs for the create request
        temp_item_id = f"#ITEM_{item['name'].upper().replace(' ', '_')}"
        temp_variation_id = f"#VAR_{item['name'].upper().replace(' ', '_')}"
        
        create_body = {
            "idempotency_key": str(uuid.uuid4()),
            "object": {
                "type": "ITEM",
                "id": temp_item_id,
                "item_data": {
                    "name": item['name'],
                    "description": f"Category: {item['category']}",
                    "variations": [
                        {
                            "type": "ITEM_VARIATION",
                            "id": temp_variation_id,
                            "item_variation_data": {
                                "name": "Regular",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {
                                    "amount": price_in_cents,
                                    "currency": "USD"
                                }
                            }
                        }
                    ]
                }
            }
        }
        
        create_response = requests.post(
            f"{SQUARE_API_BASE}/v2/catalog/object",
            headers={
                "Authorization": f"Bearer {SQUARE_ACCESS_TOKEN}",
                "Content-Type": "application/json",
                "Square-Version": "2024-01-18"
            },
            json=create_body
        )
        
        if create_response.status_code in [200, 201]:
            create_data = create_response.json()
            created_item = create_data.get('catalog_object', {})
            item_data = created_item.get('item_data', {})
            variations = item_data.get('variations', [])
            if variations:
                square_item_map[item['name']] = {
                    'item_id': created_item.get('id'),
                    'variation_id': variations[0].get('id')
                }
                print(f"  ✓ Successfully created item: {item['name']}")
        else:
            print(f"  ✗ Failed to create item {item['name']}: {create_response.json()}")

# Map local items to Square items
for item in local_items:
    if item['name'] in square_item_map:
        item['square_variation_id'] = square_item_map[item['name']]['variation_id']
    else:
        item['square_variation_id'] = None
        print(f"  ⚠ Warning: Could not map item '{item['name']}' to Square")

# Group items by category for more realistic ordering patterns
items_by_category = {}
for item in local_items:
    if item.get('square_variation_id'):  # Only include items that have Square mappings
        category = item['category']
        if category not in items_by_category:
            items_by_category[category] = []
        items_by_category[category].append(item)

if not any(items_by_category.values()):
    print("\nNo items could be mapped to Square items.")
    exit(1)

print(f"\nSuccessfully mapped {sum(len(items) for items in items_by_category.values())} items to Square catalog")

# Different patterns for weekdays vs. weekends
def get_daily_order_count(date):
    # Weekends have more orders
    if date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return random.randint(10, 20)
    # More orders on Fridays
    elif date.weekday() == 4:  # 4 = Friday
        return random.randint(10, 20)
    # Regular weekdays
    else:
        return random.randint(5, 10)

# Time distribution - coffee shop likely busy in morning and lunch
def get_random_time():
    # Distribution: 70% morning (6am-11am), 20% lunch (11am-2pm), 10% afternoon (2pm-6pm)
    distribution = random.random()
    if distribution < 0.7:  # Morning
        return f"{random.randint(6, 10)}:{random.randint(0, 59):02d}"
    elif distribution < 0.9:  # Lunch
        return f"{random.randint(11, 13)}:{random.randint(0, 59):02d}"
    else:  # Afternoon
        return f"{random.randint(14, 17)}:{random.randint(0, 59):02d}"

# Weather and seasonal adjustment (summer approaching means more cold drinks)
def get_seasonal_adjustment(date):
    # As we get closer to summer, cold drinks become more popular
    days_from_start = (date - start_date).days
    summer_factor = min(1.0, days_from_start / 30 * 0.4)  # Max 40% increase toward summer
    return summer_factor

# Customer preference simulation
def get_item_combination(current_date):
    # 60% of orders have a drink only
    # 30% have a drink and a bakery item
    # 10% have multiple items
    
    combo_type = random.random()
    items_in_order = []
    
    if combo_type < 0.6:  # Drink only
        # 70% hot drinks early in the period, shifting to 40% later
        if random.random() < (0.7 - get_seasonal_adjustment(current_date) * 0.3):
            # Hot drink
            if 'Hot Drinks' in items_by_category and items_by_category['Hot Drinks']:
                items_in_order.append(random.choice(items_by_category['Hot Drinks']))
            elif 'Specialty Drinks' in items_by_category and items_by_category['Specialty Drinks']:
                items_in_order.append(random.choice(items_by_category['Specialty Drinks']))
        else:
            # Cold drink
            if 'Cold Drinks' in items_by_category and items_by_category['Cold Drinks']:
                items_in_order.append(random.choice(items_by_category['Cold Drinks']))
            elif 'Specialty Drinks' in items_by_category and items_by_category['Specialty Drinks']:
                items_in_order.append(random.choice(items_by_category['Specialty Drinks']))
    
    elif combo_type < 0.9:  # Drink and bakery
        # Select a drink (hot or cold based on season)
        if random.random() < (0.7 - get_seasonal_adjustment(current_date) * 0.3):
            if 'Hot Drinks' in items_by_category and items_by_category['Hot Drinks']:
                items_in_order.append(random.choice(items_by_category['Hot Drinks']))
            elif 'Specialty Drinks' in items_by_category and items_by_category['Specialty Drinks']:
                items_in_order.append(random.choice(items_by_category['Specialty Drinks']))
        else:
            if 'Cold Drinks' in items_by_category and items_by_category['Cold Drinks']:
                items_in_order.append(random.choice(items_by_category['Cold Drinks']))
            elif 'Specialty Drinks' in items_by_category and items_by_category['Specialty Drinks']:
                items_in_order.append(random.choice(items_by_category['Specialty Drinks']))
        
        # Add a bakery item
        if 'Bakery' in items_by_category and items_by_category['Bakery']:
            items_in_order.append(random.choice(items_by_category['Bakery']))
    
    else:  # Multiple items
        # Select 2-3 items from any category
        num_items = random.randint(2, 3)
        categories = [cat for cat in items_by_category.keys() if items_by_category[cat]]
        if categories:
            for _ in range(min(num_items, len(categories))):
                category = random.choice(categories)
                items_in_order.append(random.choice(items_by_category[category]))
    
    # Ensure at least one item
    all_items = [item for sublist in items_by_category.values() for item in sublist if item.get('square_variation_id')]
    if not items_in_order and all_items:
        items_in_order.append(random.choice(all_items))
    
    return items_in_order

# Function to create a Square order
def create_square_order(order_items, order_datetime):
    try:
        line_items = []
        
        for item in order_items:
            quantity = item.get('quantity', 1)
            
            # Skip items that don't have Square mappings
            if not item.get('square_variation_id'):
                continue
                
            line_item = {
                'catalog_object_id': item['square_variation_id'],
                'quantity': str(quantity),
                'base_price_money': {
                    'amount': int(float(item['current_price']) * 100),  # Convert to cents
                    'currency': 'USD'
                }
            }
            line_items.append(line_item)
        
        if not line_items:
            print("Warning: No valid Square items in this order")
            return None
            
        # Create a unique idempotency key
        idempotency_key = str(uuid.uuid4())
        
        # Format the request
        request_body = {
            'idempotency_key': idempotency_key,
            'order': {
                'location_id': SQUARE_LOCATION_ID,
                'line_items': line_items
            }
        }
        
        # Create order in Square
        result = requests.post(
            f"{SQUARE_API_BASE}/v2/orders",
            headers={
                "Authorization": f"Bearer {SQUARE_ACCESS_TOKEN}",
                "Content-Type": "application/json",
                "Square-Version": "2024-01-18"
            },
            json=request_body
        )
        
        if result.status_code in [200, 201]:
            result_data = result.json()
            
            # Pay for the order using cash payment (for sandbox testing)
            order = result_data.get('order', {})
            order_id = order.get('id')
            
            if order_id and SQUARE_ENV == 'sandbox':
                # In sandbox, we can create a cash payment
                payment_body = {
                    'idempotency_key': str(uuid.uuid4()),
                    'source_id': 'CASH',
                    'amount_money': order.get('total_money'),
                    'order_id': order_id,
                    'location_id': SQUARE_LOCATION_ID
                }
                
                payment_result = requests.post(
                    f"{SQUARE_API_BASE}/v2/payments",
                    headers={
                        "Authorization": f"Bearer {SQUARE_ACCESS_TOKEN}",
                        "Content-Type": "application/json",
                        "Square-Version": "2024-01-18"
                    },
                    json=payment_body
                )
                
                if payment_result.status_code not in [200, 201]:
                    print(f"Order created but payment failed: {payment_result.json()}")
            
            return result_data
        else:
            print(f"Error creating Square order: {result.json()}")
            return None
            
    except Exception as e:
        print(f"Exception creating Square order: {e}")
        return None

# Generate and create orders
print(f"\n{'='*50}")
print("GENERATING ORDERS")
print(f"{'='*50}")

successful_orders = 0
failed_orders = 0

# Loop through each day in the date range
current_date = start_date
while current_date <= end_date:
    # Get the number of orders for this day
    num_orders = get_daily_order_count(current_date)
    daily_orders_created = 0
    
    print(f"\nDate: {current_date.strftime('%A, %B %d, %Y')}")
    print(f"Target orders: {num_orders}")
    
    for order_num in range(num_orders):
        # Generate a random time for the order
        random_time = get_random_time()
        order_datetime = f"{current_date.strftime('%Y-%m-%d')}T{random_time}:00Z"
        
        # Create an order
        selected_items = get_item_combination(current_date)
        
        if not selected_items:
            print(f"  Order {order_num + 1}: ✗ No items selected")
            failed_orders += 1
            continue
            
        # Add quantity randomness occasionally for some items
        order_items = []
        for item in selected_items:
            item_copy = item.copy()
            if random.random() < 0.2:  # 20% chance of multiple quantity
                item_copy['quantity'] = random.randint(2, 3)
            else:
                item_copy['quantity'] = 1
            order_items.append(item_copy)
        
        # Calculate total (just for our reference)
        order_total = sum(float(item['current_price']) * item.get('quantity', 1) for item in order_items)
        
        # Create the order in Square
        result = create_square_order(order_items, order_datetime)
        
        if result:
            order_id = result.get('order', {}).get('id', 'unknown')
            items_summary = ', '.join([f"{item.get('quantity', 1)}x {item['name']}" for item in order_items])
            print(f"  Order {order_num + 1}: ✓ ${order_total:.2f} - {items_summary}")
            successful_orders += 1
            daily_orders_created += 1
        else:
            print(f"  Order {order_num + 1}: ✗ Failed to create")
            failed_orders += 1
    
    print(f"  Daily summary: {daily_orders_created}/{num_orders} orders created")
    current_date += timedelta(days=1)

# Summary
total_attempted = successful_orders + failed_orders
print(f"\n{'='*50}")
print("FINAL SUMMARY")
print(f"{'='*50}")
print(f"Total orders attempted: {total_attempted}")
print(f"Successful orders: {successful_orders}")
print(f"Failed orders: {failed_orders}")
if total_attempted > 0:
    print(f"Success rate: {(successful_orders/total_attempted*100):.1f}%")
print(f"\n✅ Done! Your Square account now has seeded order data for testing.")
print(f"\n⚠️  NOTE: This script used the Square {SQUARE_ENV} environment.")

# Close connection
conn.close()