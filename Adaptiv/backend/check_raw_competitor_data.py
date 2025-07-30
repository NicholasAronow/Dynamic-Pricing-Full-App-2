#!/usr/bin/env python3
"""
Raw Database Check Script - Show Raw Database Response for Competitor Data

This script shows the raw database objects for the last competitor and last competitor item.
Useful for debugging API response format and database serialization issues.

Usage:
    python3 check_raw_competitor_data.py [user_id]
    
Default user_id is 2 if not provided.
"""

import sys
import os
import json
from sqlalchemy.orm import joinedload
from datetime import datetime

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import SessionLocal
import models
import schemas

def serialize_model(obj):
    """Convert SQLAlchemy model to dictionary for JSON serialization"""
    if obj is None:
        return None
    
    result = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        result[column.name] = value
    return result

def check_raw_competitor_data(user_id: int = 2):
    """
    Check raw competitor entities and items for a specific user
    
    Args:
        user_id: The user ID to check data for
    """
    print(f"🔍 Checking RAW competitor data for user ID: {user_id}")
    print("=" * 80)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Check if user exists
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            print(f"❌ User with ID {user_id} not found!")
            return
        
        print(f"✅ User found: {user.email}")
        print()
        
        # Get the last competitor entity for this user
        last_competitor = db.query(models.CompetitorEntity).filter(
            models.CompetitorEntity.user_id == user_id
        ).order_by(models.CompetitorEntity.created_at.desc()).first()
        
        if not last_competitor:
            print("❌ No competitor entities found for this user!")
            return
        
        print("🏪 LAST COMPETITOR ENTITY - RAW DATABASE OBJECT:")
        print("-" * 50)
        print(f"Raw Python Object: {last_competitor}")
        print(f"Object Type: {type(last_competitor)}")
        print()
        
        # Show raw attributes
        print("📋 RAW ATTRIBUTES:")
        for attr in dir(last_competitor):
            if not attr.startswith('_') and not callable(getattr(last_competitor, attr)):
                try:
                    value = getattr(last_competitor, attr)
                    print(f"  {attr}: {value} (type: {type(value)})")
                except Exception as e:
                    print(f"  {attr}: <Error accessing: {e}>")
        print()
        
        # Show serialized version
        print("📄 SERIALIZED VERSION (as dict):")
        serialized_competitor = serialize_model(last_competitor)
        print(json.dumps(serialized_competitor, indent=2, default=str))
        print()
        
        # Try to convert to Pydantic schema
        print("🔄 PYDANTIC SCHEMA CONVERSION:")
        try:
            schema_competitor = schemas.CompetitorEntity.model_validate(last_competitor)
            print("✅ Successfully converted to Pydantic schema")
            print("Schema dict:")
            print(json.dumps(schema_competitor.model_dump(), indent=2, default=str))
        except Exception as e:
            print(f"❌ Failed to convert to Pydantic schema: {e}")
        print()
        
        # Get the last competitor item for this competitor
        last_item = db.query(models.CompetitorItem).filter(
            models.CompetitorItem.competitor_entity_id == last_competitor.id
        ).order_by(models.CompetitorItem.id.desc()).first()
        
        if last_item:
            print("🍽️ LAST COMPETITOR ITEM - RAW DATABASE OBJECT:")
            print("-" * 50)
            print(f"Raw Python Object: {last_item}")
            print(f"Object Type: {type(last_item)}")
            print()
            
            # Show raw attributes
            print("📋 RAW ATTRIBUTES:")
            for attr in dir(last_item):
                if not attr.startswith('_') and not callable(getattr(last_item, attr)):
                    try:
                        value = getattr(last_item, attr)
                        print(f"  {attr}: {value} (type: {type(value)})")
                    except Exception as e:
                        print(f"  {attr}: <Error accessing: {e}>")
            print()
            
            # Show serialized version
            print("📄 SERIALIZED VERSION (as dict):")
            serialized_item = serialize_model(last_item)
            print(json.dumps(serialized_item, indent=2, default=str))
            print()
            
            # Try to convert to Pydantic schema
            print("🔄 PYDANTIC SCHEMA CONVERSION:")
            try:
                schema_item = schemas.CompetitorItem.model_validate(last_item)
                print("✅ Successfully converted to Pydantic schema")
                print("Schema dict:")
                print(json.dumps(schema_item.model_dump(), indent=2, default=str))
            except Exception as e:
                print(f"❌ Failed to convert to Pydantic schema: {e}")
        else:
            print("❌ No competitor items found for this competitor!")
        
        print()
        print("=" * 80)
        print("🔍 RAW DATA CHECK COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def main():
    """Main function to run the raw database check"""
    user_id = 2  # Default user ID
    
    # Check if user_id provided as command line argument
    if len(sys.argv) > 1:
        try:
            user_id = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid user_id provided. Using default user_id=2")
    
    check_raw_competitor_data(user_id)

if __name__ == "__main__":
    main()
