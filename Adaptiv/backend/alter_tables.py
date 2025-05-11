"""
Script to alter existing database tables to add user_id columns.
Run this script before running the migrate_existing_data.py script.
"""

import sqlite3
import os

# Database path - adjust if your database is stored elsewhere
DB_PATH = 'adaptiv.db'

def alter_tables():
    print(f"Connecting to database at {DB_PATH}...")
    
    # Connect to the SQLite database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Add user_id column to items table
        print("Adding user_id column to items table...")
        cursor.execute('ALTER TABLE items ADD COLUMN user_id INTEGER REFERENCES users(id)')
        
        # Add user_id column to price_history table
        print("Adding user_id column to price_history table...")
        cursor.execute('ALTER TABLE price_history ADD COLUMN user_id INTEGER REFERENCES users(id)')
        
        # Add user_id column to orders table
        print("Adding user_id column to orders table...")
        cursor.execute('ALTER TABLE orders ADD COLUMN user_id INTEGER REFERENCES users(id)')
        
        # Commit the changes
        conn.commit()
        print("Database schema updated successfully.")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print(f"Column already exists: {e}")
        else:
            print(f"Error altering tables: {e}")
            conn.rollback()
            raise
    finally:
        conn.close()

if __name__ == "__main__":
    alter_tables()
