#!/usr/bin/env python3
"""
Menu Manager CLI - Tool for managing restaurant menu database
"""

import argparse
import json
import sys
import os
from datetime import datetime
from menu_database import MenuDatabase

def list_restaurants(db: MenuDatabase, restaurant_type: str = None, location: str = None):
    """List restaurants in the database"""
    if restaurant_type or location:
        restaurants = db.get_restaurants_by_search(restaurant_type or "", location or "")
        print(f"\nRestaurants for {restaurant_type or 'all types'} in {location or 'all locations'}:")
    else:
        # Get all restaurants by querying with empty filters
        export_data = db.export_menu_data()
        restaurants = export_data['restaurants']
        print(f"\nAll restaurants in database:")
    
    if not restaurants:
        print("No restaurants found.")
        return
    
    for restaurant in restaurants:
        if isinstance(restaurant, dict) and 'name' in restaurant:
            # From export_menu_data - use the actual restaurant ID
            restaurant_id = restaurant.get('id', 'Unknown')
            print(f"{restaurant_id}. {restaurant['name']}")
            print(f"   URL: {restaurant['url']}")
            print(f"   Platform: {restaurant['platform']}")
            print(f"   Last Updated: {restaurant['last_updated']}")
            print(f"   Menu Items: {len(restaurant.get('menu_items', []))}")
        else:
            # From get_restaurants_by_search - use the actual restaurant ID
            restaurant_id = restaurant.get('id', 'Unknown')
            print(f"{restaurant_id}. {restaurant.get('name', 'Unknown')}")
            print(f"   URL: {restaurant.get('url', 'N/A')}")
            print(f"   Platform: {restaurant.get('platform', 'N/A')}")
            print(f"   Last Updated: {restaurant.get('last_updated', 'N/A')}")
            print(f"   Menu Items: {restaurant.get('menu_item_count', 0)}")
        print()


def show_menu(db: MenuDatabase, restaurant_id: int):
    """Show menu items for a specific restaurant"""
    menu_items = db.get_menu_items(restaurant_id)
    
    if not menu_items:
        print(f"No menu items found for restaurant ID {restaurant_id}")
        return
    
    print(f"\nMenu items for restaurant ID {restaurant_id}:")
    print("-" * 80)
    
    for i, item in enumerate(menu_items, 1):
        print(f"{i}. {item['name']} - {item['price']}")
        if item['description']:
            print(f"   {item['description']}")
        print()


def show_search_history(db: MenuDatabase, limit: int = 10):
    """Show recent search history"""
    searches = db.get_search_history(limit)
    
    if not searches:
        print("No search history found.")
        return
    
    print(f"\nRecent search history (last {limit}):")
    print("-" * 80)
    
    for search in searches:
        print(f"ID: {search['id']} | {search['restaurant_type']} in {search['location']}")
        print(f"   Date: {search['search_timestamp']}")
        print(f"   Results: {search['successful_extractions']}/{search['total_sites_found']} sites")
        print()


def export_data(db: MenuDatabase, output_file: str, restaurant_type: str = None, location: str = None):
    """Export menu data to JSON file"""
    data = db.export_menu_data(restaurant_type, location)
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Exported {len(data['restaurants'])} restaurants to {output_file}")





def fix_restaurant_names(db: MenuDatabase):
    """Fix all restaurant names using AI extraction"""
    print("Fixing restaurant names using AI extraction...")
    fixed_count = db.fix_restaurant_names()
    print(f"Successfully fixed {fixed_count} restaurant names.")


def standardize_menu(db: MenuDatabase, restaurant_id: int = None):
    """Standardize menu items using AI"""
    if restaurant_id:
        print(f"Standardizing menu for restaurant ID {restaurant_id}...")
        success = db.standardize_restaurant_menu(restaurant_id)
        if success:
            print(f"Successfully standardized menu for restaurant {restaurant_id}")
        else:
            print(f"Failed to standardize menu for restaurant {restaurant_id}")
    else:
        print("Standardizing all restaurant menus...")
        results = db.standardize_all_menus()
        print(f"Processed: {results['processed']}, Successful: {results['successful']}, Failed: {results['failed']}")


