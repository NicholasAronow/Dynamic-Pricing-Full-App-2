"""
Migration script to add item_id column to the recipes table.
"""
from sqlalchemy import create_engine, text
from database import DATABASE_URL

def run_migration():
    """
    Run the migration to add item_id column to the recipes table.
    """
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Create a connection
    with engine.connect() as connection:
        # Check if column already exists to prevent errors (SQLite compatible way)
        try:
            # For SQLite, we can query the pragma_table_info
            if DATABASE_URL.startswith('sqlite'):
                result = connection.execute(text(
                    "SELECT COUNT(*) FROM pragma_table_info('recipes') "
                    "WHERE name='item_id'"
                ))
                column_exists = result.scalar() > 0
            else:
                # For other databases like PostgreSQL
                result = connection.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                    "WHERE table_name='recipes' AND column_name='item_id')"
                ))
                column_exists = result.scalar()
                
            if not column_exists:
                print("Adding item_id column to recipes table...")
                # Add item_id column to recipes table
                connection.execute(text(
                    "ALTER TABLE recipes ADD COLUMN item_id INTEGER"
                ))
                
                # SQLite doesn't support ADD CONSTRAINT in ALTER TABLE
                if not DATABASE_URL.startswith('sqlite'):
                    # Add foreign key constraint for PostgreSQL
                    connection.execute(text(
                        "ALTER TABLE recipes ADD CONSTRAINT fk_recipes_item_id "
                        "FOREIGN KEY (item_id) REFERENCES items (id)"
                    ))
                
                # Add index for the new column
                connection.execute(text(
                    "CREATE INDEX idx_recipes_item_id ON recipes (item_id)"
                ))
                
                # Commit the transaction
                connection.commit()
                print("Migration completed successfully!")
            else:
                print("Column item_id already exists in recipes table. Skipping migration.")
        except Exception as e:
            print(f"Error during migration: {e}")
            raise e

if __name__ == "__main__":
    run_migration()
