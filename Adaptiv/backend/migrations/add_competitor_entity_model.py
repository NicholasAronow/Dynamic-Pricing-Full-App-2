"""
Migration: Add CompetitorEntity model and update CompetitorItem relationships

This migration:
1. Creates the new competitor_entities table
2. Adds competitor_id foreign key to competitor_items table
3. Migrates existing data from competitor_items to competitor_entities
4. Updates indexes for better performance

Run this migration against PostgreSQL database.
"""

import asyncio
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the backend directory to the path so we can import our models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_database_url
from models import CompetitorEntity, CompetitorItem

def run_migration():
    """Run the migration to add CompetitorEntity and update CompetitorItem"""
    
    # Get database URL
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    with engine.connect() as connection:
        # Start a transaction
        trans = connection.begin()
        
        try:
            print("Starting migration: Add CompetitorEntity model...")
            
            # Step 1: Create competitor_entities table
            print("1. Creating competitor_entities table...")
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS competitor_entities (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    name VARCHAR NOT NULL,
                    address VARCHAR,
                    category VARCHAR,
                    phone VARCHAR,
                    website VARCHAR,
                    distance_km FLOAT,
                    latitude FLOAT,
                    longitude FLOAT,
                    menu_url VARCHAR,
                    score FLOAT,
                    is_selected BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE
                );
            """))
            
            # Step 2: Create indexes for competitor_entities
            print("2. Creating indexes for competitor_entities...")
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_competitor_entities_user_id ON competitor_entities(user_id);
                CREATE INDEX IF NOT EXISTS idx_competitor_entities_name ON competitor_entities(name);
                CREATE INDEX IF NOT EXISTS idx_user_competitor ON competitor_entities(user_id, name);
            """))
            
            # Step 3: Add competitor_id column to competitor_items (if it doesn't exist)
            print("3. Adding competitor_id column to competitor_items...")
            connection.execute(text("""
                ALTER TABLE competitor_items 
                ADD COLUMN IF NOT EXISTS competitor_id INTEGER REFERENCES competitor_entities(id);
            """))
            
            # Step 4: Migrate existing data - create CompetitorEntity records for unique competitors
            print("4. Migrating existing competitor data...")
            
            # First, find all unique competitors from competitor_items
            result = connection.execute(text("""
                SELECT DISTINCT competitor_name, 
                       MIN(created_at) as first_seen,
                       COUNT(*) as item_count
                FROM competitor_items 
                WHERE competitor_name IS NOT NULL 
                GROUP BY competitor_name
                ORDER BY competitor_name;
            """))
            
            competitors = result.fetchall()
            print(f"Found {len(competitors)} unique competitors to migrate...")
            
            # For each unique competitor, create a CompetitorEntity
            # Note: We'll assign them to user_id = 1 as a default since we don't have user mapping
            # This should be updated based on your business logic
            for competitor in competitors:
                competitor_name = competitor[0]
                first_seen = competitor[1]
                
                print(f"  - Creating entity for: {competitor_name}")
                
                # Insert CompetitorEntity (assign to user_id = 1 as default)
                # You may want to modify this logic based on your data
                result = connection.execute(text("""
                    INSERT INTO competitor_entities (user_id, name, created_at, updated_at)
                    VALUES (1, :name, :created_at, :updated_at)
                    RETURNING id;
                """), {
                    'name': competitor_name,
                    'created_at': first_seen,
                    'updated_at': first_seen
                })
                
                competitor_entity_id = result.fetchone()[0]
                
                # Update all competitor_items with this competitor_name to reference the new entity
                connection.execute(text("""
                    UPDATE competitor_items 
                    SET competitor_id = :competitor_id
                    WHERE competitor_name = :competitor_name;
                """), {
                    'competitor_id': competitor_entity_id,
                    'competitor_name': competitor_name
                })
            
            # Step 5: Create new indexes for competitor_items
            print("5. Creating new indexes for competitor_items...")
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_competitor_items_competitor_id ON competitor_items(competitor_id);
                CREATE INDEX IF NOT EXISTS idx_competitor_entity_batch ON competitor_items(competitor_id, batch_id);
            """))
            
            # Step 6: Add foreign key constraint (if not exists)
            print("6. Adding foreign key constraint...")
            connection.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = 'fk_competitor_items_competitor_id'
                    ) THEN
                        ALTER TABLE competitor_items 
                        ADD CONSTRAINT fk_competitor_items_competitor_id 
                        FOREIGN KEY (competitor_id) REFERENCES competitor_entities(id);
                    END IF;
                END $$;
            """))
            
            # Commit the transaction
            trans.commit()
            print("Migration completed successfully!")
            
            # Print summary
            entity_count = connection.execute(text("SELECT COUNT(*) FROM competitor_entities")).fetchone()[0]
            item_count = connection.execute(text("SELECT COUNT(*) FROM competitor_items WHERE competitor_id IS NOT NULL")).fetchone()[0]
            
            print(f"\nMigration Summary:")
            print(f"- Created {entity_count} competitor entities")
            print(f"- Updated {item_count} competitor items with entity references")
            print(f"- Added necessary indexes and constraints")
            
        except Exception as e:
            # Rollback on error
            trans.rollback()
            print(f"Migration failed: {str(e)}")
            raise e

def rollback_migration():
    """Rollback the migration (for development/testing purposes)"""
    
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    with engine.connect() as connection:
        trans = connection.begin()
        
        try:
            print("Rolling back migration...")
            
            # Remove foreign key constraint
            connection.execute(text("""
                ALTER TABLE competitor_items DROP CONSTRAINT IF EXISTS fk_competitor_items_competitor_id;
            """))
            
            # Remove competitor_id column
            connection.execute(text("""
                ALTER TABLE competitor_items DROP COLUMN IF EXISTS competitor_id;
            """))
            
            # Drop indexes
            connection.execute(text("""
                DROP INDEX IF EXISTS idx_competitor_items_competitor_id;
                DROP INDEX IF EXISTS idx_competitor_entity_batch;
                DROP INDEX IF EXISTS idx_competitor_entities_user_id;
                DROP INDEX IF EXISTS idx_competitor_entities_name;
                DROP INDEX IF EXISTS idx_user_competitor;
            """))
            
            # Drop competitor_entities table
            connection.execute(text("""
                DROP TABLE IF EXISTS competitor_entities;
            """))
            
            trans.commit()
            print("Rollback completed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"Rollback failed: {str(e)}")
            raise e

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Competitor Entity Migration')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()
    
    if args.rollback:
        rollback_migration()
    else:
        run_migration()
