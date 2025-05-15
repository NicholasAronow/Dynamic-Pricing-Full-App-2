from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import sqlalchemy as sa
from database import get_db
import models, schemas
from auth import get_current_user

cogs_router = APIRouter()

@cogs_router.post("/", response_model=schemas.COGS)
async def create_cogs(
    cogs: schemas.COGSCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check if COGS entry already exists for the specified week
    existing_cogs = db.query(models.COGS).filter(
        models.COGS.user_id == current_user.id,
        models.COGS.week_start_date == cogs.week_start_date,
        models.COGS.week_end_date == cogs.week_end_date
    ).first()
    
    if existing_cogs:
        # Update existing entry
        existing_cogs.amount = cogs.amount
        db.commit()
        db.refresh(existing_cogs)
        return existing_cogs
    
    # Create new COGS entry
    db_cogs = models.COGS(
        user_id=current_user.id,
        week_start_date=cogs.week_start_date,
        week_end_date=cogs.week_end_date,
        amount=cogs.amount
    )
    db.add(db_cogs)
    db.commit()
    db.refresh(db_cogs)
    return db_cogs

@cogs_router.get("/", response_model=List[schemas.COGS])
async def get_cogs(
    account_id: Optional[int] = None,
    week_start_date: Optional[datetime] = None,
    week_end_date: Optional[datetime] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Build query base
    query = db.query(models.COGS)
    
    # Filter by user
    user_id = account_id if account_id else current_user.id
    query = query.filter(models.COGS.user_id == user_id)
    
    # Filter by specific week if provided
    if week_start_date and week_end_date:
        query = query.filter(
            models.COGS.week_start_date == week_start_date,
            models.COGS.week_end_date == week_end_date
        )
    
    # Filter by date range if provided
    if start_date and end_date:
        query = query.filter(
            models.COGS.week_start_date >= start_date,
            models.COGS.week_end_date <= end_date
        )
    
    # Sort by week start date
    query = query.order_by(models.COGS.week_start_date.desc())
    
    return query.all()

@cogs_router.get("/{cogs_id}", response_model=schemas.COGS)
async def get_cogs_by_id(
    cogs_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_cogs = db.query(models.COGS).filter(
        models.COGS.id == cogs_id,
        models.COGS.user_id == current_user.id
    ).first()
    
    if not db_cogs:
        raise HTTPException(status_code=404, detail="COGS entry not found")
    
    return db_cogs

@cogs_router.put("/{cogs_id}", response_model=schemas.COGS)
async def update_cogs(
    cogs_id: int,
    cogs_update: schemas.COGSUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_cogs = db.query(models.COGS).filter(
        models.COGS.id == cogs_id,
        models.COGS.user_id == current_user.id
    ).first()
    
    if not db_cogs:
        raise HTTPException(status_code=404, detail="COGS entry not found")
    
    # Update the amount
    db_cogs.amount = cogs_update.amount
    
    db.commit()
    db.refresh(db_cogs)
    return db_cogs

@cogs_router.delete("/{cogs_id}", status_code=204)
async def delete_cogs(
    cogs_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_cogs = db.query(models.COGS).filter(
        models.COGS.id == cogs_id,
        models.COGS.user_id == current_user.id
    ).first()
    
    if not db_cogs:
        raise HTTPException(status_code=404, detail="COGS entry not found")
    
    db.delete(db_cogs)
    db.commit()
    return None
