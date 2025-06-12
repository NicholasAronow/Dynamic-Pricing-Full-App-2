"""
Direct migration script to add competitor_tracking_enabled column to users table.
This standalone script is designed to be run directly in the Render environment.
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect

def run_migration():
    """Add competitor_tracking_enabled column to users table"""
    # Get database URL directly from environment variable
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return False
    
    try:
        print(f"Connecting to database...")
        # Create engine
        engine = create_engine(database_url)
        
        print(f"Checking database type...")
        # Check database type
        is_sqlite = database_url.startswith('sqlite')
        is_postgres = 'postgresql' in database_url
        
        print(f"Database appears to be: {'SQLite' if is_sqlite else 'PostgreSQL' if is_postgres else 'Unknown'}")
        
        # Add column with a default value of False
        with engine.connect() as conn:
            print("Checking if users table exists...")
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            if 'users' not in tables:
                print("ERROR: users table does not exist!")
                return False
                
            print("Checking if column already exists...")
            columns = [column['name'] for column in inspector.get_columns('users')]
            print(f"Found columns: {columns}")
            
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
                    # Try both syntaxes
                    try:
                        print("Trying standard SQL syntax...")
                        conn.execute(text(
                            "ALTER TABLE users ADD COLUMN competitor_tracking_enabled BOOLEAN DEFAULT FALSE"
                        ))
                    except Exception as e:
                        print(f"Standard SQL failed: {e}")
                        print("Trying PostgreSQL syntax...")
                        conn.execute(text(
                            "ALTER TABLE users ADD COLUMN IF NOT EXISTS competitor_tracking_enabled BOOLEAN DEFAULT FALSE"
                        ))
                        
                conn.commit()
                print("Column added successfully")
            else:
                print("Column competitor_tracking_enabled already exists in users table")
                
        return True
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting direct migration...")
    success = run_migration()
    if success:
        print("Migration completed successfully")
    else:
        print("Migration failed")
        sys.exit(1)
