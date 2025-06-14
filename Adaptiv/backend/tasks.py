from celery_app import celery_app
from typing import Dict, Any, List
from sqlalchemy.orm import Session
import models
from database import SessionLocal
import json
import asyncio
# Import datetime at the module level since it's used in multiple places
from datetime import datetime

# Helper function to run async functions in synchronous code
def run_async(coroutine):
    """
    Helper function to run an async function in a synchronous context.
    Always creates a new event loop to avoid issues with loop reuse.
    """
    # Always create a new event loop for each task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run the coroutine and get the result
        result = loop.run_until_complete(coroutine)
        return result
    finally:
        # Always close the loop to free resources
        loop.close()
        # Reset the event loop to None
        asyncio.set_event_loop(None)


@celery_app.task(name="fetch_competitor_menu_task")
def fetch_competitor_menu_task(report_id: int, user_id: int) -> Dict[str, Any]:
    """
    Celery task to fetch competitor menu in the background
    
    Workflow:
    1. Find URLs
    2. Extract menu from each URL
    3. Consolidate data and save to database
    """
    try:
        # For Celery workers, we need to make sure the current directory is in the Python path
        import sys
        import os
        # Add the current directory to sys.path if not already there
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
            
        # Import the necessary gemini_competitor_search functions locally to avoid circular imports
        from gemini_competitor_search import find_competitor_menu_urls, extract_menu_from_url, consolidate_menu
        
        # Create a new database session
        db = SessionLocal()
        
        # Simulate the current_user from the user_id
        class UserProxy:
            def __init__(self, user_id):
                self.id = user_id
                
        current_user = UserProxy(user_id)
        
        # Get competitor details first
        competitor_report = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.id == report_id,
            models.CompetitorReport.user_id == user_id
        ).first()
        
        if not competitor_report:
            db.close()
            return {
                "success": False,
                "error": "Competitor report not found",
                "status": "failed"
            }
        
        # Update task status to processing
        if not competitor_report.metadata or not isinstance(competitor_report.metadata, dict):
            competitor_report.metadata = {}
        competitor_report.metadata["menu_fetch_status"] = "processing"
        db.commit()
        
        competitor_data = competitor_report.competitor_data
        competitor_name = competitor_data.get("name")
        competitor_category = competitor_data.get("category", "")
        direct_menu_url = competitor_data.get("menu_url")
        
        # If a direct menu URL is provided, use that instead of searching
        if direct_menu_url:
            source_urls = [{"url": direct_menu_url, "confidence": "high"}]
            competitor = {
                "name": competitor_name,
                "category": competitor_category,
                "report_id": report_id
            }
        else:
            # STEP 1: Find menu URLs if no direct URL is provided
            urls_response = run_async(find_competitor_menu_urls(report_id, db, current_user))
            
            if not urls_response.get("success") or not urls_response.get("urls"):
                # Update task status to failed
                competitor_report.metadata["menu_fetch_status"] = "failed"
                competitor_report.metadata["menu_fetch_error"] = "Could not find any online menu sources"
                db.commit()
                db.close()
                
                return {
                    "success": False,
                    "error": "Could not find any online menu sources for this competitor",
                    "status": "failed"
                }
                
            # Get competitor details from the response
            competitor = urls_response.get("competitor")
            competitor_name = competitor.get("name")
            competitor_category = competitor.get("category", "")
            source_urls = urls_response.get("urls")
            
        # STEP 2: Extract menu items from each URL
        all_menu_items = []
        for source in source_urls:
            url = source.get("url")
            if not url:
                continue
                
            url_items_response = run_async(extract_menu_from_url(
                url=url,
                competitor_name=competitor_name,
                competitor_category=competitor_category
            ))
            
            if url_items_response.get("success") and url_items_response.get("menu_items"):
                all_menu_items.extend(url_items_response.get("menu_items"))
        
        if not all_menu_items:
            # Update task status to failed
            competitor_report.metadata["menu_fetch_status"] = "failed"
            competitor_report.metadata["menu_fetch_error"] = "No menu items could be extracted"
            db.commit()
            db.close()
            
            return {
                "success": False,
                "error": "No menu items could be extracted from the found URLs",
                "status": "failed"
            }
            
        # STEP 3: Consolidate menu data and save to database
        consolidated_response = run_async(consolidate_menu(
            report_id=report_id,
            menu_items=all_menu_items,
            db=db,
            current_user=current_user
        ))
        
        # Update task status to completed
        competitor_report.metadata["menu_fetch_status"] = "completed"
        competitor_report.metadata["menu_fetch_completed_at"] = json.dumps({"$date": str(datetime.now())})
        competitor_report.metadata["menu_items_count"] = len(consolidated_response.get("menu_items", []))
        db.commit()
        
        # Close the database session
        db.close()
        
        return {
            "success": True,
            "status": "completed",
            "competitor": consolidated_response.get("competitor"),
            "menu_items_count": len(consolidated_response.get("menu_items", []))
        }
        
    except Exception as e:
        # Get database session if not already created
        if 'db' not in locals():
            db = SessionLocal()
            
        # Get competitor report
        competitor_report = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.id == report_id,
            models.CompetitorReport.user_id == user_id
        ).first()
        
        if competitor_report:
            # Update task status to failed
            if not competitor_report.metadata or not isinstance(competitor_report.metadata, dict):
                competitor_report.metadata = {}
            competitor_report.metadata["menu_fetch_status"] = "failed"
            competitor_report.metadata["menu_fetch_error"] = str(e)
            db.commit()
            
        # Close the database session
        db.close()
        
        return {
            "success": False,
            "error": str(e),
            "status": "failed"
        }


@celery_app.task(name="get_menu_fetch_status_task")
def get_menu_fetch_status_task(report_id: int, user_id: int) -> Dict[str, Any]:
    """
    Check the status of a menu fetch task
    """
    try:
        # Create a new database session
        db = SessionLocal()
        
        # Get competitor report
        competitor_report = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.id == report_id,
            models.CompetitorReport.user_id == user_id
        ).first()
        
        if not competitor_report:
            db.close()
            return {
                "success": False,
                "error": "Competitor report not found",
                "status": "unknown"
            }
        
        # Get fetch status from metadata
        metadata = competitor_report.metadata or {}
        status = metadata.get("menu_fetch_status", "not_started")
        error = metadata.get("menu_fetch_error")
        items_count = metadata.get("menu_items_count", 0)
        
        db.close()
        
        return {
            "success": True,
            "status": status,
            "error": error,
            "menu_items_count": items_count,
            "competitor_name": competitor_report.competitor_data.get("name", "")
        }
        
    except Exception as e:
        # Close database session if opened
        if 'db' in locals():
            db.close()
            
        return {
            "success": False,
            "error": str(e),
            "status": "error"
        }


# Add import for datetime
from datetime import datetime
