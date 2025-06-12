#!/usr/bin/env python3
"""
Migration script to add missing columns to the business_profiles table.

The script will:
1. Add missing address-related columns to the business_profiles table if they don't exist
2. Work with both SQLite (local) and PostgreSQL (production) databases
3. Log detailed information about each operation
"""

import os
import sys
import logging
import traceback
from sqlalchemy import create_engine, text, Column, String, inspect
from sqlalchemy.exc import SQLAlchemyError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Get database URL from environment variable or use default SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./adaptiv.db")

def is_postgresql():
    """Check if the database is PostgreSQL or SQLite."""
    return DATABASE_URL.startswith("postgresql")

def add_missing_columns():
    """Add missing columns to the business_profiles table."""
    try:
        # Create SQLAlchemy engine
        logger.info(f"Connecting to database: {DATABASE_URL.split('@')[0].split(':')[0]}://***:***@***")
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        
        # Check if the business_profiles table exists
        if not inspector.has_table("business_profiles"):
            logger.error("The business_profiles table does not exist in the database!")
            return False

        # Get existing columns - safely handle different inspector API versions
        try:
            existing_columns = [column["name"] for column in inspector.get_columns("business_profiles")]
        except Exception as e:
            logger.warning(f"Error using inspector.get_columns: {str(e)}")
            # Alternative method for getting columns
            with engine.connect() as conn:
                if is_postgresql():
                    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'business_profiles'"))
                    existing_columns = [row[0] for row in result]
                else:
                    result = conn.execute(text("PRAGMA table_info(business_profiles)"))
                    existing_columns = [row[1] for row in result]
        logger.info(f"Existing columns in business_profiles: {existing_columns}")

        # Define the columns we need to add if they're missing
        columns_to_check = {
            "street_address": "VARCHAR",
            "city": "VARCHAR",
            "state": "VARCHAR",
            "postal_code": "VARCHAR",
            "country": "VARCHAR"
        }
        
        # Track success
        all_successful = True
        
        # Add columns if they don't exist
        for column_name, column_type in columns_to_check.items():
            if column_name not in existing_columns:
                try:
                    logger.info(f"Adding column {column_name} to business_profiles table...")
                    
                    # SQL for adding columns differs by database
                    if is_postgresql():
                        # PostgreSQL syntax
                        sql = text(f"ALTER TABLE business_profiles ADD COLUMN IF NOT EXISTS {column_name} {column_type}")
                    else:
                        # SQLite syntax
                        sql = text(f"ALTER TABLE business_profiles ADD COLUMN {column_name} {column_type}")
                    
                    # Use the correct API based on SQLAlchemy version
                    with engine.connect() as conn:
                        conn.execute(sql)
                        conn.commit()
                    logger.info(f"Successfully added column {column_name}")
                except SQLAlchemyError as e:
                    logger.error(f"Failed to add column {column_name}: {str(e)}")
                    all_successful = False
            else:
                logger.info(f"Column {column_name} already exists in business_profiles table")
                
        if all_successful:
            logger.info("Migration completed successfully!")
            return True
        else:
            logger.warning("Migration completed with some issues. Check the logs for details.")
            return False
            
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Starting migration to add missing columns to business_profiles table")
    if add_missing_columns():
        logger.info("Migration succeeded!")
    else:
        logger.error("Migration failed!")
        sys.exit(1)
