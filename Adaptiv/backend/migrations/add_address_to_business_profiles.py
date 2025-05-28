"""
Migration script to add address fields to business_profiles table.

This script adds address fields (street_address, city, state, postal_code, country)
to the business_profiles table to support location-based competitor research.
"""

import os
import sys
from sqlalchemy import Column, String, inspect, text

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base, SessionLocal
from models import BusinessProfile

def run_migration():
    """Run the migration to add address fields to business_profiles table"""
    print("Starting migration: Add address fields to business_profiles table")
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # Check if the columns already exist using SQLAlchemy's inspect
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('business_profiles')]
        
        # List of columns to add
        address_columns = [
            ('street_address', 'VARCHAR'),
            ('city', 'VARCHAR'),
            ('state', 'VARCHAR'),
            ('postal_code', 'VARCHAR'),
            ('country', 'VARCHAR DEFAULT \'USA\'')
        ]
        
        added_columns = []
        
        # Add each column if it doesn't exist
        for col_name, col_type in address_columns:
            if col_name in columns:
                print(f"Column {col_name} already exists in business_profiles table.")
                continue
                
            print(f"Adding {col_name} column to business_profiles table...")
            with engine.begin() as conn:
                conn.execute(text(f'ALTER TABLE business_profiles ADD COLUMN {col_name} {col_type}'))
            added_columns.append(col_name)
        
        if not added_columns:
            print("All address columns already exist. Migration not needed.")
            return False
        
        print(f"✅ Migration completed successfully! Added columns: {', '.join(added_columns)}")
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
