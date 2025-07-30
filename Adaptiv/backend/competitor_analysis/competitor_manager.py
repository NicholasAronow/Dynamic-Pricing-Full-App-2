#!/usr/bin/env python3
"""
Competitor Management Tool - View and manage competitor data

This script provides utilities to view and manage competitor entities and their menu items
using the new SQLAlchemy-based database models.
"""

import argparse
import logging
from competitor_database import CompetitorDatabase
from restaurant_menu_scraper import MenuScraper


def view_competitors(user_id: int = None, selected_only: bool = False):
    """View all competitors for a user"""
    comp_db = CompetitorDatabase()
    
    if not user_id:
        user_id = comp_db.create_or_get_user()
    
    competitors = comp_db.get_competitor_entities(user_id, selected_only)
    
    if not competitors:
        print("No competitors found.")
        return
    
    print(f"\n📊 Found {len(competitors)} competitor(s):")
    print("-" * 80)
    
    for competitor in competitors:
        items = comp_db.get_competitor_items(competitor_id=competitor.id)
        latest_items = comp_db.get_latest_batch_items(competitor.id)
        
        print(f"🏪 {competitor.name}")
        print(f"   ID: {competitor.id}")
        print(f"   Address: {competitor.address or 'N/A'}")
        print(f"   Category: {competitor.category or 'N/A'}")
        print(f"   Website: {competitor.website or 'N/A'}")
        print(f"   Selected: {'✅' if competitor.is_selected else '❌'}")
        print(f"   Total Items: {len(items)}")
        print(f"   Latest Batch Items: {len(latest_items)}")
        print(f"   Created: {competitor.created_at}")
        print("-" * 80)


def view_competitor_items(competitor_id: int, latest_only: bool = False):
    """View menu items for a specific competitor"""
    comp_db = CompetitorDatabase()
    
    if latest_only:
        items = comp_db.get_latest_batch_items(competitor_id)
        print(f"\n🍽️  Latest menu items for competitor {competitor_id}:")
    else:
        items = comp_db.get_competitor_items(competitor_id=competitor_id)
        print(f"\n🍽️  All menu items for competitor {competitor_id}:")
    
    if not items:
        print("No menu items found.")
        return
    
    print("-" * 80)
    
    for item in items:
        print(f"📝 {item.item_name}")
        print(f"   Price: ${item.price:.2f}" if item.price else "   Price: N/A")
        print(f"   Category: {item.category or 'N/A'}")
        print(f"   Description: {item.description or 'N/A'}")
        print(f"   Batch ID: {item.batch_id}")
        print(f"   Sync Time: {item.sync_timestamp}")
        print("-" * 40)


def scrape_and_save_competitor(restaurant_name: str, location: str = ""):
    """Scrape a restaurant and save as competitor"""
    
    print(f"🔍 Scraping {restaurant_name} in {location}...")
    
    scraper = MenuScraper()
    
    # Search for restaurant
    urls = scraper.search_restaurant(restaurant_name, location)
    
    if not urls:
        print("❌ No URLs found for the restaurant")
        return
    
    print(f"🔗 Found {len(urls)} URLs, trying to scrape menus...")
    
    # Try to scrape from the first few URLs
    menu_items = []
    successful_url = None
    
    for url in urls[:3]:  # Try first 3 URLs
        try:
            items = scraper.scrape_square_menu(url)
            if items:
                menu_items = items
                successful_url = url
                break
        except Exception as e:
            logging.warning(f"Failed to scrape {url}: {e}")
            continue
    
    if not menu_items:
        print("❌ Failed to scrape menu items from any URL")
        return
    
    # Clean up menu items with AI
    cleaned_items = scraper.cleanup_menu_with_ai(menu_items)
    
    # Save to competitor database
    result = scraper.save_competitor_data(
        competitor_name=restaurant_name,
        location=location,
        menu_items=cleaned_items,
        website_url=successful_url
    )
    
    if result['success']:
        print(f"✅ Successfully saved {restaurant_name}!")
        print(f"   📍 Found {result['items_added']} menu items")
        print(f"   🔗 Source: {successful_url}")
        print(f"   🆔 Competitor ID: {result['competitor_id']}")
    else:
        print(f"❌ Failed to save competitor: {result.get('error')}")


def get_summary():
    """Get a summary of all competitors"""
    comp_db = CompetitorDatabase()
    user_id = comp_db.create_or_get_user()
    
    summary = comp_db.get_competitor_summary(user_id)
    
    print("\n📊 Competitor Analysis Summary")
    print("=" * 50)
    print(f"Total Competitors: {summary['total_competitors']}")
    print(f"Selected Competitors: {summary['selected_competitors']}")
    print("\nCompetitor Details:")
    print("-" * 50)
    
    for comp in summary['competitors']:
        status = "✅ Selected" if comp['is_selected'] else "⭕ Not Selected"
        last_sync = comp['last_sync'].strftime('%Y-%m-%d %H:%M') if comp['last_sync'] else 'Never'
        
        print(f"🏪 {comp['name']} ({comp['category'] or 'N/A'})")
        print(f"   Status: {status}")
        print(f"   Items: {comp['item_count']}")
        print(f"   Last Sync: {last_sync}")
        print("-" * 30)


def main():
    parser = argparse.ArgumentParser(description='Manage competitor data')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # View competitors command
    view_parser = subparsers.add_parser('view', help='View competitors')
    view_parser.add_argument('--selected-only', action='store_true', help='Show only selected competitors')
    view_parser.add_argument('--user-id', type=int, help='User ID (optional)')
    
    # View items command
    items_parser = subparsers.add_parser('items', help='View competitor items')
    items_parser.add_argument('competitor_id', type=int, help='Competitor ID')
    items_parser.add_argument('--latest-only', action='store_true', help='Show only latest batch')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape and save competitor')
    scrape_parser.add_argument('restaurant_name', help='Restaurant name to scrape')
    scrape_parser.add_argument('--location', default='', help='Location (optional)')
    
    # Summary command
    subparsers.add_parser('summary', help='Get competitor summary')
    
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    logging.basicConfig(level=args.log_level, format='%(levelname)s %(message)s')
    
    if args.command == 'view':
        view_competitors(args.user_id, args.selected_only)
    elif args.command == 'items':
        view_competitor_items(args.competitor_id, args.latest_only)
    elif args.command == 'scrape':
        scrape_and_save_competitor(args.restaurant_name, args.location)
    elif args.command == 'summary':
        get_summary()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
