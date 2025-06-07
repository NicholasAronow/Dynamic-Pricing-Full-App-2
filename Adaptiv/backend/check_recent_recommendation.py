#!/usr/bin/env python3
import sys
import os
from datetime import datetime

# Add the current directory to the path so we can import our models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
from models import User, Item, PricingRecommendation
from sqlalchemy import desc

def check_most_recent():
    """Check the single most recent recommendation and its reevaluation date"""
    db = SessionLocal()
    
    try:
        # Get the most recent recommendation
        recommendation = db.query(PricingRecommendation).order_by(
            desc(PricingRecommendation.recommendation_date)
        ).first()
        
        if not recommendation:
            print("No recommendations found in the database.")
            return
        
        # Get the item name
        item_name = recommendation.item.name if recommendation.item else f"Item ID {recommendation.item_id}"
        
        # Calculate days from now
        reeval_date = recommendation.reevaluation_date
        days_from_now = (reeval_date - datetime.now()).days if reeval_date else None
        
        print("==== MOST RECENT RECOMMENDATION ====")
        print(f"Created: {recommendation.recommendation_date}")
        print(f"Item: {item_name}")
        print(f"Price: ${recommendation.recommended_price:.2f} (from ${recommendation.current_price:.2f})")
        print(f"Reevaluation Date: {reeval_date}")
        print(f"Days from now: {days_from_now}")
        print(f"Rationale: {recommendation.rationale[:200]}...")
        
        # Check if this appears to be a default date (around 90 days)
        if days_from_now and abs(days_from_now - 90) <= 1:
            print("\n⚠️ WARNING: This appears to be using the default 90-day reevaluation date.")
        else:
            print("\n✅ SUCCESS: This appears to be a unique reevaluation date!")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_most_recent()
