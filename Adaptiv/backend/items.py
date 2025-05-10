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
    db: Session = Depends(get_db)
    # Temporarily removed authentication for testing
    # current_user: models.User = Depends(get_current_user)
):
    """
    Get all items, with optional category filter
    """
    query = db.query(models.Item)
    
    if category:
        query = query.filter(models.Item.category == category)
        
    return query.offset(skip).limit(limit).all()

@items_router.get("/{item_id}", response_model=schemas.Item)
def get_item(
    item_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a specific item by ID
    """
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
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
    Create a new item
    """
    db_item = models.Item(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@items_router.put("/{item_id}", response_model=schemas.Item)
def update_item(
    item_id: int, 
    item: schemas.ItemUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update an item
    """
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
        
    # Update only fields that are provided (not None)
    item_data = item.dict(exclude_unset=True)
    for key, value in item_data.items():
        if value is not None:
            setattr(db_item, key, value)
            
    # If price is updated, create a price history record
    if "current_price" in item_data and item_data["current_price"] != db_item.current_price:
        price_history = models.PriceHistory(
            item_id=item_id,
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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Delete an item
    """
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
        
    db.delete(db_item)
    db.commit()
    return None

@items_router.get("/categories", response_model=List[str])
def get_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all unique categories
    """
    categories = db.query(models.Item.category).distinct().all()
    return [category[0] for category in categories]
