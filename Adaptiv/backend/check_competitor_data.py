#!/usr/bin/env python3
"""
Database Check Script - Verify Competitor Data for User

This script checks the database for competitor entities and items for a specific user ID.
Useful for debugging the scraper integration and verifying data persistence.

Usage:
    python3 check_competitor_data.py [user_id]
    
Default user_id is 2 if not provided.
"""

import sys
import os
from sqlalchemy.orm import joinedload

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import SessionLocal
import models

def check_competitor_data(user_id: int = 2):
    """
    Check competitor entities and items for a specific user
    
    Args:
        user_id: The user ID to check data for
    """
    print(f"🔍 Checking competitor data for user ID: {user_id}")
    print("=" * 80)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Check if user exists
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            print(f"❌ User with ID {user_id} not found!")
            return
        
        print(f"✅ User found: {user.email}")
        print()
        
        # Get all competitor entities for this user
        competitors = db.query(models.CompetitorEntity).filter(
            models.CompetitorEntity.user_id == user_id
        ).options(joinedload(models.CompetitorEntity.items)).all()
        
        print(f"📊 Found {len(competitors)} competitor entities:")
        print("-" * 50)
        
        if not competitors:
            print("   No competitor entities found for this user.")
            print()
            print("💡 This could mean:")
            print("   - The scraper hasn't been run for this user")
            print("   - The scraper failed to save data")
            print("   - Data was saved to a different user ID")
            return
        
        total_items = 0
        
        for i, competitor in enumerate(competitors, 1):
            print(f"\n🏪 Competitor {i}:")
            print(f"   ID: {competitor.id}")
            print(f"   Name: {competitor.name}")
            print(f"   Address: {competitor.address}")
            print(f"   Category: {competitor.category}")
            print(f"   Website: {competitor.website}")
            print(f"   Menu URL: {competitor.menu_url}")
            print(f"   Is Selected: {competitor.is_selected}")
            # Description field not available in current model
            print(f"   Created At: {competitor.created_at}")
            
            # Get items for this competitor
            items = db.query(models.CompetitorItem).filter(
                models.CompetitorItem.competitor_id == competitor.id
            ).all()
            
            print(f"   📋 Items: {len(items)}")
            total_items += len(items)
            
            if items:
                print(f"   Sample items (first 5):")
                for j, item in enumerate(items[:5], 1):
                    price_str = f"${item.price:.2f}" if item.price else "N/A"
                    print(f"     {j}. {item.item_name} - {price_str}")
                    if item.category:
                        print(f"        Category: {item.category}")
                    if item.description:
                        print(f"        Description: {item.description[:50]}{'...' if len(item.description) > 50 else ''}")
                
                if len(items) > 5:
                    print(f"     ... and {len(items) - 5} more items")
            else:
                print("     ❌ No items found for this competitor")
        
        print("\n" + "=" * 80)
        print(f"📈 SUMMARY:")
        print(f"   User: {user.email} (ID: {user_id})")
        print(f"   Competitors: {len(competitors)}")
        print(f"   Total Items: {total_items}")
        print(f"   Average Items per Competitor: {total_items / len(competitors):.1f}" if competitors else "   Average Items per Competitor: 0")
        
        # Check for recent additions (last 24 hours)
        from datetime import datetime, timedelta
        yesterday = datetime.now() - timedelta(days=1)
        
        recent_competitors = [c for c in competitors if c.created_at and c.created_at > yesterday]
        if recent_competitors:
            print(f"   🆕 Recent Competitors (last 24h): {len(recent_competitors)}")
            for comp in recent_competitors:
                print(f"      - {comp.name} (created: {comp.created_at})")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

def main():
    """Main function to run the database check"""
    user_id = 2  # Default user ID
    
    # Check if user provided a different user ID
    if len(sys.argv) > 1:
        try:
            user_id = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid user ID provided. Using default user ID 2.")
    
    check_competitor_data(user_id)

if __name__ == "__main__":
    main()
