"""
Migration to add competitor_tracking_enabled column to users table
"""
import sqlite3
from sqlalchemy import create_engine, text
from database import DATABASE_URL

def upgrade():
    """Add competitor_tracking_enabled column to users table"""
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Add column with a default value of False
        with engine.connect() as conn:
            # Check if column already exists to avoid errors
            result = conn.execute(text(
                "SELECT name FROM pragma_table_info('users') WHERE name='competitor_tracking_enabled'"
            ))
            if result.fetchone() is None:
                print("Adding competitor_tracking_enabled column to users table")
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN competitor_tracking_enabled BOOLEAN DEFAULT FALSE"
                ))
                conn.commit()
                print("Column added successfully")
            else:
                print("Column competitor_tracking_enabled already exists in users table")
                
        return True
    except Exception as e:
        print(f"Error adding competitor_tracking_enabled column: {str(e)}")
        return False
