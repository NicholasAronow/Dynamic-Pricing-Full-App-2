"""
Migration script to add stripe_customer_id and subscription_tier columns to the users table.
"""
from sqlalchemy import create_engine, text
from config.settings import get_settings; DATABASE_URL = get_settings().database_url

def run_migration():
    """
    Run the migration to add Stripe fields to the users table.
    """
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Create a connection
    with engine.connect() as connection:
        # Check if column already exists to prevent errors (SQLite compatible way)
        try:
            # For SQLite, we can query the pragma_table_info
            if DATABASE_URL.startswith('sqlite'):
                # Check for stripe_customer_id column
                result = connection.execute(text(
                    "SELECT COUNT(*) FROM pragma_table_info('users') "
                    "WHERE name='stripe_customer_id'"
                ))
                customer_id_exists = result.scalar() > 0
                
                # Check for subscription_tier column
                result = connection.execute(text(
                    "SELECT COUNT(*) FROM pragma_table_info('users') "
                    "WHERE name='subscription_tier'"
                ))
                subscription_tier_exists = result.scalar() > 0
            else:
                # For other databases like PostgreSQL
                # Check for stripe_customer_id column
                result = connection.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                    "WHERE table_name='users' AND column_name='stripe_customer_id')"
                ))
                customer_id_exists = result.scalar()
                
                # Check for subscription_tier column
                result = connection.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                    "WHERE table_name='users' AND column_name='subscription_tier')"
                ))
                subscription_tier_exists = result.scalar()
                
            # Add stripe_customer_id column if it doesn't exist
            if not customer_id_exists:
                print("Adding stripe_customer_id column to users table...")
                # Add stripe_customer_id column to users table
                connection.execute(text(
                    "ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR"
                ))
                print("Added stripe_customer_id column successfully!")
            else:
                print("Column stripe_customer_id already exists in users table. Skipping.")
            
            # Add subscription_tier column if it doesn't exist
            if not subscription_tier_exists:
                print("Adding subscription_tier column to users table...")
                # Add subscription_tier column to users table with default value 'free'
                if DATABASE_URL.startswith('sqlite'):
                    connection.execute(text(
                        "ALTER TABLE users ADD COLUMN subscription_tier VARCHAR DEFAULT 'free'"
                    ))
                else:
                    # PostgreSQL syntax
                    connection.execute(text(
                        "ALTER TABLE users ADD COLUMN subscription_tier VARCHAR DEFAULT 'free'"
                    ))
                print("Added subscription_tier column successfully!")
            else:
                print("Column subscription_tier already exists in users table. Skipping.")
            
            # Commit the transaction
            connection.commit()
            print("Migration completed successfully!")
        except Exception as e:
            print(f"Error during migration: {e}")
            raise e

if __name__ == "__main__":
    run_migration()
