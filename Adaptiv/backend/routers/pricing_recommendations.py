from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from uuid import uuid4

from config.database import get_db
from models import PricingRecommendation, Item, User
from .auth import get_current_user
from services.pricing_service import PricingService

pricing_recommendations_router = APIRouter()

class BatchInfo(BaseModel):
    batch_id: str
    recommendation_date: datetime
    count: int

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
    batch_id: str

class PricingRecommendationAction(BaseModel):
    action: str  # "accept" or "reject"
    feedback: Optional[str] = None
    
class RecommendationItem(BaseModel):
    item_id: int
    item_name: str
    current_price: float
    recommended_price: float
    price_change_amount: float
    price_change_percent: float
    confidence_score: float
    rationale: str
    implementation_status: str = "pending"
    batch_id: str
    reevaluation_date: Optional[datetime] = None

class BulkRecommendationInput(BaseModel):
    recommendations: List[RecommendationItem]
    

@pricing_recommendations_router.post("/bulk-recommendations", status_code=status.HTTP_201_CREATED)
def create_bulk_recommendations(
    recommendation_data: BulkRecommendationInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create multiple pricing recommendations at once from agent results
    """
    try:
        # Track successfully created recommendations
        created_recommendations = []
        
        # Process each recommendation
        for rec_item in recommendation_data.recommendations:
            # Create a new recommendation instance
            db_recommendation = PricingRecommendation(
                user_id=current_user.id,
                item_id=rec_item.item_id,  # Only include item_id, not item_name
                current_price=rec_item.current_price,
                recommended_price=rec_item.recommended_price,
                price_change_amount=rec_item.price_change_amount,
                price_change_percent=rec_item.price_change_percent,
                confidence_score=rec_item.confidence_score,
                rationale=rec_item.rationale,
                implementation_status=rec_item.implementation_status,
                recommendation_date=datetime.utcnow(),
                reevaluation_date=rec_item.reevaluation_date,
                batch_id=rec_item.batch_id
            )
            
            # Add to database
            db.add(db_recommendation)
            created_recommendations.append(db_recommendation)
        
        # Commit all changes
        db.commit()
        
        # Refresh to get the assigned IDs
        for rec in created_recommendations:
            db.refresh(rec)
            
        return {
            "status": "success",
            "message": f"Created {len(created_recommendations)} recommendations",
            "batch_id": recommendation_data.recommendations[0].batch_id if recommendation_data.recommendations else None,
            "count": len(created_recommendations)
        }
        
    except SQLAlchemyError as e:
        # Roll back on error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error creating recommendations: {str(e)}"
        )

@pricing_recommendations_router.get("/recommendations", response_model=List[PricingRecommendationResponse])
def get_pricing_recommendations(
    status: Optional[str] = None,
    batch_id: Optional[str] = None,
    days: int = 7,  # Default to last 7 days
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get pricing recommendations for the current user.
    Optionally filter by implementation_status and date range.
    Only returns the most recent recommendation per item.
    """
    pricing_service = PricingService(db)
    
    # For now, return existing database recommendations but could be enhanced to use service logic
    # This maintains backward compatibility while introducing the service layer
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
    
    # Check if batch_id attribute exists (handle case where migration hasn't been run yet)
    has_batch_id = hasattr(PricingRecommendation, 'batch_id')
    
    # If we have a specific batch_id filter parameter and batch_id exists in the model
    if batch_id and has_batch_id:
        try:
            # Apply the batch_id filter
            query = query.filter(PricingRecommendation.batch_id == batch_id)
        except (AttributeError, SQLAlchemyError) as e:
            print(f"Error filtering by batch_id: {e}")
            # Fallback to old method if any error with batch_id
            has_batch_id = False
    
    # Execute query to get all recommendations
    all_recommendations = query.all()
    
    # If there are no recommendations, return an empty list
    if not all_recommendations:
        return []
    
    if has_batch_id and not batch_id:  # If we have batch_id in the model but no specific batch requested
        try:
            # Use batch_id to get the most recent batch
            most_recent_rec = all_recommendations[0]  # We already sorted by date
            most_recent_batch_id = most_recent_rec.batch_id
            
            # Get all recommendations from the most recent batch
            recommendations = [rec for rec in all_recommendations if rec.batch_id == most_recent_batch_id]
        except (AttributeError, SQLAlchemyError) as e:
            print(f"Error processing batch_id: {e}")
            # Fallback to old method if any error with batch_id
            has_batch_id = False
    elif has_batch_id and batch_id:  # If we filtered by a specific batch
        # All recommendations already filtered by batch_id in query
        recommendations = all_recommendations
    else:  # No batch_id in model or error occurred
        has_batch_id = False
    
    if not has_batch_id:
        # Fallback to previous behavior: deduplicate by item_id
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
        
        # Print debug info to verify data - with detailed reevaluation date
        print(f"Recommendation - {item_name}: Current: ${rec.current_price:.2f}, Recommended: ${rec.recommended_price:.2f}, Change: {rec.price_change_percent*100:.2f}%")
        print(f"   Reevaluation date (DB): {rec.reevaluation_date} (Type: {type(rec.reevaluation_date).__name__})") 
        
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
                reevaluation_date=rec.reevaluation_date,
                batch_id=rec.batch_id if has_batch_id else 'legacy_batch'
            )
        )
    
    return result

