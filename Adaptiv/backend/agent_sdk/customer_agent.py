from agents import Agent
from .tool_wrapper import function_tool
from typing import List, Dict, Any, Optional
import os
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models as db_models
from .models import CustomerAnalysis, DemographicSegment, CustomerEvent, CustomerRecommendation
from .db_helper import DBHelper

@function_tool
def get_business_info(user_id: int, db_helper: DBHelper) -> str:
    """Get the business information for the specified user."""
    business_info = db_helper.get_business_info(user_id)
    return json.dumps(business_info)

@function_tool
def get_recent_orders(user_id: int, days: int, db_helper: DBHelper) -> str:
    """Get orders for the specified user from the last X days."""
    orders_data = db_helper.get_recent_orders(user_id, days)
    return json.dumps(orders_data)

@function_tool
def get_order_by_day_of_week(user_id: int, days: int, db_helper: DBHelper) -> str:
    """Get order distribution by day of week for the specified user from the last X days."""
    result = db_helper.get_orders_by_day_of_week(user_id, days)
    return json.dumps(result)

@function_tool
def get_current_time_and_location(user_id: int, db_helper: DBHelper) -> str:
    """Get the current time and location for the business to help with local event analysis."""
    time_location_data = db_helper.get_current_time_and_location(user_id)
    return json.dumps(time_location_data)

# Create the customer agent
customer_agent = Agent(
    name="Customer Analysis Agent",
    instructions="""
    You are a Customer Analysis Agent specializing in customer behavior and demographic analysis.
    
    Your task is to analyze customer data, identify demographic patterns, anticipate upcoming events that
    could impact customer behavior, and detect trends in customer preferences.
    
    Focus on:
    1. Key demographic groups and their characteristics
    2. Upcoming events or holidays that could impact demand
    3. Patterns in when and how customers order
    4. Changes in preferences over time
    
    Use the provided tools to gather information about the business, recent orders, and timing patterns.
    Then analyze this data to provide comprehensive customer insights.
    
    When analyzing upcoming events, consider the current date and what events will be occurring in the near future
    that could impact this business based on its industry and other factors.
    """,
    model="gpt-4.1-nano",
    tools=[get_business_info, get_recent_orders, get_order_by_day_of_week, get_current_time_and_location],
    output_type=CustomerAnalysis
)

# Function to save customer report to database
def save_customer_report(user_id: int, customer_analysis: CustomerAnalysis, db: Session) -> db_models.CustomerReport:
    """Save the customer analysis to the database."""
    db_helper = DBHelper(db)
    
    report_data = {
        "summary": customer_analysis.summary,
        "demographics": [demo.model_dump() for demo in customer_analysis.demographics],
        "price_sensitivity": customer_analysis.price_sensitivity,
        "upcoming_events": [event.model_dump() for event in customer_analysis.upcoming_events]
    }
    
    return db_helper.save_customer_report(user_id, report_data)
