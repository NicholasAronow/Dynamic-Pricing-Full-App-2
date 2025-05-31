from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from database import get_db
from models import PricingRecommendation, Item, User
from auth import get_current_user

pricing_recommendations_router = APIRouter()

class PricingRecommendationResponse(BaseModel):
    id: int
    item_id: int
    item_name: str
    current_price: float
    recommended_price: float
    price_change_amount: float
    price_change_percent: float
    confidence_score: float
    rationale: str
    implementation_status: str
    user_action: Optional[str] = None
    recommendation_date: datetime
    reevaluation_date: Optional[datetime] = None

class PricingRecommendationAction(BaseModel):
    action: str  # "accept" or "reject"
    feedback: Optional[str] = None

@pricing_recommendations_router.get("/recommendations", response_model=List[PricingRecommendationResponse])
def get_pricing_recommendations(
    status: Optional[str] = None,
    days: int = 7,  # Default to last 7 days
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get pricing recommendations for the current user.
    Optionally filter by implementation_status and date range.
    Only returns the most recent recommendation per item.
    """
    user_id = current_user.id
    
    # Filter by date - get recommendations from the last 'days' days
    date_cutoff = datetime.utcnow() - timedelta(days=days)
    query = db.query(PricingRecommendation).filter(
        PricingRecommendation.user_id == user_id,
        PricingRecommendation.recommendation_date >= date_cutoff
    )
    
    if status:
        query = query.filter(PricingRecommendation.implementation_status == status)
    
    # Get the latest recommendations first
    query = query.order_by(desc(PricingRecommendation.recommendation_date))
    all_recommendations = query.all()
    
    # Deduplicate recommendations - keep only the most recent one per item
    seen_items = set()
    unique_recommendations = []
    for rec in all_recommendations:
        if rec.item_id not in seen_items:
            seen_items.add(rec.item_id)
            unique_recommendations.append(rec)
    
    recommendations = unique_recommendations
    
    # Get item names
    result = []
    for rec in recommendations:
        item = db.query(Item).filter(Item.id == rec.item_id).first()
        item_name = item.name if item else "Unknown Item"
        
        # Double-check price data consistency
        # 1. Always recalculate price_change_percent to ensure accuracy
        if rec.current_price > 0 and rec.recommended_price != rec.current_price:
            calculated_percent = (rec.recommended_price - rec.current_price) / rec.current_price
            if abs(calculated_percent - rec.price_change_percent) > 0.0001:  # If there's a mismatch
                print(f"Fixing percent mismatch for {item_name}: {rec.price_change_percent:.4f} → {calculated_percent:.4f}")
                rec.price_change_percent = calculated_percent
        
        # 2. Double-check that price_change_amount matches the difference between prices
        calculated_amount = rec.recommended_price - rec.current_price
        if abs(calculated_amount - rec.price_change_amount) > 0.001:  # If there's a mismatch
            print(f"Fixing amount mismatch for {item_name}: {rec.price_change_amount:.2f} → {calculated_amount:.2f}")
            rec.price_change_amount = calculated_amount
        
        # Print debug info to verify data
        print(f"Recommendation - {item_name}: Current: ${rec.current_price:.2f}, Recommended: ${rec.recommended_price:.2f}, Change: {rec.price_change_percent*100:.2f}%")
        
        result.append(
            PricingRecommendationResponse(
                id=rec.id,
                item_id=rec.item_id,
                item_name=item_name,
                current_price=rec.current_price,
                recommended_price=rec.recommended_price,
                price_change_amount=rec.price_change_amount,
                price_change_percent=rec.price_change_percent,
                confidence_score=rec.confidence_score,
                rationale=rec.rationale,
                implementation_status=rec.implementation_status,
                user_action=rec.user_action,
                recommendation_date=rec.recommendation_date,
                reevaluation_date=rec.reevaluation_date
            )
        )
    
    return result

@pricing_recommendations_router.put("/recommendations/{recommendation_id}/action", response_model=PricingRecommendationResponse)
def update_recommendation_action(
    recommendation_id: int,
    action_data: PricingRecommendationAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a pricing recommendation with user action (accept/reject)
    """
    user_id = current_user.id
    recommendation = db.query(PricingRecommendation).filter(
        PricingRecommendation.id == recommendation_id,
        PricingRecommendation.user_id == user_id
    ).first()
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )
    
    # Update recommendation with user action
    recommendation.user_action = action_data.action
    recommendation.user_feedback = action_data.feedback
    recommendation.user_action_at = datetime.utcnow()
    
    # If accepted, update implementation status
    if action_data.action == "accept":
        recommendation.implementation_status = "approved"
        
        # TODO: If we want to automatically update the item's price
        # item = db.query(Item).filter(Item.id == recommendation.item_id).first()
        # if item:
        #     # Create price history record
        #     new_price_history = PriceHistory(
        #         item_id=item.id,
        #         user_id=user_id,
        #         previous_price=item.current_price,
        #         new_price=recommendation.recommended_price,
        #         change_reason=f"Accepted agent recommendation #{recommendation.id}"
        #     )
        #     db.add(new_price_history)
        #     
        #     # Update item price
        #     item.current_price = recommendation.recommended_price
        #     
        #     # Mark as implemented
        #     recommendation.implemented_at = datetime.utcnow()
        #     recommendation.implementation_status = "implemented"
        
    elif action_data.action == "reject":
        recommendation.implementation_status = "rejected"
    
    db.commit()
    
    # Get item name
    item = db.query(Item).filter(Item.id == recommendation.item_id).first()
    item_name = item.name if item else "Unknown Item"
    
    return PricingRecommendationResponse(
        id=recommendation.id,
        item_id=recommendation.item_id,
        item_name=item_name,
        current_price=recommendation.current_price,
        recommended_price=recommendation.recommended_price,
        price_change_amount=recommendation.price_change_amount,
        price_change_percent=recommendation.price_change_percent,
        confidence_score=recommendation.confidence_score,
        rationale=recommendation.rationale,
        implementation_status=recommendation.implementation_status,
        user_action=recommendation.user_action,
        recommendation_date=recommendation.recommendation_date,
        reevaluation_date=recommendation.reevaluation_date
    )
