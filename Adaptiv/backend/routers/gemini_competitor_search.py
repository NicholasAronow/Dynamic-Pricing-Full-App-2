from fastapi import APIRouter, Depends, HTTPException, Body, Query, BackgroundTasks
from sqlalchemy.orm import Session, attributes
from sqlalchemy import desc
from typing import List, Dict, Any
from config.database import get_db
import models, schemas
from .auth import get_current_user
from services.competitor_service import CompetitorService
import os
import json
from datetime import datetime, timedelta
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv
from celery.result import AsyncResult
from pydantic import BaseModel
# Load environment variables
load_dotenv()

# Configure Google Gemini API
GEMINI_API_KEY = "AIzaSyAxzLp6amQK1CJ87oD_eZ8QBpFYPDbXyUM"
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

gemini_competitor_router = APIRouter()

@gemini_competitor_router.post("/search-competitors")
def search_item_competitors(
    item_name: str = Body(..., embed=True),
    location: str = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Search for competitors using the service layer"""
    try:
        competitor_service = CompetitorService(db)
        return competitor_service.search_competitors(item_name, current_user.id, location)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@gemini_competitor_router.get("/competitor-data/{item_name}")
def get_competitor_data(
    item_name: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get stored competitor data for an item"""
    try:
        competitor_service = CompetitorService(db)
        return competitor_service.get_competitor_data(item_name, days)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@gemini_competitor_router.get("/market-analysis/{item_name}")
def get_market_analysis(
    item_name: str,
    current_price: float = Query(..., gt=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get market analysis comparing current price to competitors"""
    try:
        competitor_service = CompetitorService(db)
        return competitor_service.get_market_analysis(item_name, current_price)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@gemini_competitor_router.post("/update-all-competitors")
def update_all_competitor_prices(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update competitor prices for all user items"""
    try:
        competitor_service = CompetitorService(db)
        return competitor_service.update_competitor_prices(current_user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@gemini_competitor_router.get("/trends/{item_name}")
def get_competitor_trends(
    item_name: str,
    days: int = Query(90, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get competitor price trends over time"""
    try:
        competitor_service = CompetitorService(db)
        return competitor_service.get_competitor_trends(item_name, days)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@gemini_competitor_router.post("/find-menu-urls/{report_id}")
async def find_competitor_menu_urls(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Step 1: Find websites and online menu URLs for a specific competitor using Gemini API
    """
    try:
        # Find the competitor report
        competitor_report = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.id == report_id,
            models.CompetitorReport.user_id == current_user.id
        ).first()
        
        if not competitor_report:
            raise HTTPException(status_code=404, detail="Competitor not found or you don't have permission to access it")
        
        # Get competitor details from the report
        competitor_data = competitor_report.competitor_data
        if not isinstance(competitor_data, dict) or not competitor_data.get("name") or not competitor_data.get("address"):
            raise HTTPException(status_code=400, detail="Invalid competitor data in the database")
        
        competitor_name = competitor_data.get("name")
        competitor_address = competitor_data.get("address")
        competitor_category = competitor_data.get("category", "")
        
        # Create Gemini model
        model = genai.GenerativeModel('gemini-2.5-pro-preview-06-05')
        
        # STEP 1: Find websites and online menu URLs
        step1_prompt = f"""TASK: Find official websites, online ordering platforms, and menu pages for this SPECIFIC business:

BUSINESS DETAILS:
- Name: {competitor_name}
- Address: {competitor_address}
- Category: {competitor_category}

PROVIDE THESE SOURCES AS A JSON ARRAY OF OBJECTS:
[
  {{
    "url": "https://example.com",
    "source_type": "official_website|online_ordering|third_party_menu|review_site",
    "confidence": "high|medium|low" (how confident you are this is the correct business)
  }}
]

RETURN ONLY THE JSON ARRAY, no introduction or explanation.

RULES:
1. Include ONLY working URLs that specifically relate to THIS business at THIS location
2. PRIORITIZE: official website, online ordering systems (Toast, Square, etc.), and third-party menu directories
3. VERIFY: Double-check address/location matches
4. Include only the MOST RELIABLE source to reference both items and price, not an exhaustive list
5. Set confidence based on how certain you are that the URL belongs to this specific business location

If you cannot find ANY reliable sources, return: []""" 
        
        # Generate response for Step 1
        step1_response = model.generate_content(step1_prompt)
        step1_text = step1_response.text
        
        print("Step 1 Prompt: ", step1_prompt)
        print("Step 1 Response: ", step1_text)
        
        # Extract JSON from Step 1 response
        if "```json" in step1_text:
            json_text = step1_text.split("```json")[1].split("```")[0].strip()
        elif "```" in step1_text:
            json_text = step1_text.split("```")[1].strip()
        else:
            json_text = step1_text.strip()
            
        try:
            source_urls = json.loads(json_text)
            
            # Store the URLs in the competitor report for later use in steps 2-3
            if source_urls:
                if not competitor_report.metadata or not isinstance(competitor_report.metadata, dict):
                    competitor_report.metadata = {}
                competitor_report.metadata["menu_urls"] = source_urls
                db.commit()
            
            return {
                "success": True,
                "competitor": {
                    "name": competitor_name,
                    "address": competitor_address,
                    "category": competitor_category,
                    "report_id": competitor_report.id
                },
                "urls": source_urls
            }
            
        except json.JSONDecodeError:
            print("Error parsing URLs JSON")
            return {
                "success": False,
                "error": "Failed to parse URLs from Gemini response",
                "raw_response": step1_text
            }
            
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding menu URLs: {str(e)}")


# Define a Pydantic model for menu content extraction request
class MenuContentRequest(BaseModel):
    menu_content: str

@gemini_competitor_router.post("/extract-from-menu-content")
async def extract_from_menu_content(
    request: MenuContentRequest
):
    """
    Extract restaurant details and menu items from pasted menu content using Celery task
    """
    try:
        # Import the specific task using the fully qualified name
        from tasks import extract_menu_data_task
        
        # Submit the task to Celery and get the task ID
        # Use apply_async to ensure task name is explicitly used
        task = extract_menu_data_task.apply_async(args=[request.menu_content])
        
        # Return the task ID for the frontend to poll
        return {
            "success": True,
            "task_id": task.id,
            "status": "pending",
            "message": "Menu extraction task submitted successfully. Check the task status endpoint for results."
        }
            
    except Exception as e:
        print(f"Error submitting menu extraction task: {e}")
        return {
            "success": False,
            "error": str(e),
            "status": "failed"
        }

@gemini_competitor_router.get("/extract-menu-status/{task_id}")
async def get_menu_extraction_status(task_id: str):
    """
    Check the status of a menu extraction task and retrieve results if complete
    """
    try:
        from tasks import extract_menu_data_task
        from celery.result import AsyncResult
        
        # Get the task result
        task_result = AsyncResult(task_id)
        
        # If the task is still pending
        if task_result.status == 'PENDING':
            return {
                "success": True,
                "status": "pending",
                "message": "Menu extraction is still in progress."
            }
        
        # If the task failed
        elif task_result.status == 'FAILURE':
            return {
                "success": False,
                "status": "failed",
                "error": str(task_result.result),
                "message": "Menu extraction task failed."
            }
        
        # If the task succeeded
        elif task_result.status == 'SUCCESS':
            result = task_result.result
            
            # Check if the task itself reported success
            if result.get("success", False):
                return {
                    "success": True,
                    "status": "completed",
                    "restaurant_info": result.get("restaurant_info", {}),
                    "menu_items": result.get("menu_items", [])
                }
            else:
                return {
                    "success": False,
                    "status": "failed",
                    "error": result.get("error", "Unknown error in extraction task"),
                    "message": "Menu extraction task reported failure."
                }
                
        # Any other status
        else:
            return {
                "success": False,
                "status": task_result.status.lower(),
                "message": f"Task is in {task_result.status} state."
            }
            
    except Exception as e:
        print(f"Error checking menu extraction task status: {e}")
        return {
            "success": False,
            "error": str(e),
            "status": "error"
        }


@gemini_competitor_router.post("/extract-menu-from-url")
async def extract_menu_from_url(
    url: str = Body(...),
    competitor_name: str = Body(...),
    competitor_category: str = Body(...)
):
    """
    Step 2: Extract menu items from a specific URL
    """
    try:
        # Create Gemini model
        model = genai.GenerativeModel('gemini-2.5-pro-preview-06-05')
        
        # STEP 2: Extract menu items from URL
        step2_prompt = f"""TASK: Extract all menu items and prices from this web page for {competitor_name}.

URL: {url}

RETURN DATA AS JSON ARRAY:
[
  {{
    "item_name": "Exact menu item name",
    "category": "appetizer|main_course|dessert|beverage|side|special",
    "description": "Item description or null if none",
    "price": 12.99,
    "price_currency": "USD",
    "source_url": "{url}"
  }}
]

RULES:
1. Extract ONLY items that appear on the menu with their exact names
2. Include prices ONLY if explicitly stated (use null if no price is available)
3. Categorize items appropriately
4. Extract as many menu items as you can find
5. Do not fabricate or guess information
6. Return empty array [] if no menu items can be found
7. If the menu is not available, return empty array []

RETURN ONLY THE JSON ARRAY, no explanations."""
        
        # Generate response for Step 2
        step2_response = model.generate_content(step2_prompt)
        step2_text = step2_response.text
        
        print(f"Step 2 URL: {url}")
        print("Step 2 Response: ", step2_text[:100] + "..." if len(step2_text) > 100 else step2_text)
        
        # Extract JSON from Step 2 response
        if "```json" in step2_text:
            items_json = step2_text.split("```json")[1].split("```")[0].strip()
        elif "```" in step2_text:
            items_json = step2_text.split("```")[1].strip()
        else:
            items_json = step2_text.strip()
        
        try:
            url_items = json.loads(items_json)
            return {
                "success": True,
                "url": url,
                "menu_items": url_items
            }
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Failed to parse menu items from Gemini response",
                "raw_response": step2_text
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting menu from URL: {str(e)}")


@gemini_competitor_router.post("/consolidate-menu/{report_id}")
async def consolidate_menu(
    report_id: int,
    menu_items: List[Dict[str, Any]] = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Step 3: Consolidate and deduplicate menu data, then save to database
    """
    try:
        # Find the competitor report
        competitor_report = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.id == report_id,
            models.CompetitorReport.user_id == current_user.id
        ).first()
        
        if not competitor_report:
            raise HTTPException(status_code=404, detail="Competitor not found or you don't have permission to access it")
        
        # Get competitor details from the report
        competitor_data = competitor_report.competitor_data
        if not isinstance(competitor_data, dict) or not competitor_data.get("name"):
            raise HTTPException(status_code=400, detail="Invalid competitor data in the database")
        
        competitor_name = competitor_data.get("name")
        competitor_address = competitor_data.get("address", "")
        competitor_category = competitor_data.get("category", "")
        
        # Create Gemini model
        model = genai.GenerativeModel('gemini-2.5-pro-preview-06-05')
        
        # STEP 3: Consolidate and deduplicate menu data
        if not menu_items:
            # If no menu items provided, return empty list
            consolidated_items = []
        else:
            step3_prompt = f"""TASK: Consolidate and deduplicate this menu data for {competitor_name}.

RAW MENU DATA:
{json.dumps(menu_items[:30], indent=2)}

RETURN CONSOLIDATED DATA AS JSON ARRAY:
[
  {{
    "item_name": "Standardized item name",
    "category": "appetizer|main_course|dessert|beverage|side|special",
    "description": "Best available description or null",
    "price": 12.99,
    "price_currency": "USD",
    "availability": "available|seasonal|limited_time|unknown",
    "source_confidence": "high|medium|low"
  }}
]

RULES:
1. DEDUPLICATE items that are clearly the same product
2. STANDARDIZE item names and categories
3. Use the MOST COMPLETE description available
4. Use the MOST RECENT or MOST COMMON price when multiple exist
5. Add "availability" and "source_confidence" fields based on your assessment
6. Return maximum 30 most representative menu items
7. PRIORITIZE items with complete information (name, category, description, price)

RETURN ONLY THE JSON ARRAY, no explanations."""
            
            try:
                # Generate response for Step 3
                step3_response = model.generate_content(step3_prompt)
                step3_text = step3_response.text
                
                print("Step 3 Response: ", step3_text[:100] + "..." if len(step3_text) > 100 else step3_text)
                
                # Extract JSON from Step 3 response
                if "```json" in step3_text:
                    final_json = step3_text.split("```json")[1].split("```")[0].strip()
                elif "```" in step3_text:
                    final_json = step3_text.split("```")[1].strip()
                else:
                    final_json = step3_text.strip()
                
                consolidated_items = json.loads(final_json)
            except Exception as e:
                print(f"Error in Step 3 consolidation: {str(e)}")
                # Fallback to raw items if consolidation fails
                consolidated_items = menu_items[:30] if len(menu_items) > 30 else menu_items
        
        # Generate a unique batch ID and current timestamp for this menu sync
        import uuid
        from datetime import datetime, timedelta
        batch_id = f"{report_id}_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
        sync_timestamp = datetime.now()
        
        # Save menu items as CompetitorItems in the database
        saved_items = []
        for item in consolidated_items:
            # Handle null prices by converting to 0.0
            price = item.get("price")
            price_float = float(price) if price is not None else 0.0
            
            competitor_item = models.CompetitorItem(
                competitor_name=competitor_name,
                item_name=item.get("item_name"),
                category=item.get("category"),
                description=item.get("description") if item.get("description") else None,
                price=price_float,
                url=competitor_address,  # Using address as a reference point
                batch_id=batch_id,
                sync_timestamp=sync_timestamp
            )
            
            db.add(competitor_item)
            saved_items.append({
                "item_name": item.get("item_name", ""),
                "category": item.get("category", ""),
                "description": item.get("description"),
                "price": item.get("price"),
                "price_currency": item.get("price_currency", "USD"),
                "availability": item.get("availability", "unknown"),
                "source_confidence": item.get("source_confidence", "medium")
            })
        
        # Update the competitor report with menu information
        competitor_report.summary = f"Menu fetched for {competitor_name}"
        db.commit()
        
        return {
            "success": True,
            "competitor": {
                "name": competitor_name,
                "address": competitor_address,
                "category": competitor_category,
                "report_id": competitor_report.id
            },
            "menu_items": saved_items
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error consolidating menu: {str(e)}")


@gemini_competitor_router.get("/get-menu-batches/{report_id}")
async def get_competitor_menu_batches(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get available menu batches (syncs) for a competitor
    """
    competitor_report = db.query(models.CompetitorReport).filter(
        models.CompetitorReport.id == report_id,
        models.CompetitorReport.user_id == current_user.id
    ).first()
    
    if not competitor_report:
        raise HTTPException(status_code=404, detail="Competitor report not found")
    
    competitor_name = competitor_report.competitor_data.get("name")
    
    # Query distinct batch_ids with their timestamps
    batches_query = db.query(
        models.CompetitorItem.batch_id,
        models.CompetitorItem.sync_timestamp
    ).filter(
        models.CompetitorItem.competitor_name == competitor_name
    ).distinct()
    
    # Order by timestamp descending (newest first)
    batches_query = batches_query.order_by(desc(models.CompetitorItem.sync_timestamp))
    
    batches_data = []
    for batch_id, sync_timestamp in batches_query.all():
        batch_item_count = db.query(models.CompetitorItem).filter(
            models.CompetitorItem.competitor_name == competitor_name,
            models.CompetitorItem.batch_id == batch_id
        ).count()
        
        batches_data.append({
            "batch_id": batch_id,
            "sync_timestamp": sync_timestamp.isoformat() if sync_timestamp else None,
            "item_count": batch_item_count
        })
    
    return {
        "success": True,
        "competitor_name": competitor_name,
        "batches": batches_data
    }


@gemini_competitor_router.delete("/delete-menu-item/{item_id}", response_model=dict, tags=["Competitors"])
async def delete_menu_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete a specific menu item by ID"""
    try:
        # Find the menu item by ID
        menu_item = db.query(models.CompetitorItem).filter(models.CompetitorItem.id == item_id).first()
        
        if not menu_item:
            return {"success": False, "error": "Menu item not found"}
        
        # Get the competitor name before deleting for the response
        competitor_name = menu_item.competitor_name
        item_name = menu_item.item_name
        
        # Delete the menu item
        db.delete(menu_item)
        db.commit()
        
        print(f"DEBUG - delete_menu_item: Deleted menu item {item_id} ({item_name}) from {competitor_name}")
        
        return {
            "success": True, 
            "message": f"Successfully deleted menu item: {item_name}"
        }
        
    except Exception as e:
        db.rollback()
        print(f"ERROR - delete_menu_item: {str(e)}")
        return {"success": False, "error": f"Failed to delete menu item: {str(e)}"}


@gemini_competitor_router.get("/get-stored-menu/{report_id}")
async def get_stored_competitor_menu(
    report_id: int,
    batch_id: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieves menu items that are already stored in the database for a competitor
    without running any extraction processes
    """
    try:
        # Verify the competitor report exists
        competitor_report = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.id == report_id,
            models.CompetitorReport.user_id == current_user.id
        ).first()
        
        if not competitor_report:
            raise HTTPException(status_code=404, detail="Competitor report not found")
            
        # Get competitor name from the competitor_data dictionary
        competitor_data = competitor_report.competitor_data
        if not competitor_data or not isinstance(competitor_data, dict):
            raise HTTPException(status_code=404, detail="Invalid competitor data")
            
        competitor_name = competitor_data.get("name")
        if not competitor_name:
            raise HTTPException(status_code=404, detail="Competitor name not found")
            
        # Add debug logs for competitor name being queried
        print(f"DEBUG - get_stored_menu: Looking for menu items for competitor '{competitor_name}'")
        
        # Check if we have any menu items for this competitor at all
        item_count = db.query(models.CompetitorItem).filter(
            models.CompetitorItem.competitor_name == competitor_name
        ).count()
        
        print(f"DEBUG - get_stored_menu: Found {item_count} total menu items for '{competitor_name}'")
        
        # Check if CompetitorItem has user_id attribute before using it
        has_user_id = hasattr(models.CompetitorItem, 'user_id')
        print(f"DEBUG - get_stored_menu: CompetitorItem has user_id attribute: {has_user_id}")
        
        # Create a query for the menu items
        if has_user_id:
            menu_query = db.query(models.CompetitorItem).filter(
                models.CompetitorItem.competitor_name == competitor_name,
                models.CompetitorItem.user_id == current_user.id  # Filter by user_id if it exists
            )
            # Also check count with user_id filter
            item_count_with_user = menu_query.count()
            print(f"DEBUG - get_stored_menu: Found {item_count_with_user} menu items for '{competitor_name}' with user_id={current_user.id}")
        else:
            # If user_id attribute doesn't exist, just filter by competitor name
            menu_query = db.query(models.CompetitorItem).filter(
                models.CompetitorItem.competitor_name == competitor_name
            )
            print(f"DEBUG - get_stored_menu: No user_id field in model, using only competitor name filter")
        
        
        # If batch_id is provided, filter by that specific batch
        # Otherwise, get the most recent batch
        selected_batch = None
        if batch_id:
            print(f"DEBUG - get_stored_menu: Filtering by batch_id={batch_id}")
            menu_query = menu_query.filter(models.CompetitorItem.batch_id == batch_id)
            # Get batch details for response
            batch_info = db.query(models.CompetitorItem.batch_id, models.CompetitorItem.sync_timestamp) \
                .filter(models.CompetitorItem.competitor_name == competitor_name, 
                        models.CompetitorItem.batch_id == batch_id) \
                .first()
            if batch_info:
                selected_batch = {
                    "batch_id": batch_info[0],
                    "sync_timestamp": batch_info[1].isoformat() if batch_info[1] else None
                }
                print(f"DEBUG - get_stored_menu: Found batch details: {selected_batch}")
            else:
                print(f"DEBUG - get_stored_menu: No batch info found for batch_id={batch_id}")
        else:
            # No batch_id provided, get the most recent batch
            print(f"DEBUG - get_stored_menu: No batch_id provided, looking for most recent batch")
            
            # Check if user_id can be used in the filter
            if has_user_id:
                latest_batch = db.query(models.CompetitorItem.batch_id, models.CompetitorItem.sync_timestamp) \
                    .filter(models.CompetitorItem.competitor_name == competitor_name, 
                            models.CompetitorItem.user_id == current_user.id) \
                    .order_by(desc(models.CompetitorItem.sync_timestamp)) \
                    .first()
            else:
                # If no user_id attribute, just filter by competitor name
                latest_batch = db.query(models.CompetitorItem.batch_id, models.CompetitorItem.sync_timestamp) \
                    .filter(models.CompetitorItem.competitor_name == competitor_name) \
                    .order_by(desc(models.CompetitorItem.sync_timestamp)) \
                    .first()
            
            if latest_batch:
                batch_id = latest_batch[0]
                menu_query = menu_query.filter(models.CompetitorItem.batch_id == batch_id)
                selected_batch = {
                    "batch_id": latest_batch[0],
                    "sync_timestamp": latest_batch[1].isoformat() if latest_batch[1] else None
                }
                print(f"DEBUG - get_stored_menu: Found most recent batch: {selected_batch}")
            else:
                print(f"DEBUG - get_stored_menu: No batches found at all for this competitor")
        
        # Execute the query
        menu_items = menu_query.all()
        print(f"DEBUG - get_stored_menu: Query returned {len(menu_items)} menu items")
        
        # We've already done the appropriate filtering in the menu_query building above
        # No need for fallback query here, as it would lead to duplication
        print(f"DEBUG - get_stored_menu: Query returned {len(menu_items)} menu items, using these results directly")
        
        # Convert to response format
        menu_item_list = []
        for item in menu_items:
            menu_item_list.append({
                "item_name": item.item_name,
                "category": item.category,
                "description": item.description,
                "price": item.price,
                "price_currency": item.price_currency if hasattr(item, 'price_currency') and item.price_currency else "USD",
                "availability": "Available",
                "source_confidence": "high" if getattr(item, 'source', '') == 'manual' else "medium",
                "source_url": item.url if hasattr(item, 'url') else None,
                "item_id": item.id  # Include item ID for reference
            })
            
        print(f"DEBUG - get_stored_menu: Returning {len(menu_item_list)} formatted menu items")
        
        # Add more diagnostic info if no menu items were found
        if not menu_items:
            try:
                # Do a direct SQL query as a last resort
                from sqlalchemy import text
                result = db.execute(text(f"SELECT COUNT(*) FROM competitor_items WHERE competitor_name = '{competitor_name}'"))
                count = result.scalar()
                print(f"DEBUG - get_stored_menu: Raw SQL count for competitor '{competitor_name}': {count}")
                
                if count > 0:
                    # If items exist but weren't returned by our query, try a direct fetch
                    print(f"DEBUG - get_stored_menu: Items exist but weren't returned by our query, checking database schema")
                    # Try to get column names from table
                    columns_result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='competitor_items'"))
                    columns = [row[0] for row in columns_result]
                    print(f"DEBUG - get_stored_menu: CompetitorItem columns: {columns}")
                    
                    # Get a sample item
                    sample_result = db.execute(text(f"SELECT * FROM competitor_items WHERE competitor_name = '{competitor_name}' LIMIT 1"))
                    sample = sample_result.first()
                    if sample:
                        print(f"DEBUG - get_stored_menu: Sample item keys: {sample.keys()}")
            except Exception as e:
                print(f"DEBUG - get_stored_menu: Error checking schema: {str(e)}")
                # Continue despite errors, don't block the response
        
        
        return {
            "success": True,
            "competitor": {
                "name": competitor_data.get("name", ""),
                "address": competitor_data.get("address", ""),
                "category": competitor_data.get("category", ""),
                "report_id": competitor_report.id
            },
            "menu_items": menu_item_list,
            "batch": selected_batch
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving stored menu: {str(e)}")


@gemini_competitor_router.post("/fetch-menu/{report_id}")
async def fetch_competitor_menu(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Dispatch a background task to fetch competitor menu
    """
    try:
        # Import the task function locally to avoid circular imports
        from tasks import fetch_competitor_menu_task
        
        # Get competitor details first
        competitor_report = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.id == report_id,
            models.CompetitorReport.user_id == current_user.id
        ).first()
        
        if not competitor_report:
            raise HTTPException(status_code=404, detail="Competitor report not found")
        
        competitor_data = competitor_report.competitor_data
        competitor_name = competitor_data.get("name")
        
        # Update the metadata to store task status
        if not competitor_report.metadata or not isinstance(competitor_report.metadata, dict):
            competitor_report.metadata = {}
        
        # Set initial task status
        competitor_report.metadata["menu_fetch_status"] = "queued"
        db.commit()
        
        # Launch the Celery task
        task = fetch_competitor_menu_task.delay(report_id, current_user.id)
        
        # Store the task ID in the competitor report
        competitor_report.metadata["menu_fetch_task_id"] = task.id
        db.commit()
        
        return {
            "success": True,
            "message": "Menu fetch task has been queued",
            "task_id": task.id,
            "competitor_name": competitor_name,
            "report_id": report_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting menu fetch task: {str(e)}")


@gemini_competitor_router.get("/fetch-menu-status/{report_id}")
async def fetch_menu_status(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Check the status of a menu fetch task
    """
    try:
        # Import the task function locally to avoid circular imports
        from tasks import get_menu_fetch_status_task
        
        competitor_report = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.id == report_id,
            models.CompetitorReport.user_id == current_user.id
        ).first()
        
        if not competitor_report:
            raise HTTPException(status_code=404, detail="Competitor report not found")
        
        # Get task status from metadata
        metadata = competitor_report.metadata or {}
        status = metadata.get("menu_fetch_status", "not_started")
        task_id = metadata.get("menu_fetch_task_id")
        error = metadata.get("menu_fetch_error")
        items_count = metadata.get("menu_items_count", 0)
        
        # Check Celery task status if we have a task ID
        task_status = "unknown"
        if task_id:
            result = AsyncResult(task_id)
            task_status = result.status
        
        # If the task is complete, update the UI with menu items count
        if status == "completed":
            # Get the menu batches for the competitor
            batches_response = await get_competitor_menu_batches(report_id, db, current_user)
            batches = batches_response.get("batches", [])
            latest_batch = batches[0] if batches else None
            
            return {
                "success": True,
                "status": status,
                "celery_status": task_status,
                "menu_items_count": items_count,
                "competitor_name": competitor_report.competitor_data.get("name", ""),
                "latest_batch": latest_batch
            }
        
        return {
            "success": True,
            "status": status,
            "celery_status": task_status,
            "error": error,
            "competitor_name": competitor_report.competitor_data.get("name", "")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking menu fetch status: {str(e)}")


@gemini_competitor_router.post("/synchronous-fetch-menu/{report_id}")
async def synchronous_fetch_menu(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Full synchronous process endpoint that combines all three steps (legacy method):
    1. Find URLs
    2. Extract menu from each URL
    3. Consolidate data and save to database
    """
    try:
        # Get competitor details first
        # Check if the competitor has a specified menu URL
        competitor_report = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.id == report_id,
            models.CompetitorReport.user_id == current_user.id
        ).first()
        
        if not competitor_report:
            raise HTTPException(status_code=404, detail="Competitor report not found")
        
        competitor_data = competitor_report.competitor_data
        print(f"DEBUG: competitor_data = {competitor_data}")
        competitor_name = competitor_data.get("name")
        competitor_category = competitor_data.get("category", "")
        direct_menu_url = competitor_data.get("menu_url")
        print(f"DEBUG: direct_menu_url = {direct_menu_url}")
        
        # If a direct menu URL is provided, use that instead of searching
        if direct_menu_url:
            print(f"Using direct menu URL: {direct_menu_url}")
            source_urls = [{"url": direct_menu_url, "confidence": "high"}]
            competitor = {
                "name": competitor_name,
                "category": competitor_category,
                "report_id": report_id
            }
        else:
            # STEP 1: Find menu URLs if no direct URL is provided
            urls_response = await find_competitor_menu_urls(report_id, db, current_user)
            
            if not urls_response.get("success") or not urls_response.get("urls"):
                return {
                    "success": False,
                    "error": "Could not find any online menu sources for this competitor",
                    "competitor": urls_response.get("competitor"),
                    "menu_items": []
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
                
            url_items_response = await extract_menu_from_url(
                url=url,
                competitor_name=competitor_name,
                competitor_category=competitor_category
            )
            
            if url_items_response.get("success") and url_items_response.get("menu_items"):
                all_menu_items.extend(url_items_response.get("menu_items"))
            
        if not all_menu_items:
            return {
                "success": False,
                "error": "No menu items could be extracted from the found URLs",
                "competitor": competitor,
                "menu_items": []
            }
            
        # STEP 3: Consolidate menu data and save to database
        consolidated_response = await consolidate_menu(
            report_id=report_id,
            menu_items=all_menu_items,
            db=db,
            current_user=current_user
        )
        
        return consolidated_response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in menu fetch process: {str(e)}")

@gemini_competitor_router.post("/manually-add")
async def add_competitor_manually(
    competitor_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Manually add a competitor to the database
    """
    try:
        print("DEBUG - Received competitor data:", competitor_data)
        
        # Validate required fields
        name = competitor_data.get("name")
        address = competitor_data.get("address", "")
        category = competitor_data.get("category")
        distance_km = competitor_data.get("distance_km")
        
        print(f"DEBUG - Extracted fields: name={name}, address={address}, category={category}")
        
        # Only name and category are truly required - address can be empty
        if not name or not category:
            raise HTTPException(status_code=400, detail="Name and category are required")
        
        # Use a default address if empty
        if not address or address.strip() == "":
            address = "Address not provided"
            
        # Extract menu_url from the data if it exists
        menu_url = competitor_data.get("menu_url")
        
        # Check if there are menu items from LLM extraction 
        # Looking for JSON-encoded menu items
        extracted_menu_items = []
        metadata = {}
        
        if menu_url and ('[' in menu_url and ']' in menu_url):
            # This might be JSON with menu items from the LLM
            try:
                # Try to extract menu items from the menu_url field
                # The frontend encodes extracted items here when using manual setup
                first_bracket = menu_url.find('[')
                last_bracket = menu_url.rfind(']') + 1
                if first_bracket >= 0 and last_bracket > first_bracket:
                    json_str = menu_url[first_bracket:last_bracket]
                    extracted_menu_items = json.loads(json_str)
                    
                    # Store original menu content in metadata if we parsed menu items
                    metadata["extracted_menu_items_count"] = len(extracted_menu_items)
                    # Set a more appropriate menu_url value
                    menu_url = f"Manually added with {len(extracted_menu_items)} menu items"
            except json.JSONDecodeError:
                # Not valid JSON, probably a regular URL or text
                pass
                
        # Try to get menu items directly if they were passed separately
        menu_items_data = competitor_data.get("menu_items", [])
        if isinstance(menu_items_data, list) and len(menu_items_data) > 0:
            extracted_menu_items = menu_items_data
            metadata["extracted_menu_items_count"] = len(extracted_menu_items)
        
        # Create a competitor report to store all data
        competitor_report = models.CompetitorReport(
            user_id=current_user.id,
            summary=f"Manually added competitor: {name}",
            competitor_data={
                "name": name,
                "address": address,
                "category": category,
                "distance_km": distance_km if distance_km else None,
                "menu_url": menu_url if menu_url else None
            },
            metadata=metadata,
            created_at=datetime.now(),
            is_selected=True  # Manually added competitors are automatically selected
        )
        db.add(competitor_report)
        
        # Generate a batch ID for the menu items
        import uuid
        batch_id = f"manual_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
        sync_timestamp = datetime.now()
        
        # Process extracted menu items if available
        print(f"DEBUG - Processing {len(extracted_menu_items)} menu items")
        if extracted_menu_items:
            # First, check if we already have menu items for this competitor with this batch_id
            # to avoid duplicate entries
            existing_items_count = db.query(models.CompetitorItem).filter(
                models.CompetitorItem.competitor_name == name
            ).count()
            
            print(f"DEBUG - Found {existing_items_count} existing menu items for competitor '{name}'")
            
            if existing_items_count > 0:
                print("DEBUG - This competitor already has menu items, checking if we should update instead of add")
                # If there are existing items with the same batch_id or recent timestamp,
                # we'll just log and skip to avoid duplicates
                recent_items = db.query(models.CompetitorItem).filter(
                    models.CompetitorItem.competitor_name == name,
                    models.CompetitorItem.sync_timestamp >= datetime.now() - timedelta(minutes=10)
                ).all()
                
                if recent_items:
                    print(f"DEBUG - Found {len(recent_items)} recent items added in the last 10 minutes")
                    print("DEBUG - Skipping menu item creation to avoid duplicates")
                    # We'll return success since we already have the items
                    return {
                        "success": True,
                        "competitor": {
                            "name": name,
                            "address": address,
                            "category": category,
                            "report_id": competitor_report.id
                        },
                        "menu_items": [],  # Empty list since we're not creating new ones
                        "message": "Competitor successfully added. Menu items already exist."
                    }
            
            items_saved = 0
            # Create a set to track items we've already processed to avoid duplicates
            processed_items = set()
            
            for item in extracted_menu_items:
                try:
                    # Log the item we're processing
                    print(f"DEBUG - Processing menu item: {item}")
                    
                    # Create a key for this item to detect duplicates in the same batch
                    item_name = str(item.get("item_name", "") or "")
                    if not item_name.strip():
                        item_name = "Unnamed Item"
                    
                    item_price = item.get("price", 0)
                    item_key = f"{item_name}:{item_price}"
                    
                    # Skip if we've seen this item already
                    if item_key in processed_items:
                        print(f"DEBUG - Skipping duplicate item: {item_key}")
                        continue
                    
                    # Add to our processed set
                    processed_items.add(item_key)
                    
                    # Handle null prices by converting to 0.0
                    price = item.get("price")
                    price_float = 0.0
                    
                    if price is not None:
                        try:
                            price_float = float(price)
                        except (ValueError, TypeError):
                            print(f"Invalid price format: {price}, defaulting to 0.0")
                    
                    # Get item name and category with defaults
                    item_name = str(item.get("item_name", "") or "")
                    if not item_name.strip():
                        item_name = "Unnamed Item"
                    
                    item_category = str(item.get("category") or category or "other")
                    
                    # Check if CompetitorItem has user_id attribute
                    has_user_id = hasattr(models.CompetitorItem, 'user_id')
                    print(f"DEBUG - add_competitor_manually: CompetitorItem has user_id field: {has_user_id}")
                    
                    # CompetitorItem model doesn't have user_id, price_currency, or source fields
                    # Create with only the fields that exist in the model
                    menu_item = models.CompetitorItem(
                        competitor_name=name,
                        item_name=item_name,
                        description=item.get("description", ""),
                        category=item_category,
                        price=price_float,
                        url=address,  # Using address as reference
                        batch_id=batch_id,
                        sync_timestamp=sync_timestamp
                    )
                    
                    db.add(menu_item)
                    items_saved += 1
                except Exception as item_error:
                    print(f"Error processing menu item: {str(item_error)}")
                    # Continue with the next item even if this one fails
            
            print(f"DEBUG - Successfully added {items_saved}/{len(extracted_menu_items)} menu items to database")
        else:
            # If no menu items, create a placeholder entry
            # CompetitorItem doesn't have user_id field, so create without it
            competitor_item = models.CompetitorItem(
                competitor_name=name,
                item_name="General",  # Placeholder
                category=category,
                price=0.0,  # Placeholder
                description=address,
                batch_id=batch_id,
                sync_timestamp=sync_timestamp
            )
            
            db.add(competitor_item)
        
        # Commit all changes
        db.commit()
        
        # Return the newly created competitor
        return {
            "success": True,
            "competitor": {
                "name": name,
                "address": address,
                "category": category,
                "distance_km": distance_km,
                "report_id": competitor_report.id,
                "created_at": competitor_report.created_at,
                "menu_items_count": len(extracted_menu_items) if extracted_menu_items else 0
            }
        }
    except Exception as e:
        db.rollback()
        print(f"ERROR in add_competitor_manually: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error adding competitor: {str(e)}")

@gemini_competitor_router.delete("/competitors/{report_id}")
async def delete_competitor(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Delete a competitor by report_id
    """
    try:
        # Find the competitor report
        competitor_report = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.id == report_id,
            models.CompetitorReport.user_id == current_user.id
        ).first()
        
        if not competitor_report:
            raise HTTPException(status_code=404, detail="Competitor not found or you don't have permission to delete it")
        
        # Get competitor name for cleanup
        competitor_name = None
        if competitor_report.competitor_data and isinstance(competitor_report.competitor_data, dict):
            competitor_name = competitor_report.competitor_data.get("name")
        
        # Delete related competitor items if name is available
        if competitor_name:
            # Try to delete matching CompetitorItems
            try:
                # If CompetitorItem has user_id field
                db.query(models.CompetitorItem).filter(
                    models.CompetitorItem.competitor_name == competitor_name,
                    models.CompetitorItem.user_id == current_user.id
                ).delete()
            except:
                # If no user_id field, just delete by name
                # This is less secure but maintains compatibility
                db.query(models.CompetitorItem).filter(
                    models.CompetitorItem.competitor_name == competitor_name
                ).delete()
        
        # Delete the report itself
        db.delete(competitor_report)
        db.commit()
        
        return {"success": True, "message": "Competitor deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting competitor: {str(e)}")

@gemini_competitor_router.put("/{report_id}")
async def update_competitor(
    report_id: int,
    competitor_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update a competitor's information including selection status
    """
    try:
        # Find the competitor report
        competitor_report = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.id == report_id,
            models.CompetitorReport.user_id == current_user.id
        ).first()
        
        if not competitor_report:
            raise HTTPException(status_code=404, detail="Competitor not found")
        
        # Update is_selected flag if provided
        if 'selected' in competitor_data:
            competitor_report.is_selected = bool(competitor_data.get('selected'))
            print(f"Updated competitor {competitor_report.id} selection status to {competitor_report.is_selected}")
        
        # Validate required fields
        name = competitor_data.get("name")
        address = competitor_data.get("address")
        category = competitor_data.get("category")
        distance_km = competitor_data.get("distance_km")
        menu_url = competitor_data.get("menu_url")  # Get menu_url from request data
        
        # Update competitor_data in the CompetitorReport
        current_data = competitor_report.competitor_data
        if not isinstance(current_data, dict):
            current_data = {}
            
        # Only update fields that are provided
        if name:
            current_data["name"] = name
        if address:
            current_data["address"] = address
        if category:
            current_data["category"] = category
        
        current_data["distance_km"] = distance_km if distance_km is not None else current_data.get("distance_km")
        
        # Make sure menu_url is explicitly saved to competitor_data
        if menu_url is not None:
            current_data["menu_url"] = menu_url
        
        competitor_report.competitor_data = current_data
        
        # Explicitly mark the JSON field as modified for SQLAlchemy
        attributes.flag_modified(competitor_report, "competitor_data")
        
        # Update summary
        competitor_report.summary = f"Updated competitor: {current_data.get('name')}"
        
        db.commit()
        
        # Also update CompetitorItem entries if they exist
        competitor_items = db.query(models.CompetitorItem).filter(
            models.CompetitorItem.competitor_name == current_data.get('name')
        ).all()
        
        if competitor_items:
            for item in competitor_items:
                item.competitor_name = current_data.get('name')
            
            print(f"Updated {len(competitor_items)} competitor items to match new name")
            # No need for another commit as we'll do one final commit below
        
        # Final commit for all changes
        db.commit()
        
        return {
            "success": True,
            "message": "Competitor updated successfully",
            "competitor": {
                "name": current_data.get("name"),
                "address": current_data.get("address"),
                "category": current_data.get("category"),
                "distance_km": current_data.get("distance_km"),
                "menu_url": current_data.get("menu_url"),
                "report_id": competitor_report.id,
                "created_at": competitor_report.created_at,
                "selected": competitor_report.is_selected
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating competitor: {str(e)}")

@gemini_competitor_router.post("/bulk-select")
async def bulk_select_competitors(
    selection_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Set selection status for multiple competitors at once
    """
    try:
        # Extract selected competitor IDs and unselected competitor IDs
        selected_ids = selection_data.get("selected_ids", [])
        unselected_ids = selection_data.get("unselected_ids", [])
        
        print(f"Setting selected status for competitors: {selected_ids}")
        print(f"Setting unselected status for competitors: {unselected_ids}")
        
        # Mark selected competitors
        if selected_ids:
            db.query(models.CompetitorReport).filter(
                models.CompetitorReport.id.in_(selected_ids),
                models.CompetitorReport.user_id == current_user.id
            ).update({models.CompetitorReport.is_selected: True}, synchronize_session=False)
        
        # Mark unselected competitors
        if unselected_ids:
            db.query(models.CompetitorReport).filter(
                models.CompetitorReport.id.in_(unselected_ids),
                models.CompetitorReport.user_id == current_user.id
            ).update({models.CompetitorReport.is_selected: False}, synchronize_session=False)
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Updated selection status for {len(selected_ids) + len(unselected_ids)} competitors"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating competitor selection: {str(e)}")
        return {
            "success": True,
            "competitor": {
                "name": name,
                "address": address,
                "category": category,
                "distance_km": distance_km,
                "menu_url": menu_url,
                "report_id": competitor_report.id,
                "created_at": competitor_report.created_at
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating competitor: {str(e)}")

@gemini_competitor_router.get("/competitors")
async def get_competitors(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all competitors associated with the current user
    """
    try:
        # Get only selected competitor reports for this user
        competitor_reports = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.user_id == current_user.id,
            models.CompetitorReport.is_selected == True  # Only fetch selected competitors
        ).order_by(desc(models.CompetitorReport.created_at)).all()
        
        # Extract competitor data from reports
        competitors = []
        for report in competitor_reports:
            competitor_data = report.competitor_data
            if isinstance(competitor_data, dict) and 'name' in competitor_data:
                competitors.append({
                    "name": competitor_data.get('name'),
                    "address": competitor_data.get('address'),
                    "category": competitor_data.get('category'),
                    "distance_km": competitor_data.get('distance_km'),
                    "menu_url": competitor_data.get('menu_url'),  # Include menu_url in response
                    "report_id": report.id,
                    "created_at": report.created_at
                })
        
        return {
            "success": True,
            "competitors": competitors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching competitors: {str(e)}")

@gemini_competitor_router.post("/search", response_model=Dict[str, Any])
async def search_competitors(
    search_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Extract save_to_db from the request body
    save_to_db = search_data.get("save_to_db", False)
    """
    Search for nearby competitors based on business type and location using Google Gemini API
    """
    # Validate input
    business_type = search_data.get("business_type")
    location = search_data.get("location")
    
    if not business_type or not location:
        raise HTTPException(status_code=400, detail="Business type and location are required")
        
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")
    
    try:
        # Create Gemini model
        model = genai.GenerativeModel('gemini-2.5-pro-preview-06-05')
        
        # Craft the prompt for Gemini
        prompt = f"""
        Find nearby competitors for a {business_type} business located at {location}.
        
        Return ONLY a valid JSON array containing objects with the following properties:
        1. name: The competitor's business name
        2. address: The full address of the competitor
        3. category: The business category (similar to {business_type})
        4. distance_km: Estimated distance in kilometers (if available)
        
        Format should be strictly as follows:
        [
          {{
            "name": "Competitor Name",
            "address": "123 Business St, City, State, Zip",
            "category": "Business Category",
            "distance_km": 1.5
          }},
          ...
        ]
        
        Return only the JSON array, no additional text or explanations.
        """
        
        # Generate response from Gemini
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Extract JSON from the response
        # Sometimes Gemini adds markdown code block markers
        if "```json" in response_text:
            json_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_text = response_text.split("```")[1].strip()
        else:
            json_text = response_text.strip()
            
        competitors_data = json.loads(json_text)
        
        # Process competitors
        processed_competitors = []
        for competitor in competitors_data:
            processed_competitor = {
                "name": competitor['name'],
                "address": competitor['address'],
                "category": competitor['category'],
                "distance_km": competitor.get('distance_km', None)
            }
            
            # Check if we should save this competitor to database
            should_save = False
            if save_to_db:
                # If frontend provided a list of selected competitors, only save those
                selected_competitors = search_data.get("selected_competitors", [])
                if selected_competitors and isinstance(selected_competitors, list):
                    # Only save if this competitor's name is in the selected list
                    if competitor['name'] in selected_competitors:
                        should_save = True
                        print(f"Saving selected competitor: {competitor['name']}")
                    else:
                        print(f"Skipping unselected competitor: {competitor['name']}")
                else:
                    # If no selection list provided but save_to_db is True, save all
                    should_save = True
            
            # Only save to database if should_save is True
            if should_save:
                # Create a competitor report to store all data
                competitor_report = models.CompetitorReport(
                    user_id=current_user.id,
                    summary=f"Nearby competitor: {competitor['name']}",
                    competitor_data=competitor,
                    created_at=datetime.utcnow()
                )
                db.add(competitor_report)
                
                # Extract the ID after flush so we can return it
                db.flush()
                processed_competitor["report_id"] = competitor_report.id
                
                # Also create CompetitorItem entries for any known pricing
                try:
                    competitor_item = models.CompetitorItem(
                        user_id=current_user.id,  # Associate with current user
                        competitor_name=competitor['name'],
                        item_name="General",  # Placeholder
                        category=competitor['category'],
                        price=0.0,  # Placeholder
                        description=competitor['address']
                    )
                except Exception as e:
                    # If user_id field doesn't exist, create without it
                    competitor_item = models.CompetitorItem(
                        competitor_name=competitor['name'],
                        item_name="General",  # Placeholder
                        category=competitor['category'],
                        price=0.0,  # Placeholder
                        description=competitor['address']
                    )
                db.add(competitor_item)
            
            processed_competitors.append(processed_competitor)
        
        # Only commit if we actually saved to the database
        if save_to_db:
            db.commit()
        
        return {
            "success": True,
            "competitors": processed_competitors
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching for competitors: {str(e)}")
