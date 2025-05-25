from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import models
import schemas
import json

# Import agent modules
from local_agents.competitor_agent import generate_competitor_report
from local_agents.customer_agent import generate_customer_report
from local_agents.market_agent import generate_market_report
from local_agents.pricing_agent import generate_pricing_report
from local_agents.experiment_agent import generate_experiment_recommendation

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    responses={404: {"description": "Not found"}},
)

# Response models
class AgentResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

# Endpoints for triggering agent processes
@router.post("/competitor/generate", response_model=AgentResponse)
async def trigger_competitor_agent(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: schemas.UserBase = Depends(get_current_user)
):
    """Trigger the competitor agent to generate a new report"""
    try:
        # Run agent report generation in background
        background_tasks.add_task(
            generate_competitor_report, 
            db=db, 
            user_id=current_user.id
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
    db: Session = Depends(get_db),
    current_user: schemas.UserBase = Depends(get_current_user)
):
    """Trigger the customer agent to generate a new report"""
    try:
        # Run agent report generation in background
        background_tasks.add_task(
            generate_customer_report, 
            db=db, 
            user_id=current_user.id
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
    db: Session = Depends(get_db),
    current_user: schemas.UserBase = Depends(get_current_user)
):
    """Trigger the market agent to generate a new report"""
    try:
        # Run agent report generation in background
        background_tasks.add_task(
            generate_market_report, 
            db=db, 
            user_id=current_user.id
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
    db: Session = Depends(get_db),
    current_user: schemas.UserBase = Depends(get_current_user)
):
    """Trigger the pricing agent to generate a new report"""
    try:
        # Run agent report generation in background
        background_tasks.add_task(
            generate_pricing_report, 
            db=db, 
            user_id=current_user.id
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
    db: Session = Depends(get_db),
    current_user: schemas.UserBase = Depends(get_current_user)
):
    """Trigger the experiment agent to generate a new recommendation"""
    try:
        # Check if pricing report exists and belongs to user
        pricing_report = db.query(models.PricingReport).filter(
            models.PricingReport.id == pricing_report_id,
            models.PricingReport.user_id == current_user.id
        ).first()
        
        if not pricing_report:
            raise HTTPException(
                status_code=404,
                detail="Pricing report not found"
            )
            
        # Run agent recommendation generation in background
        background_tasks.add_task(
            generate_experiment_recommendation, 
            db=db, 
            user_id=current_user.id,
            pricing_report_id=pricing_report_id
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

@router.post("/full-process", response_model=AgentResponse)
async def trigger_full_agent_process(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: schemas.UserBase = Depends(get_current_user)
):
    """Trigger the full agent process (all agents in sequence)"""
    try:
        # This endpoint will run all agents in proper sequence
        # Starting with the independent agents in parallel
        background_tasks.add_task(
            run_full_agent_process,
            db=db, 
            user_id=current_user.id
        )
        
        return {
            "success": True,
            "message": "Full agent process started",
            "data": None
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to start full agent process: {str(e)}"
        )

# Get the most recent reports from all agents
@router.get("/reports/latest", response_model=dict)
async def get_latest_reports(
    db: Session = Depends(get_db),
    current_user: schemas.UserBase = Depends(get_current_user)
):
    """Get the most recent reports from all agents"""
    try:
        # Get the most recent competitor report
        competitor_report = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.user_id == current_user.id
        ).order_by(models.CompetitorReport.created_at.desc()).first()
        
        # Get the most recent customer report
        customer_report = db.query(models.CustomerReport).filter(
            models.CustomerReport.user_id == current_user.id
        ).order_by(models.CustomerReport.created_at.desc()).first()
        
        # Get the most recent market report
        market_report = db.query(models.MarketReport).filter(
            models.MarketReport.user_id == current_user.id
        ).order_by(models.MarketReport.created_at.desc()).first()
        
        # Get the most recent pricing report
        pricing_report = db.query(models.PricingReport).filter(
            models.PricingReport.user_id == current_user.id
        ).order_by(models.PricingReport.created_at.desc()).first()
        
        # Get the most recent experiment recommendation
        experiment_recommendation = db.query(models.ExperimentRecommendation).filter(
            models.ExperimentRecommendation.user_id == current_user.id
        ).order_by(models.ExperimentRecommendation.created_at.desc()).first()
        
        return {
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
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get latest reports: {str(e)}"
        )

# Background task to run the full agent process
async def run_full_agent_process(db: Session, user_id: int):
    """Run the full agent process in proper sequence"""
    # First run the independent agents in parallel
    competitor_report = await generate_competitor_report(db, user_id)
    customer_report = await generate_customer_report(db, user_id)
    market_report = await generate_market_report(db, user_id)
    
    # Then run the pricing agent using the reports from the independent agents
    pricing_report = await generate_pricing_report(
        db, 
        user_id, 
        competitor_report_id=competitor_report.id,
        customer_report_id=customer_report.id,
        market_report_id=market_report.id
    )
    
    # Finally run the experiment agent using the pricing report
    experiment_recommendation = await generate_experiment_recommendation(
        db, 
        user_id, 
        pricing_report_id=pricing_report.id
    )
    
    return experiment_recommendation
