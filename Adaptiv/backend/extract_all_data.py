#!/usr/bin/env python3
"""
Master script to extract all data types from the database
"""
import os
import argparse
from datetime import datetime

# Import individual extraction modules
from extract_menu_items import extract_menu_items
from extract_order_history import extract_order_history
from extract_competitor_data import extract_competitor_data
from extract_pricing_recommendations import extract_pricing_recommendations

def create_output_directory(base_dir=None):
    """Create output directory for data extraction"""
    if base_dir:
        output_dir = base_dir
    else:
        # Create directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"data_export_{timestamp}"
    
    # Create directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    return output_dir

def run_all_extractions(user_id=None, days=None, output_format='json', output_dir=None):
    """
    Run all extraction scripts and save results
    
    Args:
        user_id: Optional user ID to filter by
        days: Optional number of days to look back
        output_format: 'json' or 'csv'
        output_dir: Directory to save output files
    """
    # Create output directory if needed
    output_dir = create_output_directory(output_dir)
    
    print(f"\n{'='*80}")
    print(f"EXTRACTING ALL DATA{f' FOR USER {user_id}' if user_id else ''}{f' (LAST {days} DAYS)' if days else ''}")
    print(f"Output format: {output_format}")
    print(f"Output directory: {output_dir}")
    print(f"{'='*80}\n")
    
    # 1. Extract menu items
    print("1. Extracting menu items...")
    menu_output = os.path.join(output_dir, f"menu_items.{output_format}")
    extract_menu_items(user_id, output_format, menu_output)
    
    # 2. Extract order history
    print("\n2. Extracting order history...")
    orders_output = os.path.join(output_dir, f"order_history.{output_format}")
    extract_order_history(user_id, days, output_format, orders_output)
    
    # 3. Extract competitor data
    print("\n3. Extracting competitor data...")
    competitor_output = os.path.join(output_dir, f"competitor_data.{output_format}")
    extract_competitor_data(user_id, None, days, output_format, competitor_output)
    
    # 4. Extract pricing recommendations
    print("\n4. Extracting pricing recommendations...")
    recommendations_output = os.path.join(output_dir, f"price_recommendations.{output_format}")
    extract_pricing_recommendations(user_id, days, output_format, recommendations_output)
    
    print(f"\n{'='*80}")
    print(f"DATA EXTRACTION COMPLETE")
    print(f"All data has been saved to: {output_dir}")
    print(f"{'='*80}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract all data types from database')
    parser.add_argument('--user-id', type=int, help='Filter by user ID')
    parser.add_argument('--days', type=int, help='Filter by number of days to look back')
    parser.add_argument('--format', choices=['json', 'csv'], default='json',
                        help='Output format (default: json)')
    parser.add_argument('--output-dir', type=str, help='Output directory (defaults to timestamped folder)')
    
    args = parser.parse_args()
    
    run_all_extractions(args.user_id, args.days, args.format, args.output_dir)
