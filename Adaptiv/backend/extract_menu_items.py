#!/usr/bin/env python3
"""
Extract all menu items for a specific user or all users
"""
from database import SessionLocal
import models
import json
import sys

def extract_menu_items(user_id=None, output_format='display', output_file=None):
    """
    Extract menu items for a specific user or all users
    
    Args:
        user_id: Optional user ID to filter by, None for all users
        output_format: 'display', 'json', or 'csv'
        output_file: Optional file path to save output
    """
    db = SessionLocal()
    try:
        # Build the query
        query = db.query(models.Item)
        if user_id:
            query = query.filter(models.Item.user_id == user_id)
            
        # Execute query
        items = query.all()
        
        if not items:
            print(f"No menu items found{f' for user ID {user_id}' if user_id else ''}.")
            return
            
        # Process results based on format
        if output_format == 'display':
            print(f"\n{'='*80}")
            print(f"MENU ITEMS{f' FOR USER {user_id}' if user_id else ''} ({len(items)} total)")
            print(f"{'='*80}")
            
            # Group by category
            categories = {}
            for item in items:
                if item.category not in categories:
                    categories[item.category] = []
                categories[item.category].append(item)
                
            # Display by category
            for category, cat_items in categories.items():
                print(f"\n## {category or 'Uncategorized'} ({len(cat_items)} items)")
                print("-" * 80)
                print(f"{'ID':<6} {'Name':<30} {'Price':<10} {'Cost':<10} {'Margin %':<10}")
                print("-" * 80)
                
                for item in cat_items:
                    margin = "-"
                    if item.cost and item.current_price:
                        margin_val = (item.current_price - item.cost) / item.current_price * 100
                        margin = f"{margin_val:.1f}%"
                        
                    print(f"{item.id:<6} {item.name[:28]:<30} ${item.current_price:<9.2f} "
                          f"{'$' + str(round(item.cost, 2)) if item.cost else 'N/A':<10} {margin:<10}")
        
        elif output_format == 'json':
            result = []
            for item in items:
                # Create a serializable dict
                item_dict = {
                    'id': item.id,
                    'name': item.name,
                    'category': item.category,
                    'description': item.description,
                    'current_price': item.current_price,
                    'cost': item.cost,
                    'user_id': item.user_id,
                    'pos_id': item.pos_id,
                    'created_at': item.created_at.isoformat() if item.created_at else None,
                    'updated_at': item.updated_at.isoformat() if item.updated_at else None,
                }
                result.append(item_dict)
                
            json_output = json.dumps(result, indent=2)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(json_output)
                print(f"Exported {len(result)} items to {output_file}")
            else:
                print(json_output)
                
        elif output_format == 'csv':
            # CSV header
            csv_lines = ["id,name,category,description,current_price,cost,user_id,pos_id,created_at,updated_at"]
            
            for item in items:
                # Use a more reliable approach for escaping - pre-process the strings
                name_escaped = item.name.replace('"', '""') if item.name else ''
                category_escaped = item.category.replace('"', '""') if item.category else ''
                description_escaped = item.description.replace('"', '""') if item.description else ''
                pos_id_escaped = item.pos_id if item.pos_id else ''
                
                csv_lines.append(
                    f"{item.id},"
                    f'"{name_escaped}",'
                    f'"{category_escaped}",'
                    f'"{description_escaped}",'
                    f"{item.current_price},"
                    f"{item.cost if item.cost else ''},"
                    f"{item.user_id},"
                    f'"{pos_id_escaped}",'
                    f"{item.created_at.isoformat() if item.created_at else ''},"
                    f"{item.updated_at.isoformat() if item.updated_at else ''}"
                )
                
            csv_output = "\n".join(csv_lines)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(csv_output)
                print(f"Exported {len(items)} items to {output_file}")
            else:
                print(csv_output)
                
    except Exception as e:
        print(f"Error extracting menu items: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract menu items from database')
    parser.add_argument('--user-id', type=int, help='Filter by user ID')
    parser.add_argument('--format', choices=['display', 'json', 'csv'], default='display',
                        help='Output format (default: display)')
    parser.add_argument('--output', type=str, help='Output file path (for json/csv formats)')
    
    args = parser.parse_args()
    
    extract_menu_items(args.user_id, args.format, args.output)
