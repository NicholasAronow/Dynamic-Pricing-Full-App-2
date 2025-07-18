#!/usr/bin/env python3
"""
Database Migration Script: Add is_admin column to users table

This script safely adds the is_admin column to the users table in your Render database.
It handles the migration gracefully and provides rollback capability.

Usage:
    python migrate_admin_column.py --migrate    # Add the column
    python migrate_admin_column.py --rollback   # Remove the column (if needed)
    python migrate_admin_column.py --status     # Check current status
"""

import argparse
import sys
import os
from sqlalchemy import create_engine, text, inspect, MetaData, Table, Column, Boolean
from sqlalchemy.exc import SQLAlchemyError
from database import DATABASE_URL
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_engine():
    """Get database engine"""
    database_url = DATABASE_URL
    if not database_url:
        logger.error("DATABASE_URL not found. Please set your database connection string.")
        sys.exit(1)
    
    return create_engine(database_url)

def check_column_exists(engine, table_name, column_name):
    """Check if a column exists in a table"""
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        return any(col['name'] == column_name for col in columns)
    except Exception as e:
        logger.error(f"Error checking column existence: {e}")
        return False

def migrate_add_admin_column(engine):
    """Add is_admin column to users table"""
    try:
        # Check if column already exists
        if check_column_exists(engine, 'users', 'is_admin'):
            logger.info("Column 'is_admin' already exists in users table. No migration needed.")
            return True
        
        logger.info("Adding 'is_admin' column to users table...")
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Add the column with default value False
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN is_admin BOOLEAN DEFAULT FALSE NOT NULL
                """))
                
                # Commit the transaction
                trans.commit()
                logger.info("Successfully added 'is_admin' column to users table.")
                
                # Verify the column was added
                if check_column_exists(engine, 'users', 'is_admin'):
                    logger.info("Migration verified: 'is_admin' column exists.")
                    return True
                else:
                    logger.error("Migration verification failed: column not found after creation.")
                    return False
                    
            except Exception as e:
                trans.rollback()
                logger.error(f"Error during migration, rolled back: {e}")
                return False
                
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

def rollback_admin_column(engine):
    """Remove is_admin column from users table (rollback)"""
    try:
        # Check if column exists
        if not check_column_exists(engine, 'users', 'is_admin'):
            logger.info("Column 'is_admin' does not exist in users table. No rollback needed.")
            return True
        
        logger.warning("Rolling back: Removing 'is_admin' column from users table...")
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Remove the column
                conn.execute(text("""
                    ALTER TABLE users 
                    DROP COLUMN is_admin
                """))
                
                # Commit the transaction
                trans.commit()
                logger.info("Successfully removed 'is_admin' column from users table.")
                
                # Verify the column was removed
                if not check_column_exists(engine, 'users', 'is_admin'):
                    logger.info("Rollback verified: 'is_admin' column removed.")
                    return True
                else:
                    logger.error("Rollback verification failed: column still exists after removal.")
                    return False
                    
            except Exception as e:
                trans.rollback()
                logger.error(f"Error during rollback, rolled back: {e}")
                return False
                
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        return False

def check_migration_status(engine):
    """Check the current status of the migration"""
    try:
        logger.info("Checking migration status...")
        
        # Check if users table exists
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'users' not in tables:
            logger.error("Users table does not exist!")
            return False
        
        # Check columns in users table
        columns = inspector.get_columns('users')
        column_names = [col['name'] for col in columns]
        
        logger.info(f"Users table columns: {column_names}")
        
        if 'is_admin' in column_names:
            logger.info("✅ Migration status: 'is_admin' column EXISTS")
            
            # Check some sample data
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) as total_users, 
                           COUNT(CASE WHEN is_admin = true THEN 1 END) as admin_users
                    FROM users
                """))
                row = result.fetchone()
                logger.info(f"Total users: {row.total_users}, Admin users: {row.admin_users}")
        else:
            logger.info("❌ Migration status: 'is_admin' column MISSING")
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking migration status: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Migrate is_admin column for users table')
    parser.add_argument('--migrate', action='store_true', help='Add is_admin column')
    parser.add_argument('--rollback', action='store_true', help='Remove is_admin column')
    parser.add_argument('--status', action='store_true', help='Check migration status')
    
    args = parser.parse_args()
    
    if not any([args.migrate, args.rollback, args.status]):
        parser.print_help()
        sys.exit(1)
    
    try:
        engine = get_engine()
        logger.info("Connected to database successfully.")
        
        if args.status:
            success = check_migration_status(engine)
        elif args.migrate:
            success = migrate_add_admin_column(engine)
        elif args.rollback:
            # Confirm rollback
            confirm = input("Are you sure you want to remove the is_admin column? This will delete all admin status data. (yes/no): ")
            if confirm.lower() == 'yes':
                success = rollback_admin_column(engine)
            else:
                logger.info("Rollback cancelled.")
                success = True
        
        if success:
            logger.info("Operation completed successfully.")
            sys.exit(0)
        else:
            logger.error("Operation failed.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
