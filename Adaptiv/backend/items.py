from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import models, schemas
from auth import get_current_user

items_router = APIRouter()

@items_router.get("/", response_model=List[schemas.Item])
def get_items(
    skip: int = 0, 
    limit: int = 100, 
    category: Optional[str] = None,
    user_id: Optional[int] = None,
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all items, with optional category filter, filtered by user's account
    """
    query = db.query(models.Item)
    
    # Filter by user ID (prefer explicit user_id parameter, fall back to account_id, finally use current user ID)
    filter_user_id = None
    if user_id is not None:
        filter_user_id = user_id
        print(f"Filtering items by user_id={user_id}")
    elif account_id is not None:
        filter_user_id = account_id
        print(f"Filtering items by account_id={account_id} (mapped to user_id)")
    else:
        filter_user_id = current_user.id
        print(f"Filtering items by current_user.id={current_user.id}")
        
    query = query.filter(models.Item.user_id == filter_user_id)
    
    if category:
        query = query.filter(models.Item.category == category)
        
    return query.offset(skip).limit(limit).all()

@items_router.get("/{item_id}", response_model=schemas.Item)
def get_item(
    item_id: int, 
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a specific item by ID, ensuring it belongs to the user's account
    """
    # Filter by the current user's ID unless specifically requesting another account's data
    user_id = account_id if account_id else current_user.id
    
    item = db.query(models.Item).filter(
        models.Item.id == item_id,
        models.Item.user_id == user_id
    ).first()
    
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@items_router.post("/", response_model=schemas.Item, status_code=status.HTTP_201_CREATED)
def create_item(
    item: schemas.ItemCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a new item associated with the current user's account
    """
    # Create a dict from the item and add the user_id
    item_data = item.dict()
    item_data["user_id"] = current_user.id
    
    db_item = models.Item(**item_data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@items_router.put("/{item_id}", response_model=schemas.Item)
def update_item(
    item_id: int, 
    item: schemas.ItemUpdate, 
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update an item, ensuring it belongs to the user's account
    """
    # Filter by the current user's ID unless specifically requesting another account's data
    user_id = account_id if account_id else current_user.id
    
    db_item = db.query(models.Item).filter(
        models.Item.id == item_id,
        models.Item.user_id == user_id
    ).first()
    
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found or you don't have permission to update it")
        
    # Update only fields that are provided (not None)
    item_data = item.dict(exclude_unset=True)
    for key, value in item_data.items():
        if value is not None:
            setattr(db_item, key, value)
            
    # If price is updated, create a price history record
    if "current_price" in item_data and item_data["current_price"] != db_item.current_price:
        price_history = models.PriceHistory(
            item_id=item_id,
            user_id=current_user.id,  # Associate with the current user
            previous_price=db_item.current_price,
            new_price=item_data["current_price"],
            change_reason="Manual price update"
        )
        db.add(price_history)
    
    db.commit()
    db.refresh(db_item)
    return db_item

@items_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int, 
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Delete an item, ensuring it belongs to the user's account
    """
    # Filter by the current user's ID unless specifically requesting another account's data
    user_id = account_id if account_id else current_user.id
    
    db_item = db.query(models.Item).filter(
        models.Item.id == item_id,
        models.Item.user_id == user_id
    ).first()
    
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found or you don't have permission to delete it")
        
    db.delete(db_item)
    db.commit()
    return None

@items_router.get("/categories", response_model=List[str])
def get_categories(
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all unique categories for the user's items
    """
    # Filter by the current user's ID unless specifically requesting another account's data
    user_id = account_id if account_id else current_user.id
    
    categories = db.query(models.Item.category)\
        .filter(models.Item.user_id == user_id)\
        .distinct()\
        .all()
        
    return [category[0] for category in categories]