def clear_database(db: MenuDatabase):
    """Clear all data from the database"""
    print("⚠️  WARNING: This will delete ALL data from the database!")
    confirm = input("Type 'DELETE ALL' to confirm: ")

    if confirm == "DELETE ALL":
        print("Clearing database...")
        results = db.clear_database()
        print(f"✅ Database cleared successfully!")
        print(f"   • {results['restaurants_deleted']} restaurants deleted")
        print(f"   • {results['menu_items_deleted']} menu items deleted")
        print(f"   • {results['searches_deleted']} searches deleted")
    else:
        print("❌ Database clear cancelled.")


def remove_duplicates(db: MenuDatabase):
    """Remove duplicate restaurants from the database"""
    print("Removing duplicate restaurants...")
    removed_count = db.remove_duplicate_restaurants()
    if removed_count > 0:
        print(f"✅ Removed {removed_count} duplicate restaurants")
    else:
        print("✅ No duplicate restaurants found")


def main():
    parser = argparse.ArgumentParser(description='Restaurant Menu Database Manager')
    parser.add_argument('--db-path', default='restaurant_menus.db', help='Database file path')
    parser.add_argument('--openai-api-key', help='OpenAI API key (or set OPENAI_API_KEY env var)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List restaurants
    list_parser = subparsers.add_parser('list', help='List restaurants')
    list_parser.add_argument('--type', help='Filter by restaurant type')
    list_parser.add_argument('--location', help='Filter by location')
    
    # Show menu
    menu_parser = subparsers.add_parser('menu', help='Show menu for restaurant')
    menu_parser.add_argument('restaurant_id', type=int, help='Restaurant ID')
    
    # Search history
    history_parser = subparsers.add_parser('history', help='Show search history')
    history_parser.add_argument('--limit', type=int, default=10, help='Number of recent searches to show')
    
    # Export data
    export_parser = subparsers.add_parser('export', help='Export menu data')
    export_parser.add_argument('output_file', help='Output JSON file')
    export_parser.add_argument('--type', help='Filter by restaurant type')
    export_parser.add_argument('--location', help='Filter by location')
    


    # Fix restaurant names
    fix_names_parser = subparsers.add_parser('fix-names', help='Fix restaurant names using AI')

    # Standardize menus
    standardize_parser = subparsers.add_parser('standardize', help='Standardize menu items using AI')
    standardize_parser.add_argument('--restaurant-id', type=int, help='Specific restaurant ID to standardize (optional)')
    standardize_parser.add_argument('--all', action='store_true', help='Standardize all restaurant menus')

    # Clear database
    clear_parser = subparsers.add_parser('clear', help='Clear all data from database (DESTRUCTIVE)')

    # Remove duplicates
    dedup_parser = subparsers.add_parser('remove-duplicates', help='Remove duplicate restaurants')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize database with OpenAI API key
    db = MenuDatabase(args.db_path, args.openai_api_key)
    
    if args.command == 'list':
        list_restaurants(db, args.type, args.location)
    
    elif args.command == 'menu':
        show_menu(db, args.restaurant_id)
    
    elif args.command == 'history':
        show_search_history(db, args.limit)
    
    elif args.command == 'export':
        export_data(db, args.output_file, args.type, args.location)
    


    elif args.command == 'fix-names':
        fix_restaurant_names(db)

    elif args.command == 'standardize':
        if args.restaurant_id:
            standardize_menu(db, args.restaurant_id)
        elif args.all:
            standardize_menu(db)
        else:
            print("Please specify either --restaurant-id <ID> or --all")
            parser.print_help()

    elif args.command == 'clear':
        clear_database(db)

    elif args.command == 'remove-duplicates':
        remove_duplicates(db)


if __name__ == '__main__':
    main()
