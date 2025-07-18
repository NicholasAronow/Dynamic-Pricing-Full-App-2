from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
from .auth import get_current_user
from typing import Annotated, Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict
import asyncio
import json
import os
from datetime import datetime
from agent_progress import AgentProgress
import copy

# Import the agent manager, database interface, and session wrapper
from agent_sdk.agent_manager import AgentManager
from db_interface import DatabaseInterface
from session_wrapper import SessionDep, SessionWrapper
import models

router = APIRouter(
    prefix="/agents-sdk",
    tags=["agents-sdk"],
    responses={404: {"description": "Not found"}},
)

# Response models
class AgentResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    
class AgentProgressResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    process_id: str
    status: str
    progress_percent: int
    message: str
    current_step: str
    steps: Dict[str, Any]
    error: Optional[str] = None


def normalize_reports(reports):
    """
    Ensure report data has the expected structure for the frontend.
    
    This function ensures that array properties expected by the frontend are properly formatted,
    converting any non-array properties to empty arrays.
    """
    if not reports:
        return reports
        
    # Make a deep copy to avoid modifying the original
    normalized = copy.deepcopy(reports)
    
    # Normalize competitor report
    if normalized.get('competitor_report'):
        cr = normalized['competitor_report']
        
        # Ensure insights exists and has the right format
        if not cr.get('insights') or not isinstance(cr['insights'], dict):
            cr['insights'] = {}
        
        # Handle the deeply nested structure
        if not cr['insights'].get('insights') or not isinstance(cr['insights']['insights'], dict):
            cr['insights']['insights'] = {}
            
        # Ensure insights.insights.insights is an array
        if not cr['insights']['insights'].get('insights') or not isinstance(cr['insights']['insights']['insights'], list):
            cr['insights']['insights']['insights'] = []
            
        # Ensure insights.insights.positioning exists
        if not cr['insights']['insights'].get('positioning'):
            cr['insights']['insights']['positioning'] = ""
    
    # Normalize customer report
    if normalized.get('customer_report'):
        cust = normalized['customer_report']
        
        # Ensure demographics is an array
        if not cust.get('demographics') or not isinstance(cust['demographics'], list):
            cust['demographics'] = []
            
        # Ensure events is an array
        if not cust.get('events') or not isinstance(cust['events'], list):
            cust['events'] = []
    
    # Normalize market report
    if normalized.get('market_report'):
        mr = normalized['market_report']
        
        # Ensure supply_chain is an array
        if not mr.get('supply_chain') or not isinstance(mr['supply_chain'], list):
            mr['supply_chain'] = []
            
        # Ensure market_trends exists and has the right format
        if not mr.get('market_trends') or not isinstance(mr['market_trends'], dict):
            mr['market_trends'] = {}
            
        # Ensure market_trends.cost_trends is an array
        if not mr['market_trends'].get('cost_trends') or not isinstance(mr['market_trends']['cost_trends'], list):
            mr['market_trends']['cost_trends'] = []
    
    # Normalize pricing report
    if normalized.get('pricing_report'):
        pr = normalized['pricing_report']
        
        # Ensure recommended_changes is an array
        if not pr.get('recommended_changes') or not isinstance(pr['recommended_changes'], list):
            pr['recommended_changes'] = []
    
    # Normalize experiment recommendation
    if normalized.get('experiment_recommendation'):
        er = normalized['experiment_recommendation']
        
        # Ensure recommendations exists and has the right format
        if not er.get('recommendations') or not isinstance(er['recommendations'], dict):
            er['recommendations'] = {}
            
        # Ensure recommendations.implementation is an array
        if not er['recommendations'].get('implementation') or not isinstance(er['recommendations']['implementation'], list):
            er['recommendations']['implementation'] = []
    
    return normalized

# Define a function to run async tasks
def run_async(coroutine):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()

# Endpoint for checking the progress of an agent process
@router.get("/process/{process_id}", response_model=AgentProgressResponse)
async def get_process_status(
    process_id: str,
    current_user: models.User = Depends(get_current_user)
):
    """Get the status of an agent process"""
    try:
        process = AgentProgress.get_process(process_id)
        if not process:
            raise HTTPException(status_code=404, detail="Process not found")
            
        # Verify that the process belongs to the current user
        if process["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this process")
            
        return process
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get process status: {str(e)}")

