#!/usr/bin/env python3
"""
Test script for the new SQL-based database agent.
"""

import os
import sys
import asyncio
from datetime import datetime

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.langgraph_service_v2 import LangGraphService
from config.database import SessionLocal
from langchain_core.messages import HumanMessage

async def test_sql_agent():
    """Test the SQL database agent with various queries"""
    
    print("🧪 Testing SQL Database Agent")
    print("=" * 50)
    
    # Create database session
    db_session = SessionLocal()
    
    try:
        # Set user_id for testing (you can change this to a valid user ID)
        user_id = 2
        
        # Initialize the LangGraph service with user_id
        service = LangGraphService(db_session=db_session)
        
        print(f"✅ LangGraph service initialized for user {user_id}")
        
        # Test queries to try
        test_queries = [
            "What tables are available in the database?",
            "Show me the schema for the menu_items table",
            "What are the top 5 menu items by price?",
            "How many orders do we have in total?",
            "What's the average order value?"
        ]
        
        print(f"\n🔍 Testing {len(test_queries)} queries...")
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- Test {i}: {query} ---")
            
            try:
                # Create messages for the query
                messages = [HumanMessage(content=query)]
                
                # Stream the response from the database agent
                print("🤖 Agent Response:")
                response_chunks = []
                
                async for chunk in service.stream_supervisor_workflow(
                    task=query,
                    user_id=user_id
                ):
                    if chunk:
                        print(chunk, end='', flush=True)
                        response_chunks.append(chunk)
                
                print("\n" + "─" * 40)
                
            except Exception as e:
                print(f"❌ Error testing query: {e}")
                continue
        
        print(f"\n✅ SQL Agent testing completed!")
        
    except Exception as e:
        print(f"❌ Failed to initialize or test SQL agent: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db_session.close()

def test_sql_connection():
    """Test basic SQL database connection"""
    print("\n🔌 Testing SQL Database Connection")
    print("=" * 40)
    
    try:
        from langchain_community.utilities import SQLDatabase
        from config.database import DATABASE_URL
        
        # Create SQLDatabase connection
        db = SQLDatabase.from_uri(DATABASE_URL)
        
        print(f"✅ Connected to database: {DATABASE_URL}")
        
        # Test basic query
        tables = db.get_table_names()
        print(f"📋 Available tables: {tables}")
        
        # Test table info
        if tables:
            table_info = db.get_table_info(table_names=tables[:3])  # First 3 tables
            print(f"📊 Table schemas (first 3):\n{table_info}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting SQL Database Agent Tests")
    print("=" * 60)
    
    # Test 1: Basic SQL connection
    if test_sql_connection():
        print("\n" + "=" * 60)
        
        # Test 2: Full agent workflow
        asyncio.run(test_sql_agent())
    else:
        print("❌ Skipping agent tests due to connection failure")
    
    print("\n🏁 Testing completed!")
