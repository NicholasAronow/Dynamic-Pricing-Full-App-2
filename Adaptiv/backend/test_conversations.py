#!/usr/bin/env python3
"""
Test script for conversation functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import sessionmaker
from config.database import engine
from services.conversation_service import ConversationService
from models.core import User
from models.agents import Conversation, ConversationMessage

def test_conversation_functionality():
    """Test basic conversation functionality"""
    
    # Create a session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("🧪 Testing Conversation Functionality")
        print("=" * 50)
        
        # Find a test user (assuming user ID 1 exists)
        test_user = db.query(User).first()
        if not test_user:
            print("❌ No users found in database. Please create a user first.")
            return
        
        print(f"👤 Using test user: {test_user.email} (ID: {test_user.id})")
        
        # Initialize service
        service = ConversationService(db)
        
        # Test 1: Create a conversation
        print("\n1️⃣ Creating a new conversation...")
        conversation = service.create_conversation(
            user_id=test_user.id,
            title="Test Pricing Conversation"
        )
        print(f"✅ Created conversation: {conversation.id} - '{conversation.title}'")
        
        # Test 2: Add messages
        print("\n2️⃣ Adding messages to conversation...")
        
        # Add user message
        user_message = service.add_message(
            conversation_id=conversation.id,
            user_id=test_user.id,
            role="user",
            content="What are the best pricing strategies for my coffee shop?"
        )
        print(f"✅ Added user message: {user_message.id}")
        
        # Add assistant message
        assistant_message = service.add_message(
            conversation_id=conversation.id,
            user_id=test_user.id,
            role="assistant",
            content="Based on your menu data, I recommend implementing dynamic pricing for your premium coffee items. Here are three strategies...",
            agent_name="pricing_orchestrator",
            tools_used=["get_user_items_data", "get_competitor_data"]
        )
        print(f"✅ Added assistant message: {assistant_message.id}")
        
        # Test 3: Get conversation with messages
        print("\n3️⃣ Retrieving conversation with messages...")
        messages = service.get_conversation_messages(conversation.id, test_user.id)
        print(f"✅ Retrieved {len(messages)} messages")
        
        for msg in messages:
            print(f"   📝 {msg.role}: {msg.content[:50]}...")
            if msg.agent_name:
                print(f"      🤖 Agent: {msg.agent_name}")
            if msg.tools_used:
                print(f"      🔧 Tools: {msg.tools_used}")
        
        # Test 4: Get conversation context
        print("\n4️⃣ Getting conversation context...")
        context = service.get_conversation_context(conversation.id, test_user.id)
        print(f"✅ Retrieved context with {len(context)} messages")
        
        # Test 5: Get conversation summary
        print("\n5️⃣ Getting conversation summary...")
        summary = service.get_conversation_summary(conversation.id, test_user.id)
        print(f"✅ Summary: {summary}")
        
        # Test 6: List user conversations
        print("\n6️⃣ Listing user conversations...")
        conversations = service.get_user_conversations(test_user.id)
        print(f"✅ User has {len(conversations)} conversations")
        
        for conv in conversations:
            print(f"   💬 {conv.id}: '{conv.title}' (Updated: {conv.updated_at})")
        
        # Test 7: Update conversation title
        print("\n7️⃣ Updating conversation title...")
        updated_conversation = service.update_conversation_title(
            conversation.id,
            test_user.id,
            "Updated: Coffee Shop Pricing Strategy"
        )
        print(f"✅ Updated title: '{updated_conversation.title}'")
        
        print("\n🎉 All tests passed! Conversation functionality is working correctly.")
        print("\n📊 Test Results:")
        print(f"   - Conversation ID: {conversation.id}")
        print(f"   - Messages: {len(messages)}")
        print(f"   - User: {test_user.email}")
        print(f"   - Database: {'SQLite' if 'sqlite' in str(engine.url) else 'PostgreSQL'}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    test_conversation_functionality()
