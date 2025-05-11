"""
Migration script to associate existing records with user accounts.
Run this script once after updating the database models to add user_id fields.
"""

import sys
import os
from sqlalchemy.orm import Session
from database import get_db, engine, Base
import models
from sqlalchemy import func, select

def migrate_data():
    """Associate existing records with default user accounts."""
    print("Starting data migration...")
    
    # Create a session
    db = next(get_db())
    
    try:
        # Check if we have any users in the system
        users = db.query(models.User).all()
        if not users:
            print("No users found in the system. Please create at least one user first.")
            return
            
        default_user = users[0]  # Use the first user as the default
        print(f"Using user {default_user.email} (ID: {default_user.id}) as the default user for existing data.")
        
        # Update all items without a user_id
        items_updated = db.query(models.Item).filter(models.Item.user_id.is_(None)).update(
            {"user_id": default_user.id}, synchronize_session=False
        )
        print(f"Updated {items_updated} items with user_id {default_user.id}")
        
        # Update all price history records without a user_id
        price_history_updated = db.query(models.PriceHistory).filter(models.PriceHistory.user_id.is_(None)).update(
            {"user_id": default_user.id}, synchronize_session=False
        )
        print(f"Updated {price_history_updated} price history records with user_id {default_user.id}")
        
        # Update all orders without a user_id
        orders_updated = db.query(models.Order).filter(models.Order.user_id.is_(None)).update(
            {"user_id": default_user.id}, synchronize_session=False
        )
        print(f"Updated {orders_updated} orders with user_id {default_user.id}")
        
        # Commit the changes
        db.commit()
        print("Data migration completed successfully.")
        
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    # Ensure all tables are created
    Base.metadata.create_all(bind=engine)
    migrate_data()
