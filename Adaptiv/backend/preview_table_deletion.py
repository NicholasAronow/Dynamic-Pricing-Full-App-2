#!/usr/bin/env python3
"""
Database Table Deletion Preview Script
Shows what tables exist and would be deleted, without actually deleting them.
"""

import os
import sys
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import engine, SessionLocal

# Define the tables to delete
TABLES_TO_DELETE = [
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
    'cogs',
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

def main():
    """Main function to preview table deletion."""
    print("👀 Database Table Deletion Preview")
    print("=" * 50)
    
    session = SessionLocal()
    
    try:
        existing_tables = []
        missing_tables = []
        total_rows = 0
        
        print("\n📋 Checking tables...")
        
        for table_name in TABLES_TO_DELETE:
            if check_table_exists(table_name):
                row_count = get_table_row_count(session, table_name)
                existing_tables.append((table_name, row_count))
                total_rows += row_count
                print(f"✅ {table_name} - {row_count} rows")
            else:
                missing_tables.append(table_name)
                print(f"❌ {table_name} - does not exist")
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 DELETION PREVIEW SUMMARY")
        print("=" * 50)
        print(f"📋 Tables that would be deleted: {len(existing_tables)}")
        print(f"⚠️  Tables that don't exist: {len(missing_tables)}")
        print(f"🗂️  Total rows that would be deleted: {total_rows:,}")
        
        if existing_tables:
            print(f"\n🗑️  Tables to be deleted:")
            for table_name, row_count in existing_tables:
                print(f"   - {table_name} ({row_count:,} rows)")
        
        if missing_tables:
            print(f"\n⚠️  Tables that don't exist:")
            for table_name in missing_tables:
                print(f"   - {table_name}")
        
        print(f"\n💡 To actually delete these tables, run: python3 delete_tables_script.py")
            
    except Exception as e:
        print(f"\n❌ Error during preview: {e}")
        
    finally:
        session.close()
        print("\n🔒 Database connection closed.")

if __name__ == "__main__":
    main()
