"""
Script to alter the price_history table to add sales data columns for elasticity calculations.
"""

import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database connection
DB_PATH = "adaptiv.db"

def alter_price_history_table():
    """Add sales_before and sales_after columns to the price_history table"""
    
    logger.info(f"Connecting to database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Add sales_before column
        logger.info("Adding sales_before column to price_history table...")
        cursor.execute("ALTER TABLE price_history ADD COLUMN sales_before REAL;")
        
        # Add sales_after column
        logger.info("Adding sales_after column to price_history table...")
        cursor.execute("ALTER TABLE price_history ADD COLUMN sales_after REAL;")
        
        conn.commit()
        logger.info("Successfully altered price_history table")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info(f"Column already exists: {e}")
        else:
            logger.error(f"Error altering table: {e}")
            conn.rollback()
            raise
    finally:
        conn.close()

if __name__ == "__main__":
    alter_price_history_table()
