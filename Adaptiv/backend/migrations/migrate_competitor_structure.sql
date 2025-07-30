-- CompetitorEntity Database Migration for PostgreSQL
-- This script migrates the database to support the new CompetitorEntity structure
-- Run this on your production PostgreSQL database

BEGIN;

-- Step 1: Create competitor_entities table if it doesn't exist
CREATE TABLE IF NOT EXISTS competitor_entities (
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

-- Create indexes for competitor_entities
CREATE INDEX IF NOT EXISTS ix_competitor_entities_id ON competitor_entities(id);
CREATE INDEX IF NOT EXISTS ix_competitor_entities_user_id ON competitor_entities(user_id);
CREATE INDEX IF NOT EXISTS ix_competitor_entities_name ON competitor_entities(name);
CREATE INDEX IF NOT EXISTS idx_user_competitor ON competitor_entities(user_id, name);

-- Step 2: Add competitor_id column to competitor_items if it doesn't exist
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'competitor_items' 
        AND column_name = 'competitor_id'
    ) THEN
        ALTER TABLE competitor_items ADD COLUMN competitor_id INTEGER;
    END IF;
END $$;

-- Step 3: Migrate existing competitor data
-- Create CompetitorEntity records for each unique competitor_name
-- First, get the first available user ID
DO $$
DECLARE
    first_user_id INTEGER;
BEGIN
    -- Get the first user ID that exists
    SELECT id INTO first_user_id FROM users ORDER BY id LIMIT 1;
    
    IF first_user_id IS NULL THEN
        RAISE EXCEPTION 'No users found in database. Cannot create CompetitorEntity records.';
    END IF;
    
    -- Create CompetitorEntity records using the first available user ID
    INSERT INTO competitor_entities (user_id, name, created_at, updated_at)
    SELECT 
        first_user_id as user_id,
        competitor_name,
        MIN(created_at) as created_at,
        NOW() as updated_at
    FROM competitor_items 
    WHERE competitor_name IS NOT NULL 
        AND competitor_name != ''
        AND competitor_name NOT IN (SELECT name FROM competitor_entities)
    GROUP BY competitor_name;
    
    RAISE NOTICE 'Created CompetitorEntity records using user_id: %', first_user_id;
END $$;

-- Step 4: Update competitor_items to reference CompetitorEntity records
UPDATE competitor_items 
SET competitor_id = ce.id
FROM competitor_entities ce
WHERE competitor_items.competitor_name = ce.name
    AND competitor_items.competitor_id IS NULL;

-- Step 5: Add foreign key constraint if it doesn't exist
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT FROM information_schema.table_constraints 
        WHERE table_schema = 'public' 
        AND table_name = 'competitor_items'
        AND constraint_name = 'competitor_items_competitor_id_fkey'
    ) THEN
        ALTER TABLE competitor_items 
        ADD CONSTRAINT competitor_items_competitor_id_fkey 
        FOREIGN KEY (competitor_id) REFERENCES competitor_entities(id);
    END IF;
END $$;

-- Step 6: Add indexes for better performance
CREATE INDEX IF NOT EXISTS ix_competitor_items_competitor_id ON competitor_items(competitor_id);
CREATE INDEX IF NOT EXISTS idx_competitor_entity_batch ON competitor_items(competitor_id, batch_id);

-- Step 7: Verification queries (optional - run these to check results)
-- SELECT 'CompetitorEntity count:' as info, COUNT(*) as count FROM competitor_entities;
-- SELECT 'Linked CompetitorItem count:' as info, COUNT(*) as count FROM competitor_items WHERE competitor_id IS NOT NULL;
-- SELECT 'Unlinked CompetitorItem count:' as info, COUNT(*) as count FROM competitor_items WHERE competitor_id IS NULL;

COMMIT;

-- Success message
SELECT 'Migration completed successfully!' as status;
