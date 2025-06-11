"""
Migration script to add batch_id and sync_timestamp columns to competitor_items table
"""
from sqlalchemy import create_engine, Column, String, MetaData, Table
import sqlalchemy as sa
import sys
import os
from datetime import datetime

# Add parent directory to path to import from database.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import DATABASE_URL

def upgrade():
    """Add batch_id and sync_timestamp columns to competitor_items table"""
    print("Starting migration: add batch tracking fields to competitor_items table")
    
    # Create a connection
    engine = create_engine(DATABASE_URL)
    metadata = MetaData()
    metadata.bind = engine
    connection = engine.connect()
    inspector = sa.inspect(engine)
    
    try:
        # Begin transaction
        transaction = connection.begin()
        
        print("\n=== Processing competitor_items table ===")
        if inspector.has_table('competitor_items'):
            # Check if the columns already exist
            columns = [col['name'] for col in inspector.get_columns('competitor_items')]
            
            # Add batch_id column if it doesn't exist
            if 'batch_id' not in columns:
                print("Adding batch_id column to competitor_items...")
                connection.execute(sa.text(
                    "ALTER TABLE competitor_items ADD COLUMN batch_id VARCHAR(100);"
                ))
                
                # Set default batch_id for existing records
                default_batch_id = f"migration_{int(datetime.now().timestamp())}"
                print(f"Setting default batch_id '{default_batch_id}' for existing records...")
                connection.execute(sa.text(
                    f"UPDATE competitor_items SET batch_id = '{default_batch_id}' WHERE batch_id IS NULL;"
                ))
            else:
                print("batch_id column already exists in competitor_items, skipping addition")
            
            # Add sync_timestamp column if it doesn't exist
            if 'sync_timestamp' not in columns:
                print("Adding sync_timestamp column to competitor_items...")
                connection.execute(sa.text(
                    "ALTER TABLE competitor_items ADD COLUMN sync_timestamp TIMESTAMP;"
                ))
                
                # Set default timestamp for existing records
                now = datetime.now()
                print(f"Setting default sync_timestamp '{now}' for existing records...")
                connection.execute(sa.text(
                    f"UPDATE competitor_items SET sync_timestamp = '{now.isoformat()}' WHERE sync_timestamp IS NULL;"
                ))
            else:
                print("sync_timestamp column already exists in competitor_items, skipping addition")
            
            # Create a composite index for faster queries if it doesn't exist
            indices = inspector.get_indexes('competitor_items')
            index_names = [idx['name'] for idx in indices]
            if 'ix_competitor_items_name_batch' not in index_names:
                print("Creating composite index on (competitor_name, batch_id) for competitor_items...")
                connection.execute(sa.text(
                    "CREATE INDEX ix_competitor_items_name_batch ON competitor_items (competitor_name, batch_id);"
                ))
            else:
                print("Composite index already exists for competitor_items, skipping creation")
                
            # Commit transaction
            transaction.commit()
            print("Migration completed successfully!")
        else:
            print("competitor_items table does not exist, skipping migration")
            transaction.rollback()
    
    except Exception as e:
        print(f"Error during migration: {e}")
        transaction.rollback()
        raise
    finally:
        connection.close()

if __name__ == "__main__":
    upgrade()