# Endpoint for getting the latest process for a user
@router.get("/process/latest", response_model=AgentProgressResponse)
@router.get("/latest-process", response_model=AgentProgressResponse)  # Additional route for consistency
async def get_latest_process(
    current_user: models.User = Depends(get_current_user)
):
    """Get the latest agent process for the current user"""
    try:
        process = AgentProgress.get_latest_user_process(current_user.id)
        if not process:
            raise HTTPException(status_code=404, detail="No process found for this user")
            
        return process
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get latest process: {str(e)}")

# Endpoint for triggering the full agent process
@router.post("/full-process", response_model=AgentResponse)
@router.post("/run-full-process", response_model=AgentResponse)  # Additional route to match frontend's expected path
async def trigger_full_agent_process(
    background_tasks: BackgroundTasks,
    db_wrapper: SessionDep,
    current_user: models.User = Depends(get_current_user)
):
    """Trigger the full agent process (all agents in sequence)"""
    try:
        # Create a database interface
        db_interface = DatabaseInterface(db_wrapper.session)
        
        # Create an agent manager
        agent_manager = AgentManager(db_wrapper.session)
        
        # Start tracking the process
        process_id = AgentProgress.start_process(current_user.id)
        
        # Run the full process in the background
        background_tasks.add_task(
            run_async,
            agent_manager.run_full_process(current_user.id)
        )
        
        return {
            "success": True,
            "message": "Full agent process started",
            "data": {
                "user_id": current_user.id,
                "process_id": process_id
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to start full agent process: {str(e)}"
        )

# Endpoint for triggering individual agents
@router.post("/competitor/generate", response_model=AgentResponse)
async def trigger_competitor_agent(
    background_tasks: BackgroundTasks,
    db_wrapper: SessionDep,
    current_user: models.User = Depends(get_current_user)
):
    """Trigger the competitor agent to generate a new report"""
    try:
        # Create a database interface
        db_interface = DatabaseInterface(db_wrapper.session)
        
        # Create an agent manager
        agent_manager = AgentManager(db_wrapper.session)
        
        background_tasks.add_task(
            run_async,
            agent_manager.run_competitor_agent(current_user.id)
        )
        
        return {
            "success": True,
            "message": "Competitor agent report generation started",
            "data": None
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to start competitor agent: {str(e)}"
        )

@router.post("/customer/generate", response_model=AgentResponse)
async def trigger_customer_agent(
    background_tasks: BackgroundTasks,
    db_wrapper: SessionDep,
    current_user: models.User = Depends(get_current_user)
):
    """Trigger the customer agent to generate a new report"""
    try:
        # Create a database interface
        db_interface = DatabaseInterface(db_wrapper.session)
        
        # Create an agent manager
        agent_manager = AgentManager(db_wrapper.session)
        
        background_tasks.add_task(
            run_async,
            agent_manager.run_customer_agent(current_user.id)
        )
        
        return {
            "success": True,
            "message": "Customer agent report generation started",
            "data": None
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to start customer agent: {str(e)}"
        )

@router.post("/market/generate", response_model=AgentResponse)
async def trigger_market_agent(
    background_tasks: BackgroundTasks,
    db_wrapper: SessionDep,
    current_user: models.User = Depends(get_current_user)
):
    """Trigger the market agent to generate a new report"""
    try:
        # Create a database interface
        db_interface = DatabaseInterface(db_wrapper.session)
        
        # Create an agent manager
        agent_manager = AgentManager(db_wrapper.session)
        
        background_tasks.add_task(
            run_async,
            agent_manager.run_market_agent(current_user.id)
        )
        
        return {
            "success": True,
            "message": "Market agent report generation started",
            "data": None
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to start market agent: {str(e)}"
        )

@router.post("/pricing/generate", response_model=AgentResponse)
async def trigger_pricing_agent(
    background_tasks: BackgroundTasks,
    db_wrapper: SessionDep,
    current_user: models.User = Depends(get_current_user)
):
    """Trigger the pricing agent to generate a new report"""
    try:
        # Create a database interface
        db_interface = DatabaseInterface(db_wrapper.session)
        
        # Create an agent manager
        agent_manager = AgentManager(db_wrapper.session)
        
        background_tasks.add_task(
            run_async,
            agent_manager.run_pricing_agent(current_user.id)
        )
        
        return {
            "success": True,
            "message": "Pricing agent report generation started",
            "data": None
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to start pricing agent: {str(e)}"
        )

@router.post("/experiment/generate", response_model=AgentResponse)
async def trigger_experiment_agent(
    background_tasks: BackgroundTasks,
    pricing_report_id: int,
    db_wrapper: SessionDep,
    current_user: models.User = Depends(get_current_user)
):
    """Trigger the experiment agent to generate a new recommendation"""
    try:
        # Create a database interface
        db_interface = DatabaseInterface(db)
        
        # Check if pricing report exists and belongs to user
        pricing_report = db_interface.get_pricing_report_by_id(pricing_report_id)
        
        if not pricing_report or pricing_report.user_id != current_user.id:
            raise HTTPException(
                status_code=404,
                detail="Pricing report not found"
            )
        
        # Create a database interface
        db_interface = DatabaseInterface(db_wrapper.session)
        
        # Create an agent manager
        agent_manager = AgentManager(db_wrapper.session)
        
        background_tasks.add_task(
            run_async,
            agent_manager.run_experiment_agent(current_user.id, pricing_report_id)
        )
        
        return {
            "success": True,
            "message": "Experiment agent recommendation generation started",
            "data": None
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to start experiment agent: {str(e)}"
        )

# Request model for price recommendation action
class PriceRecommendationActionRequest(BaseModel):
    product_id: int
    approved: bool
    action_taken: Optional[str] = None

# Handle price recommendation approval or denial
@router.post("/pricing/recommendation")
async def handle_price_recommendation(
    request: PriceRecommendationActionRequest,
    db_wrapper: SessionDep,
    current_user: models.User = Depends(get_current_user)
) -> AgentResponse:
    """Handle a price recommendation approval or denial"""
    try:
        db = db_wrapper.session
        
        # Find the latest pricing report for this user
        latest_pricing_report = db.query(models.PricingReport).filter(
            models.PricingReport.user_id == current_user.id
        ).order_by(models.PricingReport.created_at.desc()).first()
        
        if not latest_pricing_report:
            return AgentResponse(
                success=False,
                message="No pricing report found",
                data=None
            )
            
        # Get the report content
        report_content = json.loads(latest_pricing_report.content) if latest_pricing_report.content else {}
        recommended_changes = report_content.get('recommended_changes', [])
        
        # Find the specific recommendation for this product
        product_recommendation = None
        for rec in recommended_changes:
            if rec.get('product_id') == request.product_id:
                product_recommendation = rec
                break
                
        if not product_recommendation:
            return AgentResponse(
                success=False,
                message=f"No recommendation found for product ID {request.product_id}",
                data=None
            )
            
        # Record the action in the database
        # First, check if we already have a record for this recommendation
        price_action = db.query(models.PriceRecommendationAction).filter(
            models.PriceRecommendationAction.report_id == latest_pricing_report.id,
            models.PriceRecommendationAction.product_id == request.product_id
        ).first()
        
        if price_action:
            # Update existing record
            price_action.approved = request.approved
            price_action.action_taken_at = request.action_taken or datetime.utcnow().isoformat()
        else:
            # Create new record
            price_action = models.PriceRecommendationAction(
                report_id=latest_pricing_report.id,
                product_id=request.product_id,
                current_price=product_recommendation.get('current_price'),
                recommended_price=product_recommendation.get('recommended_price'),
                change_percentage=product_recommendation.get('change_percentage'),
                approved=request.approved,
                action_taken_at=request.action_taken or datetime.utcnow().isoformat(),
                implemented=False  # This will be set to True when the price is actually changed
            )
            db.add(price_action)
            
        db.commit()
        
        # If approved, update the product price (this would be implemented in a real application)
        if request.approved:
            # This is a placeholder for actual price update logic
            # In a real app, you would update the price in your product database
            pass
            
        return AgentResponse(
            success=True,
            message=f"Price recommendation {'approved' if request.approved else 'declined'} for product {request.product_id}",
            data={
                "product_id": request.product_id,
                "approved": request.approved,
                "action_taken": request.action_taken or datetime.utcnow().isoformat(),
                "recommendation": product_recommendation
            }
        )
    except Exception as e:
        return AgentResponse(
            success=False,
            message=f"Error handling price recommendation: {str(e)}",
            data=None
        )

# Get the most recent reports from all agents
@router.get("/reports/latest", response_model=Dict[str, Any])
@router.get("/latest-reports", response_model=Dict[str, Any])  # Additional route to match frontend's expected path
async def get_latest_reports(
    db_wrapper: SessionDep,
    current_user: models.User = Depends(get_current_user)
):
    """Get the most recent reports from all agents"""
    try:
        # Create a database interface
        db_interface = DatabaseInterface(db_wrapper.session)
        
        # Get the most recent competitor report
        competitor_report = db_interface.get_latest_competitor_report(current_user.id)
        
        # Get the most recent customer report
        customer_report = db_interface.get_latest_customer_report(current_user.id)
        
        # Get the most recent market report
        market_report = db_interface.get_latest_market_report(current_user.id)
        
        # Get the most recent pricing report
        pricing_report = db_interface.get_latest_pricing_report(current_user.id)
        
        # Get the most recent experiment recommendation
        experiment_recommendation = db_interface.get_latest_experiment_recommendation(current_user.id)
        
        # Construct the raw reports data
        reports_data = {
            "competitor_report": {
                "id": competitor_report.id if competitor_report else None,
                "summary": competitor_report.summary if competitor_report else None,
                "insights": json.loads(competitor_report.insights) if competitor_report and competitor_report.insights else None,
                "created_at": competitor_report.created_at if competitor_report else None
            },
            "customer_report": {
                "id": customer_report.id if customer_report else None,
                "summary": customer_report.summary if customer_report else None,
                "demographics": json.loads(customer_report.demographics) if customer_report and customer_report.demographics else None,
                "events": json.loads(customer_report.events) if customer_report and customer_report.events else None,
                "trends": json.loads(customer_report.trends) if customer_report and customer_report.trends else None,
                "created_at": customer_report.created_at if customer_report else None
            },
            "market_report": {
                "id": market_report.id if market_report else None,
                "summary": market_report.summary if market_report else None,
                "market_trends": json.loads(market_report.market_trends) if market_report and market_report.market_trends else None,
                "supply_chain": json.loads(market_report.supply_chain) if market_report and market_report.supply_chain else None,
                "industry_insights": json.loads(market_report.industry_insights) if market_report and market_report.industry_insights else None,
                "created_at": market_report.created_at if market_report else None
            },
            "pricing_report": {
                "id": pricing_report.id if pricing_report else None,
                "summary": pricing_report.summary if pricing_report else None,
                "recommended_changes": json.loads(pricing_report.recommended_changes) if pricing_report and pricing_report.recommended_changes else None,
                "rationale": json.loads(pricing_report.rationale) if pricing_report and pricing_report.rationale else None,
                "created_at": pricing_report.created_at if pricing_report else None
            },
            "experiment_recommendation": {
                "id": experiment_recommendation.id if experiment_recommendation else None,
                "summary": experiment_recommendation.summary if experiment_recommendation else None,
                "start_date": experiment_recommendation.start_date if experiment_recommendation else None,
                "evaluation_date": experiment_recommendation.evaluation_date if experiment_recommendation else None,
                "recommendations": json.loads(experiment_recommendation.recommendations) if experiment_recommendation and experiment_recommendation.recommendations else None,
                "status": experiment_recommendation.status if experiment_recommendation else None,
                "created_at": experiment_recommendation.created_at if experiment_recommendation else None
            }
        }
        
        # Normalize the reports data to ensure arrays are properly formatted
        return normalize_reports(reports_data)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get latest reports: {str(e)}"
        )
