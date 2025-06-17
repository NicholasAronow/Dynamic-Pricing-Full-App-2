"""
API Routes for Dynamic Pricing Agent System
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
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


@router.post("/run-agent")
async def run_agent(
    request_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Run a specific agent with parameters
    """
    user_id = current_user.id
    
    # Extract agent_name, action and parameters
    agent_name = request_data.get("agent_name")
    action = request_data.get("action", "process")
    parameters = request_data.get("parameters", {})
    
    # Validate agent name
    if agent_name not in orchestrator.agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_name}' not found. Available agents: {list(orchestrator.agents.keys())}"
        )
    
    try:
        # Get the agent instance
        agent_instance = orchestrator.agents[agent_name]
        
        # Fetch business profile data if available
        try:
            business_profile = db.query(models.BusinessProfile).filter(
                models.BusinessProfile.user_id == user_id
            ).first()
            
            business_context = {}
            if business_profile:
                business_context = {
                    "business_name": business_profile.business_name,
                    "industry": business_profile.industry,
                    "company_size": business_profile.company_size,
                    "location": f"{business_profile.city or ''}, {business_profile.state or ''}, {business_profile.country or 'USA'}".strip().strip(','),
                    "city": business_profile.city,
                    "state": business_profile.state,
                    "country": business_profile.country or "USA"
                }
        except Exception as e:
            logger.error(f"Error fetching business profile: {e}")
            business_context = {}
            
        # Debug log to understand the User object
        logger.info(f"User object attributes: {dir(current_user)}")
        logger.info(f"User ID: {user_id}")
        
        # Create execution context with minimal required parameters
        # and handle potential missing attributes safely
        context = {
            "db": db,
            "user_id": user_id,
            # Only include email if it exists, otherwise use id as a string
            "email": getattr(current_user, 'email', f'user_{user_id}@example.com'),
            "business_context": business_context,
            "parameters": parameters
        }
        
        # Log the execution details
        logger.info(f"Running agent {agent_name} with action {action} for user {user_id}")
        logger.info(f"Agent context keys: {list(context.keys())}")
        
        try:
            # Execute the agent's process method
            if action == "process":
                result = await agent_instance.process(context)
                logger.info(f"Agent {agent_name} completed successfully with result keys: {list(result.keys()) if isinstance(result, dict) else 'non-dict result'}")
                return result
            else:
                # For future, could support other actions
                raise HTTPException(
                    status_code=400,
                    detail=f"Action '{action}' not supported for agent '{agent_name}'"
                )
        except Exception as e:
            logger.error(f"Error executing agent {agent_name}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Error executing agent {agent_name}: {str(e)}"
            }
        
    except Exception as e:
        logger.error(f"Error running agent {agent_name}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
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
        },
        "competitor_agent": {
            "name": "Competitor Analysis Agent",
            "description": "Analyzes data collection output to identify items that would benefit from competitor analysis and generates detailed competitive insights",
            "actions": ["analyze_data", "identify_competitor_candidates", "analyze_competitive_landscape", "calculate_pricing_gaps", "provide_positioning_recommendations"]
        },
        "test_web_agent": {
            "name": "Web Search Test Agent",
            "description": "Demonstrates web search capabilities using the OpenAI Agents SDK",
            "actions": ["search_web", "summarize_results"]
        },
        "competitor_tracking_db": {
            "name": "Competitor Tracking Agent",
            "description": "Analyzes menu items against competitors to provide detailed pricing comparisons and recommendations",
            "actions": ["analyze_competitor_prices", "determine_competitive_positioning", "provide_pricing_recommendations"]
        },
        "aggregate_pricing": {
            "name": "Aggregate Pricing Agent",
            "description": "Orchestrates and aggregates outputs from data collection, competitor analysis, and market research agents into a consolidated view",
            "actions": ["run_data_collection", "run_competitor_analysis", "run_market_research", "aggregate_results"]
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


@router.post("/test-agent/{agent_name}")
async def test_agent(
    agent_name: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Test a specific agent and return its output
    
    Allows testing individual agents with direct output display
    """
    # Validate agent name
    if agent_name not in orchestrator.agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_name}' not found. Available agents: {list(orchestrator.agents.keys())}"
        )
    
    user_id = current_user.id
    start_time = datetime.now()
    agent_instance = orchestrator.agents[agent_name]
    
    try:
        # Fetch business profile data if available
        try:
            business_profile = db.query(models.BusinessProfile).filter(
                models.BusinessProfile.user_id == user_id
            ).first()
            
            business_context = {}
            if business_profile:
                business_context = {
                    "business_name": business_profile.business_name,
                    "industry": business_profile.industry,
                    "company_size": business_profile.company_size,
                    "city": business_profile.city,
                    "state": business_profile.state,
                    "country": business_profile.country or "USA",
                    "location": f"{business_profile.city or ''}, {business_profile.state or ''}, {business_profile.country or 'USA'}".strip().strip(',')
                }
                logging.info(f"Found business profile for user {user_id}: {business_context['business_name']} in {business_context['location']}")
        except Exception as e:
            logging.error(f"Error fetching business profile: {e}")
            business_context = {}
            
        # Create execution context with key parameters needed by the agent
        # Get username from current_user if available or use user_id as fallback
        username = getattr(current_user, 'username', None) or getattr(current_user, 'email', None) or str(user_id)
        
        context = {
            "user_id": user_id,
            "username": username,
            "test_mode": True,  # Flag to indicate test mode
            "request_timestamp": start_time.isoformat(),
            **business_context,  # Add business profile data if available
            # Add any other context needed by the agent
        }
        
        # Add db to context instead of passing it directly to process method
        context["db"] = db
        
        # Run the agent with context - handle both async and sync process methods
        if asyncio.iscoroutinefunction(agent_instance.process):
            agent_output = await agent_instance.process(context)
        else:
            agent_output = agent_instance.process(context)
        
        # Record test execution
        test_record = {
            "test_id": f"test_{agent_name}_{start_time.strftime('%Y%m%d_%H%M%S')}",
            "user_id": user_id,
            "agent_name": agent_name,
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - start_time).total_seconds(),
            "status": "success"
        }
        
        return {
            "status": "success",
            "agent_name": agent_name,
            "output": agent_output,
            "execution_details": test_record
        }
        
    except Exception as e:
        logger.exception(f"Error testing agent {agent_name}: {str(e)}")
        return {
            "status": "error",
            "agent_name": agent_name,
            "error": str(e),
            "error_type": type(e).__name__
        }


@router.post("/llm-analysis")
async def generate_llm_analysis(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generate an LLM analysis of the provided data using the appropriate agent
    """
    try:
        user_id = current_user.id
        
        # Extract the agent name from the data
        agent_name = data.get("agent_name", "data_collection")
        
        # Extract the actual data to analyze
        agent_data = data
        if isinstance(data, dict) and data.get("output"):
            agent_data = data.get("output")
        
        # Get the appropriate agent based on agent_name
        if agent_name == "openai_agent":
            # Special handling for OpenAI agent output
            return analyze_openai_agent_output(agent_data)
        else:
            # Default to data_collection agent for other outputs
            data_collection_agent = orchestrator.agents.get("data_collection")
            if not data_collection_agent:
                raise HTTPException(
                    status_code=404,
                    detail="Data Collection Agent not found"
                )
                
            # Call the analyze_with_llm method
            result = data_collection_agent.analyze_with_llm(agent_data)
            
            return result
        
    except Exception as e:
        logger.exception(f"Error generating LLM analysis: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }


def analyze_openai_agent_output(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze OpenAI agent output with a formatted summary
    """
    try:
        # Extract relevant information from the OpenAI agent output
        research_candidates = data.get("research_candidates", [])
        research_results = data.get("research_results", {})
        status = data.get("status", "unknown")
        message = data.get("message", "")
        
        # Generate a formatted analysis
        analysis = [
            "## OpenAI Agent Output Analysis\n\n",
            f"**Status**: {status}\n\n",
            f"**Message**: {message}\n\n",
        ]
        
        # Analyze research candidates
        if research_candidates:
            analysis.append(f"### Research Candidates Identified ({len(research_candidates)})\n\n")
            
            for i, candidate in enumerate(research_candidates):
                item_name = candidate.get("item_name", f"Item {i+1}")
                item_id = candidate.get("item_id", "unknown")
                reason = candidate.get("research_reason", "No reason specified")
                
                analysis.append(f"**{item_name}** (ID: {item_id})\n")
                analysis.append(f"- Research Reason: {reason}\n")
                
                # Add other relevant details
                if "price" in candidate:
                    analysis.append(f"- Current Price: ${candidate.get('price', 'N/A')}\n")
                if "elasticity" in candidate:
                    analysis.append(f"- Elasticity: {candidate.get('elasticity', 'N/A')}\n")
                analysis.append("\n")
        else:
            analysis.append("### No Research Candidates Identified\n\n")
            
        # Analyze research results if available
        if isinstance(research_results, dict) and research_results:
            analysis.append("### Research Results\n\n")
            
            # Check if summary or recommendations exist
            if "summary" in research_results:
                analysis.append(f"**Summary**: {research_results['summary']}\n\n")
            if "recommendations" in research_results and research_results["recommendations"]:
                analysis.append("**Recommendations**:\n")
                for rec in research_results["recommendations"]:
                    analysis.append(f"- {rec}\n")
                analysis.append("\n")
                
            # Check for individual research items
            if "items" in research_results and research_results["items"]:
                analysis.append("**Detailed Research**:\n\n")
                for item in research_results["items"]:
                    item_name = item.get("item_name", "Unknown item")
                    analysis.append(f"**{item_name}**:\n")
                    
                    # Market trends
                    if "market_trends" in item:
                        analysis.append(f"- Market Trends: {item['market_trends']}\n")
                    
                    # Competitor information
                    if "competitor_info" in item:
                        analysis.append(f"- Competitor Info: {item['competitor_info']}\n")
                    
                    # Supply chain insights
                    if "supply_chain_insights" in item:
                        analysis.append(f"- Supply Chain: {item['supply_chain_insights']}\n")
                    
                    # Events
                    if "relevant_events" in item:
                        analysis.append(f"- Relevant Events: {item['relevant_events']}\n")
                    
                    # Price recommendation
                    if "price_recommendation" in item:
                        analysis.append(f"- Price Recommendation: {item['price_recommendation']}\n")
                    
                    analysis.append("\n")
        
        # Final conclusion
        analysis.append("### Conclusion\n\n")
        if status == "success":
            analysis.append("The OpenAI agent successfully identified items for market research ")
            if "research_results" in data and data["research_results"]:
                analysis.append("and conducted detailed market analysis to inform pricing decisions. ")
            else:
                analysis.append("but did not conduct the full market research phase. ")
                
            analysis.append("The agent can identify promising candidates for price adjustments based on ")
            analysis.append("elasticity, market position, and other factors.")
        else:
            analysis.append("The agent encountered issues during execution. Please check the error messages ")
            analysis.append("and consider providing an OpenAI API key if one is required.")
        
        return {
            "content": "".join(analysis),
            "status": "success"
        }
        
    except Exception as e:
        logger.exception(f"Error analyzing OpenAI agent output: {str(e)}")
        return {
            "content": f"Error analyzing OpenAI agent output: {str(e)}",
            "status": "error"
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
