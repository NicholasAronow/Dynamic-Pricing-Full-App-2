from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import models, schemas
from auth import get_current_user

price_history_router = APIRouter()

@price_history_router.get("/", response_model=List[schemas.PriceHistory])
def get_price_histories(
    item_id: Optional[int] = None,
    account_id: Optional[int] = None,
    user_id: Optional[int] = None,  # Added user_id parameter to match frontend
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get price histories, with optional item_id and account_id filter
    """
    try:
        query = db.query(models.PriceHistory)
        
        if item_id:
            # Start with a simple filter for item_id without joining
            # This is more efficient and less prone to errors if table relationships have issues
            query = query.filter(models.PriceHistory.item_id == item_id)
            
            # Use user_id if provided (preferred parameter name)
            filter_user_id = user_id if user_id is not None else account_id
            
            if filter_user_id:
                try:
                    # Join with items table for user filtering
                    query = query.join(models.Item, models.PriceHistory.item_id == models.Item.id)
                    query = query.filter(models.Item.user_id == filter_user_id)
                except Exception as e:
                    # Log the error but continue with just the item_id filter
                    print(f"Error applying user filter: {e}")
            else:
                # If no user/account ID provided, just filter by current authenticated user
                try:
                    if hasattr(current_user, 'id'):
                        query = query.join(models.Item, models.PriceHistory.item_id == models.Item.id)
                        query = query.filter(models.Item.user_id == current_user.id)
                except Exception as e:
                    print(f"Error filtering by current user: {e}")
        
        return query.order_by(models.PriceHistory.changed_at.desc()).offset(skip).limit(limit).all()
    except Exception as e:
        # Log any errors but return empty list instead of failing
        print(f"Error getting price histories: {e}")
        return []

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
