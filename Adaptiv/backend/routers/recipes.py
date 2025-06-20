from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import User
from recipe_models import Recipe, Ingredient, RecipeIngredient
from auth import get_current_user
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List

# Pydantic models for request/response
class IngredientCreate(BaseModel):
    name: str
    quantity: float
    unit: str
    price: float

class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    price: Optional[float] = None

class IngredientResponse(BaseModel):
    id: int
    name: str
    quantity: float
    unit: str
    price: float
    unit_price: float
    date_created: datetime

    class Config:
        orm_mode = True

class RecipeIngredientCreate(BaseModel):
    ingredient_id: int
    quantity: float
    unit: str

class RecipeIngredientResponse(BaseModel):
    ingredient_id: int
    name: str
    quantity: float
    unit: str
    cost: float

    class Config:
        orm_mode = True

class RecipeCreate(BaseModel):
    name: str
    ingredients: List[RecipeIngredientCreate]

class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    ingredients: Optional[List[RecipeIngredientCreate]] = None

class RecipeResponse(BaseModel):
    id: int
    name: str
    ingredients: List[RecipeIngredientResponse]
    total_cost: float
    date_created: datetime

    class Config:
        orm_mode = True

router = APIRouter(
    prefix="/recipes",
    tags=["recipes"],
    responses={404: {"description": "Not found"}}
)

# Ingredient routes
@router.post("/ingredients", response_model=IngredientResponse)
def create_ingredient(
    ingredient: IngredientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_ingredient = Ingredient(
        user_id=current_user.id,
        name=ingredient.name,
        quantity=ingredient.quantity,
        unit=ingredient.unit,
        price=ingredient.price
    )
    db.add(db_ingredient)
    db.commit()
    db.refresh(db_ingredient)
    
    # Add calculated unit_price to response
    response = db_ingredient.__dict__.copy()
    response["unit_price"] = db_ingredient.unit_price()
    
    return response

@router.get("/ingredients", response_model=List[IngredientResponse])
def get_ingredients(
    user_id: Optional[int] = None,
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    # Filter by user ID (prefer explicit user_id parameter, fall back to account_id, finally use current user ID)
    filter_user_id = None
    if user_id is not None:
        filter_user_id = user_id
        print(f"Filtering ingredients by user_id={user_id}")
    elif account_id is not None:
        filter_user_id = account_id
        print(f"Filtering ingredients by account_id={account_id} (mapped to user_id)")
    else:
        filter_user_id = current_user.id
        print(f"Filtering ingredients by current_user.id={current_user.id}")
        
    ingredients = db.query(Ingredient).filter(
        Ingredient.user_id == filter_user_id
    ).offset(skip).limit(limit).all()
    
    # Add calculated unit_price to each ingredient
    response = []
    for ing in ingredients:
        ing_dict = ing.__dict__.copy()
        ing_dict["unit_price"] = ing.unit_price()
        response.append(ing_dict)
    
    return response

@router.get("/ingredients/{ingredient_id}", response_model=IngredientResponse)
def get_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ingredient = db.query(Ingredient).filter(
        Ingredient.id == ingredient_id,
        Ingredient.user_id == current_user.id
    ).first()
    
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found"
        )
    
    # Add calculated unit_price to response
    response = ingredient.__dict__.copy()
    response["unit_price"] = ingredient.unit_price()
    
    return response

@router.put("/ingredients/{ingredient_id}", response_model=IngredientResponse)
def update_ingredient(
    ingredient_id: int,
    ingredient_update: IngredientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_ingredient = db.query(Ingredient).filter(
        Ingredient.id == ingredient_id,
        Ingredient.user_id == current_user.id
    ).first()
    
    if not db_ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found"
        )
    
    # Update ingredient fields if provided
    update_data = ingredient_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_ingredient, key, value)
    
    db.commit()
    db.refresh(db_ingredient)
    
    # Add calculated unit_price to response
    response = db_ingredient.__dict__.copy()
    response["unit_price"] = db_ingredient.unit_price()
    
    return response

@router.delete("/ingredients/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # First check if ingredient is used in any recipes
    recipe_ingredient = db.query(RecipeIngredient).filter(
        RecipeIngredient.ingredient_id == ingredient_id
    ).first()
    
    if recipe_ingredient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete ingredient that is used in recipes"
        )
    
    ingredient = db.query(Ingredient).filter(
        Ingredient.id == ingredient_id,
        Ingredient.user_id == current_user.id
    ).first()
    
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found"
        )
    
    db.delete(ingredient)
    db.commit()
    
    return None

# Recipe routes
@router.post("/", response_model=RecipeResponse)
def create_recipe(
    recipe: RecipeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Create recipe first
    db_recipe = Recipe(
        user_id=current_user.id,
        name=recipe.name
    )
    db.add(db_recipe)
    db.commit()
    db.refresh(db_recipe)
    
    # Add ingredients to recipe
    for ingredient_data in recipe.ingredients:
        # Check if ingredient exists and belongs to user
        db_ingredient = db.query(Ingredient).filter(
            Ingredient.id == ingredient_data.ingredient_id,
            Ingredient.user_id == current_user.id
        ).first()
        
        if not db_ingredient:
            db.delete(db_recipe)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ingredient with id {ingredient_data.ingredient_id} not found"
            )
        
        # Create recipe ingredient
        recipe_ingredient = RecipeIngredient(
            recipe_id=db_recipe.id,
            ingredient_id=ingredient_data.ingredient_id,
            quantity=ingredient_data.quantity,
            unit=ingredient_data.unit
        )
        db.add(recipe_ingredient)
    
    db.commit()
    db.refresh(db_recipe)
    
    # Prepare response with calculated costs
    ingredients_response = []
    total_cost = 0
    
    for ri in db_recipe.ingredients:
        cost = ri.calculate_cost()
        total_cost += cost
        ingredients_response.append({
            "ingredient_id": ri.ingredient_id,
            "name": ri.ingredient.name,
            "quantity": ri.quantity,
            "unit": ri.unit,
            "cost": cost
        })
    
    return {
        "id": db_recipe.id,
        "name": db_recipe.name,
        "ingredients": ingredients_response,
        "total_cost": total_cost,
        "date_created": db_recipe.date_created
    }

