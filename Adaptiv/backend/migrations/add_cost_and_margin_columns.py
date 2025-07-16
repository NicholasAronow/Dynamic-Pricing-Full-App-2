"""
Migration script to add cost and margin columns to orders and order_items tables.
"""
from sqlalchemy import create_engine, text
from database import DATABASE_URL

def run_migration():
    """
    Run the migration to add cost and margin-related columns to orders and order_items tables.
    """
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Create a connection
    with engine.connect() as connection:
        try:
            # Add columns to orders table
            add_columns_to_orders(connection)
            
            # Add columns to order_items table
            add_columns_to_order_items(connection)
            
            # Commit the transaction
            connection.commit()
            print("Migration completed successfully!")
        except Exception as e:
            print(f"Error during migration: {e}")
            raise e

def add_columns_to_orders(connection):
    """Add total_cost, gross_margin, and net_margin columns to orders table."""
    # Check if columns already exist to prevent errors
    columns_to_add = {
        'total_cost': 'FLOAT',
        'gross_margin': 'FLOAT',
        'net_margin': 'FLOAT'
    }
    
    for column_name, data_type in columns_to_add.items():
        if not column_exists(connection, 'orders', column_name):
            print(f"Adding {column_name} column to orders table...")
            connection.execute(text(
                f"ALTER TABLE orders ADD COLUMN {column_name} {data_type}"
            ))
        else:
            print(f"Column {column_name} already exists in orders table. Skipping.")

def add_columns_to_order_items(connection):
    """Add unit_cost and subtotal_cost columns to order_items table."""
    # Check if columns already exist to prevent errors
    columns_to_add = {
        'unit_cost': 'FLOAT',
        'subtotal_cost': 'FLOAT'
    }
    
    for column_name, data_type in columns_to_add.items():
        if not column_exists(connection, 'order_items', column_name):
            print(f"Adding {column_name} column to order_items table...")
            connection.execute(text(
                f"ALTER TABLE order_items ADD COLUMN {column_name} {data_type}"
            ))
        else:
            print(f"Column {column_name} already exists in order_items table. Skipping.")

def column_exists(connection, table_name, column_name):
    """Check if a column exists in the table."""
    # For SQLite, we can query the pragma_table_info
    if DATABASE_URL.startswith('sqlite'):
        result = connection.execute(text(
            f"SELECT COUNT(*) FROM pragma_table_info('{table_name}') "
            f"WHERE name='{column_name}'"
        ))
        return result.scalar() > 0
    else:
        # For other databases like PostgreSQL
        result = connection.execute(text(
            f"SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            f"WHERE table_name='{table_name}' AND column_name='{column_name}')"
        ))
        return result.scalar()

if __name__ == "__main__":
    run_migration()
