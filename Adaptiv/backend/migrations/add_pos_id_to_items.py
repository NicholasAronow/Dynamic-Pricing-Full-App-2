"""
Migration script to add pos_id column to items table.

This script adds the pos_id column to the items table to support Square integration.
The pos_id column will store external IDs from Square's catalog.
"""

import os
import sys
from sqlalchemy import Column, String, inspect, text

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base, SessionLocal
from models import Item

def run_migration():
    """Run the migration to add pos_id column to items table"""
    print("Starting migration: Add pos_id column to items table")
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # Check if the column already exists using SQLAlchemy's inspect
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('items')]
        
        if 'pos_id' in columns:
            print("Column pos_id already exists in items table. Migration not needed.")
            return False
            
        # Add the pos_id column
        print("Adding pos_id column to items table...")
        with engine.begin() as conn:
            conn.execute(text('ALTER TABLE items ADD COLUMN pos_id VARCHAR'))
        
        # Add an index for performance
        print("Adding index on pos_id column...")
        with engine.begin() as conn:
            conn.execute(text('CREATE INDEX ix_items_pos_id ON items (pos_id)'))
        
        print("✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
