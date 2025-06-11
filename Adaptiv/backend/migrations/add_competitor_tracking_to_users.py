import sys
from sqlalchemy import text

# Import the engine from the project's database.py
sys.path.append('.')
from database import engine

# Define the migration
def migrate():
    print("Starting migration: Adding competitor_tracking_enabled to users table...")
    
    with engine.begin() as connection:
        # Check if the column already exists to avoid errors
        # Use pragma_table_info for SQLite compatibility
        check_column = connection.execute(text("""
            SELECT name FROM pragma_table_info('users') WHERE name = 'competitor_tracking_enabled'
        """))
        
        if check_column.fetchone() is None:
            print("Adding competitor_tracking_enabled column to users table...")
            
            # Add the column with a default value of False
            # SQLite syntax for ALTER TABLE
            connection.execute(text("""
                ALTER TABLE users 
                ADD COLUMN competitor_tracking_enabled BOOLEAN NOT NULL DEFAULT 0
            """))
            
            print("Successfully added competitor_tracking_enabled column")
        else:
            print("Column competitor_tracking_enabled already exists in users table")
            
    print("Migration completed successfully")

if __name__ == "__main__":
    migrate()
