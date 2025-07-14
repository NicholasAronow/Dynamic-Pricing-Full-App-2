from celery_app import celery_app
from typing import Dict, Any, List
from sqlalchemy.orm import Session
import models
from database import SessionLocal
import json
import asyncio
import os
import logging
import re
from openai import OpenAI
from dotenv import load_dotenv
# Import datetime at the module level since it's used in multiple places
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
clients = {}
if OPENAI_API_KEY:
    try:
        clients['openai'] = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client in tasks.py: {e}")

# Explicitly register task with a unique name
@celery_app.task(name="adaptiv.tasks.extract_menu_data_task", bind=True)
def extract_menu_data_task(self, menu_content: str) -> Dict[str, Any]:
    """
    Celery task to extract restaurant details and menu items from menu content
    using OpenAI LLM. Returns structured data for restaurant info and menu items.
    
    Args:
        menu_content: Raw text content from a restaurant menu
        
    Returns:
        Dictionary with restaurant_info and menu_items
    """
    try:
        logger.info(f"Starting menu extraction task {self.request.id}")
        
        # Check if OpenAI client is available
        if 'openai' not in clients:
            raise ValueError("OpenAI client not properly initialized")
            
        client = clients['openai']
        
        # Create prompt for extraction
        prompt = f"""TASK: Extract restaurant information and ALL menu items from the following menu content.

MENU CONTENT:
{menu_content}

RETURN DATA AS JSON with two parts:

1. Restaurant information:
{{
  "restaurant_name": "Name of the restaurant",
  "category": "Main category like restaurant, cafe, bakery, etc.",
  "address": "Full address if found in the content"  
}}

2. Menu items as an array:
[
  {{
    "item_name": "Exact menu item name",
    "category": "appetizer|main_course|dessert|beverage|side|special",
    "description": "Item description or null if none",
    "price": 12.99,
    "price_currency": "USD"
  }}
]

RETURN YOUR RESPONSE IN THIS FORMAT:
{{
  "restaurant_info": {{ Restaurant info object }},
  "menu_items": [ Array of menu items ]
}}

RULES:
1. Extract ONLY information explicitly found in the menu content
2. For restaurant_name, if multiple restaurant names appear, choose the most prominent one
3. For address, concatenate all address components found
4. Extract as many menu items as possible with their exact prices
5. Do not fabricate or guess information
6. If certain information is not available, use null values
7. Return an empty array for menu_items if none are found

RETURN ONLY THE JSON OBJECT, no explanations."""
        
        # Generate response using OpenAI
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are a specialized AI assistant that extracts structured data from restaurant menu content. Your outputs should be clean JSON objects only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Get the response text
        response_text = response.choices[0].message.content
        
        # Clean the response text in case there are any markdown code blocks
        if "```json" in response_text:
            extracted_json = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            extracted_json = response_text.split("```")[1].strip()
        else:
            extracted_json = response_text.strip()
        
        # Parse the JSON
        result = json.loads(extracted_json)
        
        logger.info(f"Successfully extracted menu data in task {self.request.id}")
        return {
            "success": True,
            "restaurant_info": result.get("restaurant_info", {}),
            "menu_items": result.get("menu_items", [])
        }
        
    except Exception as e:
        logger.error(f"Error in menu extraction task {self.request.id}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "restaurant_info": {},
            "menu_items": []
        }

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
        print(f"DEBUG: Starting fetch_competitor_menu_task with report_id={report_id}, user_id={user_id}")
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
        print(f"DEBUG: Querying database for CompetitorReport with id={report_id} and user_id={user_id}")
        try:
            # First check if the report exists at all, regardless of user_id
            any_report = db.query(models.CompetitorReport).filter(
                models.CompetitorReport.id == report_id
            ).first()
            
            if any_report:
                print(f"DEBUG: Found a report with id={report_id}, but it belongs to user_id={any_report.user_id}")
            else:
                print(f"DEBUG: No report found with id={report_id} at all")
                
            # Check if any reports exist for this user
            user_reports = db.query(models.CompetitorReport).filter(
                models.CompetitorReport.user_id == user_id
            ).all()
            
            print(f"DEBUG: User {user_id} has {len(user_reports)} reports in the database")
            if user_reports:
                print(f"DEBUG: Available report IDs for user {user_id}: {[r.id for r in user_reports]}")
            
            # Now try the original query
            competitor_report = db.query(models.CompetitorReport).filter(
                models.CompetitorReport.id == report_id,
                models.CompetitorReport.user_id == user_id
            ).first()
            
            print(f"DEBUG: Query result for specific report: {competitor_report}")
        except Exception as e:
            print(f"DEBUG: Exception during database query: {str(e)}")
            raise
        
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


