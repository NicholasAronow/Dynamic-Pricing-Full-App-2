#!/usr/bin/env python3
"""
Get User Info Script

This script retrieves information about a user by their ID.

Usage:
    python get_user_info.py <user_id>
"""

import sys
import os
from typing import Dict, Any, Optional

# Add the current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import database models
from config.database import SessionLocal
import models
from sqlalchemy.orm import Session

def get_user_info(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get user information by ID
    
    Args:
        user_id: The ID of the user to look up
        
    Returns:
        Dictionary with user information or None if user not found
    """
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            print(f"User with ID {user_id} not found")
            return None
        
        # Get business profile if it exists
        business = db.query(models.BusinessProfile).filter(models.BusinessProfile.user_id == user_id).first()
        business_name = business.business_name if business else "No business profile"
        
        # Get counts of related data
        item_count = db.query(models.Item).filter(models.Item.user_id == user_id).count()
        pricing_rec_count = db.query(models.PricingRecommendation).filter(models.PricingRecommendation.user_id == user_id).count()
        
        user_info = {
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "business_name": business_name,
            "item_count": item_count,
            "pricing_rec_count": pricing_rec_count
        }
        
        return user_info
    except Exception as e:
        print(f"Error: {str(e)}")
        return None
    finally:
        db.close()

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python get_user_info.py <user_id>")
        sys.exit(1)
    
    try:
        user_id = int(sys.argv[1])
    except ValueError:
        print("Error: User ID must be a number")
        sys.exit(1)
    
    user_info = get_user_info(user_id)
    if user_info:
        print("\nUSER INFORMATION")
        print("=" * 50)
        print(f"ID:             {user_info['id']}")
        print(f"Email:          {user_info['email']}")
        print(f"Active:         {user_info['is_active']}")
        print(f"Business:       {user_info['business_name']}")
        print(f"Menu Items:     {user_info['item_count']}")
        print(f"Pricing Recs:   {user_info['pricing_rec_count']}")
        print("=" * 50)

if __name__ == "__main__":
    main()
