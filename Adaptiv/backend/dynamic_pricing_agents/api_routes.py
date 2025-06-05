"""
API Routes for Dynamic Pricing Agent System
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from database import get_db
from auth import get_current_user
import models
from .orchestrator import DynamicPricingOrchestrator
from .task_manager import running_tasks  # Import from shared module

# Initialize router
router = APIRouter(
    tags=["dynamic-pricing-agents"]
)

# Initialize orchestrator (singleton)
orchestrator = DynamicPricingOrchestrator()

# Logger
logger = logging.getLogger(__name__)

@router.post("/run-full-analysis")
async def run_full_analysis(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Trigger a full dynamic pricing analysis with all agents
    """
    user_id = current_user.id
    
    # Check if analysis is already running for this user
    if user_id in running_tasks and running_tasks[user_id].get('status') == 'running':
        return {
            "status": "already_running",
            "message": "Analysis is already in progress for this user",
            "task_id": running_tasks[user_id].get('task_id')
        }
    
    # Create task ID
    task_id = f"task_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Store task info
    running_tasks[user_id] = {
        'task_id': task_id,
        'status': 'running',
        'started_at': datetime.now().isoformat()
    }
    
    # Run analysis in background
    background_tasks.add_task(
        _run_analysis_task,
        user_id,
        task_id,
        "api_trigger"
    )
    
    return {
        "status": "started",
        "task_id": task_id,
        "message": "Dynamic pricing analysis started successfully"
    }


