#!/usr/bin/env python3
from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import sys
import os

# Add the current directory to the path so we can import our models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Base, PricingRecommendation

# Create database connection
engine = create_engine('sqlite:///./adaptiv.db')
Session = sessionmaker(bind=engine)
session = Session()

def check_latest_recommendations():
    print("\n" + "="*50)
    print("CHECKING LATEST PRICING RECOMMENDATIONS")
    print("="*50)
    
    # Get the latest timestamp
    latest_timestamp = session.query(func.max(PricingRecommendation.created_at)).scalar()
    
    if not latest_timestamp:
        print("No recommendations found in database.")
        return
    
    print(f"Latest recommendations timestamp: {latest_timestamp}")
    
    # Get recommendations from the latest batch (within 5 minutes of latest timestamp)
    five_min_before = latest_timestamp - timedelta(minutes=5)
    latest_recs = session.query(PricingRecommendation).filter(
        PricingRecommendation.created_at >= five_min_before
    ).order_by(desc(PricingRecommendation.created_at)).all()
    
    print(f"Found {len(latest_recs)} recommendations in latest batch.")
    
    # Check reevaluation dates
    all_dates = []
    for i, rec in enumerate(latest_recs):
        # Use the relationship to get item name
        item_name = rec.item.name if rec.item else f"Item ID {rec.item_id}"
        reeval_date = rec.reevaluation_date
        days_from_now = (reeval_date - datetime.now()).days if reeval_date else None
        
        all_dates.append(days_from_now)
        
        print(f"{i+1}. {item_name}: {reeval_date} (Days from now: {days_from_now})")
        
        # Print recommended price for reference
        print(f"   Price: ${rec.recommended_price:.2f} (from ${rec.current_price:.2f})")

        
        # Check if this is likely the default date (90 days)
        if days_from_now and abs(days_from_now - 90) <= 1:
            print(f"   ⚠️ LIKELY USING DEFAULT DATE (within 1 day of 90-day default)")
    
    # Calculate unique date counts
    unique_dates = set([d for d in all_dates if d is not None])
    print(f"\nFound {len(unique_dates)} unique day counts among {len(latest_recs)} dates")
    
    # Print summary
    if len(unique_dates) <= 1 and any(abs(d - 90) <= 1 for d in unique_dates if d is not None):
        print(f"⚠️ All dates appear to be using the default 90-day value")
    else:
        print(f"✅ Found multiple unique reevaluation dates! Our fix appears to be working.")

if __name__ == "__main__":
    check_latest_recommendations()
