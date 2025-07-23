#!/usr/bin/env python3
"""
Migration script to add location_id column to orders table
"""

from sqlalchemy import text
from config.database import engine

def add_location_id_column():
    """Add location_id column to orders table"""
    try:
        with engine.connect() as connection:
            # Check if column already exists (PostgreSQL version)
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'orders' AND column_name = 'location_id'
            """))
            
            if result.fetchone():
                print("Column 'location_id' already exists in orders table")
                return
            
            # Add the column
            connection.execute(text("""
                ALTER TABLE orders 
                ADD COLUMN location_id VARCHAR(255)
            """))
            
            # Add index for better performance
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_orders_location_id 
                ON orders(location_id)
            """))
            
            connection.commit()
            print("Successfully added location_id column to orders table")
            
    except Exception as e:
        print(f"Error adding location_id column: {str(e)}")
        raise

if __name__ == "__main__":
    add_location_id_column()
