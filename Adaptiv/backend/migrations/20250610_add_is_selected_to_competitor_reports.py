"""
Migration script to add is_selected field to CompetitorReport table
"""
from sqlalchemy import Boolean, Column, Table, MetaData
from sqlalchemy.sql import text

def upgrade():
    """
    Add is_selected column to competitor_reports table with default False
    """
    from database import engine
    from models import Base, CompetitorReport
    
    # Create the metadata object
    metadata = MetaData()
    
    # Define the structure we want to add
    conn = engine.connect()
    trans = conn.begin()
    
    try:
        # First check if column exists to avoid errors
        # SQLite uses pragma_table_info instead of information_schema
        inspector = conn.execute(text("""
            SELECT name FROM pragma_table_info('competitor_reports') 
            WHERE name='is_selected'
        """)).fetchone()
        
        if not inspector:
            print("Adding is_selected column to competitor_reports table...")
            conn.execute(text("""
                ALTER TABLE competitor_reports 
                ADD COLUMN is_selected BOOLEAN NOT NULL DEFAULT FALSE
            """))
            
            # Update existing manually added competitors to be selected
            conn.execute(text("""
                UPDATE competitor_reports
                SET is_selected = TRUE
                WHERE summary LIKE 'Manually added competitor%'
            """))
            
            print("Migration completed successfully")
            trans.commit()
        else:
            print("Column is_selected already exists in competitor_reports table")
            trans.rollback()
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        trans.rollback()
        raise
    finally:
        conn.close()

def downgrade():
    """
    Remove is_selected column from competitor_reports table
    """
    from database import engine
    
    conn = engine.connect()
    trans = conn.begin()
    
    try:
        conn.execute(text("ALTER TABLE competitor_reports DROP COLUMN is_selected"))
        trans.commit()
    except Exception as e:
        print(f"Error during downgrade: {str(e)}")
        trans.rollback()
        raise
    finally:
        conn.close()
