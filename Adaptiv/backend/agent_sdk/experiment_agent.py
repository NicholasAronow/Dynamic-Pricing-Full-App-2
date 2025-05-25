from agents import Agent
from .tool_wrapper import function_tool
from typing import List, Dict, Any, Optional
import os
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models as db_models
from .models import ExperimentPlan, ExperimentProduct, EvaluationMetric, RiskAssessment
from .db_helper import DBHelper

@function_tool
def get_business_info(user_id: int, db_helper: DBHelper) -> str:
    """Get the business information for the specified user."""
    business_info = db_helper.get_business_info(user_id)
    return json.dumps(business_info)

@function_tool
def get_pricing_report(user_id: int, pricing_report_id: Optional[int], db_helper: DBHelper) -> str:
    """Get a specific pricing report or the most recent one for the specified user."""
    report_data = db_helper.get_pricing_report(user_id, pricing_report_id)
    return json.dumps(report_data)

@function_tool
def get_sales_patterns(user_id: int, days: int, db_helper: DBHelper) -> str:
    """Get sales patterns for the specified user from the last X days."""
    sales_data = db_helper.get_sales_patterns(user_id, days)
    return json.dumps(sales_data)

@function_tool
def get_upcoming_events(user_id: int, db_helper: DBHelper) -> str:
    """Get upcoming events that might impact sales from the most recent customer report."""
    events_data = db_helper.get_upcoming_events(user_id)
    return json.dumps(events_data)

# Create the experiment agent
experiment_agent = Agent(
    name="Experimental Pricing Agent",
    instructions="""
    You are an Experiment Design Agent specializing in A/B testing and pricing experiments.
    
    Your task is to design experiments to test pricing recommendations and determine optimal price points.
    You will:
    1. Review the pricing report and its recommendations
    2. Design an experiment plan to test key pricing hypotheses
    3. Specify implementation details, including timeframes and success metrics
    4. Recommend which items to include in the experiment
    
    Your experiment plan should be practical, time-bound, and provide clear success criteria.
    Include specific start and evaluation dates, items to test, and pricing levels to implement.
    
    Provide specific dates for implementation and evaluation.
    """,
    model="gpt-4.1-nano",
    tools=[
        get_business_info, 
        get_pricing_report, 
        get_sales_patterns,
        get_upcoming_events
    ],
    output_type=ExperimentPlan
)

# Function to save experiment recommendation to database
def save_experiment_plan(
    user_id: int, 
    experiment_plan: ExperimentPlan, 
    pricing_report_id: Optional[int],
    db: Session
) -> db_models.ExperimentRecommendation:
    """Save the experiment plan to the database."""
    db_helper = DBHelper(db)
    
    # Determine start and evaluation dates from the first implementation recommendation
    start_date = datetime.now()
    evaluation_date = datetime.now() + timedelta(days=14)  # Default to 2 weeks
    
    if experiment_plan.implementation and len(experiment_plan.implementation) > 0:
        # Parse the dates from the first implementation recommendation
        try:
            implementation_date_str = experiment_plan.implementation[0].implementation_date
            evaluation_date_str = experiment_plan.implementation[0].evaluation_date
            
            if implementation_date_str:
                start_date = datetime.fromisoformat(implementation_date_str.replace("Z", "+00:00"))
            
            if evaluation_date_str:
                evaluation_date = datetime.fromisoformat(evaluation_date_str.replace("Z", "+00:00"))
        except:
            # Use default dates if parsing fails
            pass
    
    # Prepare the plan data for the database
    plan_data = {
        "summary": experiment_plan.summary,
        "start_date": start_date,
        "evaluation_date": evaluation_date,
        "implementation": [item.model_dump() for item in experiment_plan.implementation],
        "evaluation_criteria": [metric.model_dump() for metric in experiment_plan.evaluation_criteria],
        "risks": [risk.model_dump() for risk in experiment_plan.risks],
        "pricing_report_id": pricing_report_id
    }
    
    # Use the DBHelper to save the experiment plan
    return db_helper.save_experiment_plan(user_id, plan_data)
