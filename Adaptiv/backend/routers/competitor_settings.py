from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel
import models
from database import get_db
from .auth import get_current_user

class BusinessProfileResponse(BaseModel):
    business_name: Optional[str] = None
    industry: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

competitor_settings_router = APIRouter()

@competitor_settings_router.get("/tracking-status")
async def get_competitor_tracking_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get the competitor tracking status for the current user
    """
    return {
        "success": True,
        "competitor_tracking_enabled": current_user.competitor_tracking_enabled
    }

@competitor_settings_router.put("/tracking-status")
async def update_competitor_tracking_status(
    settings: Dict[str, bool],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update the competitor tracking status for the current user
    """
    try:
        # Update the user record
        user = db.query(models.User).filter(models.User.id == current_user.id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update the tracking status
        user.competitor_tracking_enabled = settings.get("enabled", False)
        
        # Commit the changes
        db.commit()
        
        return {
            "success": True,
            "competitor_tracking_enabled": user.competitor_tracking_enabled
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@competitor_settings_router.get("/business-profile", response_model=BusinessProfileResponse)
async def get_business_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get the business profile for the current user for competitor search
    """
    try:
        # Get the business profile
        business_profile = db.query(models.BusinessProfile).filter(
            models.BusinessProfile.user_id == current_user.id
        ).first()
        
        if not business_profile:
            # Return empty profile if not found
            return BusinessProfileResponse()
        
        return BusinessProfileResponse(
            business_name=business_profile.business_name,
            industry=business_profile.industry,
            street_address=business_profile.street_address,
            city=business_profile.city,
            state=business_profile.state,
            postal_code=business_profile.postal_code,
            country=business_profile.country
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving business profile: {str(e)}")
