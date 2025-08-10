#!/usr/bin/env python3
"""
Migration script to add location_ids column to pos_integrations table
"""

from sqlalchemy import text
from sqlalchemy import inspect
from config.database import engine

def add_location_ids_column():
    """Add location_ids column to pos_integrations table (SQLite/Postgres compatible)."""
    try:
        inspector = inspect(engine)
        existing_cols = [c["name"] for c in inspector.get_columns("pos_integrations")]
        if "location_ids" in existing_cols:
            print("Column 'location_ids' already exists in pos_integrations table")
            return

        dialect = engine.dialect.name
        sql = "ALTER TABLE pos_integrations ADD COLUMN location_ids TEXT"

        with engine.connect() as connection:
            connection.execute(text(sql))
            connection.commit()
            print(
                f"Successfully added location_ids column to pos_integrations table (dialect={dialect})"
            )
    except Exception as e:
        print(f"Error adding location_ids column: {str(e)}")
        raise

if __name__ == "__main__":
    add_location_ids_column()
