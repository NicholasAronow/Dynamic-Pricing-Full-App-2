"""
Migration to add competitor_tracking_enabled column to users table
"""
import sqlite3
from sqlalchemy import create_engine, text, inspect
from database import DATABASE_URL

def upgrade():
    """Add competitor_tracking_enabled column to users table"""
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Check database type
        is_sqlite = DATABASE_URL.startswith('sqlite')
        is_postgres = 'postgresql' in DATABASE_URL
        
        # Add column with a default value of False
        with engine.connect() as conn:
            # Check if column already exists to avoid errors
            inspector = inspect(engine)
            columns = [column['name'] for column in inspector.get_columns('users')]
            
            if 'competitor_tracking_enabled' not in columns:
                print("Adding competitor_tracking_enabled column to users table")
                if is_sqlite:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN competitor_tracking_enabled BOOLEAN DEFAULT FALSE"
                    ))
                elif is_postgres:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS competitor_tracking_enabled BOOLEAN DEFAULT FALSE"
                    ))
                else:
                    # Generic SQL for other database types
                    try:
                        conn.execute(text(
                            "ALTER TABLE users ADD COLUMN competitor_tracking_enabled BOOLEAN DEFAULT FALSE"
                        ))
                    except Exception as e:
                        print(f"Standard SQL failed, trying PostgreSQL syntax: {e}")
                        conn.execute(text(
                            "ALTER TABLE users ADD COLUMN IF NOT EXISTS competitor_tracking_enabled BOOLEAN DEFAULT FALSE"
                        ))
                        
                conn.commit()
                print("Column added successfully")
            else:
                print("Column competitor_tracking_enabled already exists in users table")
                
        return True
    except Exception as e:
        print(f"Error adding competitor_tracking_enabled column: {str(e)}")
        return False
