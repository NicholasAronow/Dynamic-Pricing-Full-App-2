from celery_app import celery_app
from typing import Dict, Any, List
from sqlalchemy.orm import Session
import models
from database import SessionLocal
import json
import asyncio
# Import datetime at the module level since it's used in multiple places
from datetime import datetime, timedelta

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
