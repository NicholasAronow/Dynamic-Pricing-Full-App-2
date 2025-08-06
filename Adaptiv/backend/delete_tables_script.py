#!/usr/bin/env python3
"""
Database Table Deletion Script
Deletes specified tables from the Dynamic Pricing database.

Tables to delete:
- Strategy Evolutions
- Pricing Decisions & Experiments & Reports
- Price Recommendation Actions
- Performance Anomalies & Baselines
- Bundle Recommendations
- COGS
- Customer Reports
- Experiment Learnings
- Experiment Price Changes
- Experiment Recommendations
"""

import os
import sys
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import engine, SessionLocal

# Define the tables to delete (in order to handle foreign key constraints)
TABLES_TO_DELETE = [
    # Agent memory and analysis tables
    'strategy_evolutions',
    'pricing_decisions', 
    'experiment_learnings',
    'experiment_price_changes',
    'price_recommendation_actions',
    'experiment_recommendations',
    'pricing_reports',
    'performance_anomalies',
    'performance_baselines',
    'bundle_recommendations',
    'customer_reports',
    'competitor_reports',
    'market_reports',
    
    # Core business tables
    'cogs',
    
    # Agent memory tables
    'pricing_recommendations',
    'pricing_experiments',
    'data_collection_snapshots',
    'market_analysis_snapshots',
    'competitor_price_histories',
    'agent_memories'
]

def check_table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        return table_name in existing_tables
    except Exception as e:
        print(f"Error checking if table {table_name} exists: {e}")
        return False

def get_table_row_count(session, table_name: str) -> int:
    """Get the number of rows in a table."""
    try:
        result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.scalar()
    except Exception as e:
        print(f"Error getting row count for {table_name}: {e}")
        return 0

def delete_table(session, table_name: str) -> bool:
    """Delete a table from the database."""
    try:
        # First check if table exists
        if not check_table_exists(table_name):
            print(f"⚠️  Table '{table_name}' does not exist, skipping...")
            return True
            
        # Get row count before deletion
        row_count = get_table_row_count(session, table_name)
        
        # Drop the table
        session.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
        session.commit()
        
        print(f"✅ Successfully deleted table '{table_name}' (had {row_count} rows)")
        return True
        
    except SQLAlchemyError as e:
        print(f"❌ Error deleting table '{table_name}': {e}")
        session.rollback()
        return False
    except Exception as e:
        print(f"❌ Unexpected error deleting table '{table_name}': {e}")
        session.rollback()
        return False

def main():
    """Main function to delete all specified tables."""
    print("🗑️  Database Table Deletion Script")
    print("=" * 50)
    
    # Get user confirmation
    print("\nTables to be deleted:")
    for table in TABLES_TO_DELETE:
        if check_table_exists(table):
            print(f"  - {table}")
    
    print(f"\nThis will permanently delete {len(TABLES_TO_DELETE)} tables and all their data.")
    confirmation = input("\nAre you sure you want to proceed? (type 'DELETE' to confirm): ")
    
    if confirmation != 'DELETE':
        print("❌ Operation cancelled.")
        return
    
    # Create database session
    session = SessionLocal()
    
    try:
        print(f"\n🚀 Starting deletion of {len(TABLES_TO_DELETE)} tables...")
        
        deleted_count = 0
        skipped_count = 0
        failed_count = 0
        
        # Disable foreign key constraints temporarily (for SQLite)
        try:
            session.execute(text("PRAGMA foreign_keys = OFF"))
            session.commit()
        except:
            pass  # Not SQLite or doesn't support this pragma
        
        # Delete tables in the specified order
        for table_name in TABLES_TO_DELETE:
            print(f"\n🔄 Processing table: {table_name}")
            
            if not check_table_exists(table_name):
                print(f"⚠️  Table '{table_name}' does not exist, skipping...")
                skipped_count += 1
                continue
            
            if delete_table(session, table_name):
                deleted_count += 1
            else:
                failed_count += 1
        
        # Re-enable foreign key constraints
        try:
            session.execute(text("PRAGMA foreign_keys = ON"))
            session.commit()
        except:
            pass
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 DELETION SUMMARY")
        print("=" * 50)
        print(f"✅ Tables deleted: {deleted_count}")
        print(f"⚠️  Tables skipped (didn't exist): {skipped_count}")
        print(f"❌ Tables failed: {failed_count}")
        print(f"📋 Total processed: {len(TABLES_TO_DELETE)}")
        
        if failed_count == 0:
            print("\n🎉 All operations completed successfully!")
        else:
            print(f"\n⚠️  {failed_count} tables failed to delete. Check the errors above.")
            
    except Exception as e:
        print(f"\n❌ Fatal error during deletion process: {e}")
        session.rollback()
        
    finally:
        session.close()
        print("\n🔒 Database connection closed.")

if __name__ == "__main__":
    main()
