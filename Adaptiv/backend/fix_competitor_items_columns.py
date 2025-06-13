#!/usr/bin/env python3
import os
import logging
import sqlalchemy
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_connection_url():
    # Get database URL from environment variable or use a default for local development
    database_url = os.environ.get("DATABASE_URL")
    
    # If no URL is provided, use SQLite for local development
    if not database_url:
        logger.info("No DATABASE_URL found, using SQLite for local development")
        return "sqlite:///./sql_app.db"
    
    # For PostgreSQL URLs from Heroku or similar platforms, convert from postgres:// to postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
        
    # Mask the URL for logging purposes
    masked_url = database_url.replace("://", "://***:***@***")
    logger.info(f"Connecting to database: {masked_url}")
    return database_url

def check_table_exists(connection, table_name):
    """Check if a table exists in the database"""
    try:
        # Try PostgreSQL syntax first
        result = connection.execute(text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = '{table_name}'
            );
        """))
        exists = result.scalar()
        if exists is not None:
            return exists
    except Exception as e:
        logger.info(f"PostgreSQL table check failed: {e}, trying SQLite syntax")
    
    try:
        # Fallback to SQLite syntax
        result = connection.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';"))
        exists = result.fetchone() is not None
        return exists
    except Exception as e:
        logger.error(f"Failed to check table with SQLite syntax: {e}")
        return False

def get_existing_columns(connection, table_name):
    """Get existing columns for a table using raw SQL queries for both PostgreSQL and SQLite"""
    # First check if the table exists
    if not check_table_exists(connection, table_name):
        logger.warning(f"Table {table_name} does not exist in the database")
        return []
        
    try:
        # Try PostgreSQL syntax first
        result = connection.execute(text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
        """))
        columns = [row[0] for row in result]
        if columns:
            return columns
    except Exception as e:
        logger.info(f"PostgreSQL query failed: {e}, trying SQLite syntax")
    
    try:
        # Fallback to SQLite syntax
        result = connection.execute(text(f"PRAGMA table_info({table_name})"))
        columns = [row[1] for row in result]  # Column name is at index 1 in SQLite's PRAGMA table_info
        return columns
    except Exception as e:
        logger.error(f"Failed to get columns with SQLite syntax: {e}")
        return []

def add_missing_columns():
    """Add missing columns to competitor_items table"""
    logger.info("Starting migration to add missing columns to competitor_items table")
    
    try:
        # Create database engine
        database_url = get_connection_url()
        engine = create_engine(database_url)
        
        # Check if table exists first
        with engine.connect() as connection:
            # Check if table exists
            table_exists = check_table_exists(connection, "competitor_items")
            
            if not table_exists:
                logger.warning("The competitor_items table does not exist in this database. Skipping column additions.")
                return True
                
            # Get existing columns
            existing_columns = get_existing_columns(connection, "competitor_items")
            logger.info(f"Existing columns in competitor_items: {existing_columns}")
            
            # Columns we want to ensure exist
            required_columns = {
                "batch_id": "VARCHAR",
                "sync_timestamp": "TIMESTAMP",
                "updated_at": "TIMESTAMP"
            }
            
            # Add each missing column
            for column_name, column_type in required_columns.items():
                if column_name.lower() not in [col.lower() for col in existing_columns]:
                    logger.info(f"Adding missing column {column_name} to competitor_items table")
                    
                    try:
                        # For PostgreSQL
                        connection.execute(text(f"ALTER TABLE competitor_items ADD COLUMN {column_name} {column_type}"))
                        connection.commit()
                        logger.info(f"Successfully added column {column_name} to competitor_items table")
                    except Exception as e:
                        logger.warning(f"PostgreSQL alter failed: {e}, trying SQLite syntax")
                        
                        try:
                            # For SQLite
                            connection.execute(text(f"ALTER TABLE competitor_items ADD COLUMN {column_name} {column_type}"))
                            connection.commit()
                            logger.info(f"Successfully added column {column_name} to competitor_items table using SQLite syntax")
                        except Exception as inner_e:
                            logger.error(f"Failed to add column with SQLite syntax: {inner_e}")
                else:
                    logger.info(f"Column {column_name} already exists in competitor_items table")
        
        logger.info("Migration completed successfully!")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = add_missing_columns()
    if success:
        logger.info("Migration succeeded!")
    else:
        logger.error("Migration failed!")
