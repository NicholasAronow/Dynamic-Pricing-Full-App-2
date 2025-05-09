from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import models, schemas
from database import get_db
from auth import get_current_user

profile_router = APIRouter()

@profile_router.post("/business", response_model=schemas.BusinessProfile)
async def create_business_profile(
    profile: schemas.BusinessProfileCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user already has a business profile
    if current_user.business:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a business profile"
        )
    
    # Create new business profile
    db_profile = models.BusinessProfile(
        **profile.dict(),
        user_id=current_user.id
    )
    
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    
    return db_profile

@profile_router.get("/business", response_model=schemas.BusinessProfile)
async def get_business_profile(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found"
        )
    
    return current_user.business

@profile_router.put("/business", response_model=schemas.BusinessProfile)
async def update_business_profile(
    profile: schemas.BusinessProfileUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user has a business profile
    if not current_user.business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found"
        )
    
    # Update fields that are provided
    update_data = profile.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user.business, key, value)
    
    db.commit()
    db.refresh(current_user.business)
    
    return current_user.business
