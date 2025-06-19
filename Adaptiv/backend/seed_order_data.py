#!/usr/bin/env python3
import sqlite3
import random
from datetime import datetime, timedelta
import json

# Connect to the database
conn = sqlite3.connect('./Adaptiv/backend/adaptiv.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Define the date range
start_date = datetime(2025, 5, 15)
end_date = datetime(2025, 6, 19)
days = (end_date - start_date).days + 1

print(f"Seeding order data for user ID 1 from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

# Get items for user_id 1
cursor.execute('SELECT id, name, current_price, category FROM items WHERE user_id = 1')
items = [dict(row) for row in cursor.fetchall()]

if not items:
    print("No items found for user_id 1. Please make sure the items exist.")
    exit(1)

# Group items by category for more realistic ordering patterns
items_by_category = {}
for item in items:
    category = item['category']
    if category not in items_by_category:
        items_by_category[category] = []
    items_by_category[category].append(item)

# Generate random orders
total_orders = 0

# Different patterns for weekdays vs. weekends
def get_daily_order_count(date):
    # Weekends have more orders
    if date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return random.randint(600, 1000)
    # More orders on Fridays
    elif date.weekday() == 4:  # 4 = Friday
        return random.randint(600, 1000)
    # Regular weekdays
    else:
        return random.randint(300, 600)

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
def get_item_combination():
    # 60% of orders have a drink only
    # 30% have a drink and a bakery item
    # 10% have multiple items
    
    combo_type = random.random()
    items_in_order = []
    
    if combo_type < 0.6:  # Drink only
        # 70% hot drinks early in the period, shifting to 40% later
        if random.random() < (0.7 - get_seasonal_adjustment(current_date) * 0.3):
            # Hot drink
            if 'Hot Drinks' in items_by_category:
                items_in_order.append(random.choice(items_by_category['Hot Drinks']))
            elif 'Specialty Drinks' in items_by_category:
                items_in_order.append(random.choice(items_by_category['Specialty Drinks']))
        else:
            # Cold drink
            if 'Cold Drinks' in items_by_category:
                items_in_order.append(random.choice(items_by_category['Cold Drinks']))
            elif 'Specialty Drinks' in items_by_category:
                items_in_order.append(random.choice(items_by_category['Specialty Drinks']))
    
    elif combo_type < 0.9:  # Drink and bakery
        # Select a drink (hot or cold based on season)
        if random.random() < (0.7 - get_seasonal_adjustment(current_date) * 0.3):
            if 'Hot Drinks' in items_by_category:
                items_in_order.append(random.choice(items_by_category['Hot Drinks']))
            elif 'Specialty Drinks' in items_by_category:
                items_in_order.append(random.choice(items_by_category['Specialty Drinks']))
        else:
            if 'Cold Drinks' in items_by_category:
                items_in_order.append(random.choice(items_by_category['Cold Drinks']))
            elif 'Specialty Drinks' in items_by_category:
                items_in_order.append(random.choice(items_by_category['Specialty Drinks']))
        
        # Add a bakery item
        if 'Bakery' in items_by_category:
            items_in_order.append(random.choice(items_by_category['Bakery']))
    
    else:  # Multiple items
        # Select 2-3 items from any category
        num_items = random.randint(2, 3)
        categories = list(items_by_category.keys())
        selected_categories = random.sample(categories, min(len(categories), num_items))
        
        for category in selected_categories:
            items_in_order.append(random.choice(items_by_category[category]))
    
    # Ensure at least one item
    if not items_in_order and items:
        items_in_order.append(random.choice(items))
    
    return items_in_order

orders_data = []

# Loop through each day in the date range
current_date = start_date
while current_date <= end_date:
    # Get the number of orders for this day
    num_orders = get_daily_order_count(current_date)
    
    for _ in range(num_orders):
        # Generate a random time for the order
        random_time = get_random_time()
        order_datetime = f"{current_date.strftime('%Y-%m-%d')} {random_time}:00"
        
        # Create an order
        selected_items = get_item_combination()
        
        # Add quantity randomness occasionally for some items
        for i in range(len(selected_items)):
            if random.random() < 0.2:  # 20% chance of multiple quantity
                selected_items[i]['quantity'] = random.randint(2, 3)
            else:
                selected_items[i]['quantity'] = 1
        
        # Calculate total with quantities
        order_total = sum(item['current_price'] * item['quantity'] for item in selected_items)
        
        # Store order data with its items
        orders_data.append({
            'user_id': 1,
            'order_date': order_datetime,
            'total_amount': order_total,
            'items': selected_items  # Store the selected items with each order
        })
    
    current_date += timedelta(days=1)
    total_orders += num_orders

print(f"Generated data for {total_orders} orders across {days} days")

# Begin transaction
conn.execute('BEGIN TRANSACTION')

# Insert orders and their items
try:
    orders_inserted = 0
    items_inserted = 0
    
    for order in orders_data:
        # Insert the order
        cursor.execute(
            'INSERT INTO orders (user_id, order_date, total_amount) VALUES (?, ?, ?)',
            (order['user_id'], order['order_date'], order['total_amount'])
        )
        order_id = cursor.lastrowid
        orders_inserted += 1
        
        # Insert all items for this order
        for item in order['items']:
            cursor.execute(
                'INSERT INTO order_items (order_id, item_id, quantity, unit_price) VALUES (?, ?, ?, ?)',
                (order_id, item['id'], item['quantity'], item['current_price'])
            )
            items_inserted += 1

    # Commit the transaction
    conn.commit()
    print(f"Successfully added {orders_inserted} orders with {items_inserted} order items")
    
except Exception as e:
    # Rollback in case of error
    conn.rollback()
    print(f"Error: {e}")
    
    # Print more details if there's an error in the data
    if 'items' in locals() and order_id:
        print(f"Error occurred at order ID {order_id}")
        print(f"Item data: {json.dumps(item, default=str)}")


# Close connection
conn.close()
