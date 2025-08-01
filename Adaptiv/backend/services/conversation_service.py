"""
Conversation Service for managing persistent conversations and messages
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import datetime
import logging

from models.agents import Conversation, ConversationMessage
from models.core import User

logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(self, db: Session):
        self.db = db

    def create_conversation(self, user_id: int, title: Optional[str] = None) -> Conversation:
        """Create a new conversation for a user"""
        try:
            # Don't auto-generate title - let it be set later when first message is sent
            conversation = Conversation(
                user_id=user_id,
                title=title,  # Can be None initially
                is_active=True
            )
            
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)
            
            logger.info(f"Created conversation {conversation.id} for user {user_id}")
            return conversation
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating conversation: {e}")
            raise

    def get_user_conversations(self, user_id: int, limit: int = 50, include_inactive: bool = False) -> List[Conversation]:
        """Get all conversations for a user, ordered by most recent"""
        try:
            query = self.db.query(Conversation).filter(Conversation.user_id == user_id)
            
            if not include_inactive:
                query = query.filter(Conversation.is_active == True)
            
            conversations = query.order_by(desc(Conversation.updated_at)).limit(limit).all()
            
            logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting user conversations: {e}")
            raise

    def get_conversation(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        """Get a specific conversation with user validation"""
        try:
            conversation = self.db.query(Conversation).filter(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id
                )
            ).first()
            
            if conversation:
                logger.info(f"Retrieved conversation {conversation_id} for user {user_id}")
            else:
                logger.warning(f"Conversation {conversation_id} not found for user {user_id}")
            
            return conversation
            
        except Exception as e:
            logger.error(f"Error getting conversation: {e}")
            raise

    def get_conversation_messages(self, conversation_id: int, user_id: int, limit: int = 100) -> List[ConversationMessage]:
        """Get messages for a conversation with user validation"""
        try:
            # First verify the conversation belongs to the user
            conversation = self.get_conversation(conversation_id, user_id)
            if not conversation:
                return []

            messages = self.db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation_id
            ).order_by(ConversationMessage.created_at).limit(limit).all()
            
            logger.info(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Error getting conversation messages: {e}")
            raise

    def add_message(
        self, 
        conversation_id: int, 
        user_id: int,
        role: str, 
        content: str, 
        agent_name: Optional[str] = None,
        tools_used: Optional[List[str]] = None
    ) -> ConversationMessage:
        """Add a message to a conversation"""
        try:
            # Verify the conversation belongs to the user
            conversation = self.get_conversation(conversation_id, user_id)
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found for user {user_id}")

            message = ConversationMessage(
                conversation_id=conversation_id,
                role=role,
                content=content,
                agent_name=agent_name,
                tools_used=tools_used
            )
            
            self.db.add(message)
            
            # Update conversation's updated_at timestamp
            conversation.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(message)
            
            logger.info(f"Added {role} message to conversation {conversation_id}")
            return message
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding message: {e}")
            raise

    def update_conversation_title(self, conversation_id: int, user_id: int, title: str) -> Optional[Conversation]:
        """Update a conversation's title"""
        try:
            conversation = self.get_conversation(conversation_id, user_id)
            if not conversation:
                return None

            conversation.title = title
            conversation.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(conversation)
            
            logger.info(f"Updated title for conversation {conversation_id}")
            return conversation
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating conversation title: {e}")
            raise

    def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        """Delete a conversation and all its messages"""
        try:
            conversation = self.get_conversation(conversation_id, user_id)
            if not conversation:
                return False

            # Delete all messages first (cascade should handle this, but being explicit)
            self.db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation_id
            ).delete()
            
            # Delete the conversation
            self.db.delete(conversation)
            self.db.commit()
            
            logger.info(f"Deleted conversation {conversation_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting conversation: {e}")
            raise

    def archive_conversation(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        """Archive a conversation (set is_active to False)"""
        try:
            conversation = self.get_conversation(conversation_id, user_id)
            if not conversation:
                return None

            conversation.is_active = False
            conversation.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(conversation)
            
            logger.info(f"Archived conversation {conversation_id}")
            return conversation
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error archiving conversation: {e}")
            raise

    def get_conversation_context(self, conversation_id: int, user_id: int, context_limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation context for LangGraph (last N messages formatted for API)"""
        try:
            messages = self.get_conversation_messages(conversation_id, user_id, limit=context_limit)
            
            # Convert to format expected by LangGraph
            context = []
            for message in messages[-context_limit:]:  # Get last N messages
                context.append({
                    "role": message.role,
                    "content": message.content,
                    "agent_name": message.agent_name,
                    "tools_used": message.tools_used,
                    "created_at": message.created_at.isoformat()
                })
            
            logger.info(f"Retrieved context with {len(context)} messages for conversation {conversation_id}")
            return context
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            raise

    def get_conversation_summary(self, conversation_id: int, user_id: int) -> Dict[str, Any]:
        """Get a summary of the conversation (message count, participants, etc.)"""
        try:
            conversation = self.get_conversation(conversation_id, user_id)
            if not conversation:
                return {}

            message_count = self.db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation_id
            ).count()
            
            # Get unique agents that participated
            agents = self.db.query(ConversationMessage.agent_name).filter(
                and_(
                    ConversationMessage.conversation_id == conversation_id,
                    ConversationMessage.agent_name.isnot(None)
                )
            ).distinct().all()
            
            agent_names = [agent[0] for agent in agents if agent[0]]
            
            summary = {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "is_active": conversation.is_active,
                "message_count": message_count,
                "participating_agents": agent_names
            }
            
            logger.info(f"Generated summary for conversation {conversation_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Error getting conversation summary: {e}")
            raise
