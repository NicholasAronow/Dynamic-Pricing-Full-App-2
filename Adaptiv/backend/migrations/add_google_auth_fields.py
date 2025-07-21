"""
Migration script to add Google authentication fields to the User model
"""
import sys
import os
from sqlalchemy import Column, String, Boolean, text, inspect
from sqlalchemy.exc import OperationalError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import engine
from config.database import Base
from models import User

def add_columns():
    # Check if columns exist and add them if they don't
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('users')]

    # Add name column if it doesn't exist
    if 'name' not in columns:
        try:
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE users ADD COLUMN name VARCHAR(255)'))
                conn.commit()
                print("Added 'name' column to users table")
        except Exception as e:
            print(f"Error adding 'name' column: {e}")
    else:
        print("'name' column already exists")

    # Add is_google_user column if it doesn't exist
    if 'is_google_user' not in columns:
        try:
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE users ADD COLUMN is_google_user BOOLEAN DEFAULT FALSE'))
                conn.commit()
                print("Added 'is_google_user' column to users table")
        except Exception as e:
            print(f"Error adding 'is_google_user' column: {e}")
    else:
        print("'is_google_user' column already exists")

if __name__ == "__main__":
    add_columns()
    print("Migration completed successfully.")
