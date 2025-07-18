from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

import models, schemas
from database import get_db
from .auth import get_current_user

action_items_router = APIRouter()

@action_items_router.get("", response_model=List[schemas.ActionItem])
async def get_action_items(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all action items for the current user"""
    action_items = db.query(models.ActionItem).filter(models.ActionItem.user_id == current_user.id).all()
    return action_items

@action_items_router.post("", response_model=schemas.ActionItem)
async def create_action_item(
    action_item: schemas.ActionItemCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new action item for the current user"""
    db_action_item = models.ActionItem(
        user_id=current_user.id,
        title=action_item.title,
        description=action_item.description,
        priority=action_item.priority,
        status=action_item.status,
        action_type=action_item.action_type
    )
    db.add(db_action_item)
    db.commit()
    db.refresh(db_action_item)
    return db_action_item

@action_items_router.put("/{action_item_id}", response_model=schemas.ActionItem)
async def update_action_item(
    action_item_id: int,
    action_item: schemas.ActionItemUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing action item"""
    db_action_item = db.query(models.ActionItem).filter(
        models.ActionItem.id == action_item_id,
        models.ActionItem.user_id == current_user.id
    ).first()
    
    if db_action_item is None:
        raise HTTPException(status_code=404, detail="Action item not found")
    
    # Update fields
    for field, value in action_item.dict(exclude_unset=True).items():
        setattr(db_action_item, field, value)
    
    # Set completed_at timestamp if status is changed to completed
    if action_item.status == "completed" and db_action_item.completed_at is None:
        db_action_item.completed_at = datetime.now()
    
    # If status is changed back to pending, reset completed_at
    if action_item.status == "pending":
        db_action_item.completed_at = None
    
    db.commit()
    db.refresh(db_action_item)
    return db_action_item

@action_items_router.delete("/{action_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_action_item(
    action_item_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an action item"""
    db_action_item = db.query(models.ActionItem).filter(
        models.ActionItem.id == action_item_id,
        models.ActionItem.user_id == current_user.id
    ).first()
    
    if db_action_item is None:
        raise HTTPException(status_code=404, detail="Action item not found")
    
    db.delete(db_action_item)
    db.commit()
    return None

def seed_default_action_items(user_id: int, db: Session):
    """Seed default action items for a new user"""
    
    # Check if user already has action items
    existing_items = db.query(models.ActionItem).filter(models.ActionItem.user_id == user_id).count()
    if existing_items > 0:
        print(f"User {user_id} already has action items, skipping default items")
        return
    
    # Create default action items
    default_items = [
        models.ActionItem(
            user_id=user_id,
            title="Connect POS provider",
            description="Connect your Point of Sale system to enable automatic sales data import",
            priority="high",
            action_type="integration",
            status="pending"
        ),
        models.ActionItem(
            user_id=user_id,
            title="Connect Intuit",
            description="Connect your Intuit account to enable financial data synchronization",
            priority="high",
            action_type="integration",
            status="pending"
        ),
        models.ActionItem(
            user_id=user_id,
            title="Enter COGS for current week",
            description="Update your Cost of Goods Sold data for the current week to see profit margin visualizations",
            priority="medium",
            action_type="data_entry",
            status="pending"
        )
    ]
    
    for item in default_items:
        db.add(item)
    
    db.commit()
    print(f"Default action items added for user {user_id}")
