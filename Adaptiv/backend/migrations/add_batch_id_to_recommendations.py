"""
Migration script to add batch_id column to pricing_recommendations table
"""
from sqlalchemy import create_engine, Column, String, MetaData, Table
import sqlalchemy as sa
import sys
import os

# Add parent directory to path to import from database.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import DATABASE_URL

def upgrade():
    """Add batch_id column to pricing_recommendations and bundle_recommendations tables"""
    print("Starting migration: add batch_id to recommendations tables")
    
    # Create a connection
    engine = create_engine(DATABASE_URL)
    metadata = MetaData()
    metadata.bind = engine
    connection = engine.connect()
    inspector = sa.inspect(engine)
    
    try:
        # Begin transaction
        transaction = connection.begin()
        
        # Handle pricing_recommendations table
        print("\n=== Processing pricing_recommendations table ===")
        if inspector.has_table('pricing_recommendations'):
            # Check if the column already exists
            columns = [col['name'] for col in inspector.get_columns('pricing_recommendations')]
            if 'batch_id' not in columns:
                # Add batch_id column if it doesn't exist
                print("Adding batch_id column to pricing_recommendations...")
                connection.execute(sa.text(
                    "ALTER TABLE pricing_recommendations ADD COLUMN batch_id VARCHAR(100);"
                ))
            else:
                print("batch_id column already exists in pricing_recommendations, skipping addition")
            
            # Create an index for faster queries if it doesn't exist
            indices = inspector.get_indexes('pricing_recommendations')
            index_names = [idx['name'] for idx in indices]
            if 'ix_pricing_recommendations_batch_id' not in index_names:
                print("Creating index on batch_id column for pricing_recommendations...")
                connection.execute(sa.text(
                    "CREATE INDEX ix_pricing_recommendations_batch_id ON pricing_recommendations (batch_id);"
                ))
            else:
                print("Index on batch_id already exists for pricing_recommendations, skipping creation")
            
            # Update existing records with a default batch ID
            print("Updating existing records with default batch_id in pricing_recommendations...")
            connection.execute(sa.text(
                "UPDATE pricing_recommendations SET batch_id = 'legacy_batch_' || strftime('%Y%m%d', recommendation_date) WHERE batch_id IS NULL;"
            ))
        else:
            print("pricing_recommendations table does not exist, skipping")
        
        # Handle bundle_recommendations table
        print("\n=== Processing bundle_recommendations table ===")
        if inspector.has_table('bundle_recommendations'):
            # Check if the column already exists
            columns = [col['name'] for col in inspector.get_columns('bundle_recommendations')]
            if 'batch_id' not in columns:
                # Add batch_id column if it doesn't exist
                print("Adding batch_id column to bundle_recommendations...")
                connection.execute(sa.text(
                    "ALTER TABLE bundle_recommendations ADD COLUMN batch_id VARCHAR(100);"
                ))
            else:
                print("batch_id column already exists in bundle_recommendations, skipping addition")
            
            # Create an index for faster queries if it doesn't exist
            indices = inspector.get_indexes('bundle_recommendations')
            index_names = [idx['name'] for idx in indices]
            if 'ix_bundle_recommendations_batch_id' not in index_names:
                print("Creating index on batch_id column for bundle_recommendations...")
                connection.execute(sa.text(
                    "CREATE INDEX ix_bundle_recommendations_batch_id ON bundle_recommendations (batch_id);"
                ))
            else:
                print("Index on batch_id already exists for bundle_recommendations, skipping creation")
            
            # Update existing records with a default batch ID
            print("Updating existing records with default batch_id in bundle_recommendations...")
            connection.execute(sa.text(
                "UPDATE bundle_recommendations SET batch_id = 'legacy_batch_' || strftime('%Y%m%d', recommendation_date) WHERE batch_id IS NULL;"
            ))
        else:
            print("bundle_recommendations table does not exist, skipping")
        
        # SQLite doesn't support ALTER COLUMN NOT NULL directly
        # We need to use a more complex approach for SQLite
        # For this application, we'll enforce NOT NULL at the application level instead
        if DATABASE_URL.startswith('sqlite'):
            print("SQLite database detected - NOT NULL constraint will be enforced at application level")
        else:
            # For other databases like PostgreSQL, we can use ALTER COLUMN
            print("Making batch_id not nullable for future entries...")
            connection.execute(sa.text(
                "ALTER TABLE pricing_recommendations ALTER COLUMN batch_id SET NOT NULL;"
            ))
        
        # Commit the transaction
        transaction.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        # Roll back the transaction in case of error
        transaction.rollback()
        print(f"Error during migration: {str(e)}")
        raise
    finally:
        # Close the connection
        connection.close()

