#!/usr/bin/env python3
"""
Migration script to add sync_metadata column to pos_integrations table
"""

from sqlalchemy import text
from sqlalchemy import inspect
from config.database import engine

def add_sync_metadata_column():
    """Add sync_metadata column to pos_integrations table (SQLite/Postgres compatible)."""
    try:
        inspector = inspect(engine)
        existing_cols = [c["name"] for c in inspector.get_columns("pos_integrations")]
        if "sync_metadata" in existing_cols:
            print("Column 'sync_metadata' already exists in pos_integrations table")
            return

        # Use TEXT so it works across SQLite and Postgres (JSON is represented as TEXT in SQLite)
        sql = "ALTER TABLE pos_integrations ADD COLUMN sync_metadata TEXT"

        with engine.connect() as connection:
            connection.execute(text(sql))
            connection.commit()
            print("Successfully added sync_metadata column to pos_integrations table")
    except Exception as e:
        print(f"Error adding sync_metadata column: {str(e)}")
        raise

if __name__ == "__main__":
    add_sync_metadata_column()