@celery_app.task(name="run_dynamic_pricing_analysis_task")
def run_dynamic_pricing_analysis_task(user_id: int, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Celery task to run the dynamic pricing agent analysis in the background using AggregatePricingAgent
    
    Workflow:
    1. Initialize the AggregatePricingAgent
    2. Run the analysis process asynchronously
    3. Process the results and return them in the expected format
    """
    try:
        print(f"DEBUG: Starting run_dynamic_pricing_analysis_task for user_id={user_id}")
        # Import necessary modules
        import sys
        import os
        import asyncio
        
        # Add the current directory to sys.path if not already there
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
            
        # Import the AggregatePricingAgent
        from dynamic_pricing_agents.agents.aggregate_pricing_agent import AggregatePricingAgent
        
        # Create a new database session
        db = SessionLocal()
        
        # Initialize the aggregate pricing agent
        aggregate_agent = AggregatePricingAgent()
        
        # Fetch business context information from the database for this user
        try:
            # Get the user and their associated business profile
            user = db.query(models.User).filter(models.User.id == user_id).first()
            business_profile = db.query(models.BusinessProfile).filter(models.BusinessProfile.user_id == user_id).first()
            
            # Prepare business context
            business_context = {
                "business_name": business_profile.business_name if business_profile else "Your Business",
                "industry": business_profile.industry if business_profile else "Food Service",
                # Use city and state as location
                "location": f"{business_profile.city}, {business_profile.state}" if business_profile and business_profile.city and business_profile.state else "New York",
                "company_size": business_profile.company_size if business_profile else "Small Business"
            }
            
            print(f"DEBUG: Using business context: {business_context}")
            
        except Exception as e:
            print(f"WARNING: Could not fetch business context from DB: {str(e)}")
            business_context = {
                "business_name": "Your Business",
                "industry": "Food Service",
                "location": "New York",
                "company_size": "Small Business"
            }
        
        # Prepare the context for the agent
        context = {
            "user_id": user_id,
            "db": db,
            "parameters": parameters or {},
            # Pass business context directly and also as individual fields
            "business_context": business_context,
            "business_name": business_context["business_name"],
            "industry": business_context["industry"],
            "location": business_context["location"],
            "company_size": business_context["company_size"]
        }
        
        # Create a dictionary to track agent statuses
        agent_statuses = [
            {"name": "Data Collection", "status": "running", "lastRun": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            {"name": "Market Analysis", "status": "idle", "lastRun": ""},
            {"name": "Pricing Strategy", "status": "idle", "lastRun": ""},
            {"name": "Performance Monitor", "status": "idle", "lastRun": ""},
            {"name": "Experimentation", "status": "idle", "lastRun": ""}
        ]
        
        # Set up event loop for async execution
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Define an async function to update status and run the agent
        async def run_with_status_updates():
            # Update status for Data Collection
            agent_statuses[0]["status"] = "running"
            
            # Start the analysis process
            print("DEBUG: Running AggregatePricingAgent analysis")
            results = await aggregate_agent.process(context)
            
            # Update all agent statuses to completed
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for status in agent_statuses:
                status["status"] = "completed"
                status["lastRun"] = timestamp
                
            return results
        
        # Run the async function and get the results
        results = loop.run_until_complete(run_with_status_updates())
        loop.close()
        
        # Generate unique batch ID for this set of recommendations
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}"
        
        # Extract pricing recommendations
        pricing_recommendations = results.get("pricing_recommendations", [])
        
        # Debug information
        print(f"DEBUG: Received {len(pricing_recommendations)} recommendations from agent")
        if len(pricing_recommendations) > 0:
            print(f"DEBUG: Sample recommendation: {pricing_recommendations[0]}")
        
        # Format the analysis results for the frontend
        analysis_results = {
            "executive_summary": {
                "overall_status": "completed",
                "revenue_trend": "improving" if results.get("success") else "neutral",
                "key_opportunities": [],
                "immediate_actions": [],
                "risk_factors": []
            },
            "consolidated_recommendations": pricing_recommendations,
            "next_steps": [
                {"step": 1, "action": "Review pricing recommendations", "expected_impact": "Increased revenue", "timeline": "Immediate"},
                {"step": 2, "action": "Implement price changes", "expected_impact": "Improved profitability", "timeline": "1-2 weeks"},
                {"step": 3, "action": "Monitor results", "expected_impact": "Data-driven decisions", "timeline": "Ongoing"}
            ]
        }
        
        # Save pricing recommendations to database
        print(f"DEBUG: Saving {len(pricing_recommendations)} recommendations to database with batch_id {batch_id}")
        
        try:
            # Create recommendations in database
            for rec in pricing_recommendations:
                # Parse string price values to float
                try:
                    # Handle string price values with dollar signs (e.g. '$2.75')
                    if isinstance(rec.get('current_price'), str):
                        current_price = float(rec.get('current_price', '0').replace('$', '').strip())
                    else:
                        current_price = float(rec.get('current_price', 0))
                    
                    # The agent uses 'suggested_price' instead of 'recommended_price'
                    if 'suggested_price' in rec:
                        if isinstance(rec.get('suggested_price'), str):
                            recommended_price = float(rec.get('suggested_price', '0').replace('$', '').strip())
                        else:
                            recommended_price = float(rec.get('suggested_price', 0))
                    else:
                        if isinstance(rec.get('recommended_price'), str):
                            recommended_price = float(rec.get('recommended_price', '0').replace('$', '').strip())
                        else:
                            recommended_price = float(rec.get('recommended_price', 0))
                    
                    # Calculate price changes
                    price_change_amount = recommended_price - current_price
                    price_change_percent = (price_change_amount / current_price * 100) if current_price > 0 else 0
                    
                    print(f"DEBUG: Processed price for {rec.get('item_name')}: {current_price} -> {recommended_price}")
                except Exception as price_error:
                    print(f"ERROR parsing price for item {rec.get('item_id', 'unknown')}: {str(price_error)}")
                    # Set default values if parsing fails
                    current_price = 0.0
                    recommended_price = 0.0
                    price_change_amount = 0.0
                    price_change_percent = 0.0
                
                # Get the item ID - convert to integer if possible
                item_id = None
                try:
                    if isinstance(rec.get('item_id'), str) and rec.get('item_id').isdigit():
                        item_id = int(rec.get('item_id'))
                    else:
                        item_id = rec.get('item_id')
                except:
                    # If we can't convert, use as is
                    item_id = rec.get('item_id')
                    
                # Extract rationale from the right field
                rationale = rec.get('rationale', '') or rec.get('reason', '')
                
                # Parse re-evaluation days if available
                reevaluation_date = None
                if rec.get('re_evaluation_days'):
                    try:
                        days = int(rec.get('re_evaluation_days'))
                        reevaluation_date = datetime.now() + timedelta(days=days)
                    except:
                        pass
                
                # Create new recommendation object
                new_rec = models.PricingRecommendation(
                    user_id=user_id,
                    batch_id=batch_id,
                    item_id=item_id,
                    current_price=current_price,
                    recommended_price=recommended_price,
                    price_change_amount=price_change_amount,
                    price_change_percent=price_change_percent,
                    strategy_type=rec.get('strategy', 'dynamic_pricing'),
                    confidence_score=rec.get('confidence', 0.8),
                    rationale=rationale,
                    expected_revenue_change=rec.get('expected_revenue_change'),
                    expected_quantity_change=rec.get('expected_quantity_change'),
                    expected_margin_change=rec.get('expected_margin_change'),
                    implementation_status='pending',
                    recommendation_date=datetime.now(),
                    reevaluation_date=reevaluation_date,
                    created_at=datetime.now()
                )
                db.add(new_rec)
            
            # Save analysis results summary to database - commented out because AgentAnalysisResult model doesn't exist yet
            # TODO: Either create the AgentAnalysisResult model or remove this code
            # analysis_record = models.AgentAnalysisResult(
            #     user_id=user_id,
            #     batch_id=batch_id,
            #     analysis_date=datetime.now(),
            #     overall_status=analysis_results.get('executive_summary', {}).get('overall_status', 'completed'),
            #     revenue_trend=analysis_results.get('executive_summary', {}).get('revenue_trend', 'neutral'),
            #     results_json=json.dumps(analysis_results)
            # )
            # db.add(analysis_record)
            
            # Commit changes to database
            db.commit()
            print(f"DEBUG: Successfully saved recommendations and analysis results to database")
            
        except Exception as db_error:
            db.rollback()  # Rollback on error
            print(f"ERROR: Failed to save recommendations to database: {str(db_error)}")
        
        # Close the database session
        db.close()
        
        return {
            "success": True,
            "status": "completed",
            "batch_id": batch_id,
            "analysis_results": analysis_results,
            "pricing_recommendations": pricing_recommendations,
            "agent_statuses": agent_statuses,
            "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except Exception as e:
        print(f"ERROR in run_dynamic_pricing_analysis_task: {str(e)}")
        import traceback
        print(traceback.format_exc())
        
        # Close database session if opened
        if 'db' in locals():
            db.close()
            
        return {
            "success": False,
            "error": str(e),
            "status": "failed"
        }


@celery_app.task(name="generate_menu_suggestions_task")
def generate_menu_suggestions_task(menu_items: List[Dict[str, Any]], user_id: int) -> Dict[str, Any]:
    """
    Celery task to generate menu suggestions using OpenAI API
    
    This offloads the potentially long-running API call to a background worker
    to avoid web worker timeouts in the FastAPI application.
    
    Args:
        menu_items: List of menu items with name, description, and category
        user_id: ID of the user making the request
    
    Returns:
        Dictionary containing the recipe suggestions or error information
    """
    try:
        # Check if OpenAI API key is configured
        if not OPENAI_API_KEY:
            return {
                "success": False,
                "error": "OpenAI API is not configured. Please add your API key to the environment variables.",
                "status": "failed"
            }
        
        # Check if OpenAI client is initialized
        if 'openai' not in clients:
            return {
                "success": False,
                "error": "OpenAI client failed to initialize. Please check the API key.",
                "status": "failed"
            }
        
        # Format menu items for the prompt
        menu_items_text = "\n".join([
            f"- {item['name']}: {item.get('description', 'No description')} (Category: {item.get('category', 'Unknown')})"
            for item in menu_items
        ])
        
        # Create the prompt for OpenAI
        prompt = f"""
        Given the following menu items from a food service business:
        
        {menu_items_text}
        
        Please suggest:
        1. Recipes for each menu item using those ingredients
        
        Format your response as a valid JSON object with the following structure:
        {{
            "recipes": [
                {{
                    "item_name": "Menu item name",
                    "ingredients": [
                        {{
                            "ingredient": ingredient name,
                            "quantity": quantity needed for this recipe as number,
                            "unit": "unit of measurement"
                        }}
                    ]
                }}
            ]
        }}
        
        Be realistic with ingredient quantities and prices. Use common units of measurement. Be as granular as possible (i.e. for an americano, use grams of beans, not shots of espresso). Do not give any extra details about the ingredient, just return the base ingredient (i.e. frothed milk is just whole milk)
        """
        
        # Create a database session to update task status (if needed)
        db = SessionLocal()
        
        # Call OpenAI API
        try:
            logger.info(f"Celery task: Calling OpenAI API with menu items: {[item['name'] for item in menu_items]}")
            response = clients['openai'].chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant with expertise in food service and recipe identification."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract and parse the response
            suggestion_text = response.choices[0].message.content
            logger.info(f"Celery task: Received response from OpenAI API")
        except Exception as e:
            logger.error(f"Celery task: OpenAI API call failed: {str(e)}")
            db.close()
            return {
                "success": False,
                "error": f"OpenAI API call failed: {str(e)}",
                "status": "failed"
            }
        
        # Find the JSON part of the response
        suggestion_json = None
        try:
            # Try to find a JSON object in the response
            json_match = re.search(r'({[\s\S]*})', suggestion_text)
            if json_match:
                suggestion_json = json.loads(json_match.group(1))
            else:
                # If no JSON found, try to parse the whole response
                suggestion_json = json.loads(suggestion_text)
                
            logger.info(f"Celery task: Successfully parsed JSON response")
        except json.JSONDecodeError as e:
            logger.error(f"Celery task: Failed to parse JSON from OpenAI response: {e}")
            db.close()
            return {
                "success": False,
                "error": f"Failed to parse AI response as JSON: {str(e)}",
                "status": "failed"
            }
        
        if not suggestion_json or not isinstance(suggestion_json, dict):
            db.close()
            return {
                "success": False,
                "error": "Invalid response format from AI service",
                "status": "failed"
            }
        
        # Process the recipes to ensure they match our expected format
        recipes = suggestion_json.get("recipes", [])
        for recipe in recipes:
            # Ensure each recipe has ingredients list
            if "ingredients" not in recipe:
                recipe["ingredients"] = []
        
        # Close the database session
        db.close()
        
        # Return the successful result
        return {
            "success": True,
            "status": "completed",
            "recipes": recipes
        }
        
    except Exception as e:
        logger.exception("Celery task: Unexpected error in generate_menu_suggestions_task")
        
        # Close database session if opened
        if 'db' in locals():
            db.close()
            
        return {
            "success": False,
            "error": str(e),
            "status": "failed"
        }


@celery_app.task(name="get_menu_suggestions_task_status")
def get_menu_suggestions_task_status(task_id: str, user_id: int) -> Dict[str, Any]:
    """
    Check the status of a menu suggestions generation task
    
    Args:
        task_id: The Celery task ID to check
        user_id: ID of the user making the request
        
    Returns:
        Dictionary with task status information
    """
    try:
        # Get the AsyncResult for the task
        from celery.result import AsyncResult
        task_result = AsyncResult(task_id)
        
        # Get the task status
        task_status = task_result.status
        
        if task_status == "PENDING":
            status_message = "Menu suggestions task is queued for processing"
            return {
                "success": True,
                "task_status": task_status,
                "status_message": status_message,
                "completed": False
            }
        elif task_status == "STARTED":
            status_message = "Menu suggestions generation is in progress"
            return {
                "success": True,
                "task_status": task_status,
                "status_message": status_message,
                "completed": False
            }
        elif task_status == "SUCCESS":
            status_message = "Menu suggestions completed successfully"
            
            # Get the results
            result = task_result.result
            
            # Check if the result contains an error
            if result and isinstance(result, dict) and not result.get("success", True):
                return {
                    "success": False,
                    "task_status": task_status,
                    "status_message": f"Task completed but operation failed: {result.get('error', 'Unknown error')}",
                    "error": result.get("error"),
                    "completed": True
                }
            
            return {
                "success": True,
                "task_status": task_status,
                "status_message": status_message,
                "result": result,
                "completed": True
            }
        elif task_status == "FAILURE":
            status_message = "Menu suggestions generation failed"
            error_msg = str(task_result.result) if task_result.result else "Unknown error"
            
            return {
                "success": False,
                "task_status": task_status,
                "status_message": status_message,
                "error": error_msg,
                "completed": True
            }
        else:
            status_message = f"Unknown task status: {task_status}"
            return {
                "success": True,
                "task_status": task_status,
                "status_message": status_message,
                "completed": False
            }
        
    except Exception as e:
        logger.exception(f"Error checking menu suggestions task status: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "task_status": "ERROR",
            "status_message": "Error checking task status",
            "completed": False
        }


@celery_app.task(name="get_dynamic_pricing_task_status")
def get_dynamic_pricing_task_status(task_id: str, user_id: int) -> Dict[str, Any]:
    """
    Check the status of a dynamic pricing analysis task
    """
    try:
        # Get the AsyncResult for the task
        from celery.result import AsyncResult
        task_result = AsyncResult(task_id)
        
        # Get the task status
        task_status = task_result.status
        
        # Create a new database session
        db = SessionLocal()
        
        # Check for agent statuses in the database (if implemented)
        # This would be a placeholder for actual implementation
        agent_statuses = [
            {"name": "Data Collection", "status": "idle", "lastRun": ""},
            {"name": "Market Analysis", "status": "idle", "lastRun": ""},
            {"name": "Pricing Strategy", "status": "idle", "lastRun": ""},
            {"name": "Performance Monitor", "status": "idle", "lastRun": ""},
            {"name": "Experimentation", "status": "idle", "lastRun": ""}
        ]
        
        # If the task is still pending, we don't have status info yet
        if task_status == "PENDING":
            status_message = "Analysis task is queued for processing"
        elif task_status == "STARTED":
            status_message = "Analysis is in progress"
            
            # If we have partial results available, update agent statuses
            if task_result.info and isinstance(task_result.info, dict):
                if "agent_statuses" in task_result.info:
                    agent_statuses = task_result.info["agent_statuses"]
        elif task_status == "SUCCESS":
            status_message = "Analysis completed successfully"
            
            # Get the results if available
            result = task_result.result
            if result and isinstance(result, dict) and "agent_statuses" in result:
                agent_statuses = result["agent_statuses"]
                
            db.close()
            return {
                "success": True,
                "task_status": task_status,
                "status_message": status_message,
                "agent_statuses": agent_statuses,
                "result": result
            }
        elif task_status == "FAILURE":
            status_message = "Analysis failed"
            error_msg = str(task_result.result) if task_result.result else "Unknown error"
            
            # Update all agent statuses to error
            agent_statuses = [
                {**status, "status": "error"} for status in agent_statuses
            ]
            
            db.close()
            return {
                "success": False,
                "task_status": task_status,
                "status_message": status_message,
                "agent_statuses": agent_statuses,
                "error": error_msg
            }
        else:
            status_message = f"Unknown task status: {task_status}"
        
        db.close()
        
        return {
            "success": True,
            "task_status": task_status,
            "status_message": status_message,
            "agent_statuses": agent_statuses
        }
        
    except Exception as e:
        # Close database session if opened
        if 'db' in locals():
            db.close()
            
        return {
            "success": False,
            "error": str(e),
            "task_status": "ERROR",
            "status_message": "Error checking task status"
        }


@celery_app.task(name="adaptiv.tasks.sync_square_data_task", bind=True)
def sync_square_data_task(self, user_id: int, force_sync: bool = False) -> Dict[str, Any]:
    """
    Celery task to sync Square catalog items and orders in the background
    
    This prevents RAM issues by running the potentially memory-intensive
    Square API sync operations in a background worker process.
    
    Args:
        user_id: ID of the user to sync Square data for
        force_sync: Whether to force a full sync regardless of recent sync status
        
    Returns:
        Dictionary with sync results including items/orders created/updated
    """
    import requests
    from square_integration import SQUARE_API_BASE
    
    db = None
    try:
        logger.info(f"Starting Square sync task {self.request.id} for user {user_id}")
        
        # Create database session
        db = SessionLocal()
        
        # Get Square integration for user
        integration = db.query(models.POSIntegration).filter(
            models.POSIntegration.user_id == user_id,
            models.POSIntegration.provider == "square"
        ).first()
        
        if not integration:
            return {
                "success": False,
                "error": "No Square integration found for user",
                "task_status": "COMPLETED"
            }
        
        # Update task progress
        self.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Getting locations...'})
        
        # Get merchant's locations
        logger.info("Square API: Fetching locations for sync")
        locations_response = requests.get(
            f"{SQUARE_API_BASE}/v2/locations",
            headers={
                "Authorization": f"Bearer {integration.access_token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        locations_data = locations_response.json()
        
        if locations_response.status_code != 200 or "locations" not in locations_data:
            return {
                "success": False,
                "error": "Failed to get locations",
                "task_status": "COMPLETED"
            }
        
        if not locations_data.get("locations"):
            return {
                "success": False,
                "error": "No locations found",
                "task_status": "COMPLETED"
            }
        
        locations = locations_data.get("locations", [])
        catalog_mapping = {}  # Maps Square catalog IDs to local item IDs
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 20, 'status': 'Syncing catalog items...'})
        
        # Sync catalog items
        items_created = 0
        items_updated = 0
        
        # Get catalog from Square
        logger.info("Square API: Fetching catalog items")
        catalog_response = requests.get(
            f"{SQUARE_API_BASE}/v2/catalog/list?types=ITEM",
            headers={
                "Authorization": f"Bearer {integration.access_token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if catalog_response.status_code != 200:
            return {
                "success": False,
                "error": "Failed to get catalog",
                "task_status": "COMPLETED"
            }
            
        catalog_data = catalog_response.json()
        items = catalog_data.get("objects", [])
        
        logger.info(f"Found {len(items)} items in Square catalog")
        
        # Process each catalog item
        for i, item_obj in enumerate(items):
            if i % 10 == 0:  # Update progress every 10 items
                progress = 20 + (i / len(items)) * 30  # 20-50% for catalog sync
                self.update_state(state='PROGRESS', meta={
                    'progress': int(progress), 
                    'status': f'Processing catalog item {i+1}/{len(items)}...'
                })
            
            if item_obj.get("type") != "ITEM":
                continue
                
            square_item_id = item_obj.get("id")
            item_data = item_obj.get("item_data", {})
            name = item_data.get("name", "")
            description = item_data.get("description", "")
            
            # Skip items without name
            if not name:
                continue
                
            # Get price from first variation
            variations = item_data.get("variations", [])
            price = None
            square_variation_id = None
            
            if variations:
                variation = variations[0]
                square_variation_id = variation.get("id")
                variation_data = variation.get("item_variation_data", {})
                price_money = variation_data.get("price_money", {})
                if price_money:
                    # Convert cents to dollars
                    price = price_money.get("amount", 0) / 100.0
            
            # Skip items without price
            if price is None:
                continue
                
            # Check if item already exists by Square ID first
            existing_item = db.query(models.Item).filter(
                models.Item.pos_id == square_item_id,
                models.Item.user_id == user_id
            ).first()
            
            if existing_item:
                # Update existing item
                existing_item.name = name
                existing_item.description = description
                existing_item.current_price = price
                existing_item.updated_at = datetime.utcnow()
                items_updated += 1
                catalog_mapping[square_item_id] = existing_item.id
            else:
                # Create new item
                new_item = models.Item(
                    user_id=user_id,
                    name=name,
                    description=description,
                    current_price=price,
                    pos_id=square_item_id,
                    category="Square Import",
                    created_at=datetime.utcnow()
                )
                db.add(new_item)
                db.flush()  # Get the ID
                items_created += 1
                catalog_mapping[square_item_id] = new_item.id
        
        # Commit catalog changes
        db.commit()
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 50, 'status': 'Syncing orders...'})
        
        # Sync orders for each location
        orders_created = 0
        orders_updated = 0
        orders_failed = 0
        
        for loc_idx, location in enumerate(locations):
            location_id = location.get("id")
            if not location_id:
                continue
                
            logger.info(f"Processing orders for location {location_id}")
            
            # Update progress
            loc_progress = 50 + (loc_idx / len(locations)) * 40  # 50-90% for orders
            self.update_state(state='PROGRESS', meta={
                'progress': int(loc_progress),
                'status': f'Processing orders for location {loc_idx+1}/{len(locations)}...'
            })
            
            try:
                # Get orders for this location with pagination
                cursor = None
                page_count = 0
                max_pages = 50 if force_sync else 10  # Limit pages to prevent memory issues
                
                while page_count < max_pages:
                    page_count += 1
                    
                    # Build request payload
                    request_payload = {
                        "location_ids": [location_id],
                        "query": {
                            "filter": {
                                "state_filter": {"states": ["COMPLETED", "OPEN"]}
                            },
                            "sort": {
                                "sort_field": "CREATED_AT",
                                "sort_order": "DESC"
                            }
                        },
                        "limit": 100  # Process in smaller batches
                    }
                    
                    if cursor:
                        request_payload["cursor"] = cursor
                    
                    # Make API request
                    orders_response = requests.post(
                        f"{SQUARE_API_BASE}/v2/orders/search",
                        headers={
                            "Authorization": f"Bearer {integration.access_token}",
                            "Content-Type": "application/json"
                        },
                        json=request_payload,
                        timeout=30
                    )
                    
                    if orders_response.status_code != 200:
                        logger.error(f"Failed to get orders for location {location_id}: {orders_response.text}")
                        orders_failed += 1
                        break
                    
                    orders_data = orders_response.json()
                    orders = orders_data.get("orders", [])
                    
                    if not orders:
                        break  # No more orders
                    
                    # Process orders in this batch
                    for order in orders:
                        try:
                            square_order_id = order.get("id")
                            if not square_order_id:
                                continue
                            
                            # Check if order already exists
                            existing_order = db.query(models.Order).filter(
                                models.Order.pos_id == square_order_id,
                                models.Order.user_id == user_id
                            ).first()
                            
                            if existing_order and not force_sync:
                                continue  # Skip existing orders unless force sync
                            
                            # Extract order data
                            order_date_str = order.get("created_at", "")
                            order_date = datetime.fromisoformat(order_date_str.replace('Z', '+00:00')) if order_date_str else datetime.utcnow()
                            
                            # Calculate total from line items
                            line_items = order.get("line_items", [])
                            total_amount = 0
                            total_cost = 0
                            
                            for line_item in line_items:
                                quantity = int(line_item.get("quantity", "1"))
                                
                                # Get price from line item
                                total_money = line_item.get("total_money", {})
                                item_total = total_money.get("amount", 0) / 100.0  # Convert cents to dollars
                                total_amount += item_total
                                
                                # Try to get cost from catalog mapping
                                catalog_object_id = line_item.get("catalog_object_id")
                                if catalog_object_id and catalog_object_id in catalog_mapping:
                                    local_item_id = catalog_mapping[catalog_object_id]
                                    local_item = db.query(models.Item).filter(models.Item.id == local_item_id).first()
                                    if local_item and local_item.cost:
                                        total_cost += quantity * local_item.cost
                            
                            if existing_order:
                                # Update existing order
                                existing_order.order_date = order_date
                                existing_order.total_amount = total_amount
                                existing_order.total_cost = total_cost
                                existing_order.gross_margin = total_amount - total_cost
                                existing_order.updated_at = datetime.utcnow()
                                orders_updated += 1
                                order_id = existing_order.id
                            else:
                                # Create new order
                                new_order = models.Order(
                                    user_id=user_id,
                                    pos_id=square_order_id,
                                    order_date=order_date,
                                    total_amount=total_amount,
                                    total_cost=total_cost,
                                    gross_margin=total_amount - total_cost,
                                    created_at=datetime.utcnow()
                                )
                                db.add(new_order)
                                db.flush()  # Get the ID
                                orders_created += 1
                                order_id = new_order.id
                            
                            # Process line items
                            if not existing_order or force_sync:
                                # Delete existing order items if updating
                                if existing_order:
                                    db.query(models.OrderItem).filter(
                                        models.OrderItem.order_id == order_id
                                    ).delete()
                                
                                # Add line items
                                for line_item in line_items:
                                    catalog_object_id = line_item.get("catalog_object_id")
                                    if catalog_object_id and catalog_object_id in catalog_mapping:
                                        local_item_id = catalog_mapping[catalog_object_id]
                                        quantity = int(line_item.get("quantity", "1"))
                                        
                                        # Get unit price
                                        total_money = line_item.get("total_money", {})
                                        item_total = total_money.get("amount", 0) / 100.0
                                        unit_price = item_total / quantity if quantity > 0 else 0
                                        
                                        # Get unit cost
                                        local_item = db.query(models.Item).filter(models.Item.id == local_item_id).first()
                                        unit_cost = local_item.cost if local_item else None
                                        
                                        order_item = models.OrderItem(
                                            order_id=order_id,
                                            item_id=local_item_id,
                                            quantity=quantity,
                                            unit_price=unit_price,
                                            unit_cost=unit_cost
                                        )
                                        db.add(order_item)
                        
                        except Exception as e:
                            logger.error(f"Error processing order {square_order_id}: {str(e)}")
                            orders_failed += 1
                            continue
                    
                    # Check for next page
                    cursor = orders_data.get("cursor")
                    if not cursor:
                        break  # No more pages
                    
                    # Commit batch to prevent memory buildup
                    db.commit()
                    
            except Exception as e:
                logger.error(f"Error processing location {location_id}: {str(e)}")
                orders_failed += 1
                continue
        
        # Final commit
        db.commit()
        
        # Update final progress
        self.update_state(state='PROGRESS', meta={'progress': 100, 'status': 'Sync completed!'})
        
        result = {
            "success": True,
            "task_status": "COMPLETED",
            "items_created": items_created,
            "items_updated": items_updated,
            "orders_created": orders_created,
            "orders_updated": orders_updated,
            "orders_failed": orders_failed,
            "locations_processed": len(locations)
        }
        
        logger.info(f"Square sync task completed: {result}")
        return result
        
    except Exception as e:
        logger.exception(f"Error in Square sync task: {str(e)}")
        if db:
            db.rollback()
        return {
            "success": False,
            "error": str(e),
            "task_status": "ERROR"
        }
    finally:
        if db:
            db.close()


@celery_app.task(name="adaptiv.tasks.get_square_sync_status", bind=True)
def get_square_sync_status(self, task_id: str, user_id: int) -> Dict[str, Any]:
    """
    Check the status of a Square sync task
    
    Args:
        task_id: The Celery task ID to check
        user_id: ID of the user making the request
        
    Returns:
        Dictionary with task status information
    """
    try:
        # Get task result
        result = celery_app.AsyncResult(task_id)
        
        if result.state == 'PENDING':
            return {
                "task_id": task_id,
                "task_status": "PENDING",
                "status_message": "Task is waiting to be processed",
                "progress": 0
            }
        elif result.state == 'PROGRESS':
            return {
                "task_id": task_id,
                "task_status": "PROGRESS",
                "status_message": result.info.get('status', 'Processing...'),
                "progress": result.info.get('progress', 0)
            }
        elif result.state == 'SUCCESS':
            return {
                "task_id": task_id,
                "task_status": "COMPLETED",
                "status_message": "Square sync completed successfully",
                "progress": 100,
                "result": result.result
            }
        elif result.state == 'FAILURE':
            return {
                "task_id": task_id,
                "task_status": "ERROR",
                "status_message": f"Task failed: {str(result.info)}",
                "progress": 0,
                "error": str(result.info)
            }
        else:
            return {
                "task_id": task_id,
                "task_status": result.state,
                "status_message": f"Task state: {result.state}",
                "progress": 0
            }
            
    except Exception as e:
        logger.exception(f"Error checking Square sync task status: {str(e)}")
        return {
            "task_id": task_id,
            "task_status": "ERROR",
            "status_message": f"Error checking task status: {str(e)}",
            "progress": 0,
            "error": str(e)
        }


@celery_app.task(bind=True)
def generate_user_csv_task(self, user_id: int, data_type: str):
    """
    Simple and efficient CSV export - just raw database data without complex processing
    """
    import csv
    import tempfile
    import os
    from datetime import datetime
    
    logger.info(f"Starting simple CSV export for user {user_id}, type: {data_type}")
    
    try:
        self.update_state(
            state='PROGRESS',
            meta={'progress': 10, 'status': 'Starting export...'}
        )
        
        db = SessionLocal()
        
        try:
            # Verify user exists
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if not user:
                raise Exception(f"User {user_id} not found")
            
            # Create temporary CSV file
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8')
            writer = csv.writer(temp_file)
            
            self.update_state(
                state='PROGRESS',
                meta={'progress': 20, 'status': 'Exporting data...'}
            )
            
            if data_type == "menu_items" or data_type == "all":
                # Simple menu items export - just the raw data
                writer.writerow(["MENU ITEMS"])
                writer.writerow([
                    "ID", "Name", "Description", "Category", "Current Price", 
                    "Cost", "Created At", "Updated At"
                ])
                
                # Get all menu items in one simple query
                items = db.query(models.Item).filter(models.Item.user_id == user_id).all()
                
                for item in items:
                    writer.writerow([
                        item.id,
                        item.name or "",
                        item.description or "",
                        item.category or "",
                        item.current_price or 0,
                        item.cost or 0,
                        item.created_at.strftime("%Y-%m-%d %H:%M:%S") if item.created_at else "",
                        item.updated_at.strftime("%Y-%m-%d %H:%M:%S") if item.updated_at else ""
                    ])
                
                if data_type == "all":
                    writer.writerow([])  # Empty row
            
            self.update_state(
                state='PROGRESS',
                meta={'progress': 60, 'status': 'Processing orders...'}
            )
            
            if data_type == "orders" or data_type == "all":
                # Simple orders export
                writer.writerow(["ORDERS"])
                writer.writerow([
                    "Order ID", "Order Date", "Total Amount", "Total Cost", 
                    "Gross Margin", "POS ID", "Created At"
                ])
                
                # Get all orders in one simple query
                orders = db.query(models.Order).filter(
                    models.Order.user_id == user_id
                ).order_by(models.Order.order_date.desc()).all()
                
                for order in orders:
                    writer.writerow([
                        order.id,
                        order.order_date.strftime("%Y-%m-%d %H:%M:%S") if order.order_date else "",
                        order.total_amount or 0,
                        order.total_cost or 0,
                        order.gross_margin or 0,
                        order.pos_id or "",
                        order.created_at.strftime("%Y-%m-%d %H:%M:%S") if order.created_at else ""
                    ])
                
                # Add order items section
                writer.writerow([])  # Empty row
                writer.writerow(["ORDER ITEMS"])
                writer.writerow([
                    "Order Item ID", "Order ID", "Item ID", "Item Name", 
                    "Quantity", "Unit Price", "Unit Cost"
                ])
                
                # Get all order items with item names
                order_items = db.query(
                    models.OrderItem.id,
                    models.OrderItem.order_id,
                    models.OrderItem.item_id,
                    models.Item.name,
                    models.OrderItem.quantity,
                    models.OrderItem.unit_price,
                    models.OrderItem.unit_cost
                ).join(
                    models.Order, models.OrderItem.order_id == models.Order.id
                ).outerjoin(
                    models.Item, models.OrderItem.item_id == models.Item.id
                ).filter(
                    models.Order.user_id == user_id
                ).all()
                
                for item in order_items:
                    writer.writerow([
                        item.id,
                        item.order_id,
                        item.item_id or "",
                        item.name or "Unknown Item",
                        item.quantity or 0,
                        item.unit_price or 0,
                        item.unit_cost or 0
                    ])
            
            temp_file.close()
            
            self.update_state(
                state='PROGRESS',
                meta={'progress': 90, 'status': 'Finalizing file...'}
            )
            
            # Don't read the full CSV content into memory - Redis can't handle large files
            # Instead, we'll store the file path temporarily and serve it directly
            
            # Move temp file to a more permanent location
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"user_{user_id}_{data_type}_simple_{timestamp}.csv"
            
            # Create exports directory if it doesn't exist
            exports_dir = "/tmp/csv_exports"
            os.makedirs(exports_dir, exist_ok=True)
            
            # Move file to exports directory
            final_path = os.path.join(exports_dir, filename)
            os.rename(temp_file.name, final_path)
            
            logger.info(f"Simple CSV export completed for user {user_id}, saved to {final_path}")
            
            return {
                "success": True,
                "filename": filename,
                "file_path": final_path,
                "message": "CSV export completed successfully"
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.exception(f"Error in simple CSV export for user {user_id}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to generate CSV: {str(e)}"
        }


@celery_app.task
def get_csv_generation_status(task_id: str):
    """
    Get the status of a CSV generation task
    """
    try:
        result = celery_app.AsyncResult(task_id)
        
        if result.state == 'PENDING':
            return {
                "task_id": task_id,
                "task_status": "PENDING",
                "status_message": "CSV generation is waiting to start...",
                "progress": 0
            }
        elif result.state == 'PROGRESS':
            return {
                "task_id": task_id,
                "task_status": "PROGRESS",
                "status_message": result.info.get('status', 'Processing...'),
                "progress": result.info.get('progress', 0)
            }
        elif result.state == 'SUCCESS':
            return {
                "task_id": task_id,
                "task_status": "COMPLETED",
                "status_message": "CSV generation completed successfully",
                "progress": 100,
                "result": result.result
            }
        elif result.state == 'FAILURE':
            return {
                "task_id": task_id,
                "task_status": "ERROR",
                "status_message": f"CSV generation failed: {str(result.info)}",
                "progress": 0,
                "error": str(result.info)
            }
        else:
            return {
                "task_id": task_id,
                "task_status": result.state,
                "status_message": f"Task state: {result.state}",
                "progress": 0
            }
            
    except Exception as e:
        logger.exception(f"Error checking CSV generation task status: {str(e)}")
        return {
            "task_id": task_id,
            "task_status": "ERROR",
            "status_message": f"Error checking task status: {str(e)}",
            "progress": 0,
            "error": str(e)
        }


@celery_app.task
def cleanup_old_csv_files():
    """
    Clean up CSV files older than 24 hours to prevent disk space issues
    """
    import os
    import time
    from datetime import datetime, timedelta
    
    try:
        exports_dir = "/tmp/csv_exports"
        if not os.path.exists(exports_dir):
            return {"message": "No exports directory found"}
        
        # Remove files older than 24 hours
        cutoff_time = time.time() - (24 * 60 * 60)  # 24 hours ago
        removed_count = 0
        
        for filename in os.listdir(exports_dir):
            file_path = os.path.join(exports_dir, filename)
            if os.path.isfile(file_path):
                file_mtime = os.path.getmtime(file_path)
                if file_mtime < cutoff_time:
                    try:
                        os.remove(file_path)
                        removed_count += 1
                        logger.info(f"Removed old CSV file: {filename}")
                    except Exception as e:
                        logger.error(f"Failed to remove CSV file {filename}: {str(e)}")
        
        logger.info(f"CSV cleanup completed. Removed {removed_count} old files.")
        return {
            "success": True,
            "removed_count": removed_count,
            "message": f"Cleaned up {removed_count} old CSV files"
        }
        
    except Exception as e:
        logger.exception(f"Error during CSV cleanup: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": f"CSV cleanup failed: {str(e)}"
        }
