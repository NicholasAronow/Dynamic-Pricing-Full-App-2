import sys
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from datetime import datetime

import models
from database import engine
from action_items import seed_default_action_items

# Create a new session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def check_if_table_exists(table_name):
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def create_action_items_table():
    """Create the action_items table if it doesn't exist"""
    print("Creating action_items table...")
    # This will create only missing tables, not touch existing ones
    models.Base.metadata.create_all(bind=engine)
    print("Table created successfully!")

def seed_all_users_with_action_items():
    """Add default action items to all existing users"""
    # Get all users
    users = db.query(models.User).all()
    print(f"Found {len(users)} users to seed with action items")
    
    for user in users:
        print(f"Seeding action items for user {user.id} ({user.email})")
        seed_default_action_items(user.id, db)
    
    print("Done seeding action items for all users")

def main():
    """Main migration function"""
    print("Starting action items migration")
    
    # Check if the action_items table already exists
    if not check_if_table_exists("action_items"):
        print("Table 'action_items' does not exist, creating...")
        create_action_items_table()
    else:
        print("Table 'action_items' already exists")
    
    # Seed action items for all users
    seed_all_users_with_action_items()
    
    print("Action items migration completed successfully")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)
    finally:
        db.close()
