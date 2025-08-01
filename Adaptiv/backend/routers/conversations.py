"""
Conversation Management API Routes
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config.database import get_db
from dependencies import get_current_user
from models.core import User
from services.conversation_service import ConversationService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

# Request/Response Models
class ConversationCreate(BaseModel):
    title: Optional[str] = None

class ConversationUpdate(BaseModel):
    title: str

class MessageCreate(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    agent_name: Optional[str] = None
    tools_used: Optional[List[str]] = None

class ConversationResponse(BaseModel):
    id: int
    title: Optional[str] = None
    created_at: str
    updated_at: str
    is_active: bool
    message_count: Optional[int] = None
    participating_agents: Optional[List[str]] = None

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    agent_name: Optional[str] = None
    tools_used: Optional[List[str]] = None
    created_at: str

class ConversationWithMessages(BaseModel):
    conversation: ConversationResponse
    messages: List[MessageResponse]

# API Endpoints

@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation"""
    try:
        service = ConversationService(db)
        conversation = service.create_conversation(
            user_id=current_user.id,
            title=request.title
        )
        
        summary = service.get_conversation_summary(conversation.id, current_user.id)
        
        return ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat(),
            is_active=conversation.is_active,
            message_count=summary.get("message_count", 0),
            participating_agents=summary.get("participating_agents", [])
        )
        
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}"
        )

@router.get("/", response_model=List[ConversationResponse])
async def get_conversations(
    limit: int = 50,
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all conversations for the current user"""
    try:
        service = ConversationService(db)
        conversations = service.get_user_conversations(
            user_id=current_user.id,
            limit=limit,
            include_inactive=include_inactive
        )
        
        # Get summaries for each conversation
        response = []
        for conversation in conversations:
            summary = service.get_conversation_summary(conversation.id, current_user.id)
            response.append(ConversationResponse(
                id=conversation.id,
                title=conversation.title,
                created_at=conversation.created_at.isoformat(),
                updated_at=conversation.updated_at.isoformat(),
                is_active=conversation.is_active,
                message_count=summary.get("message_count", 0),
                participating_agents=summary.get("participating_agents", [])
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversations: {str(e)}"
        )

@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: int,
    message_limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific conversation with its messages"""
    try:
        service = ConversationService(db)
        
        # Get conversation
        conversation = service.get_conversation(conversation_id, current_user.id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Get messages
        messages = service.get_conversation_messages(
            conversation_id, 
            current_user.id, 
            limit=message_limit
        )
        
        # Get summary
        summary = service.get_conversation_summary(conversation_id, current_user.id)
        
        return ConversationWithMessages(
            conversation=ConversationResponse(
                id=conversation.id,
                title=conversation.title,
                created_at=conversation.created_at.isoformat(),
                updated_at=conversation.updated_at.isoformat(),
                is_active=conversation.is_active,
                message_count=summary.get("message_count", 0),
                participating_agents=summary.get("participating_agents", [])
            ),
            messages=[
                MessageResponse(
                    id=msg.id,
                    conversation_id=msg.conversation_id,
                    role=msg.role,
                    content=msg.content,
                    agent_name=msg.agent_name,
                    tools_used=msg.tools_used,
                    created_at=msg.created_at.isoformat()
                ) for msg in messages
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation: {str(e)}"
        )

@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    request: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a conversation's title"""
    try:
        service = ConversationService(db)
        conversation = service.update_conversation_title(
            conversation_id, 
            current_user.id, 
            request.title
        )
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        summary = service.get_conversation_summary(conversation_id, current_user.id)
        
        return ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat(),
            is_active=conversation.is_active,
            message_count=summary.get("message_count", 0),
            participating_agents=summary.get("participating_agents", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update conversation: {str(e)}"
        )

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation and all its messages"""
    try:
        service = ConversationService(db)
        success = service.delete_conversation(conversation_id, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return {"message": "Conversation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}"
        )

@router.post("/{conversation_id}/archive", response_model=ConversationResponse)
async def archive_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Archive a conversation (set is_active to False)"""
    try:
        service = ConversationService(db)
        conversation = service.archive_conversation(conversation_id, current_user.id)
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        summary = service.get_conversation_summary(conversation_id, current_user.id)
        
        return ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat(),
            is_active=conversation.is_active,
            message_count=summary.get("message_count", 0),
            participating_agents=summary.get("participating_agents", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive conversation: {str(e)}"
        )

@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(
    conversation_id: int,
    request: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a message to a conversation"""
    try:
        service = ConversationService(db)
        message = service.add_message(
            conversation_id=conversation_id,
            user_id=current_user.id,
            role=request.role,
            content=request.content,
            agent_name=request.agent_name,
            tools_used=request.tools_used
        )
        
        return MessageResponse(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            agent_name=message.agent_name,
            tools_used=message.tools_used,
            created_at=message.created_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add message: {str(e)}"
        )

@router.get("/{conversation_id}/context")
async def get_conversation_context(
    conversation_id: int,
    context_limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get conversation context for LangGraph (formatted for API)"""
    try:
        service = ConversationService(db)
        context = service.get_conversation_context(
            conversation_id, 
            current_user.id, 
            context_limit
        )
        
        return {"context": context}
        
    except Exception as e:
        logger.error(f"Error getting conversation context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation context: {str(e)}"
        )
