from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from database import get_db
from .auth import get_current_user
from models import User
import os
from openai import OpenAI
import logging
from dotenv import load_dotenv
import tasks  # Import the tasks module which contains our Celery tasks

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
clients = {}
if OPENAI_API_KEY:
    try:
        clients['openai'] = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")

router = APIRouter(
    prefix="/ai-suggestions",
    tags=["ai-suggestions"],
    responses={404: {"description": "Not found"}}
)

class MenuItem(BaseModel):
    name: str
    description: str = ""
    category: str = ""
    price: float = 0.0

class MenuSuggestionRequest(BaseModel):
    menu_items: List[MenuItem]

class RecipeIngredient(BaseModel):
    ingredient: str
    quantity: float
    unit: str

class RecipeSuggestion(BaseModel):
    item_name: str
    ingredients: List[RecipeIngredient]

class MenuSuggestionResponse(BaseModel):
    recipes: List[RecipeSuggestion]

class MenuSuggestionTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class MenuSuggestionTaskStatusResponse(BaseModel):
    status: str
    message: str
    completed: bool
    recipes: Optional[List[RecipeSuggestion]] = None
    error: Optional[str] = None

@router.post("/menu-suggestions", response_model=MenuSuggestionTaskResponse)
async def suggest_recipes_from_menu(
    request: MenuSuggestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if OpenAI API key is configured
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI API is not configured. Please add your API key to the environment variables."
        )
    
    try:
        # Convert Pydantic models to dictionaries for Celery
        menu_items_dict = [item.dict() for item in request.menu_items]
        
        # Start the Celery task
        logger.info(f"Starting Celery task for menu items: {[item.name for item in request.menu_items]}")
        task = tasks.generate_menu_suggestions_task.delay(
            menu_items=menu_items_dict,
            user_id=current_user.id
        )
        
        # Return the task ID for status checking
        return MenuSuggestionTaskResponse(
            task_id=task.id,
            status="started",
            message="Menu suggestion generation has started. Check the task status endpoint for results."
        )
        
    except Exception as e:
        logger.exception("Unexpected error in suggest_recipes_from_menu")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start suggestions task: {str(e)}"
        )


@router.get("/menu-suggestions/status/{task_id}", response_model=MenuSuggestionTaskStatusResponse)
async def get_menu_suggestions_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check the status of a menu suggestions generation task.
    
    This endpoint polls the Celery worker to get the status of a long-running OpenAI API call.
    """
    try:
        # Call the Celery task that checks the status
        task_status = tasks.get_menu_suggestions_task_status.delay(
            task_id=task_id,
            user_id=current_user.id
        )
        
        # Get the result with a short timeout
        result = task_status.get(timeout=5)  # 5 second timeout should be plenty for a status check
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Unknown error checking task status")
            )
        
        # Check if the task has completed successfully and has results
        if result.get("completed") and "result" in result and result["result"].get("recipes"):
            # Extract recipes from the result
            recipes_data = result["result"].get("recipes", [])
            
            # Return the status with recipes
            return MenuSuggestionTaskStatusResponse(
                status=result.get("task_status", "unknown"),
                message=result.get("status_message", "Status check completed"),
                completed=True,
                recipes=recipes_data  # Include the recipes if available
            )
        elif result.get("completed") and result.get("error"):
            # Task failed with an error
            return MenuSuggestionTaskStatusResponse(
                status="failed",
                message=f"Task failed: {result.get('error', 'Unknown error')}",
                completed=True,
                error=result.get("error")
            )
        else:
            # Task is still in progress
            return MenuSuggestionTaskStatusResponse(
                status=result.get("task_status", "unknown"),
                message=result.get("status_message", "Task is in progress"),
                completed=result.get("completed", False)
            )
            
    except Exception as e:
        logger.exception(f"Error checking menu suggestions task status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check task status: {str(e)}"
        )
