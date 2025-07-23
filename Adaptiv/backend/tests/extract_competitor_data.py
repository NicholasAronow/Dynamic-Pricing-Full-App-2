#!/usr/bin/env python3
"""
Extract competitor data from the database
"""
import sys
import os
# Add the backend directory to the Python path and change working directory
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)
# Change to backend directory so database path is correct
os.chdir(backend_dir)
from config.database import SessionLocal
from models import CompetitorItem, PricingRecommendation
import json
from datetime import datetime, timedelta
from sqlalchemy import func, desc

def extract_competitor_data(user_id=None, competitor_name=None, days=None, output_format='display', output_file=None, fallback_to_all=True):
    """
    Extract competitor data from the database
    
    Args:
        user_id: Optional user ID to filter by, None for all users
        competitor_name: Optional competitor name to filter by
        days: Optional number of days to look back
        output_format: 'display', 'json', or 'csv'
        output_file: Optional file path to save output
        fallback_to_all: Whether to fall back to all competitor data if no user-specific data is found
    """
    db = SessionLocal()
    try:
        # Track whether we're using the fallback format
        using_fallback_format = False
        
        # First get a list of unique competitors
        competitor_query = db.query(CompetitorItem.competitor_name, 
                                    func.count(CompetitorItem.id).label('item_count'),
                                    func.max(CompetitorItem.sync_timestamp).label('last_sync')) \
                            .group_by(CompetitorItem.competitor_name)
                           
        # Filter by user_id if specified
        if user_id:
            # Look for pricing recommendations or items for this user
            print(f"Looking up batch IDs for user {user_id}...")
            
            # Try first with PricingRecommendation
            user_batch_ids = db.query(PricingRecommendation.batch_id)\
                            .filter(PricingRecommendation.user_id == user_id)\
                            .distinct().all()
                            
            if not user_batch_ids:
                print("No batches found in PricingRecommendation, will skip user filtering")
            else:
                # Convert list of tuples to list of batch_ids
                batch_ids = [bid[0] for bid in user_batch_ids]
                print(f"Found {len(batch_ids)} batch IDs for user {user_id}")
                competitor_query = competitor_query.filter(CompetitorItem.batch_id.in_(batch_ids))
                           
        # Filter competitors if requested
        if competitor_name:
            competitor_query = competitor_query.filter(CompetitorItem.competitor_name == competitor_name)
            
        # Filter by date if requested
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            competitor_query = competitor_query.filter(CompetitorItem.sync_timestamp >= cutoff_date)
        
        # Execute query to get competitors list
        competitors = competitor_query.all()
        
        if not competitors:
            if user_id and fallback_to_all:
                print(f"No competitors found for user {user_id}. Falling back to showing all competitor data.")
                # Start a new query without user_id filter
                competitor_query = db.query(CompetitorItem).distinct(CompetitorItem.competitor_name)
                
                # Re-apply other filters
                if competitor_name:
                    competitor_query = competitor_query.filter(CompetitorItem.competitor_name == competitor_name)
                    
                if days:
                    cutoff_date = datetime.now() - timedelta(days=days)
                    competitor_query = competitor_query.filter(CompetitorItem.sync_timestamp >= cutoff_date)
                    
                competitors = competitor_query.all()
                using_fallback_format = True  # Flag that we're using the fallback format
                
                if not competitors:
                    print("Still no competitors found after removing user filter.")
                    return
                    
                print(f"Found {len(competitors)} competitors (all users)")
            else:
                print(f"No competitors found{f' for competitor {competitor_name}' if competitor_name else ''}"
                     f"{f' in the last {days} days' if days else ''}{f' for user {user_id}' if user_id else ''}.")
                return
        
        print(f"Found {len(competitors)} competitors{f' for user {user_id}' if user_id else ''}")
            
        # Process results based on format
        if output_format == 'display':
            print(f"\n{'='*100}")
            print(f"COMPETITOR DATA{f' FOR {competitor_name}' if competitor_name else ''}"
                 f"{f' (LAST {days} DAYS)' if days else ''} ({len(competitors)} competitors)")
            print(f"{'='*100}")
            
            # Display each competitor's summary
            for competitor_info in competitors:
                if using_fallback_format:
                    # In fallback format, we get CompetitorItem objects directly
                    competitor = competitor_info.competitor_name
                    # Get item count and last sync separately
                    item_count_query = db.query(func.count(CompetitorItem.id))\
                                       .filter(CompetitorItem.competitor_name == competitor)
                    item_count = item_count_query.scalar() or 0
                    
                    last_sync_query = db.query(func.max(CompetitorItem.sync_timestamp))\
                                      .filter(CompetitorItem.competitor_name == competitor)
                    last_sync_date = last_sync_query.scalar()
                    last_sync = last_sync_date.strftime('%Y-%m-%d %H:%M') if last_sync_date else 'Unknown'
                else:
                    # In original format, we get tuples with (name, count, timestamp)
                    competitor = competitor_info[0]
                    item_count = competitor_info[1]
                    last_sync = competitor_info[2].strftime('%Y-%m-%d %H:%M') if competitor_info[2] else 'Unknown'
                
                print(f"\n## Competitor:{competitor} - ({item_count} items)")
                print(f"Last sync: {last_sync}")
                print("-" * 100)
                
                # Get competitor items
                items_query = db.query(CompetitorItem) \
                               .filter(CompetitorItem.competitor_name == competitor)
                
                # Apply user filter if specified
                if user_id:
                    # Get batch IDs associated with the user
                    user_batch_ids = db.query(PricingRecommendation.batch_id)\
                                    .filter(PricingRecommendation.user_id == user_id)\
                                    .distinct().all()
                    
                    if user_batch_ids:
                        batch_ids = [bid[0] for bid in user_batch_ids]
                        items_query = items_query.filter(CompetitorItem.batch_id.in_(batch_ids))
                
                # Apply additional filters
                if days:
                    cutoff_date = datetime.now() - timedelta(days=days)
                    items_query = items_query.filter(CompetitorItem.sync_timestamp >= cutoff_date)
                    
                # Get latest items first
                items = items_query.order_by(desc(CompetitorItem.sync_timestamp)).all()
                
                # Group by category
                categories = {}
                for item in items:
                    category = item.category or 'Uncategorized'
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(item)
        
        elif output_format == 'json':
            result = []
            
            for competitor_info in competitors:
                if using_fallback_format:
                    # In fallback format, we get CompetitorItem objects directly
                    competitor = competitor_info.competitor_name
                else:
                    # In original format, we get tuples with (name, count, timestamp)
                    competitor = competitor_info[0]
                
                # Get competitor items
                items_query = db.query(CompetitorItem) \
                               .filter(CompetitorItem.competitor_name == competitor)
                
                # Apply additional filters
                if days:
                    cutoff_date = datetime.now() - timedelta(days=days)
                    items_query = items_query.filter(CompetitorItem.sync_timestamp >= cutoff_date)
                
                items = items_query.all()
                
                # Format items
                formatted_items = []
                for item in items:
                    formatted_items.append({
                        'id': item.id,
                        'item_name': item.item_name,
                        'description': item.description,
                        'price': float(item.price) if item.price is not None else None,
                        'category': item.category,
                        # Note: 'subcategory' doesn't exist in the model
                        'url': item.url,
                        'batch_id': item.batch_id,
                        'sync_timestamp': item.sync_timestamp.isoformat() if item.sync_timestamp else None
                    })
                
                # Group by category
                categories = {}
                for item in formatted_items:
                    category = item['category'] or 'Uncategorized'
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(item)
                
                result.append({
                    'name': competitor,
                    'item_count': len(formatted_items),
                    'categories': categories
                })
            
            # Output JSON result
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(result, f, indent=2)
            else:
                print(json.dumps(result, indent=2))
        
        elif output_format == 'csv':
            csv_lines = ["competitor_name,item_id,item_name,description,price,category,subcategory,url,batch_id,sync_timestamp"]
            
            for competitor_info in competitors:
                if using_fallback_format:
                    # In fallback format, we get CompetitorItem objects directly
                    competitor = competitor_info.competitor_name
                else:
                    # In original format, we get tuples with (name, count, timestamp)
                    competitor = competitor_info[0]
                
                # Get competitor items
                items_query = db.query(CompetitorItem) \
                               .filter(CompetitorItem.competitor_name == competitor)
                
                # Apply additional filters
                if days:
                    cutoff_date = datetime.now() - timedelta(days=days)
                    items_query = items_query.filter(CompetitorItem.sync_timestamp >= cutoff_date)
                
                items = items_query.all()
                
                for item in items:
                    # Safely handle potential None values and escaping for CSV
                    name_escaped = item.item_name.replace('"', '""') if item.item_name else ''
                    description_escaped = item.description.replace('"', '""') if item.description else ''
                    category_escaped = item.category.replace('"', '""') if item.category else ''
                    # No subcategory field in the model
                    url_escaped = item.url.replace('"', '""') if item.url else ''
                    batch_id_escaped = item.batch_id.replace('"', '""') if item.batch_id else ''
                    competitor_escaped = competitor.replace('"', '""')
                    
                    # Build one CSV line at a time (no string concatenation issues)
                    csv_line = f'"{competitor_escaped}",{item.id},"{name_escaped}","{description_escaped}",'
                    csv_line += f'{item.price if item.price is not None else ""},"{category_escaped}",'
                    csv_line += f'"","{url_escaped}","{batch_id_escaped}",'
                    csv_line += f'{item.sync_timestamp.isoformat() if item.sync_timestamp else ""}'
                    
                    csv_lines.append(csv_line)
            
            # Output CSV result
            csv_output = "\n".join(csv_lines)
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(csv_output)
            else:
                print(csv_output)
        
    finally:
        db.close()

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract competitor data from database')
    parser.add_argument('--user-id', type=int, help='Filter by user ID')
    parser.add_argument('--competitor', help='Filter by competitor name')
    parser.add_argument('--days', type=int, help='Filter by number of days to look back')
    parser.add_argument('--format', choices=['display', 'json', 'csv'], default='display',
                        help='Output format (default: display)')
    parser.add_argument('--output', help='Output file path (if not provided, print to console)')
    parser.add_argument('--no-fallback', action='store_true', 
                        help='Do not fall back to showing all competitor data if no user-specific data is found')
    
    args = parser.parse_args()
    
    try:
        extract_competitor_data(
            args.user_id, 
            args.competitor, 
            args.days, 
            args.format, 
            args.output,
            fallback_to_all=not args.no_fallback
        )
    except Exception as e:
        print(f"\nError extracting competitor data: {e}")
        import traceback
        traceback.print_exc()
