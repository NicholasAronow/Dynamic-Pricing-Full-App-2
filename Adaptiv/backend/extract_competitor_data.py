#!/usr/bin/env python3
"""
Extract competitor data from the database
"""
from database import SessionLocal
import models
import json
import sys
from datetime import datetime, timedelta
from sqlalchemy import func, desc

def extract_competitor_data(user_id=None, competitor_name=None, days=None, output_format='display', output_file=None):
    """
    Extract competitor data from the database
    
    Args:
        user_id: Optional user ID to filter by, None for all users
        competitor_name: Optional competitor name to filter by
        days: Optional number of days to look back
        output_format: 'display', 'json', or 'csv'
        output_file: Optional file path to save output
    """
    db = SessionLocal()
    try:
        # First get a list of unique competitors
        competitor_query = db.query(models.CompetitorItem.competitor_name, 
                                    func.count(models.CompetitorItem.id).label('item_count'),
                                    func.max(models.CompetitorItem.sync_timestamp).label('last_sync')) \
                             .group_by(models.CompetitorItem.competitor_name)
                             
        # Filter by user_id if specified
        if user_id:
            # Get batch IDs associated with the user from CompetitorReport
            # Since CompetitorReport doesn't directly have batch_id, we need to find another way
            # Look for pricing recommendations for this user
            user_batch_ids = db.query(models.PricingRecommendation.batch_id)\
                            .filter(models.PricingRecommendation.user_id == user_id)\
                            .distinct().all()
            
            if user_batch_ids:
                # Convert list of tuples to list of batch_ids
                batch_ids = [bid[0] for bid in user_batch_ids]
                competitor_query = competitor_query.filter(models.CompetitorItem.batch_id.in_(batch_ids))
            else:
                # No batches found for this user, return empty result
                return
                             
        # Filter competitors if requested
        if competitor_name:
            competitor_query = competitor_query.filter(models.CompetitorItem.competitor_name == competitor_name)
            
        # Filter by date if requested
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            competitor_query = competitor_query.filter(models.CompetitorItem.sync_timestamp >= cutoff_date)
        
        # Execute query to get competitors list
        competitors = competitor_query.all()
        
        if not competitors:
            print(f"No competitors found{f' for competitor {competitor_name}' if competitor_name else ''}"
                 f"{f' in the last {days} days' if days else ''}.")
            return
            
        # Process results based on format
        if output_format == 'display':
            print(f"\n{'='*100}")
            print(f"COMPETITOR DATA{f' FOR {competitor_name}' if competitor_name else ''}"
                 f"{f' (LAST {days} DAYS)' if days else ''} ({len(competitors)} competitors)")
            print(f"{'='*100}")
            
            # Display each competitor's summary
            for competitor_info in competitors:
                competitor = competitor_info[0]
                item_count = competitor_info[1]
                last_sync = competitor_info[2].strftime('%Y-%m-%d %H:%M') if competitor_info[2] else 'Unknown'
                
                print(f"\n## {competitor} ({item_count} items)")
                print(f"Last sync: {last_sync}")
                print("-" * 100)
                
                # Get competitor items
                items_query = db.query(models.CompetitorItem) \
                               .filter(models.CompetitorItem.competitor_name == competitor)
                
                # Apply user filter if specified
                if user_id:
                    # Get batch IDs associated with the user
                    user_batch_ids = db.query(models.PricingRecommendation.batch_id)\
                                    .filter(models.PricingRecommendation.user_id == user_id)\
                                    .distinct().all()
                    
                    if user_batch_ids:
                        batch_ids = [bid[0] for bid in user_batch_ids]
                        items_query = items_query.filter(models.CompetitorItem.batch_id.in_(batch_ids))
                
                # Apply additional filters
                if days:
                    items_query = items_query.filter(models.CompetitorItem.sync_timestamp >= cutoff_date)
                    
                # Get latest items first
                items = items_query.order_by(desc(models.CompetitorItem.sync_timestamp)).all()
                
                # Group by category
                categories = {}
                for item in items:
                    category = item.category or 'Uncategorized'
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(item)
                
                # Print items by category
                for category, cat_items in categories.items():
                    print(f"\n### {category} ({len(cat_items)} items)")
                    print(f"{'Item Name':<40} {'Price':<10} {'Batch':<20} {'Sync Date':<20}")
                    print("-" * 100)
                    
                    # Show the first 10 items per category
                    for item in cat_items[:10]:
                        sync_date = item.sync_timestamp.strftime('%Y-%m-%d %H:%M') if item.sync_timestamp else 'Unknown'
                        batch_id_display = item.batch_id[:18] if item.batch_id else '-'
                        # Ensure values can't be None before display formatting
                        item_name = item.item_name if item.item_name else ''
                        batch_id_display = item.batch_id[:18] if item.batch_id else '-'
                        price_display = f"${item.price:<9.2f}" if item.price is not None else "$-.--"
                        print(f"{item_name[:38]:<40} {price_display} {batch_id_display:<20} {sync_date:<20}")
                    
                    if len(cat_items) > 10:
                        print(f"... and {len(cat_items) - 10} more items in this category")
        
        elif output_format == 'json':
            result = []
            
            for competitor_info in competitors:
                competitor = competitor_info[0]
                
                # Get competitor items
                items_query = db.query(models.CompetitorItem) \
                               .filter(models.CompetitorItem.competitor_name == competitor)
                
                # Apply additional filters
                if days:
                    cutoff_date = datetime.now() - timedelta(days=days)
                    items_query = items_query.filter(models.CompetitorItem.sync_timestamp >= cutoff_date)
                
                items = items_query.all()
                
                # Format items
                formatted_items = []
                for item in items:
                    formatted_items.append({
                        'id': item.id,
                        'item_name': item.item_name,
                        'description': item.description,
                        'category': item.category,
                        'price': item.price,
                        'similarity_score': item.similarity_score,
                        'url': item.url,
                        'batch_id': item.batch_id,
                        'sync_timestamp': item.sync_timestamp.isoformat() if item.sync_timestamp else None,
                        'created_at': item.created_at.isoformat() if item.created_at else None,
                        'updated_at': item.updated_at.isoformat() if item.updated_at else None
                    })
                
                # Create competitor object
                competitor_dict = {
                    'name': competitor,
                    'item_count': len(items),
                    'last_sync': competitor_info[2].isoformat() if competitor_info[2] else None,
                    'items': formatted_items
                }
                
                result.append(competitor_dict)
                
            json_output = json.dumps(result, indent=2)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(json_output)
                print(f"Exported {len(result)} competitors to {output_file}")
            else:
                print(json_output)
                
        elif output_format == 'csv':
            # CSV header
            csv_lines = ["competitor_name,item_name,category,price,similarity_score,url,batch_id,sync_timestamp,created_at"]
            
            for competitor_info in competitors:
                competitor = competitor_info[0]
                
                # Get competitor items
                items_query = db.query(models.CompetitorItem) \
                               .filter(models.CompetitorItem.competitor_name == competitor)
                
                # Apply additional filters
                if days:
                    cutoff_date = datetime.now() - timedelta(days=days)
                    items_query = items_query.filter(models.CompetitorItem.sync_timestamp >= cutoff_date)
                
                items = items_query.all()
                
                # Add each item to CSV
                for item in items:
                    # Use a more reliable approach by avoiding nested quotes in f-strings
                    comp_name_escaped = item.competitor_name.replace('"', '""') if item.competitor_name else ''
                    item_name_escaped = item.item_name.replace('"', '""') if item.item_name else ''
                    category_escaped = item.category.replace('"', '""') if item.category else ''
                    url_escaped = item.url.replace('"', '""') if item.url else ''
                    
                    csv_lines.append(
                        f'"{comp_name_escaped}",'
                        f'"{item_name_escaped}",'
                        f'"{category_escaped}",'
                        f'{item.price},'
                        f'{item.similarity_score if item.similarity_score else ""},'
                        f'"{url_escaped}",'
                        f'"{item.batch_id}",'
                        f'{item.sync_timestamp.isoformat() if item.sync_timestamp else ""},'
                        f'{item.created_at.isoformat() if item.created_at else ""}'
                    )
                
            csv_output = "\n".join(csv_lines)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(csv_output)
                print(f"Exported competitor items to {output_file}")
            else:
                print(csv_output)
                
    except Exception as e:
        print(f"Error extracting competitor data: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract competitor data from database')
    parser.add_argument('--user-id', type=int, help='Filter by user ID')
    parser.add_argument('--competitor', type=str, help='Filter by competitor name')
    parser.add_argument('--days', type=int, help='Filter by number of days to look back')
    parser.add_argument('--format', choices=['display', 'json', 'csv'], default='display',
                        help='Output format (default: display)')
    parser.add_argument('--output', type=str, help='Output file path (for json/csv formats)')
    
    args = parser.parse_args()
    
    extract_competitor_data(args.user_id, args.competitor, args.days, args.format, args.output)
