from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from config.database import get_db
import models, schemas
from .auth import get_current_user

price_history_router = APIRouter()

@price_history_router.get("/", response_model=List[schemas.PriceHistory])
def get_price_histories(
    item_id: Optional[int] = None,
    item_ids: Optional[str] = None,  # Add support for multiple item IDs as comma-separated string
    user_id: Optional[int] = None,
    account_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get price histories, with optional item_id/item_ids and user filtering
    """
    query = db.query(models.PriceHistory)
    
    # Handle either single item_id or multiple item_ids
    if item_ids:
        try:
            # Convert comma-separated string to list of integers
            id_list = [int(i) for i in item_ids.split(',')]
            query = query.filter(models.PriceHistory.item_id.in_(id_list))
            print(f"Filtering price history for multiple items: {id_list}")
        except ValueError as e:
            print(f"Error parsing item_ids: {e}")
    elif item_id:  # Only check item_id if item_ids is not provided
        query = query.filter(models.PriceHistory.item_id == item_id)
        print(f"Filtering price history for single item_id: {item_id}")
        
    # Filter by user ID (prefer explicit user_id parameter, fall back to account_id, finally use current user ID)
    filter_user_id = None
    if user_id is not None:
        filter_user_id = user_id
        print(f"Filtering price history by user_id={user_id}")
    elif account_id is not None:
        filter_user_id = account_id
        print(f"Filtering price history by account_id={account_id} (mapped to user_id)")
    else:
        filter_user_id = current_user.id
        print(f"Filtering price history by current_user.id={current_user.id}")

    # Apply the user filter
    query = query.filter(models.PriceHistory.user_id == filter_user_id)
    
    # Add index hint for performance if multiple items
    if item_ids:
        # No direct index hint in SQLAlchemy, but we'll optimize the query order
        query = query.order_by(models.PriceHistory.item_id, models.PriceHistory.changed_at.desc())
    else:
        query = query.order_by(models.PriceHistory.changed_at.desc())
    
    # Execute the query
    result = query.offset(skip).limit(limit).all()
    print(f"Found {len(result)} price history records for user {filter_user_id}")
    
    return result

@price_history_router.get("/{price_history_id}", response_model=schemas.PriceHistory)
def get_price_history(
    price_history_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a specific price history record by ID
    """
    price_history = db.query(models.PriceHistory).filter(models.PriceHistory.id == price_history_id).first()
    if price_history is None:
        raise HTTPException(status_code=404, detail="Price history record not found")
    return price_history

@price_history_router.post("/", response_model=schemas.PriceHistory, status_code=status.HTTP_201_CREATED)
def create_price_history(
    price_history: schemas.PriceHistoryCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Manually create a price history record
    """
    # Check if item exists
    item = db.query(models.Item).filter(models.Item.id == price_history.item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
        
    db_price_history = models.PriceHistory(**price_history.dict())
    db.add(db_price_history)
    
    # Update the item's current price
    item.current_price = price_history.new_price
    
    db.commit()
    db.refresh(db_price_history)
    return db_price_history

@price_history_router.post("/simulate", response_model=schemas.PriceHistory, status_code=status.HTTP_201_CREATED)
def simulate_price_change(
    simulation: schemas.PriceSimulation, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Simulate a price change (for testing without Square API)
    """
    # Check if item exists
    item = db.query(models.Item).filter(models.Item.id == simulation.item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
        
    # Create price history record
    db_price_history = models.PriceHistory(
        item_id=simulation.item_id,
        previous_price=item.current_price,
        new_price=simulation.new_price,
        change_reason=simulation.change_reason
    )
    db.add(db_price_history)
    
    # Update the item's current price
    item.current_price = simulation.new_price
    
    db.commit()
    db.refresh(db_price_history)
    return db_price_history
