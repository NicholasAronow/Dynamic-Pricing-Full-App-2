"""
Script to create a business profile for an existing user.
This is used to fix the "No business profile found for user ID" error 
that occurs when running agents without a business profile.
"""

from sqlalchemy.orm import Session
import models
from database import SessionLocal

def create_business_profile_for_user(user_id: int, db: Session):
    """Create a business profile for the specified user if one doesn't exist."""
    # Check if user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        print(f"User with ID {user_id} not found.")
        return False
    
    # Check if user already has a business profile
    existing_profile = db.query(models.BusinessProfile).filter(
        models.BusinessProfile.user_id == user_id
    ).first()
    
    if existing_profile:
        print(f"User with ID {user_id} already has a business profile.")
        return True
    
    # Create new business profile
    new_profile = models.BusinessProfile(
        user_id=user_id,
        business_name="Adaptiv Demo Business",
        industry="Retail",
        company_size="Small",
        founded_year=2023,
        description="A demo business for testing the Adaptiv dynamic pricing system."
    )
    
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    
    print(f"Business profile created successfully for user ID {user_id}.")
    return True

if __name__ == "__main__":
    # Create a business profile for user ID 1
    db = SessionLocal()
    try:
        create_business_profile_for_user(user_id=1, db=db)
    finally:
        db.close()
