#!/usr/bin/env python3
"""
Migration script to add reevaluation_date column to pricing_recommendations table
"""
import os
import sqlite3
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('migration')

def run_migration():
    """Add reevaluation_date column to pricing_recommendations table"""
    # Path to the database file
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'adaptiv.db')
    
    logger.info(f"Starting migration on database: {db_path}")
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return False
    
    conn = None
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(pricing_recommendations)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'reevaluation_date' in column_names:
            logger.info("reevaluation_date column already exists in pricing_recommendations table")
            return True
        
        # Begin transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Add the reevaluation_date column
        logger.info("Adding reevaluation_date column to pricing_recommendations table")
        cursor.execute("""
            ALTER TABLE pricing_recommendations 
            ADD COLUMN reevaluation_date DATETIME
        """)
        
        # Update existing records to have a default reevaluation date 90 days in the future
        # (This is optional - you can remove if you don't want to set default values)
        default_reevaluation = (datetime.now().replace(microsecond=0).isoformat())
        logger.info(f"Setting default reevaluation date: {default_reevaluation}")
        cursor.execute("""
            UPDATE pricing_recommendations
            SET reevaluation_date = ?
        """, (default_reevaluation,))
        
        # Commit the transaction
        conn.commit()
        logger.info("Migration completed successfully")
        return True
        
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"SQLite error: {e}")
        return False
    
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Unexpected error: {e}")
        return False
    
    finally:
        if conn:
            conn.close()

def verify_migration():
    """Verify that the migration was successful"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'adaptiv.db')
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the column exists
        cursor.execute("PRAGMA table_info(pricing_recommendations)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'reevaluation_date' in column_names:
            logger.info("Verification successful: reevaluation_date column exists")
            
            # Get sample data to verify
            cursor.execute("""
                SELECT id, item_id, reevaluation_date 
                FROM pricing_recommendations 
                LIMIT 5
            """)
            samples = cursor.fetchall()
            if samples:
                logger.info(f"Sample records with reevaluation_date: {samples}")
            else:
                logger.info("No records found in pricing_recommendations table")
            
            return True
        else:
            logger.error("Verification failed: reevaluation_date column does not exist")
            return False
            
    except Exception as e:
        logger.error(f"Verification error: {e}")
        return False
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    logger.info("Starting database migration...")
    if run_migration():
        verify_migration()
        print("\n✅ Migration completed successfully!")
        print("The pricing_recommendations table now has a reevaluation_date column.")
        print("Your pricing strategy agent can now store reevaluation dates for price changes.")
    else:
        print("\n❌ Migration failed. Please check the logs for details.")
