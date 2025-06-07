#!/usr/bin/env python
"""
Script to check reevaluation dates in the pricing_recommendations table
"""

from sqlalchemy import create_engine, text 
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime

# Connect to database
engine = create_engine('postgresql://postgres:postgres@localhost:5432/adaptiv')  # Postgresql connection
Session = sessionmaker(bind=engine)
session = Session()

# Query recent recommendations
print("\n=== RECENT PRICING RECOMMENDATIONS ===")
result = session.execute(text('''
    SELECT item_id, recommended_price, reevaluation_date, metadata 
    FROM pricing_recommendations 
    ORDER BY recommendation_date DESC 
    LIMIT 15
'''))

# Process results
rows = []
for row in result:
    metadata = row.metadata
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except:
            metadata = {}
            
    item_name = metadata.get('item_name', 'Unknown')
    reeval_str = metadata.get('reevaluation_date_str', 'None')
    reeval_date = row.reevaluation_date
    
    # Calculate days from now to reevaluation
    days_diff = None
    if reeval_date:
        try:
            days_diff = (reeval_date - datetime.now()).days
        except:
            days_diff = "Error"
    
    rows.append({
        'item_id': row.item_id,
        'item_name': item_name,
        'recommended_price': row.recommended_price,
        'reevaluation_date': reeval_date,
        'reeval_date_str': reeval_str,
        'days_until_reeval': days_diff
    })

# Print results in a formatted table
print(f"{'Item Name':<15} | {'Recom. Price':^12} | {'Reeval Date':^12} | {'Days Until':^10} | {'Reeval String'}")
print("-" * 80)

for row in rows:
    reeval_date = row['reevaluation_date'].strftime("%Y-%m-%d") if row['reevaluation_date'] else "None"
    print(f"{row['item_name'][:15]:<15} | ${row['recommended_price']:^10.2f} | {reeval_date:^12} | {row['days_until_reeval']:^10} | {row['reeval_date_str']}")

# Check for uniqueness
if rows:
    unique_dates = set(r['reevaluation_date'].strftime("%Y-%m-%d") if r['reevaluation_date'] else "None" for r in rows)
    print("\n=== UNIQUENESS ANALYSIS ===")
    print(f"Total recommendations: {len(rows)}")
    print(f"Unique reevaluation dates: {len(unique_dates)}")
    print(f"Unique dates: {', '.join(unique_dates)}")
    
    # Check if all are 90 days apart
    ninety_days_count = sum(1 for r in rows if r['days_until_reeval'] and 89 <= r['days_until_reeval'] <= 91)
    print(f"Recommendations with ~90 days reevaluation: {ninety_days_count} ({(ninety_days_count/len(rows))*100:.1f}%)")
else:
    print("No recommendations found")
    
print("\nDone.")
