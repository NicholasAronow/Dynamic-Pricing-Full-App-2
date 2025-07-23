#!/usr/bin/env python3
"""
Migration script to add location_ids column to pos_integrations table
"""

from sqlalchemy import text
from config.database import engine

def add_location_ids_column():
    """Add location_ids column to pos_integrations table"""
    try:
        with engine.connect() as connection:
            # Check if column already exists (PostgreSQL version)
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'pos_integrations' AND column_name = 'location_ids'
            """))
            
            if result.fetchone():
                print("Column 'location_ids' already exists in pos_integrations table")
                return
            
            # Add the column
            connection.execute(text("""
                ALTER TABLE pos_integrations 
                ADD COLUMN location_ids TEXT
            """))
            
            connection.commit()
            print("Successfully added location_ids column to pos_integrations table")
            
    except Exception as e:
        print(f"Error adding location_ids column: {str(e)}")
        raise

if __name__ == "__main__":
    add_location_ids_column()
