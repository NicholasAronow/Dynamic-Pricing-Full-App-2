"""
LangGraph Multi-Agent API Routes
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.langgraph_service_v2 import LangGraphService, MultiAgentResponse
from dependencies import get_current_user
from models.core import User
from config.database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/langgraph", tags=["langgraph"])

# Request/Response Models
class MultiAgentRequest(BaseModel):
    task: str
    context: str = ""
    architecture: str = "supervisor"  # "supervisor" or "swarm"
    previous_messages: List[Dict[str, Any]] = []  # Add conversation history

@router.post("/stream")
async def stream_multi_agent_task(
    request: MultiAgentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stream multi-agent task execution with real-time updates"""
    try:
        logger.info(f"Starting streaming multi-agent task: {request.task[:100]}...")
        
        # Create service with database session
        langgraph_service = LangGraphService(db_session=db)
        
        async def generate_stream():
            async for chunk in langgraph_service.stream_supervisor_workflow(
                task=request.task,
                context=request.context,
                previous_messages=request.previous_messages,
                user_id=current_user.id
            ):
                yield f"data: {chunk}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Streaming failed: {str(e)}")

class ArchitectureInfo(BaseModel):
    name: str
    title: str
    description: str
    agents: List[str]
    best_for: str

# Service will be created per request with database session

@router.post("/execute", response_model=MultiAgentResponse)
async def execute_multi_agent_task(
    request: MultiAgentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute a task using the specified multi-agent architecture"""
    try:
        logger.info(f"User {current_user.id} executing multi-agent task: {request.task[:100]}...")
        
        # Create service with database session
        langgraph_service = LangGraphService(db_session=db)
        
        if request.architecture == "supervisor":
            result = await langgraph_service.execute_supervisor_workflow(
                task=request.task,
                context=request.context,
                user_id=current_user.id  # Pass user_id
            )
        elif request.architecture == "swarm":
            result = await langgraph_service.execute_swarm_workflow(
                task=request.task,
                context=request.context,
                user_id=current_user.id  # Pass user_id
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown architecture: {request.architecture}. Use 'supervisor' or 'swarm'"
            )
        
        logger.info(f"Multi-agent task completed in {result.total_execution_time:.2f}s")
        return result
        
    except Exception as e:
        logger.error(f"Multi-agent execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")



@router.get("/architectures", response_model=List[ArchitectureInfo])
async def get_available_architectures(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of available multi-agent architectures"""
    try:
        langgraph_service = LangGraphService(db_session=db)
        architectures = await langgraph_service.get_available_architectures()
        return [ArchitectureInfo(**arch) for arch in architectures]
        
    except Exception as e:
        logger.error(f"Error getting architectures: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get architectures: {str(e)}")

@router.get("/health")
async def health_check(
    db: Session = Depends(get_db)
):
    """Health check endpoint for LangGraph service"""
    try:
        # Basic health check - ensure service can be initialized
        service = LangGraphService(db_session=db)
        return {
            "status": "healthy",
            "service": "langgraph_multi_agent",
            "architectures_available": ["supervisor", "swarm"]
        }
    except Exception as e:
        logger.error(f"LangGraph health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@router.post("/test")
async def test_multi_agent_system(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test endpoint to verify multi-agent system is working"""
    try:
        # Create service with database session
        langgraph_service = LangGraphService(db_session=db)
        
        # Test with a conversational pricing question
        test_request = MultiAgentRequest(
            task="I'm launching a new wireless headphone product and need help with pricing. The market seems very competitive. What should I consider?",
            architecture="supervisor",
            context="Product: Premium wireless earbuds with noise cancellation. Target: Young professionals."
        )
        
        result = await langgraph_service.execute_supervisor_workflow(
            task=test_request.task,
            context=test_request.context
        )
        
        return {
            "status": "success",
            "test_completed": True,
            "execution_time": result.total_execution_time,
            "agents_executed": len(result.execution_path),
            "sample_result": result.final_result[:500] + "..." if len(result.final_result) > 500 else result.final_result
        }
        
    except Exception as e:
        logger.error(f"Multi-agent test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")