@router.get("/", response_model=List[RecipeResponse])
def get_recipes(
    user_id: Optional[int] = None,
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    # Filter by user ID (prefer explicit user_id parameter, fall back to account_id, finally use current user ID)
    filter_user_id = None
    if user_id is not None:
        filter_user_id = user_id
        print(f"Filtering recipes by user_id={user_id}")
    elif account_id is not None:
        filter_user_id = account_id
        print(f"Filtering recipes by account_id={account_id} (mapped to user_id)")
    else:
        filter_user_id = current_user.id
        print(f"Filtering recipes by current_user.id={current_user.id}")
        
    recipes = db.query(Recipe).filter(
        Recipe.user_id == filter_user_id
    ).offset(skip).limit(limit).all()
    
    response = []
    
    for recipe in recipes:
        ingredients_response = []
        total_cost = 0
        
        for ri in recipe.ingredients:
            cost = ri.calculate_cost()
            total_cost += cost
            ingredients_response.append({
                "ingredient_id": ri.ingredient_id,
                "name": ri.ingredient.name,
                "quantity": ri.quantity,
                "unit": ri.unit,
                "cost": cost
            })
        
        response.append({
            "id": recipe.id,
            "name": recipe.name,
            "ingredients": ingredients_response,
            "total_cost": total_cost,
            "date_created": recipe.date_created
        })
    
    return response

@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    recipe = db.query(Recipe).filter(
        Recipe.id == recipe_id,
        Recipe.user_id == current_user.id
    ).first()
    
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    
    ingredients_response = []
    total_cost = 0
    
    for ri in recipe.ingredients:
        cost = ri.calculate_cost()
        total_cost += cost
        ingredients_response.append({
            "ingredient_id": ri.ingredient_id,
            "name": ri.ingredient.name,
            "quantity": ri.quantity,
            "unit": ri.unit,
            "cost": cost
        })
    
    return {
        "id": recipe.id,
        "name": recipe.name,
        "ingredients": ingredients_response,
        "total_cost": total_cost,
        "date_created": recipe.date_created
    }

@router.put("/{recipe_id}", response_model=RecipeResponse)
def update_recipe(
    recipe_id: int,
    recipe_update: RecipeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_recipe = db.query(Recipe).filter(
        Recipe.id == recipe_id,
        Recipe.user_id == current_user.id
    ).first()
    
    if not db_recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    
    # Update recipe name if provided
    if recipe_update.name:
        db_recipe.name = recipe_update.name
    
    # Update ingredients if provided
    if recipe_update.ingredients is not None:
        # Delete existing recipe ingredients
        db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id == recipe_id
        ).delete()
        
        # Add new ingredients
        for ingredient_data in recipe_update.ingredients:
            # Check if ingredient exists and belongs to user
            db_ingredient = db.query(Ingredient).filter(
                Ingredient.id == ingredient_data.ingredient_id,
                Ingredient.user_id == current_user.id
            ).first()
            
            if not db_ingredient:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Ingredient with id {ingredient_data.ingredient_id} not found"
                )
            
            # Create recipe ingredient
            recipe_ingredient = RecipeIngredient(
                recipe_id=db_recipe.id,
                ingredient_id=ingredient_data.ingredient_id,
                quantity=ingredient_data.quantity,
                unit=ingredient_data.unit
            )
            db.add(recipe_ingredient)
    
    db.commit()
    db.refresh(db_recipe)
    
    # Prepare response with calculated costs
    ingredients_response = []
    total_cost = 0
    
    for ri in db_recipe.ingredients:
        cost = ri.calculate_cost()
        total_cost += cost
        ingredients_response.append({
            "ingredient_id": ri.ingredient_id,
            "name": ri.ingredient.name,
            "quantity": ri.quantity,
            "unit": ri.unit,
            "cost": cost
        })
    
    return {
        "id": db_recipe.id,
        "name": db_recipe.name,
        "ingredients": ingredients_response,
        "total_cost": total_cost,
        "date_created": db_recipe.date_created
    }

@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    recipe = db.query(Recipe).filter(
        Recipe.id == recipe_id,
        Recipe.user_id == current_user.id
    ).first()
    
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    
    db.delete(recipe)
    db.commit()
    
    return None

@router.get("/{recipe_id}/net-margin")
def get_recipe_net_margin(
    recipe_id: int,
    selling_price: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculate and return the net margin for a recipe, including ingredient costs
    and fixed costs (rent, utilities, labor) allocated based on trailing month sales."""
    # Find the recipe
    recipe = db.query(Recipe).filter(
        Recipe.id == recipe_id,
        Recipe.user_id == current_user.id
    ).first()
    
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    
    # Calculate the net margin using the recipe's method
    net_margin = recipe.calculate_net_margin(
        db=db,
        selling_price=selling_price
    )
    
    return net_margin
