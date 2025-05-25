from agents import Agent
from .tool_wrapper import function_tool
from typing import List, Dict, Any, Optional
import os
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models as db_models
from .models import MarketAnalysis, SupplyChainFactor, CostTrend, MarketRecommendation
from .db_helper import DBHelper

@function_tool
def get_business_info(user_id: int, db_helper: DBHelper) -> str:
    """Get the business information for the specified user."""
    business_info = db_helper.get_business_info(user_id)
    return json.dumps(business_info)

@function_tool
def get_cogs_data(user_id: int, weeks: int, db_helper: DBHelper) -> str:
    """Get COGS data for the specified user for the last X weeks."""
    cogs_data = db_helper.get_cogs_data(user_id, weeks)
    return json.dumps(cogs_data)

@function_tool
def get_industry_data(industry: str, db_helper: DBHelper) -> str:
    """Get market data for the specified industry."""
    industry_data = db_helper.get_industry_data(industry)
    return json.dumps(industry_data)

@function_tool
def get_supply_chain_trends(db_helper: DBHelper) -> str:
    """Get general supply chain trends relevant to pricing decisions."""
    supply_chain_data = db_helper.get_supply_chain_trends()
    return json.dumps(supply_chain_data)

# Create the market agent
market_agent = Agent(
    name="Market Analysis Agent",
    instructions="""
    You are a Market Analysis Agent specializing in industry trends, economic forecasting, and supply chain analysis.
    
    Your task is to analyze market conditions, supply chain factors, and industry dynamics to provide pricing insights.
    Focus on:
    1. Cost factors that impact the business's industry
    2. Supply chain trends and disruptions
    3. Market pricing elasticity for similar businesses
    4. Industry-specific seasonal trends
    
    Use the provided tools to gather information about the business, costs, and industry data.
    Then analyze this data to provide comprehensive market insights.
    
    Focus on current market conditions and how they impact pricing decisions. Identify both risks and opportunities.
    """,
    model="gpt-4.1-nano",
    tools=[get_business_info, get_cogs_data, get_industry_data, get_supply_chain_trends],
    output_type=MarketAnalysis
)

# Function to save market report to database
def save_market_report(user_id: int, market_analysis: MarketAnalysis, db: Session) -> db_models.MarketReport:
    """Save the market analysis to the database."""
    db_helper = DBHelper(db)
    
    report_data = {
        "summary": market_analysis.summary,
        "supply_chain": [factor.model_dump() for factor in market_analysis.supply_chain],
        "cost_trends": [trend.model_dump() for trend in market_analysis.cost_trends],
        "competitive_landscape": market_analysis.competitive_landscape
    }
    
    return db_helper.save_market_report(user_id, report_data)
