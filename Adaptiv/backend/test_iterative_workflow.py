#!/usr/bin/env python3
"""
Test script for iterative multi-agent workflow
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.langgraph_service_v2 import LangGraphService
from config.database import get_db

async def test_iterative_workflow():
    """Test the iterative multi-agent workflow with a comprehensive pricing analysis"""
    
    # Get database session
    db = next(get_db())
    
    # Initialize the service
    service = LangGraphService(db_session=db)
    
    # Test user ID (adjust as needed)
    test_user_id = 2
    
    # Complex prompt that should trigger multiple agent iterations
    complex_prompt = """
    Please run a comprehensive optimization analysis of every item on my menu. 
    Conduct thorough market research on the web for things like supply costs, local events, 
    and other industry trends. Make thorough analysis in the database for things like 
    competitors, sales trends, and complex analyses of our data. With all of this, 
    give me a decision on what algorithm and parameters would be best to implement 
    for each item (i.e. no_change(expiry: 7, item_id: a1bd3), 
    gradual_rise(expiry: 14, delta: 0.20, item_id: 1b43o))
    """
    
    print("🚀 Starting iterative multi-agent workflow test...")
    print(f"📝 Prompt: {complex_prompt[:100]}...")
    print("=" * 80)
    
    try:
        # Stream the workflow to see agent interactions
        async for chunk in service.stream_supervisor_workflow(
            task=complex_prompt,
            user_id=test_user_id
        ):
            if chunk.get('type') == 'agent_start':
                agent_name = chunk.get('agent', 'Unknown')
                print(f"\n🤖 {agent_name.upper()} ACTIVATED")
                print("-" * 40)
            elif chunk.get('type') == 'message_chunk':
                content = chunk.get('content', '')
                if content.strip():
                    print(content, end='', flush=True)
            elif chunk.get('type') == 'message_complete':
                print("\n")
            elif chunk.get('type') == 'complete':
                print("\n" + "=" * 80)
                print("✅ WORKFLOW COMPLETED")
                break
                
    except Exception as e:
        print(f"❌ Error during workflow: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    print("🧪 Testing Iterative Multi-Agent Workflow")
    print("=" * 50)
    asyncio.run(test_iterative_workflow())
