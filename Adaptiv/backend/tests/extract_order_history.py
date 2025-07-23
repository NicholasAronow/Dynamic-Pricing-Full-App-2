#!/usr/bin/env python3
"""
Extract order history for a specific user or all users
"""
import sys
import os
# Add the backend directory to the Python path and change working directory
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)
# Change to backend directory so database path is correct
os.chdir(backend_dir)
from config.database import SessionLocal
from models import Order, OrderItem
import json
from datetime import datetime, timedelta

def extract_order_history(user_id=None, days=None, output_format='display', output_file=None):
    """
    Extract order history for a specific user or all users
    
    Args:
        user_id: Optional user ID to filter by, None for all users
        days: Optional number of days to look back
        output_format: 'display', 'json', or 'csv'
        output_file: Optional file path to save output
    """
    db = SessionLocal()
    try:
        # Build the order query
        query = db.query(Order)
        
        # Apply filters
        if user_id:
            query = query.filter(Order.user_id == user_id)
            
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            query = query.filter(Order.order_date >= cutoff_date)
            
        # Sort by date
        query = query.order_by(Order.order_date.desc())
            
        # Execute query
        orders = query.all()
        
        if not orders:
            print(f"No orders found{f' for user ID {user_id}' if user_id else ''}{f' in the last {days} days' if days else ''}.")
            return
            
        # Process results based on format
        if output_format == 'display':
            print(f"\n{'='*100}")
            print(f"ORDER HISTORY{f' FOR USER {user_id}' if user_id else ''}{f' (LAST {days} DAYS)' if days else ''} ({len(orders)} total)")
            print(f"{'='*100}")
            
            for order in orders:
                # Format the date
                order_date = order.order_date.strftime('%Y-%m-%d %H:%M') if order.order_date else "Unknown date"
                
                # Get order items
                db_order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
                
                print(f"\nOrder #{order.id} | Date: {order_date} | Total: ${order.total_amount:.2f}")
                print(f"POS ID: {order.pos_id or 'N/A'}")
                print("-" * 100)
                
                if db_order_items:
                    print(f"{'Item ID':<8} {'Item Name':<40} {'Qty':<5} {'Unit Price':<12} {'Subtotal':<12}")
                    print("-" * 100)
                    
                    for order_item in db_order_items:
                        # Get item name
                        item_name = "Unknown"
                        if order_item.item:
                            item_name = order_item.item.name
                            
                        subtotal = order_item.quantity * order_item.unit_price
                        
                        print(f"{order_item.item_id:<8} {item_name[:38]:<40} {order_item.quantity:<5} "
                              f"${order_item.unit_price:<11.2f} ${subtotal:<11.2f}")
                else:
                    print("No items in this order")
        
        elif output_format == 'json':
            result = []
            
            for order in orders:
                # Get order items
                db_order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
                
                # Build order items list
                order_items = []
                for oi in db_order_items:
                    item_name = "Unknown"
                    if oi.item:
                        item_name = oi.item.name
                        
                    order_items.append({
                        'id': oi.id,
                        'item_id': oi.item_id,
                        'item_name': item_name,
                        'quantity': oi.quantity,
                        'unit_price': oi.unit_price,
                        'subtotal': oi.quantity * oi.unit_price
                    })
                
                # Create a serializable dict
                order_dict = {
                    'id': order.id,
                    'order_date': order.order_date.isoformat() if order.order_date else None,
                    'total_amount': order.total_amount,
                    'user_id': order.user_id,
                    'pos_id': order.pos_id,
                    'created_at': order.created_at.isoformat() if order.created_at else None,
                    'updated_at': order.updated_at.isoformat() if order.updated_at else None,
                    'items': order_items
                }
                
                result.append(order_dict)
                
            json_output = json.dumps(result, indent=2)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(json_output)
                print(f"Exported {len(result)} orders to {output_file}")
            else:
                print(json_output)
                
        elif output_format == 'csv':
            # Main CSV file for orders
            order_lines = ["id,order_date,total_amount,user_id,pos_id,created_at,updated_at"]
            
            # Second CSV file for order items
            item_lines = ["order_id,item_id,item_name,quantity,unit_price,subtotal"]
            
            for order in orders:
                order_lines.append(
                    f"{order.id},"
                    f"{order.order_date.isoformat() if order.order_date else ''},"
                    f"{order.total_amount},"
                    f"{order.user_id},"
                    f"\"{order.pos_id if order.pos_id else ''}\"," 
                    f"{order.created_at.isoformat() if order.created_at else ''},"
                    f"{order.updated_at.isoformat() if order.updated_at else ''}"
                )
                
                # Get order items
                db_order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
                
                for oi in db_order_items:
                    item_name = "Unknown"
                    if oi.item:
                        item_name = oi.item.name.replace('"', '""')  # Escape quotes for CSV
                    
                    subtotal = oi.quantity * oi.unit_price
                    
                    item_lines.append(
                        f"{order.id},"
                        f"{oi.item_id},"
                        f"\"{item_name}\","
                        f"{oi.quantity},"
                        f"{oi.unit_price},"
                        f"{subtotal}"
                    )
                
            # Write order CSV
            orders_csv = "\n".join(order_lines)
            items_csv = "\n".join(item_lines)
            
            if output_file:
                # Write main orders file
                with open(output_file, 'w') as f:
                    f.write(orders_csv)
                
                # Write items to a separate file
                items_file = output_file.replace('.csv', '_items.csv')
                with open(items_file, 'w') as f:
                    f.write(items_csv)
                    
                print(f"Exported {len(orders)} orders to {output_file}")
                print(f"Exported order items to {items_file}")
            else:
                print("ORDERS CSV:")
                print(orders_csv)
                print("\nORDER ITEMS CSV:")
                print(items_csv)
                
    except Exception as e:
        print(f"Error extracting order history: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract order history from database')
    parser.add_argument('--user-id', type=int, help='Filter by user ID')
    parser.add_argument('--days', type=int, help='Filter by number of days to look back')
    parser.add_argument('--format', choices=['display', 'json', 'csv'], default='display',
                        help='Output format (default: display)')
    parser.add_argument('--output', type=str, help='Output file path (for json/csv formats)')
    
    args = parser.parse_args()
    
    extract_order_history(args.user_id, args.days, args.format, args.output)
