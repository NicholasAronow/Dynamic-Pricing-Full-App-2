#!/usr/bin/env python3
"""
Migration script to upgrade PostgreSQL database for new CompetitorEntity structure.

This script:
1. Creates the new competitor_entities table
2. Adds competitor_id column to competitor_items table
3. Migrates existing competitor_items data to create CompetitorEntity records
4. Updates competitor_items to reference the new CompetitorEntity records
5. Adds proper indexes and constraints

Run this script to migrate your production database.
"""

import os
import sys
import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(backend_dir)
sys.path.insert(0, parent_dir)

# Import database configuration
try:
    from config.database import get_settings
    settings = get_settings()
    DATABASE_URL = settings.database_url
except ImportError:
    # Fallback to environment variable
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("ERROR: Could not find DATABASE_URL. Please set it as an environment variable.")
        sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """Run the complete migration process."""
    
    logger.info("🚀 Starting CompetitorEntity migration...")
    
    # Create database engine
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Step 1: Check if competitor_entities table exists
                logger.info("📋 Step 1: Checking existing database structure...")
                
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'competitor_entities'
                    );
                """))
                
                competitor_entities_exists = result.scalar()
                
                if not competitor_entities_exists:
                    logger.info("🏗️  Creating competitor_entities table...")
                    
                    # Create competitor_entities table
                    conn.execute(text("""
                        CREATE TABLE competitor_entities (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER NOT NULL REFERENCES users(id),
                            name VARCHAR NOT NULL,
                            address VARCHAR,
                            category VARCHAR,
                            phone VARCHAR,
                            website VARCHAR,
                            distance_km DOUBLE PRECISION,
                            latitude DOUBLE PRECISION,
                            longitude DOUBLE PRECISION,
                            menu_url VARCHAR,
                            score DOUBLE PRECISION,
                            is_selected BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            updated_at TIMESTAMP WITH TIME ZONE
                        );
                    """))
                    
                    # Create indexes
                    conn.execute(text("""
                        CREATE INDEX ix_competitor_entities_id ON competitor_entities(id);
                    """))
                    conn.execute(text("""
                        CREATE INDEX ix_competitor_entities_user_id ON competitor_entities(user_id);
                    """))
                    conn.execute(text("""
                        CREATE INDEX ix_competitor_entities_name ON competitor_entities(name);
                    """))
                    conn.execute(text("""
                        CREATE INDEX idx_user_competitor ON competitor_entities(user_id, name);
                    """))
                    
                    logger.info("✅ competitor_entities table created successfully")
                else:
                    logger.info("✅ competitor_entities table already exists")
                
                # Step 2: Check if competitor_id column exists in competitor_items
                logger.info("📋 Step 2: Checking competitor_items table structure...")
                
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = 'competitor_items' 
                        AND column_name = 'competitor_id'
                    );
                """))
                
                competitor_id_exists = result.scalar()
                
                if not competitor_id_exists:
                    logger.info("🔧 Adding competitor_id column to competitor_items...")
                    
                    # Add competitor_id column (nullable initially for migration)
                    conn.execute(text("""
                        ALTER TABLE competitor_items 
                        ADD COLUMN competitor_id INTEGER;
                    """))
                    
                    logger.info("✅ competitor_id column added")
                else:
                    logger.info("✅ competitor_id column already exists")
                
                # Step 3: Migrate existing data
                logger.info("📊 Step 3: Migrating existing competitor data...")
                
                # Get distinct competitors from competitor_items
                result = conn.execute(text("""
                    SELECT DISTINCT 
                        competitor_name,
                        MIN(created_at) as first_seen,
                        COUNT(*) as item_count
                    FROM competitor_items 
                    WHERE competitor_name IS NOT NULL 
                    AND competitor_name != ''
                    GROUP BY competitor_name
                    ORDER BY competitor_name;
                """))
                
                competitors = result.fetchall()
                logger.info(f"📈 Found {len(competitors)} unique competitors to migrate")
                
                # For each competitor, create or find CompetitorEntity
                migrated_count = 0
                for competitor_name, first_seen, item_count in competitors:
                    logger.info(f"🏪 Processing competitor: {competitor_name} ({item_count} items)")
                    
                    # Check if CompetitorEntity already exists
                    result = conn.execute(text("""
                        SELECT id FROM competitor_entities 
                        WHERE name = :name
                        LIMIT 1;
                    """), {"name": competitor_name})
                    
                    existing_entity = result.fetchone()
                    
                    if existing_entity:
                        competitor_entity_id = existing_entity[0]
                        logger.info(f"   ✅ Found existing entity with ID: {competitor_entity_id}")
                    else:
                        # Create new CompetitorEntity
                        # We'll assign to user_id = 1 as default, or you can modify this logic
                        # to determine the correct user based on your business logic
                        
                        # Try to find a user who has items for this competitor
                        user_result = conn.execute(text("""
                            SELECT DISTINCT ci.batch_id
                            FROM competitor_items ci
                            WHERE ci.competitor_name = :name
                            LIMIT 1;
                        """), {"name": competitor_name})
                        
                        # For now, we'll use user_id = 1 as default
                        # You may want to modify this based on your specific needs
                        default_user_id = 1
                        
                        result = conn.execute(text("""
                            INSERT INTO competitor_entities 
                            (user_id, name, created_at, updated_at)
                            VALUES (:user_id, :name, :created_at, :updated_at)
                            RETURNING id;
                        """), {
                            "user_id": default_user_id,
                            "name": competitor_name,
                            "created_at": first_seen or datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc)
                        })
                        
                        competitor_entity_id = result.scalar()
                        logger.info(f"   ✅ Created new entity with ID: {competitor_entity_id}")
                    
                    # Update competitor_items to reference the CompetitorEntity
                    result = conn.execute(text("""
                        UPDATE competitor_items 
                        SET competitor_id = :competitor_id
                        WHERE competitor_name = :competitor_name
                        AND competitor_id IS NULL;
                    """), {
                        "competitor_id": competitor_entity_id,
                        "competitor_name": competitor_name
                    })
                    
                    updated_rows = result.rowcount
                    logger.info(f"   📝 Updated {updated_rows} competitor_items records")
                    
                    migrated_count += 1
                
                logger.info(f"✅ Successfully migrated {migrated_count} competitors")
                
                # Step 4: Add constraints and indexes
                logger.info("🔧 Step 4: Adding constraints and indexes...")
                
                # Check if foreign key constraint exists
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.table_constraints 
                        WHERE table_schema = 'public' 
                        AND table_name = 'competitor_items'
                        AND constraint_name = 'competitor_items_competitor_id_fkey'
                    );
                """))
                
                fk_exists = result.scalar()
                
                if not fk_exists:
                    # Add foreign key constraint
                    conn.execute(text("""
                        ALTER TABLE competitor_items 
                        ADD CONSTRAINT competitor_items_competitor_id_fkey 
                        FOREIGN KEY (competitor_id) REFERENCES competitor_entities(id);
                    """))
                    logger.info("✅ Added foreign key constraint")
                else:
                    logger.info("✅ Foreign key constraint already exists")
                
                # Add indexes if they don't exist
                try:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS ix_competitor_items_competitor_id 
                        ON competitor_items(competitor_id);
                    """))
                    
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_competitor_entity_batch 
                        ON competitor_items(competitor_id, batch_id);
                    """))
                    
                    logger.info("✅ Added indexes")
                except SQLAlchemyError as e:
                    logger.warning(f"⚠️  Index creation warning: {e}")
                
                # Step 5: Verify migration
                logger.info("🔍 Step 5: Verifying migration...")
                
                # Count records
                result = conn.execute(text("SELECT COUNT(*) FROM competitor_entities;"))
                entity_count = result.scalar()
                
                result = conn.execute(text("SELECT COUNT(*) FROM competitor_items WHERE competitor_id IS NOT NULL;"))
                linked_items_count = result.scalar()
                
                result = conn.execute(text("SELECT COUNT(*) FROM competitor_items WHERE competitor_id IS NULL;"))
                unlinked_items_count = result.scalar()
                
                logger.info(f"📊 Migration Results:")
                logger.info(f"   • CompetitorEntity records: {entity_count}")
                logger.info(f"   • Linked CompetitorItem records: {linked_items_count}")
                logger.info(f"   • Unlinked CompetitorItem records: {unlinked_items_count}")
                
                if unlinked_items_count > 0:
                    logger.warning(f"⚠️  {unlinked_items_count} competitor items are still unlinked!")
                    
                    # Show some examples
                    result = conn.execute(text("""
                        SELECT id, competitor_name, item_name 
                        FROM competitor_items 
                        WHERE competitor_id IS NULL 
                        LIMIT 5;
                    """))
                    
                    unlinked_examples = result.fetchall()
                    logger.warning("   Examples of unlinked items:")
                    for item_id, comp_name, item_name in unlinked_examples:
                        logger.warning(f"     • ID {item_id}: {comp_name} - {item_name}")
                
                # Commit transaction
                trans.commit()
                logger.info("✅ Migration completed successfully!")
                
                return True
                
            except Exception as e:
                # Rollback on error
                trans.rollback()
                logger.error(f"❌ Migration failed: {e}")
                raise
                
    except SQLAlchemyError as e:
        logger.error(f"❌ Database connection error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main function to run the migration."""
    
    print("🗃️  CompetitorEntity Database Migration")
    print("=" * 50)
    print()
    
    # Confirm before running
    response = input("⚠️  This will modify your production database. Continue? (y/N): ")
    if response.lower() not in ['y', 'yes']:
        print("❌ Migration cancelled.")
        return
    
    print()
    
    # Run migration
    success = run_migration()
    
    print()
    if success:
        print("🎉 Migration completed successfully!")
        print()
        print("Next steps:")
        print("1. Test the competitor scraping functionality")
        print("2. Verify that competitor data appears correctly in the frontend")
        print("3. Check that all competitor items are properly linked")
        print()
    else:
        print("❌ Migration failed. Please check the logs and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
