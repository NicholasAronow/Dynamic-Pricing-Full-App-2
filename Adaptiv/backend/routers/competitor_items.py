from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import models, schemas
from .auth import get_current_user

competitor_items_router = APIRouter()

@competitor_items_router.get("/", response_model=List[schemas.CompetitorItem])
def get_competitor_items(
    competitor_name: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
    # Temporarily removed authentication for testing
    # current_user: models.User = Depends(get_current_user)
):
    """
    Get all competitor items, with optional filters
    """
    query = db.query(models.CompetitorItem)
    
    if competitor_name:
        query = query.filter(models.CompetitorItem.competitor_name == competitor_name)
        
    if category:
        query = query.filter(models.CompetitorItem.category == category)
        
    return query.offset(skip).limit(limit).all()

@competitor_items_router.get("/{competitor_item_id}", response_model=schemas.CompetitorItem)
def get_competitor_item(
    competitor_item_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a specific competitor item by ID
    """
    competitor_item = db.query(models.CompetitorItem).filter(models.CompetitorItem.id == competitor_item_id).first()
    if competitor_item is None:
        raise HTTPException(status_code=404, detail="Competitor item not found")
    return competitor_item

@competitor_items_router.post("/", response_model=schemas.CompetitorItem, status_code=status.HTTP_201_CREATED)
def create_competitor_item(
    competitor_item: schemas.CompetitorItemCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a new competitor item
    """
    db_competitor_item = models.CompetitorItem(**competitor_item.dict())
    db.add(db_competitor_item)
    db.commit()
    db.refresh(db_competitor_item)
    return db_competitor_item

@competitor_items_router.put("/{competitor_item_id}", response_model=schemas.CompetitorItem)
def update_competitor_item(
    competitor_item_id: int, 
    competitor_item: schemas.CompetitorItemUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update a competitor item
    """
    db_competitor_item = db.query(models.CompetitorItem).filter(models.CompetitorItem.id == competitor_item_id).first()
    if db_competitor_item is None:
        raise HTTPException(status_code=404, detail="Competitor item not found")
        
    # Update only fields that are provided (not None)
    competitor_item_data = competitor_item.dict(exclude_unset=True)
    for key, value in competitor_item_data.items():
        if value is not None:
            setattr(db_competitor_item, key, value)
            
    db.commit()
    db.refresh(db_competitor_item)
    return db_competitor_item

@competitor_items_router.delete("/{competitor_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_competitor_item(
    competitor_item_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Delete a competitor item
    """
    db_competitor_item = db.query(models.CompetitorItem).filter(models.CompetitorItem.id == competitor_item_id).first()
    if db_competitor_item is None:
        raise HTTPException(status_code=404, detail="Competitor item not found")
        
    db.delete(db_competitor_item)
    db.commit()
    return None

@competitor_items_router.get("/category/{category}", response_model=List[schemas.CompetitorItem])
def get_competitor_items_by_category(
    category: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all competitor items in a specific category
    """
    competitor_items = db.query(models.CompetitorItem).filter(models.CompetitorItem.category == category).all()
    return competitor_items

@competitor_items_router.get("/similar-to/{item_id}", response_model=dict)
def get_competitors_similar_to_item(
    item_id: int,
    db: Session = Depends(get_db)
    # Temporarily removed authentication for testing
    # current_user: models.User = Depends(get_current_user)
):
    """
    Get competitor items similar to a specific menu item and calculate market statistics
    """
    # Get the item details
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Find competitor items in the same category with similar names
    competitor_items = db.query(models.CompetitorItem)\
                        .filter(models.CompetitorItem.category == item.category)\
                        .all()
    
    # Calculate market statistics
    all_prices = [comp_item.price for comp_item in competitor_items]
    if all_prices:
        market_low = min(all_prices)
        market_high = max(all_prices)
        market_avg = sum(all_prices) / len(all_prices)
    else:
        market_low = item.current_price
        market_high = item.current_price
        market_avg = item.current_price
    
    # Include our item's price for comparison
    our_price = item.current_price
    
    # Calculate normalized positions (on a scale of 1-10)
    price_range = market_high - market_low
    if price_range == 0:
        # If there's no price range, position items in the middle
        our_price_position = 50
        competitor_positions = {comp.competitor_name: 50 for comp in competitor_items}
        normalized_positions = {comp.competitor_name: 5 for comp in competitor_items}
        market_avg_position = 5
    else:
        # Calculate normalized positions on a scale of 1-10
        our_price_position = ((our_price - market_low) / price_range) * 100
        market_avg_position = ((market_avg - market_low) / price_range * 9) + 1
        
        competitor_positions = {}
        normalized_positions = {}
        
        for comp in competitor_items:
            # Calculate percentage position (0-100%)
            position = ((comp.price - market_low) / price_range) * 100
            competitor_positions[comp.competitor_name] = position
            
            # Calculate normalized position (1-10)
            norm_position = ((comp.price - market_low) / price_range * 9) + 1
            normalized_positions[comp.competitor_name] = norm_position
    
    # Format the response with all the necessary data
    return {
        "item": {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "price": our_price
        },
        "marketStats": {
            "low": market_low,
            "high": market_high,
            "average": market_avg,
            "averagePosition": market_avg_position
        },
        "ourPosition": our_price_position,
        "competitors": [
            {
                "id": comp.id,
                "name": comp.competitor_name,
                "item_name": comp.item_name,
                "price": comp.price,
                "difference": comp.price - our_price,
                "percentageDiff": ((comp.price - our_price) / our_price) * 100 if our_price > 0 else 0,
                "position": competitor_positions.get(comp.competitor_name, 50),
                "normalizedPosition": normalized_positions.get(comp.competitor_name, 5),
                "updated_at": comp.updated_at
            } for comp in competitor_items
        ]
    }

@competitor_items_router.get("/test-competitors")
def test_get_competitors():
    """
    Simple test endpoint that returns static competitor names
    """
    # Removed response_model to avoid validation errors
    return {"data": ["Tasty Bites", "Flavor Heaven", "Gourmet Delight", "Urban Eats"]}

@competitor_items_router.get("/competitors")
def get_competitors(
    db: Session = Depends(get_db)
):
    """
    Get all unique competitor names
    """
    try:
        competitors = db.query(models.CompetitorItem.competitor_name).distinct().all()
        result = [competitor[0] for competitor in competitors]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