def downgrade():
    """Remove batch_id column from pricing_recommendations and bundle_recommendations tables"""
    print("Starting downgrade: remove batch_id from recommendation tables")
    
    # Create a connection
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    inspector = sa.inspect(engine)
    
    try:
        # Begin transaction
        transaction = connection.begin()
        
        # Handle pricing_recommendations table
        print("\n=== Processing pricing_recommendations table ===")
        if inspector.has_table('pricing_recommendations'):
            # Check if the index exists before trying to drop it
            indices = inspector.get_indexes('pricing_recommendations')
            index_names = [idx['name'] for idx in indices]
            
            if 'ix_pricing_recommendations_batch_id' in index_names:
                # Drop the index first
                print("Dropping index on batch_id column in pricing_recommendations...")
                connection.execute(sa.text(
                    "DROP INDEX IF EXISTS ix_pricing_recommendations_batch_id;"
                ))
            else:
                print("Index ix_pricing_recommendations_batch_id not found, skipping drop")
            
            # Check if column exists before dropping
            columns = [col['name'] for col in inspector.get_columns('pricing_recommendations')]
            
            if 'batch_id' in columns:
                if DATABASE_URL.startswith('sqlite'):
                    # SQLite requires more complex handling for dropping columns
                    print("SQLite detected - creating temporary table without batch_id column")
                    
                    # Get all columns except batch_id
                    columns_to_keep = [col for col in columns if col != 'batch_id']
                    columns_str = ', '.join(columns_to_keep)
                    
                    # Create a new table without the batch_id column
                    connection.execute(sa.text(f"""
                        CREATE TABLE pricing_recommendations_temp AS 
                        SELECT {columns_str} FROM pricing_recommendations;
                    """))
                    
                    # Drop the old table
                    connection.execute(sa.text("DROP TABLE pricing_recommendations;"))
                    
                    # Rename the new table to the original name
                    connection.execute(sa.text(
                        "ALTER TABLE pricing_recommendations_temp RENAME TO pricing_recommendations;"
                    ))
                    
                    print("Recreated pricing_recommendations table without batch_id column")
                else:
                    # For other databases, we can use ALTER TABLE DROP COLUMN
                    print("Dropping batch_id column from pricing_recommendations...")
                    connection.execute(sa.text(
                        "ALTER TABLE pricing_recommendations DROP COLUMN batch_id;"
                    ))
            else:
                print("batch_id column not found in pricing_recommendations, skipping drop")
        else:
            print("pricing_recommendations table does not exist, skipping")
        
        # Handle bundle_recommendations table
        print("\n=== Processing bundle_recommendations table ===")
        if inspector.has_table('bundle_recommendations'):
            # Check if the index exists before trying to drop it
            indices = inspector.get_indexes('bundle_recommendations')
            index_names = [idx['name'] for idx in indices]
            
            if 'ix_bundle_recommendations_batch_id' in index_names:
                # Drop the index first
                print("Dropping index on batch_id column in bundle_recommendations...")
                connection.execute(sa.text(
                    "DROP INDEX IF EXISTS ix_bundle_recommendations_batch_id;"
                ))
            else:
                print("Index ix_bundle_recommendations_batch_id not found, skipping drop")
            
            # Check if column exists before dropping
            columns = [col['name'] for col in inspector.get_columns('bundle_recommendations')]
            
            if 'batch_id' in columns:
                if DATABASE_URL.startswith('sqlite'):
                    # SQLite requires more complex handling for dropping columns
                    print("SQLite detected - creating temporary table without batch_id column")
                    
                    # Get all columns except batch_id
                    columns_to_keep = [col for col in columns if col != 'batch_id']
                    columns_str = ', '.join(columns_to_keep)
                    
                    # Create a new table without the batch_id column
                    connection.execute(sa.text(f"""
                        CREATE TABLE bundle_recommendations_temp AS 
                        SELECT {columns_str} FROM bundle_recommendations;
                    """))
                    
                    # Drop the old table
                    connection.execute(sa.text("DROP TABLE bundle_recommendations;"))
                    
                    # Rename the new table to the original name
                    connection.execute(sa.text(
                        "ALTER TABLE bundle_recommendations_temp RENAME TO bundle_recommendations;"
                    ))
                    
                    print("Recreated bundle_recommendations table without batch_id column")
                else:
                    # For other databases, we can use ALTER TABLE DROP COLUMN
                    print("Dropping batch_id column from bundle_recommendations...")
                    connection.execute(sa.text(
                        "ALTER TABLE bundle_recommendations DROP COLUMN batch_id;"
                    ))
            else:
                print("batch_id column not found in bundle_recommendations, skipping drop")
        else:
            print("bundle_recommendations table does not exist, skipping")
        
        # Commit the transaction
        transaction.commit()
        print("Downgrade completed successfully!")
        
    except Exception as e:
        # Roll back the transaction in case of error
        transaction.rollback()
        print(f"Error during downgrade: {str(e)}")
        raise
    finally:
        # Close the connection
        connection.close()

if __name__ == "__main__":
    upgrade()