@pricing_recommendations_router.get("/recommendation-batches", response_model=List[BatchInfo])
def get_recommendation_batches(
    days: int = 30,  # Default to last 30 days
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get available recommendation batches for the current user.
    Returns a list of batch_ids with their dates and count of recommendations.
    """
    user_id = current_user.id
    
    # Filter by date - get batches from the last 'days' days
    date_cutoff = datetime.utcnow() - timedelta(days=days)
    
    # Check if batch_id attribute exists (handle case where migration hasn't been run yet)
    has_batch_id = hasattr(PricingRecommendation, 'batch_id')
    
    if not has_batch_id:
        # Return a single legacy batch if batch_id column doesn't exist
        count = db.query(PricingRecommendation).filter(
            PricingRecommendation.user_id == user_id,
            PricingRecommendation.recommendation_date >= date_cutoff
        ).count()
        
        if count > 0:
            # Get the most recent recommendation date
            most_recent = db.query(PricingRecommendation).filter(
                PricingRecommendation.user_id == user_id,
                PricingRecommendation.recommendation_date >= date_cutoff
            ).order_by(desc(PricingRecommendation.recommendation_date)).first()
            
            return [BatchInfo(
                batch_id="legacy_batch",
                recommendation_date=most_recent.recommendation_date,
                count=count
            )]
        return []
    
    try:
        # Use SQL to get distinct batch_ids, their dates, and counts
        result = []
        
        # Get distinct batch_ids and their most recent dates
        batch_query = db.query(
            PricingRecommendation.batch_id,
            # Use MAX to get the most recent date per batch
            func.max(PricingRecommendation.recommendation_date).label('max_date'),
            # Use func.count to count recommendations per batch
            func.count(PricingRecommendation.id).label('count')
        ).filter(
            PricingRecommendation.user_id == user_id,
            PricingRecommendation.recommendation_date >= date_cutoff
        ).group_by(
            PricingRecommendation.batch_id
        ).order_by(
            # Order by the max date
            desc(func.max(PricingRecommendation.recommendation_date))
        )
        
        # Execute the query and format results
        batches = batch_query.all()
        
        # Debug the batch query results
        print(f"Found {len(batches)} batches for user {user_id}")
        for i, batch in enumerate(batches):
            print(f"Batch {i}: {batch}")
            
        for batch in batches:
            # The query returns tuples with (batch_id, date, count)
            batch_id, rec_date, count = batch
            result.append(BatchInfo(
                batch_id=batch_id,
                recommendation_date=rec_date,
                count=count
            ))
            
        return result
    except (AttributeError, SQLAlchemyError) as e:
        print(f"Error retrieving batches: {e}")
        return []

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
        reevaluation_date=recommendation.reevaluation_date,
        batch_id=recommendation.batch_id  # Added the missing batch_id field
    )
