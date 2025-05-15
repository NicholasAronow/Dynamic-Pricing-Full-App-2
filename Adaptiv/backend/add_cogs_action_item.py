from sqlalchemy.orm import Session
from database import engine, SessionLocal
import models

def add_cogs_action_item():
    """Add the 'Enter COGS for current week' action item to all existing users who don't already have it"""
    
    db = SessionLocal()
    try:
        # Get all users
        users = db.query(models.User).all()
        
        updated_count = 0
        already_exists_count = 0
        
        for user in users:
            # Check if the user already has this action item
            existing_item = db.query(models.ActionItem).filter(
                models.ActionItem.user_id == user.id,
                models.ActionItem.title == "Enter COGS for current week"
            ).first()
            
            if existing_item:
                already_exists_count += 1
                continue
            
            # Add the new action item
            new_action_item = models.ActionItem(
                user_id=user.id,
                title="Enter COGS for current week",
                description="Update your Cost of Goods Sold data for the current week to see profit margin visualizations",
                priority="medium",
                action_type="data_entry",
                status="pending"
            )
            
            db.add(new_action_item)
            updated_count += 1
        
        db.commit()
        print(f"Added 'Enter COGS for current week' action item to {updated_count} users")
        print(f"{already_exists_count} users already had this action item")
        
    except Exception as e:
        db.rollback()
        print(f"Error adding COGS action item: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Create tables if they don't exist
    models.Base.metadata.create_all(bind=engine)
    
    # Add COGS action item to existing users
    add_cogs_action_item()