@router.post("/run-specific-agents")
async def run_specific_agents(
    agent_names: List[str],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Run specific agents only
    """
    user_id = current_user.id
    
    # Validate agent names
    valid_agents = ['data_collection', 'market_analysis', 'pricing_strategy', 
                    'performance_monitor', 'experimentation']
    invalid_agents = [name for name in agent_names if name not in valid_agents]
    
    if invalid_agents:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent names: {invalid_agents}. Valid agents are: {valid_agents}"
        )
    
    try:
        results = orchestrator.run_specific_agents(db, user_id, agent_names)
        
        return {
            "status": "success",
            "agents_executed": agent_names,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error running specific agents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis-status/{task_id}")
async def get_analysis_status(
    task_id: str,
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the status of a running analysis task
    """
    user_id = current_user.id
    
    # Check if task exists for this user
    if user_id not in running_tasks:
        return {
            "status": "not_found",
            "message": "No analysis task found for this user"
        }
    
    task_info = running_tasks[user_id]
    
    if task_info.get('task_id') != task_id:
        return {
            "status": "not_found",
            "message": "Task ID does not match current task"
        }
    
    return {
        "task_id": task_info.get('task_id'),
        "status": task_info.get('status'),
        "message": task_info.get('message', ''),
        "started_at": task_info.get('started_at'),
        "completed_at": task_info.get('completed_at'),
        "results": task_info.get('results') if task_info.get('status') == 'completed' else None,
        "error": task_info.get('error') if task_info.get('status') == 'error' else None
    }


@router.get("/latest-results")
async def get_latest_results(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the latest analysis results for the current user
    """
    user_id = current_user.id
    
    # Check if we have cached results in memory
    if user_id in running_tasks:
        task_info = running_tasks[user_id]
        if task_info.get('status') == 'completed' and 'results' in task_info:
            logger.info(f"Returning cached results for user {user_id}")
            return {
                "status": "success",
                "source": "cache",
                "results": task_info['results']
            }
    
    # No cached results, try to retrieve from database
    try:
        logger.info(f"Retrieving latest analysis results from database for user {user_id}")
        
        # Get the latest data collection snapshot
        latest_data_snapshot = db.query(models.DataCollectionSnapshot)\
            .filter(models.DataCollectionSnapshot.user_id == user_id)\
            .order_by(models.DataCollectionSnapshot.snapshot_date.desc())\
            .first()
            
        # Get the latest market analysis snapshot
        latest_market_snapshot = db.query(models.MarketAnalysisSnapshot)\
            .filter(models.MarketAnalysisSnapshot.user_id == user_id)\
            .order_by(models.MarketAnalysisSnapshot.analysis_date.desc())\
            .first()
            
        # Get pricing recommendations (limit to 50 most recent)
        recent_recommendations = db.query(models.PricingRecommendation)\
            .filter(models.PricingRecommendation.user_id == user_id)\
            .order_by(models.PricingRecommendation.recommendation_date.desc())\
            .limit(50)\
            .all()
            
        # Get performance data
        latest_performance = db.query(models.PerformanceBaseline)\
            .filter(models.PerformanceBaseline.user_id == user_id)\
            .order_by(models.PerformanceBaseline.baseline_date.desc())\
            .first()
            
        # Check if we have results
        if not (latest_data_snapshot or latest_market_snapshot or recent_recommendations):
            logger.info(f"No analysis data found in database for user {user_id}")
            return {
                "status": "no_results",
                "message": "No previous analysis results found. Please run a new analysis.",
                "timestamp": datetime.now().isoformat()
            }
        
        # Get the latest date from either market analysis or recommendations
        analysis_date = None
        if latest_market_snapshot and latest_market_snapshot.analysis_date:
            analysis_date = latest_market_snapshot.analysis_date
        elif recent_recommendations and recent_recommendations[0].recommendation_date:
            analysis_date = recent_recommendations[0].recommendation_date
        elif latest_data_snapshot and latest_data_snapshot.snapshot_date:
            analysis_date = latest_data_snapshot.snapshot_date
            
        # Compile results from database records
        compiled_results = {
            "status": "success",
            "source": "database",
            "timestamp": datetime.now().isoformat(),
            "analysis_date": analysis_date.isoformat() if analysis_date else None,
            "results": {
                "executive_summary": {
                    "overall_status": latest_market_snapshot.market_position if latest_market_snapshot else "stable",
                    "revenue_trend": "improving" if latest_market_snapshot and latest_market_snapshot.avg_price_vs_market > 0 else "stable",
                    "key_opportunities": latest_market_snapshot.competitive_opportunities if latest_market_snapshot and latest_market_snapshot.competitive_opportunities else [],
                    "immediate_actions": [],
                    "risk_factors": latest_market_snapshot.competitive_threats if latest_market_snapshot and latest_market_snapshot.competitive_threats else []
                },
                "consolidated_recommendations": [],
                "next_steps": [
                    {"step": 1, "action": "Review pricing recommendations", "expected_impact": "Increased revenue", "timeline": "Immediate"}
                ]
            },
            "agent_statuses": [
                {"name": "Data Collection", "status": "completed", "lastRun": latest_data_snapshot.snapshot_date.isoformat() if latest_data_snapshot else datetime.now().isoformat()},
                {"name": "Market Analysis", "status": "completed", "lastRun": latest_market_snapshot.analysis_date.isoformat() if latest_market_snapshot else datetime.now().isoformat()},
                {"name": "Pricing Strategy", "status": "completed", "lastRun": recent_recommendations[0].recommendation_date.isoformat() if recent_recommendations else datetime.now().isoformat()},
                {"name": "Performance Monitor", "status": "completed", "lastRun": latest_performance.baseline_date.isoformat() if latest_performance else datetime.now().isoformat()},
                {"name": "Experimentation", "status": "completed", "lastRun": datetime.now().isoformat()}
            ]
        }
        
        # Add recommendations to the results
        if recent_recommendations:
            for rec in recent_recommendations:
                compiled_results["results"]["consolidated_recommendations"].append({
                    "priority": "high" if rec.price_change_percent > 10 else "medium" if rec.price_change_percent > 5 else "low",
                    "recommendation": f"Adjust price for {rec.item.name if rec.item else 'item'} from ${rec.current_price:.2f} to ${rec.recommended_price:.2f}",
                    "expected_impact": f"${rec.expected_revenue_change:.2f} revenue increase" if rec.expected_revenue_change else "Improved pricing alignment",
                    "category": "pricing"
                })
        
        # Cache these results for future quick access
        running_tasks[user_id] = {
            'task_id': f"historical_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'status': 'completed',
            'results': compiled_results,
            'started_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat(),
            'message': 'Retrieved from database'
        }
        
        logger.info(f"Successfully retrieved and compiled analysis results from database for user {user_id}")
        return compiled_results
        
    except Exception as e:
        logger.error(f"Error retrieving analysis results from database: {str(e)}")
        return {
            "status": "error",
            "message": f"Error retrieving previous analysis results: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@router.post("/agent/{agent_name}/action")
async def trigger_agent_action(
    agent_name: str,
    action: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Trigger a specific action for an agent
    """
    user_id = current_user.id
    
    # Validate agent name
    valid_agents = ['data_collection', 'market_analysis', 'pricing_strategy', 
                    'performance_monitor', 'experimentation']
    
    if agent_name not in valid_agents:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent name: {agent_name}"
        )
    
    try:
        # Run the specific agent with custom action
        context = {
            "db": db,
            "user_id": user_id,
            "action": action
        }
        
        agent = orchestrator.agents[agent_name]
        result = agent.process(context)
        
        return {
            "status": "success",
            "agent": agent_name,
            "action": action,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error triggering agent action: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-capabilities")
async def get_agent_capabilities() -> Dict[str, Any]:
    """
    Get information about available agents and their capabilities
    """
    capabilities = {
        "data_collection": {
            "name": "Data Collection Agent",
            "description": "Gathers POS data, competitor pricing, and historical price changes",
            "actions": ["collect_pos_data", "collect_competitor_data", "collect_price_history"]
        },
        "market_analysis": {
            "name": "Market Analysis Agent",
            "description": "Analyzes market conditions and competitive landscape",
            "actions": ["analyze_competitors", "identify_trends", "assess_market_position"]
        },
        "pricing_strategy": {
            "name": "Pricing Strategy Agent",
            "description": "Develops and optimizes pricing strategies",
            "actions": ["generate_recommendations", "optimize_prices", "simulate_scenarios"]
        },
        "performance_monitor": {
            "name": "Performance Monitor Agent",
            "description": "Tracks and analyzes the impact of pricing changes",
            "actions": ["monitor_metrics", "detect_anomalies", "generate_alerts"]
        },
        "experimentation": {
            "name": "Experimentation Agent",
            "description": "Manages pricing experiments and A/B tests",
            "actions": ["design_experiments", "analyze_results", "recommend_rollouts"]
        }
    }
    
    return {
        "agents": capabilities,
        "orchestration_modes": ["full_analysis", "specific_agents", "custom_workflow"]
    }


@router.get("/execution-history")
async def get_execution_history(
    limit: int = 10,
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the execution history of agent runs
    """
    # Filter history for current user
    user_history = [
        record for record in orchestrator.execution_history
        if record.get('user_id') == current_user.id
    ]
    
    # Sort by timestamp (most recent first)
    user_history.sort(key=lambda x: x.get('start_time', ''), reverse=True)
    
    return {
        "history": user_history[:limit],
        "total_executions": len(user_history)
    }


# Background task function
def _run_analysis_task(user_id: int, task_id: str, trigger_source: str):
    """
    Background task to run the full analysis
    """
    # Import get_db inside the function to avoid circular imports
    from database import get_db
    
    # Create a fresh database session
    db = next(get_db())
    try:
        # Run the analysis
        results = orchestrator.run_full_analysis(db, user_id, trigger_source)
        
        # Update task status
        if user_id in running_tasks:
            # Ensure we have proper results structure to return
            if not results.get('executive_summary', {}):
                logger.warning("No executive summary found in results, adding default")
            if not results.get('consolidated_recommendations', []):
                logger.warning("No recommendations found in results, adding default")
            if not results.get('next_steps', []):
                logger.warning("No next steps found in results, adding default")
                
            # Extract the 'results' field from the orchestrator output if it exists
            results_data = results.get('results', results)
            
            # Log the actual results structure
            logger.info(f"Analysis results structure: {list(results_data.keys())}")
            
            running_tasks[user_id].update({
                'status': 'completed',
                'completed_at': datetime.now().isoformat(),
                'results': {
                    'executive_summary': results_data.get('executive_summary', {}),
                    'consolidated_recommendations': results_data.get('consolidated_recommendations', []),
                    'next_steps': results_data.get('next_steps', [])
                }
            })
            
            # Log what we're returning to the frontend
            logger.info(f"Task status updated with results: {running_tasks[user_id]['results'].keys()}")
            logger.info(f"Executive summary: {bool(running_tasks[user_id]['results']['executive_summary'])}")
            logger.info(f"Recommendations length: {len(running_tasks[user_id]['results']['consolidated_recommendations'])}")
            logger.info(f"Next steps length: {len(running_tasks[user_id]['results']['next_steps'])}")
            
            
    except Exception as e:
        logger.error(f"Error in background analysis task: {str(e)}")
        
        # Update task status with error
        if user_id in running_tasks:
            running_tasks[user_id].update({
                'status': 'error',
                'completed_at': datetime.now().isoformat(),
                'error': str(e)
            })
