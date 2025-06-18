#!/usr/bin/env python3
"""
Extract pricing recommendations for a specific user or all users
"""
from database import SessionLocal
import models
import json
import sys
from datetime import datetime, timedelta
from sqlalchemy import desc, func

def extract_pricing_recommendations(user_id=None, days=None, output_format='display', output_file=None):
    """
    Extract pricing recommendations for a specific user or all users
    
    Args:
        user_id: Optional user ID to filter by, None for all users
        days: Optional number of days to look back
        output_format: 'display', 'json', or 'csv'
        output_file: Optional file path to save output
    """
    db = SessionLocal()
    try:
        # Get unique batches of recommendations
        batch_query = db.query(
            models.PricingRecommendation.batch_id,
            models.PricingRecommendation.user_id,
            models.PricingRecommendation.recommendation_date,
            models.User.email,
            func.count(models.PricingRecommendation.id).label('rec_count')
        ).join(
            models.User, models.PricingRecommendation.user_id == models.User.id
        ).group_by(
            models.PricingRecommendation.batch_id,
            models.PricingRecommendation.user_id,
            models.PricingRecommendation.recommendation_date,
            models.User.email
        )
        
        # Apply filters
        if user_id:
            batch_query = batch_query.filter(models.PricingRecommendation.user_id == user_id)
            
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            batch_query = batch_query.filter(models.PricingRecommendation.recommendation_date >= cutoff_date)
            
        # Sort by date (newest first)
        batch_query = batch_query.order_by(desc(models.PricingRecommendation.recommendation_date))
        
        # Execute batch query
        batches = batch_query.all()
        
        if not batches:
            print(f"No pricing recommendations found{f' for user ID {user_id}' if user_id else ''}{f' in the last {days} days' if days else ''}.")
            return
            
        # Process results based on format
        if output_format == 'display':
            print(f"\n{'='*100}")
            print(f"PRICING RECOMMENDATIONS{f' FOR USER {user_id}' if user_id else ''}{f' (LAST {days} DAYS)' if days else ''}")
            print(f"{'='*100}")
            
            # Display each batch
            for batch in batches:
                batch_id = batch.batch_id
                user = batch.user_id
                email = batch.email
                rec_date = batch.recommendation_date.strftime('%Y-%m-%d %H:%M') if batch.recommendation_date else 'Unknown'
                rec_count = batch.rec_count
                
                print(f"\n## Batch: {batch_id}")
                print(f"User: {email} (ID: {user})")
                print(f"Date: {rec_date}")
                print(f"Recommendations: {rec_count}")
                print("-" * 100)
                
                # Get recommendations for this batch
                recs = db.query(models.PricingRecommendation) \
                        .filter(models.PricingRecommendation.batch_id == batch_id) \
                        .order_by(desc(models.PricingRecommendation.price_change_percent)) \
                        .all()
                
                print(f"{'Item Name':<40} {'Current':<10} {'Rec.':<10} {'Change':<10} {'Status':<12}")
                print("-" * 100)
                
                # Show all recommendations in this batch
                for rec in recs:
                    # Get item name
                    item_name = "Unknown"
                    if rec.item:
                        item_name = rec.item.name
                    
                    # Calculate change percentage
                    change_pct = rec.price_change_percent * 100
                    change_str = f"{change_pct:+.1f}%"
                    
                    print(f"{item_name[:38]:<40} ${rec.current_price:<9.2f} ${rec.recommended_price:<9.2f} "
                          f"{change_str:<10} {rec.implementation_status:<12}")
                
                print("\n")
        
        elif output_format == 'json':
            result = []
            
            for batch in batches:
                batch_id = batch.batch_id
                
                # Get recommendations for this batch
                recs = db.query(models.PricingRecommendation) \
                        .filter(models.PricingRecommendation.batch_id == batch_id) \
                        .all()
                
                # Format recommendations
                formatted_recs = []
                for rec in recs:
                    # Get item name
                    item_name = "Unknown"
                    if rec.item:
                        item_name = rec.item.name
                        
                    formatted_recs.append({
                        'id': rec.id,
                        'item_id': rec.item_id,
                        'item_name': item_name,
                        'current_price': rec.current_price,
                        'recommended_price': rec.recommended_price,
                        'price_change_amount': rec.price_change_amount,
                        'price_change_percent': rec.price_change_percent,
                        'strategy_type': rec.strategy_type,
                        'confidence_score': rec.confidence_score,
                        'rationale': rec.rationale,
                        'implementation_status': rec.implementation_status,
                        'implemented_at': rec.implemented_at.isoformat() if rec.implemented_at else None,
                        'implemented_price': rec.implemented_price
                    })
                
                # Create batch object
                batch_dict = {
                    'batch_id': batch_id,
                    'user_id': batch.user_id,
                    'user_email': batch.email,
                    'recommendation_date': batch.recommendation_date.isoformat() if batch.recommendation_date else None,
                    'recommendation_count': batch.rec_count,
                    'recommendations': formatted_recs
                }
                
                result.append(batch_dict)
                
            json_output = json.dumps(result, indent=2)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(json_output)
                print(f"Exported {len(result)} recommendation batches to {output_file}")
            else:
                print(json_output)
                
        elif output_format == 'csv':
            # CSV header
            csv_lines = ["batch_id,user_id,user_email,recommendation_date,item_id,item_name,current_price,"
                        "recommended_price,price_change_amount,price_change_percent,strategy_type,confidence_score,"
                        "implementation_status,implemented_at,implemented_price,rationale"]
            
            for batch in batches:
                batch_id = batch.batch_id
                user_id = batch.user_id
                user_email = batch.email
                rec_date = batch.recommendation_date.isoformat() if batch.recommendation_date else ''
                
                # Get recommendations for this batch
                recs = db.query(models.PricingRecommendation) \
                        .filter(models.PricingRecommendation.batch_id == batch_id) \
                        .all()
                
                for rec in recs:
                    # Get item name
                    item_name = "Unknown"
                    if rec.item:
                        item_name = rec.item.name.replace('"', '""')  # Escape quotes for CSV
                        
                    # Clean rationale for CSV
                    rationale = ""
                    if rec.rationale:
                        rationale = rec.rationale.replace('"', '""').replace('\n', ' ')
                    
                    csv_lines.append(
                        f"\"{batch_id}\"," 
                        f"{user_id},"
                        f"\"{user_email}\","
                        f"{rec_date},"
                        f"{rec.item_id},"
                        f"\"{item_name}\","
                        f"{rec.current_price},"
                        f"{rec.recommended_price},"
                        f"{rec.price_change_amount},"
                        f"{rec.price_change_percent},"
                        f"\"{rec.strategy_type if rec.strategy_type else ''}\","
                        f"{rec.confidence_score if rec.confidence_score else ''},"
                        f"\"{rec.implementation_status if rec.implementation_status else ''}\","
                        f"{rec.implemented_at.isoformat() if rec.implemented_at else ''},"
                        f"{rec.implemented_price if rec.implemented_price else ''},"
                        f"\"{rationale}\""
                    )
                
            csv_output = "\n".join(csv_lines)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(csv_output)
                print(f"Exported pricing recommendations to {output_file}")
            else:
                print(csv_output)
                
    except Exception as e:
        print(f"Error extracting pricing recommendations: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract pricing recommendations from database')
    parser.add_argument('--user-id', type=int, help='Filter by user ID')
    parser.add_argument('--days', type=int, help='Filter by number of days to look back')
    parser.add_argument('--format', choices=['display', 'json', 'csv'], default='display',
                        help='Output format (default: display)')
    parser.add_argument('--output', type=str, help='Output file path (for json/csv formats)')
    
    args = parser.parse_args()
    
    extract_pricing_recommendations(args.user_id, args.days, args.format, args.output)
