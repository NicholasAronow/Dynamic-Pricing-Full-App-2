from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
from database import get_db
from auth import get_current_user
from models import User
import os
from openai import OpenAI
import logging
from dotenv import load_dotenv

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

@router.post("/menu-suggestions", response_model=MenuSuggestionResponse)
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
        # Format menu items for the prompt
        menu_items_text = "\n".join([
            f"- {item.name}: {item.description or 'No description'} (Category: {item.category or 'Unknown'})"
            for item in request.menu_items
        ])
        
        # Create the prompt for OpenAI
        prompt = f"""
        Given the following menu items from a food service business:
        
        {menu_items_text}
        
        Please suggest:
        1. Recipes for each menu item using those ingredients
        
        Format your response as a valid JSON object with the following structure:
        {{
            "recipes": [
                {{
                    "item_name": "Menu item name",
                    "ingredients": [
                        {{
                            "ingredient": ingredient name,
                            "quantity": quantity needed for this recipe as number,
                            "unit": "unit of measurement"
                        }}
                    ]
                }}
            ]
        }}
        
        Be realistic with ingredient quantities and prices. Use common units of measurement. Be as granular as possible (i.e. for an americano, use grams of beans, not shots of espresso). Do not give any extra details about the ingredient, just return the base ingredient (i.e. frothed milk is just whole milk)
        """
        
        # Check if OpenAI client is initialized
        if 'openai' not in clients:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI client failed to initialize. Please check the API key."
            )
            
        # Call OpenAI API
        try:
            logger.info(f"Calling OpenAI API with menu items: {[item.name for item in request.menu_items]}")
            response = clients['openai'].chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant with expertise in food service and recipe identification."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract and parse the response
            suggestion_text = response.choices[0].message.content
            logger.info(f"Received response from OpenAI API: {suggestion_text}")
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"OpenAI API call failed: {str(e)}"
            )
        
        # Find the JSON part of the response
        import json
        import re
        
        suggestion_json = None
        try:
            # Try to find a JSON object in the response
            json_match = re.search(r'({[\s\S]*})', suggestion_text)
            if json_match:
                suggestion_json = json.loads(json_match.group(1))
            else:
                # If no JSON found, try to parse the whole response
                suggestion_json = json.loads(suggestion_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from OpenAI response: {e}")
            logger.error(f"Response text: {suggestion_text}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to parse AI response as JSON: {str(e)}"
            )
            
        if not suggestion_json or not isinstance(suggestion_json, dict):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid response format from AI service"
            )
        
        # Process the recipes to ensure they match our expected format
        recipes = suggestion_json.get("recipes", [])
        for recipe in recipes:
            # Ensure each recipe has ingredients list
            if "ingredients" not in recipe:
                recipe["ingredients"] = []
        
        # Return the processed suggestions
        return MenuSuggestionResponse(
            recipes=recipes
        )
        
    except HTTPException:
        # Re-raise HTTPExceptions without modification
        raise
    except Exception as e:
        logger.exception("Unexpected error in suggest_recipes_from_menu")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate suggestions: {str(e)}"
        )
