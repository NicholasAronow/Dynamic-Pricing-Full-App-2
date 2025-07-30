from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from config.database import get_db
import models, schemas
from .auth import get_current_user
from services.competitor_entity_service import CompetitorEntityService
import sys
import os
from pydantic import BaseModel
import json
import logging

competitor_entities_router = APIRouter()

# Schema for competitor scraping request
class CompetitorScrapeRequest(BaseModel):
    restaurant_name: str
    location: str = ""

class CompetitorScrapeResponse(BaseModel):
    success: bool
    competitor_id: Optional[int] = None
    items_added: int = 0
    message: str
    error: Optional[str] = None

@competitor_entities_router.get("/")
def get_competitor_entities(
    include_items: bool = False,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all competitor entities for the current user
    """
    try:
        service = CompetitorEntityService(db)
        competitors = service.get_competitor_entities(
            user_id=current_user.id,
            include_items=include_items,
            skip=skip,
            limit=limit
        )
        
        # Manual serialization
        result = []
        for competitor in competitors:
            comp_dict = {
                "id": competitor.id,
                "user_id": competitor.user_id,
                "name": competitor.name,
                "address": competitor.address,
                "category": competitor.category,
                "phone": competitor.phone,
                "website": competitor.website,
                "distance_km": competitor.distance_km,
                "latitude": competitor.latitude,
                "longitude": competitor.longitude,
                "menu_url": competitor.menu_url,
                "score": competitor.score,
                "is_selected": competitor.is_selected,
                "created_at": competitor.created_at.isoformat() if competitor.created_at else None,
                "updated_at": competitor.updated_at.isoformat() if competitor.updated_at else None,
            }
            
            if include_items and hasattr(competitor, 'items'):
                comp_dict["items"] = [
                    {
                        "id": item.id,
                        "competitor_id": item.competitor_id,
                        "competitor_name": item.competitor_name,
                        "item_name": item.item_name,
                        "description": item.description,
                        "category": item.category,
                        "price": float(item.price) if item.price else None,
                        "similarity_score": item.similarity_score,
                        "url": item.url,
                        "created_at": item.created_at.isoformat() if item.created_at else None,
                        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                    }
                    for item in competitor.items
                ] if competitor.items else []
            
            result.append(comp_dict)
        
        return result
        
    except Exception as e:
        import traceback
        print(f"Error in get_competitor_entities: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@competitor_entities_router.get("/selected")
def get_selected_competitors(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all competitors selected for tracking by the current user
    """
    service = CompetitorEntityService(db)
    competitors = service.get_selected_competitors(user_id=current_user.id)
    
    # Manual serialization
    result = []
    for competitor in competitors:
        comp_dict = {
            "id": competitor.id,
            "user_id": competitor.user_id,
            "name": competitor.name,
            "address": competitor.address,
            "category": competitor.category,
            "phone": competitor.phone,
            "website": competitor.website,
            "distance_km": competitor.distance_km,
            "latitude": competitor.latitude,
            "longitude": competitor.longitude,
            "menu_url": competitor.menu_url,
            "score": competitor.score,
            "is_selected": competitor.is_selected,
            "created_at": competitor.created_at.isoformat() if competitor.created_at else None,
            "updated_at": competitor.updated_at.isoformat() if competitor.updated_at else None,
        }
        result.append(comp_dict)
    
    return result



@competitor_entities_router.get("/summary")
def get_competitor_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get summary statistics for competitors
    """
    try:
        service = CompetitorEntityService(db)
        
        # Get all competitors
        competitors = service.get_competitor_entities(user_id=current_user.id)
        selected_count = sum(1 for c in competitors if c.is_selected)
        
        # Get total items count
        total_items = db.query(models.CompetitorItem).join(
            models.CompetitorEntity
        ).filter(
            models.CompetitorEntity.user_id == current_user.id
        ).count()
        
        return {
            "total_competitors": len(competitors),
            "selected_competitors": selected_count,
            "total_items": total_items,
            "recent_activity": []
        }
    except Exception as e:
        import traceback
        print(f"Error in get_competitor_summary: {str(e)}")
        print(traceback.format_exc())
        return {
            "total_competitors": 0,
            "selected_competitors": 0,
            "total_items": 0,
            "recent_activity": []
        }

@competitor_entities_router.get("/{competitor_id}")
def get_competitor_entity(
    competitor_id: int,
    include_items: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a specific competitor entity by ID
    """
    service = CompetitorEntityService(db)
    competitor = service.get_competitor_entity(
        competitor_id=competitor_id,
        user_id=current_user.id,
        include_items=include_items
    )
    if competitor is None:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    # Manual serialization
    result = {
        "id": competitor.id,
        "user_id": competitor.user_id,
        "name": competitor.name,
        "address": competitor.address,
        "category": competitor.category,
        "phone": competitor.phone,
        "website": competitor.website,
        "distance_km": competitor.distance_km,
        "latitude": competitor.latitude,
        "longitude": competitor.longitude,
        "menu_url": competitor.menu_url,
        "score": competitor.score,
        "is_selected": competitor.is_selected,
        "created_at": competitor.created_at.isoformat() if competitor.created_at else None,
        "updated_at": competitor.updated_at.isoformat() if competitor.updated_at else None,
    }
    
    if include_items and hasattr(competitor, 'items') and competitor.items is not None:
        result["items"] = []
        for item in competitor.items:
            item_dict = {
                "id": item.id,
                "competitor_id": item.competitor_id,
                "competitor_name": item.competitor_name if item.competitor_name else competitor.name,  # Fallback to competitor name
                "item_name": item.item_name,
                "description": item.description,
                "category": item.category,
                "price": float(item.price) if item.price else None,
                "similarity_score": float(item.similarity_score) if item.similarity_score else None,
                "url": item.url,
                "created_at": item.created_at.isoformat() if hasattr(item, 'created_at') and item.created_at else None,
                "updated_at": item.updated_at.isoformat() if hasattr(item, 'updated_at') and item.updated_at else None,
            }
            # DO NOT include the competitor object in the item to avoid circular reference
            result["items"].append(item_dict)
    
    return result

@competitor_entities_router.post("/", status_code=status.HTTP_201_CREATED)
def create_competitor_entity(
    competitor: schemas.CompetitorEntityCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a new competitor entity
    """
    service = CompetitorEntityService(db)
    db_competitor = service.create_competitor_entity(
        competitor_data=competitor,
        user_id=current_user.id
    )
    
    # Manual serialization to avoid circular references
    return {
        "id": db_competitor.id,
        "user_id": db_competitor.user_id,
        "name": db_competitor.name,
        "address": db_competitor.address,
        "category": db_competitor.category,
        "phone": db_competitor.phone,
        "website": db_competitor.website,
        "distance_km": db_competitor.distance_km,
        "latitude": db_competitor.latitude,
        "longitude": db_competitor.longitude,
        "menu_url": db_competitor.menu_url,
        "score": db_competitor.score,
        "is_selected": db_competitor.is_selected,
        "created_at": db_competitor.created_at.isoformat() if db_competitor.created_at else None,
        "updated_at": db_competitor.updated_at.isoformat() if db_competitor.updated_at else None,
    }

@competitor_entities_router.put("/{competitor_id}")
def update_competitor_entity(
    competitor_id: int,
    competitor: schemas.CompetitorEntityUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update a competitor entity
    """
    service = CompetitorEntityService(db)
    updated_competitor = service.update_competitor_entity(
        competitor_id=competitor_id,
        competitor_data=competitor,
        user_id=current_user.id
    )
    if updated_competitor is None:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    # Manual serialization to avoid circular references
    return {
        "id": updated_competitor.id,
        "user_id": updated_competitor.user_id,
        "name": updated_competitor.name,
        "address": updated_competitor.address,
        "category": updated_competitor.category,
        "phone": updated_competitor.phone,
        "website": updated_competitor.website,
        "distance_km": updated_competitor.distance_km,
        "latitude": updated_competitor.latitude,
        "longitude": updated_competitor.longitude,
        "menu_url": updated_competitor.menu_url,
        "score": updated_competitor.score,
        "is_selected": updated_competitor.is_selected,
        "created_at": updated_competitor.created_at.isoformat() if updated_competitor.created_at else None,
        "updated_at": updated_competitor.updated_at.isoformat() if updated_competitor.updated_at else None,
    }

@competitor_entities_router.delete("/{competitor_id}")
def delete_competitor_entity(
    competitor_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Delete a competitor entity and all its items
    """
    service = CompetitorEntityService(db)
    success = service.delete_competitor_entity(
        competitor_id=competitor_id,
        user_id=current_user.id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return {"message": "Competitor deleted successfully"}

@competitor_entities_router.post("/{competitor_id}/select")
def select_competitor_for_tracking(
    competitor_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Mark a competitor as selected for tracking
    """
    service = CompetitorEntityService(db)
    competitor = service.toggle_competitor_selection(
        competitor_id=competitor_id,
        user_id=current_user.id,
        is_selected=True
    )
    if competitor is None:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    # Manual serialization to avoid circular references
    competitor_data = {
        "id": competitor.id,
        "user_id": competitor.user_id,
        "name": competitor.name,
        "address": competitor.address,
        "category": competitor.category,
        "phone": competitor.phone,
        "website": competitor.website,
        "distance_km": competitor.distance_km,
        "latitude": competitor.latitude,
        "longitude": competitor.longitude,
        "menu_url": competitor.menu_url,
        "score": competitor.score,
        "is_selected": competitor.is_selected,
        "created_at": competitor.created_at.isoformat() if competitor.created_at else None,
        "updated_at": competitor.updated_at.isoformat() if competitor.updated_at else None,
    }
    
    return {"message": "Competitor selected for tracking", "competitor": competitor_data}

@competitor_entities_router.post("/{competitor_id}/unselect")
def unselect_competitor_for_tracking(
    competitor_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Mark a competitor as not selected for tracking
    """
    service = CompetitorEntityService(db)
    competitor = service.toggle_competitor_selection(
        competitor_id=competitor_id,
        user_id=current_user.id,
        is_selected=False
    )
    if competitor is None:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    # Manual serialization to avoid circular references
    competitor_data = {
        "id": competitor.id,
        "user_id": competitor.user_id,
        "name": competitor.name,
        "address": competitor.address,
        "category": competitor.category,
        "phone": competitor.phone,
        "website": competitor.website,
        "distance_km": competitor.distance_km,
        "latitude": competitor.latitude,
        "longitude": competitor.longitude,
        "menu_url": competitor.menu_url,
        "score": competitor.score,
        "is_selected": competitor.is_selected,
        "created_at": competitor.created_at.isoformat() if competitor.created_at else None,
        "updated_at": competitor.updated_at.isoformat() if competitor.updated_at else None,
    }
    
    return {"message": "Competitor unselected from tracking", "competitor": competitor_data}



@competitor_entities_router.get("/{competitor_id}/stats")
def get_competitor_stats(
    competitor_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get statistics for a specific competitor
    """
    try:
        service = CompetitorEntityService(db)
        stats = service.get_competitor_stats(
            competitor_id=competitor_id,
            user_id=current_user.id
        )
        
        # Ensure all numeric values are JSON serializable
        return {
            "competitor_id": stats["competitor_id"],
            "competitor_name": stats["competitor_name"],
            "total_items": stats["total_items"],
            "price_stats": {
                "min_price": float(stats["price_stats"]["min_price"]) if stats["price_stats"]["min_price"] else 0,
                "max_price": float(stats["price_stats"]["max_price"]) if stats["price_stats"]["max_price"] else 0,
                "avg_price": float(stats["price_stats"]["avg_price"]) if stats["price_stats"]["avg_price"] else 0
            },
            "category_breakdown": [
                {
                    "category": item["category"],
                    "item_count": item["item_count"],
                    "avg_price": float(item["avg_price"]) if item["avg_price"] else 0
                }
                for item in stats["category_breakdown"]
            ]
        }
    except Exception as e:
        import traceback
        print(f"Error in get_competitor_stats: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@competitor_entities_router.post("/migrate-legacy-data")
def migrate_legacy_competitor_data(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Migrate legacy competitor data from competitor_items.competitor_name to CompetitorEntity structure
    """
    service = CompetitorEntityService(db)
    result = service.migrate_legacy_competitor_data(user_id=current_user.id)
    return {
        "message": "Legacy data migration completed",
        "details": result
    }

@competitor_entities_router.post("/scrape")
def scrape_competitor(
    request: CompetitorScrapeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Start a competitor scraping task in the background using Celery
    """
    try:
        from tasks import scrape_competitor_task
        
        # Start the Celery task
        task = scrape_competitor_task.delay(
            restaurant_name=request.restaurant_name,
            location=request.location,
            user_id=current_user.id
        )
        
        logging.info(f"🚀 Started competitor scraping task {task.id} for user {current_user.id}")
        logging.info(f"🏪 Restaurant: {request.restaurant_name}")
        logging.info(f"📍 Location: {request.location}")
        
        return {
            "task_id": task.id,
            "message": f"Started scraping task for {request.restaurant_name}",
            "status": "started"
        }
        
    except Exception as e:
        error_msg = f"Failed to start scraping task: {str(e)}"
        logging.error(error_msg)
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )


@competitor_entities_router.get("/scrape/status/{task_id}")
def get_scrape_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Check the status of a competitor scraping task
    """
    try:
        from tasks import get_competitor_scrape_status
        
        # Get the task status
        status_result = get_competitor_scrape_status(task_id, current_user.id)
        
        logging.info(f"📊 Checking scrape task {task_id} status for user {current_user.id}")
        
        return status_result
        
    except Exception as e:
        error_msg = f"Failed to get task status: {str(e)}"
        logging.error(error_msg)
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )
