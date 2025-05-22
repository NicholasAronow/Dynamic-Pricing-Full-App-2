"""
Square Integration Migration Script

This script adds the necessary columns to the database to support Square integration.
"""
import logging
from sqlalchemy import create_engine, Column, String, MetaData, Table, text
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database connection string from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set!")
    exit(1)

def run_migration():
    """
    Run the migration to add Square-related columns to the database.
    """
    logger.info("Starting Square integration migration...")
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    metadata = MetaData()
    
    # Define the tables we need to modify
    items_table = Table('items', metadata, autoload_with=engine)
    orders_table = Table('orders', metadata, autoload_with=engine)
    
    # Add columns if they don't exist
    try:
        # Try to add pos_id to items table
        logger.info("Adding pos_id column to items table...")
        with engine.begin() as connection:
            try:
                # Use text() to create executable SQL statements
                connection.execute(text("ALTER TABLE items ADD COLUMN IF NOT EXISTS pos_id VARCHAR;"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_items_pos_id ON items (pos_id);"))
                logger.info("Successfully added pos_id to items table")
            except ProgrammingError as e:
                if "already exists" in str(e):
                    logger.info("items.pos_id column already exists")
                else:
                    raise
        
        # Try to add pos_id and source to orders table
        logger.info("Adding pos_id and source columns to orders table...")
        with engine.begin() as connection:
            try:
                # Use text() to create executable SQL statements
                connection.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS pos_id VARCHAR;"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_orders_pos_id ON orders (pos_id);"))
                connection.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'manual';"))
                connection.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS square_merchant_id VARCHAR;"))
                
                # Add updated_at column with the same default behavior as created_at
                connection.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;"))
                logger.info("Successfully added Square-related columns to orders table")
            except ProgrammingError as e:
                if "already exists" in str(e):
                    logger.info("orders.pos_id and/or orders.source columns already exist")
                else:
                    raise
        
        logger.info("Square integration migration completed successfully")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Error during migration: {str(e)}")
        return False

if __name__ == "__main__":
    run_migration()
