from agents import Agent
from .tool_wrapper import function_tool
from typing import List, Dict, Any, Optional
import os
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models as db_models
from .models import PricingAnalysis, PriceRecommendation, PricingInsight, ImplementationAdvice
from .db_helper import DBHelper

@function_tool
def get_business_info(user_id: int, db_helper: DBHelper) -> str:
    """Get the business information for the specified user."""
    business_info = db_helper.get_business_info(user_id)
    return json.dumps(business_info)

@function_tool
def get_items_with_sales(user_id: int, days: int, db_helper: DBHelper) -> str:
    """Get all items with their sales data for the specified user from the last X days."""
    # Get our items and recent orders using the helper methods
    items_data = db_helper.get_our_items(user_id)
    orders_data = db_helper.get_recent_orders(user_id, days)
    
    # Create a map of item sales
    item_sales = {}
    for order in orders_data:
        for order_item in order.get('items', []):
            item_id = order_item.get('item_id')
            if not item_id:
                continue
                
            if item_id not in item_sales:
                item_sales[item_id] = {
                    "quantity": 0,
                    "revenue": 0
                }
            item_sales[item_id]["quantity"] += order_item.get('quantity', 0)
            item_sales[item_id]["revenue"] += order_item.get('quantity', 0) * order_item.get('unit_price', 0)
    # Compile item data with sales
    result_items = []
    for item in items_data:
        item_id = item.get('id')
        result_items.append({
            "id": item_id,
            "name": item.get('name', ''),
            "category": item.get('category', ''),
            "current_price": item.get('current_price', 0.0),
            "cost": item.get('cost', 0.0),
            "sales_quantity": item_sales.get(item_id, {}).get("quantity", 0),
            "sales_revenue": item_sales.get(item_id, {}).get("revenue", 0)
        })
    
    return json.dumps({
        "items": result_items,
        "days_analyzed": days
    })

@function_tool
def get_competitor_report(user_id: int, db_helper: DBHelper) -> str:
    """Get the most recent competitor report for the specified user."""
    # In a real implementation, we would add a get_competitor_report method to DBHelper
    # For now, we'll construct a simple response
    competitor_items = db_helper.get_competitor_items()
    
    return json.dumps({
        "summary": "Competitor analysis summary",
        "insights": ["Competitors are focusing on value pricing", "Several new competitors have entered the market"],
        "competitor_data": competitor_items,
        "created_at": datetime.now().isoformat()
    })

@function_tool
def get_customer_report(user_id: int, db_helper: DBHelper) -> str:
    """Get the most recent customer report for the specified user."""
    # In a real implementation, we would add a get_customer_report method to DBHelper
    # For now, we'll return information about upcoming events
    upcoming_events = db_helper.get_upcoming_events(user_id)
    
    return json.dumps({
        "summary": "Customer analysis summary",
        "demographics": [
            {"segment": "Young adults", "percentage": 35},
            {"segment": "Families", "percentage": 40},
            {"segment": "Seniors", "percentage": 25}
        ],
        "price_sensitivity": {"level": "medium", "notes": "Customers are somewhat price-sensitive, but value quality"},
        "upcoming_events": upcoming_events.get("events", [])
    })

@function_tool
def get_market_report(user_id: int, db_helper: DBHelper) -> str:
    """Get the most recent market report for the specified user."""
    # In a real implementation, we would add a get_market_report method to DBHelper
    # For now, we'll construct a sample response using related data from DBHelper
    industry_data = db_helper.get_industry_data("restaurants")  # Default to restaurants
    supply_chain_trends = db_helper.get_supply_chain_trends()
    
    return json.dumps({
        "summary": "Market analysis summary",
        "market_trends": {
            "growth_rate": industry_data.get("growth_rate", 0),
            "current_trends": industry_data.get("current_trends", [])
        },
        "supply_chain": supply_chain_trends,
        "created_at": datetime.now().isoformat()
    })

@function_tool
def get_recent_cogs(user_id: int, db_helper: DBHelper) -> str:
    """Get the most recent COGS data for the specified user."""
    # Get the most recent COGS data using DBHelper
    cogs_data = db_helper.get_cogs_data(user_id, weeks=1)
    
    if not cogs_data or len(cogs_data) == 0:
        return json.dumps({"error": "No COGS data found"})
    
    # Return the first (most recent) COGS entry
    return json.dumps(cogs_data[0])

# Create the pricing agent
pricing_agent = Agent(
    name="Pricing Agent",
    instructions="""
    You are a Pricing Strategy Agent specializing in dynamic pricing and revenue optimization.
    
    Your task is to analyze data from various sources and recommend optimal pricing adjustments.
    You will:
    1. Review reports from the competitor, customer, and market agents
    2. Analyze recent sales data and price elasticity
    3. Consider seasonal factors and upcoming events
    4. Identify items that are candidates for price changes
    
    Then, provide specific, actionable price change recommendations with clear rationales.
    Your recommendations should balance maximizing revenue, maintaining competitiveness, and ensuring customer satisfaction.
    Include:
    - Which items should have price changes
    - The specific price changes (both absolute and percentage)
    - Rationale for each recommendation
    - Implementation guidance (timing, sequencing, monitoring)
    
    Focus on creating actionable recommendations with specific price points. Be sure to justify each recommendation. If an item is best off with no change, do not recommend a change, or show that product with zero change. Be as detailed in your rationale as possible.
    """,
    model="gpt-4.1-nano",
    tools=[
        get_business_info, 
        get_items_with_sales, 
        get_competitor_report, 
        get_customer_report, 
        get_market_report
    ],
    output_type=PricingAnalysis
)

# Function to save pricing report to database
def save_pricing_report(
    user_id: int, 
    pricing_analysis: PricingAnalysis, 
    competitor_report_id: Optional[int],
    customer_report_id: Optional[int],
    market_report_id: Optional[int],
    db: Session
) -> db_models.PricingReport:
    """Save the pricing analysis to the database."""
    db_helper = DBHelper(db)
    
    report_data = {
        "summary": pricing_analysis.summary,
        "product_recommendations": [rec.model_dump() for rec in pricing_analysis.product_recommendations],
        "pricing_insights": [insight.model_dump() for insight in pricing_analysis.pricing_insights],
        "implementation": pricing_analysis.implementation.model_dump(),
        "competitor_report_id": competitor_report_id,
        "customer_report_id": customer_report_id,
        "market_report_id": market_report_id
    }
    
    return db_helper.save_pricing_report(user_id, report_data)
