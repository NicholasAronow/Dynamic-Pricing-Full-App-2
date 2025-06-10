from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session, attributes
from sqlalchemy import desc
from typing import List, Dict, Any
from database import get_db
import models, schemas
from auth import get_current_user
import os
import json
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
# Load environment variables
load_dotenv()

# Configure Google Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

gemini_competitor_router = APIRouter()

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
4. Include the 3 MOST RELIABLE sources, not an exhaustive list
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
                url=competitor_address  # Using address as a reference point
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


@gemini_competitor_router.get("/get-stored-menu/{report_id}")
async def get_stored_competitor_menu(
    report_id: int,
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
            
        # Get stored menu items (using CompetitorItem model)
        menu_items = db.query(models.CompetitorItem).filter(
            models.CompetitorItem.competitor_name == competitor_name
        ).all()
        
        # Convert to response format
        menu_item_list = []
        for item in menu_items:
            menu_item_list.append({
                "item_name": item.item_name,
                "category": item.category,
                "description": item.description,
                "price": item.price,
                "price_currency": "USD",  # Default since CompetitorItem might not have this field
                "availability": "Available",  # Default since CompetitorItem might not have this field
                "source_confidence": "medium",  # Default since CompetitorItem might not have this field
                "source_url": item.url if hasattr(item, 'url') else None
            })
        
        return {
            "success": True,
            "competitor": {
                "name": competitor_data.get("name", ""),
                "address": competitor_data.get("address", ""),
                "category": competitor_data.get("category", ""),
                "report_id": competitor_report.id
            },
            "menu_items": menu_item_list
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
    Full process endpoint that combines all three steps:
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
        # Validate required fields
        name = competitor_data.get("name")
        address = competitor_data.get("address")
        category = competitor_data.get("category")
        distance_km = competitor_data.get("distance_km")
        
        if not name or not address or not category:
            raise HTTPException(status_code=400, detail="Name, address, and category are required")
            
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
            created_at=datetime.utcnow()
        )
        db.add(competitor_report)
        
        # Also create CompetitorItem entry
        try:
            competitor_item = models.CompetitorItem(
                user_id=current_user.id,
                competitor_name=name,
                item_name="General",  # Placeholder
                category=category,
                price=0.0,  # Placeholder
                description=address
            )
        except Exception as e:
            # If user_id field doesn't exist, create without it
            competitor_item = models.CompetitorItem(
                competitor_name=name,
                item_name="General",  # Placeholder
                category=category,
                price=0.0,  # Placeholder
                description=address
            )
        
        db.add(competitor_item)
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
                "created_at": competitor_report.created_at
            }
        }
    except Exception as e:
        db.rollback()
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

@gemini_competitor_router.put("/competitors/{report_id}")
async def update_competitor(
    report_id: int,
    competitor_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update a competitor's information
    """
    try:
        # Find the competitor report
        competitor_report = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.id == report_id,
            models.CompetitorReport.user_id == current_user.id
        ).first()
        
        if not competitor_report:
            raise HTTPException(status_code=404, detail="Competitor not found or you don't have permission to update it")
        
        # Validate required fields
        name = competitor_data.get("name")
        address = competitor_data.get("address")
        category = competitor_data.get("category")
        distance_km = competitor_data.get("distance_km")
        menu_url = competitor_data.get("menu_url")  # Get menu_url from request data
        
        print(f"DEBUG UPDATE: Received competitor_data: {competitor_data}")
        print(f"DEBUG UPDATE: Menu URL from request: {menu_url}")
        
        if not name or not address or not category:
            raise HTTPException(status_code=400, detail="Name, address, and category are required")
        
        # Update competitor_data in the CompetitorReport
        current_data = competitor_report.competitor_data
        if not isinstance(current_data, dict):
            current_data = {}
            
        current_data["name"] = name
        current_data["address"] = address
        current_data["category"] = category
        current_data["distance_km"] = distance_km if distance_km else None
        
        # Make sure menu_url is explicitly saved to competitor_data
        if menu_url:
            current_data["menu_url"] = menu_url
        else:
            # Remove menu_url if it's being set to None/empty
            if "menu_url" in current_data:
                del current_data["menu_url"]
        
        # Debug before setting competitor_data
        print(f"DEBUG UPDATE: Before setting data: {current_data}")
        
        competitor_report.competitor_data = current_data
        
        # Explicitly mark the JSON field as modified for SQLAlchemy
        attributes.flag_modified(competitor_report, "competitor_data")
        
        competitor_report.summary = f"Updated competitor: {name}"
        
        # Also update CompetitorItem entries if they exist
        competitor_items = db.query(models.CompetitorItem).filter(
            models.CompetitorItem.competitor_name == current_data.get("name")
        ).all()
        
        for item in competitor_items:
            item.competitor_name = name
            item.category = category
        
        db.commit()
        
        # Debug: Check the actual saved data in the database
        updated_competitor = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.id == report_id
        ).first()
        print(f"DEBUG UPDATE: Data saved in DB: {updated_competitor.competitor_data}")
        
        # Return the updated competitor
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
        # Get competitor reports for this user
        competitor_reports = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.user_id == current_user.id
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
    search_data: Dict[str, str] = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
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
        
        # Save competitors to database
        saved_competitors = []
        for competitor in competitors_data:
            # Create a competitor report to store all data
            competitor_report = models.CompetitorReport(
                user_id=current_user.id,
                summary=f"Nearby competitor: {competitor['name']}",
                competitor_data=competitor,
                created_at=datetime.utcnow()
            )
            db.add(competitor_report)
            
            # Also create CompetitorItem entries for any known pricing
            # We might not have pricing info from this search, but the schema is prepared for future use
            # Try to get user_id field from the model if it exists
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
            
            saved_competitors.append({
                "name": competitor['name'],
                "address": competitor['address'],
                "category": competitor['category'],
                "distance_km": competitor.get('distance_km', None)
            })
        
        db.commit()
        
        return {
            "success": True,
            "competitors": saved_competitors
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching for competitors: {str(e)}")
