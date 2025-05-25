from agents import Agent, function_tool
from typing import List, Dict, Any, Optional
import os
import json
from sqlalchemy.orm import Session
import models as db_models
from .models import CompetitorAnalysis, CompetitorInsight, CompetitorRecommendation

@function_tool
def get_business_info(user_id: int, db_helper: Any) -> str:
    """Get the business information for the specified user."""
    business_info = db_helper.get_business_info(user_id)
    return json.dumps(business_info)

@function_tool
def get_competitor_items(db_helper: Any) -> str:
    """Get all competitor items from the database."""
    competitor_data = db_helper.get_competitor_items()
    return json.dumps(competitor_data)

@function_tool
def get_our_items(user_id: int, db_helper: Any) -> str:
    """Get all items for the specified user."""
    items_data = db_helper.get_our_items(user_id)
    return json.dumps(items_data)

@function_tool
def get_price_history(user_id: int, db_helper: Any) -> str:
    """Get price history for the specified user's items."""
    history_data = db_helper.get_price_history(user_id)
    return json.dumps(history_data)

# Create the competitor agent
competitor_agent = Agent(
    name="Competitor Analysis Agent",
    instructions="""
    You are a Competitor Analysis Agent specializing in market research and competitive intelligence.
    
    Your task is to analyze competitor data, identify pricing trends, and provide insights on how the business's prices compare to competitors.
    Focus on:
    1. Price differences between our products and competitor products
    2. Recent price changes by competitors
    3. Categories where our prices are significantly higher or lower than competitors
    4. Recommendations for price adjustments based on competitor positioning
    
    Use the provided tools to gather information about the business, its products, competitors, and price history.
    Then analyze this data to provide comprehensive competitive insights.
    """,
    model="gpt-4.1-nano",
    tools=[get_business_info, get_competitor_items, get_our_items, get_price_history],
    output_type=CompetitorAnalysis
)

# This function is now handled by DBHelper
def save_competitor_report(user_id: int, competitor_analysis: CompetitorAnalysis, db: Session) -> db_models.CompetitorReport:
    """Legacy function for backward compatibility. Use DBHelper instead."""
    from .db_helper import DBHelper
    db_helper = DBHelper(db)
    report_data = competitor_analysis.model_dump()
    return db_helper.save_competitor_report(user_id, report_data)
