"""
Debug script to inspect Square integration data for a specific user.

This script examines:
1. POS Integration records
2. Items with Square catalog IDs
3. Orders with Square order IDs
4. Most recent orders in the database
"""

import os
import sys
import json
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base, SessionLocal
import models
from sqlalchemy import desc, func, text
from sqlalchemy.orm import joinedload

def inspect_database(user_id=2):
    """
    Inspect database for Square integration data for a specific user
    """
    db = SessionLocal()
    
    try:
        print(f"\n{'=' * 50}")
        print(f" DEBUG DATABASE FOR USER ID: {user_id} ".center(50, '='))
        print(f"{'=' * 50}")
        
        # 1. Check POS Integration
        print("\n[1] CHECKING POS INTEGRATION")
        print("-" * 50)
        
        integration = db.query(models.POSIntegration).filter(
            models.POSIntegration.user_id == user_id,
            models.POSIntegration.provider == "square"
        ).first()
        
        if not integration:
            print("❌ No Square integration found for this user!")
            return
        
        print(f"✅ Found Square integration (ID: {integration.id})")
        print(f"   Merchant ID: {integration.merchant_id}")
        print(f"   Last sync: {integration.last_sync_at}")
        print(f"   Created at: {integration.created_at}")
        print(f"   Updated at: {integration.updated_at}")
        
        # 2. Check Items with Square IDs
        print("\n[2] CHECKING ITEMS WITH SQUARE IDs")
        print("-" * 50)
        
        square_items = db.query(models.Item).filter(
            models.Item.user_id == user_id,
            models.Item.pos_id.isnot(None)  # Has Square catalog ID
        ).all()
        
        print(f"Found {len(square_items)} items with Square catalog IDs")
        
        if square_items:
            print("\nSample of Square items:")
            for i, item in enumerate(square_items[:5]):  # Show first 5
                print(f"   {i+1}. {item.name} (ID: {item.id}, Square ID: {item.pos_id})")
                print(f"      Price: ${item.current_price:.2f}")
                print(f"      Created: {item.created_at}")
        
        # 3. Check Orders with Square IDs
        print("\n[3] CHECKING ORDERS WITH SQUARE IDs")
        print("-" * 50)
        
        square_orders = db.query(models.Order).filter(
            models.Order.user_id == user_id,
            models.Order.pos_id.isnot(None)  # Has Square order ID
        ).order_by(models.Order.order_date.desc()).all()
        
        print(f"Found {len(square_orders)} orders with Square order IDs")
        
        if square_orders:
            print("\nMost recent Square orders:")
            for i, order in enumerate(square_orders[:5]):  # Show first 5
                order_items = db.query(models.OrderItem).filter(
                    models.OrderItem.order_id == order.id
                ).all()
                
                print(f"   {i+1}. Order #{order.id} (Square ID: {order.pos_id})")
                print(f"      Date: {order.order_date}")
                print(f"      Total: ${order.total_amount:.2f}")
                print(f"      Items: {len(order_items)}")
                print(f"      Created: {order.created_at}")
        
        # 4. Check Most Recent Orders (with or without Square IDs)
        print("\n[4] CHECKING MOST RECENT ORDERS")
        print("-" * 50)
        
        # Get all orders from the last 7 days
        week_ago = datetime.now() - timedelta(days=7)
        recent_orders = db.query(models.Order).filter(
            models.Order.user_id == user_id,
            models.Order.order_date >= week_ago
        ).order_by(models.Order.order_date.desc()).all()
        
        print(f"Found {len(recent_orders)} orders from the last 7 days")
        
        if recent_orders:
            print("\nMost recent orders (last 7 days):")
            for i, order in enumerate(recent_orders[:10]):  # Show first 10
                order_items = db.query(models.OrderItem).filter(
                    models.OrderItem.order_id == order.id
                ).all()
                
                square_id = order.pos_id if order.pos_id else "None"
                print(f"   {i+1}. Order #{order.id} (Square ID: {square_id})")
                print(f"      Date: {order.order_date}")
                print(f"      Total: ${order.total_amount:.2f}")
                print(f"      Items: {len(order_items)}")
        
        # 5. Check Today's Orders Specifically
        print("\n[5] CHECKING TODAY'S ORDERS")
        print("-" * 50)
        
        # Get all orders from today
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_orders = db.query(models.Order).filter(
            models.Order.user_id == user_id,
            models.Order.order_date >= today
        ).order_by(models.Order.order_date.desc()).all()
        
        print(f"Found {len(today_orders)} orders from today ({today.date()})")
        
        if today_orders:
            print("\nToday's orders:")
            for i, order in enumerate(today_orders):
                order_items = db.query(models.OrderItem).filter(
                    models.OrderItem.order_id == order.id
                ).all()
                
                square_id = order.pos_id if order.pos_id else "None"
                print(f"   {i+1}. Order #{order.id} (Square ID: {square_id})")
                print(f"      Date: {order.order_date}")
                print(f"      Total: ${order.total_amount:.2f}")
                
                # Show items in this order
                if order_items:
                    print(f"      Items:")
                    for j, item in enumerate(order_items):
                        product = db.query(models.Item).filter(models.Item.id == item.item_id).first()
                        product_name = product.name if product else "Unknown"
                        print(f"         - {item.quantity}x {product_name} (${item.unit_price:.2f} each)")
        
        # 6. Check for any potential database issues
        print("\n[6] CHECKING FOR DATABASE ISSUES")
        print("-" * 50)
        
        # Check for orders with no order items
        empty_orders = db.query(models.Order).outerjoin(models.OrderItem).group_by(models.Order.id).having(
            func.count(models.OrderItem.id) == 0
        ).filter(models.Order.user_id == user_id).count()
        
        if empty_orders > 0:
            print(f"⚠️ Found {empty_orders} orders with no items!")
        else:
            print("✅ All orders have associated items")
        
        # Check for order items referencing non-existent items
        orphan_order_items = db.query(models.OrderItem).outerjoin(
            models.Item, models.OrderItem.item_id == models.Item.id
        ).filter(models.Item.id == None).count()
        
        if orphan_order_items > 0:
            print(f"⚠️ Found {orphan_order_items} order items referencing non-existent products!")
        else:
            print("✅ All order items reference valid products")
        
    except Exception as e:
        print(f"❌ Error inspecting database: {str(e)}")
    
    finally:
        db.close()

if __name__ == "__main__":
    # Get user ID from command line if provided, otherwise use default (2)
    user_id = 2
    if len(sys.argv) > 1:
        try:
            user_id = int(sys.argv[1])
        except ValueError:
            print(f"Invalid user ID: {sys.argv[1]}")
            sys.exit(1)
    
    inspect_database(user_id)
