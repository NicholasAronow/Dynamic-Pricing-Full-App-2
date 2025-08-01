#!/usr/bin/env python3
"""
Migration script to add Conversation and ConversationMessage tables
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from config.database import DATABASE_URL, engine
from models.agents import Conversation, ConversationMessage
from config.database import Base

def run_migration():
    """Run the migration to add conversation tables"""
    # Use the existing engine from config
    
    print("🚀 Starting conversation models migration...")
    
    # Detect database type
    is_sqlite = str(engine.url).startswith('sqlite')
    is_postgresql = str(engine.url).startswith('postgresql')
    
    print(f"📊 Database type detected: {'SQLite' if is_sqlite else 'PostgreSQL' if is_postgresql else 'Unknown'}")
    
    try:
        # Create the new tables with database-specific SQL
        print("📝 Creating conversation tables...")
        
        if is_sqlite:
            # SQLite syntax
            conversations_sql = """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                title VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            );
            """
            
            messages_sql = """
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id),
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                agent_name VARCHAR(50),
                tools_used JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
            """
        else:
            # PostgreSQL syntax
            conversations_sql = """
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                title VARCHAR(255),
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc') NOT NULL,
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
                is_active BOOLEAN DEFAULT true
            );
            """
            
            messages_sql = """
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id SERIAL PRIMARY KEY,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id),
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                agent_name VARCHAR(50),
                tools_used JSON,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc') NOT NULL
            );
            """
        
        # Create indexes
        indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_conversations_user_updated ON conversations(user_id, updated_at);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_user_active ON conversations(user_id, is_active);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_created ON conversation_messages(conversation_id, created_at);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_role ON conversation_messages(conversation_id, role);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_id ON conversation_messages(conversation_id);"
        ]
        
        with engine.connect() as connection:
            # Create tables
            connection.execute(text(conversations_sql))
            print("✅ Created conversations table")
            
            connection.execute(text(messages_sql))
            print("✅ Created conversation_messages table")
            
            # Create indexes
            for index_sql in indexes_sql:
                connection.execute(text(index_sql))
            print("✅ Created indexes")
            
            connection.commit()
        
        print("🎉 Migration completed successfully!")
        print("\n📊 New tables created:")
        print("  - conversations: Store conversation metadata")
        print("  - conversation_messages: Store individual messages")
        print("\n🔧 Features enabled:")
        print("  - Persistent conversation storage")
        print("  - Multiple conversation management")
        print("  - Message history with agent tracking")
        print("  - Tool usage tracking per message")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise e
    finally:
        engine.dispose()

if __name__ == "__main__":
    run_migration()
