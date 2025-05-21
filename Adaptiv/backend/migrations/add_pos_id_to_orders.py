"""
Migration script to add pos_id and updated_at columns to orders table.

This script adds:
1. The pos_id column to the orders table to support Square integration
2. The updated_at column to track when orders are modified
"""

import os
import sys
from sqlalchemy import Column, String, inspect, text

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base, SessionLocal
from models import Order

def run_migration():
    """Run the migration to add pos_id and updated_at columns to orders table"""
    print("Starting migration: Add pos_id and updated_at columns to orders table")
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # Check if the columns already exist
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('orders')]
        
        # Add pos_id column if it doesn't exist
        if 'pos_id' not in columns:
            print("Adding pos_id column to orders table...")
            with engine.begin() as conn:
                conn.execute(text('ALTER TABLE orders ADD COLUMN pos_id VARCHAR'))
            
            # Add an index for performance
            print("Adding index on pos_id column...")
            with engine.begin() as conn:
                conn.execute(text('CREATE INDEX ix_orders_pos_id ON orders (pos_id)'))
            
            print("✅ pos_id column added successfully!")
        else:
            print("Column pos_id already exists in orders table.")
        
        # Add updated_at column if it doesn't exist
        if 'updated_at' not in columns:
            print("Adding updated_at column to orders table...")
            with engine.begin() as conn:
                conn.execute(text('ALTER TABLE orders ADD COLUMN updated_at TIMESTAMP'))
            
            print("✅ updated_at column added successfully!")
        else:
            print("Column updated_at already exists in orders table.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
