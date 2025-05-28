from agents import Agent, function_tool
from typing import List, Dict, Any, Optional
import os
import json
import requests
from sqlalchemy.orm import Session
import models as db_models
from .models import CompetitorAnalysis, CompetitorInsight, CompetitorRecommendation
import openai

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

@function_tool
def search_web(query: str) -> str:
    """Search the web for information about competitor menus, items and prices."""
    try:
        # Get OpenAI API key from environment
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return json.dumps({
                "error": "OpenAI API key not found in environment variables",
                "results": [
                    {
                        "title": f"Simulated search results for {query}",
                        "content": "This is a simulation. Set OPENAI_API_KEY to enable real web search.",
                        "url": f"https://example.com/search?q={query.replace(' ', '+')}"
                    }
                ]
            })
        
        # Configure OpenAI client with API key
        client = openai.OpenAI(api_key=api_key)
        
        # Create a completion with web browsing capability
        try:
            response = client.chat.completions.create(
                model="gpt-4-turbo",  # Use model version with browsing capability
                messages=[
                    {"role": "system", "content": "You are a research assistant that helps find information about business menu items and prices. Return only factual information without commentary."}, 
                    {"role": "user", "content": f"Search the web for: {query}. Focus on finding menu items and prices. Format the results as a clear, structured list."}
                ],
                tools=[{"type": "web_search"}],  # Enable web search capability
                tool_choice="auto"
            )
            
            # Extract the result
            result = response.choices[0].message.content
            return json.dumps({
                "query": query,
                "results": [{
                    "title": "Web Search Results", 
                    "content": result,
                    "source": "OpenAI Web Search"
                }]
            })
            
        except Exception as e:
            return json.dumps({
                "error": f"OpenAI API error: {str(e)}",
                "results": []
            })
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "results": []
        })

@function_tool
def lookup_competitor_menu(competitor_name: str, location: str = "") -> str:
    """Look up a specific competitor's menu information."""
    try:
        # Get OpenAI API key from environment
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return json.dumps({
                "error": "OpenAI API key not found in environment variables",
                "menu": [
                    {"category": "Beverages", "name": "Coffee", "price": "$3.50"},
                    {"category": "Food", "name": "Sandwich", "price": "$8.95"}
                ]
            })
        
        # Configure OpenAI client with API key
        client = openai.OpenAI(api_key=api_key)
        
        # Create a more specific search query for the menu
        query = f"{competitor_name} menu prices"
        if location:
            query += f" in {location}"
        
        try:
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "You are a specialized menu researcher. Return only the menu items with prices in a structured format. Each item should include category, name, and price."}, 
                    {"role": "user", "content": f"Find the menu for {competitor_name} {location if location else ''}. Return only a list of menu items with their prices in JSON-like format with categories."}
                ],
                tools=[{"type": "web_search"}],
                tool_choice="auto"
            )
            
            # Extract the result
            result = response.choices[0].message.content
            return json.dumps({
                "competitor": competitor_name,
                "location": location,
                "menu_data": result
            })
            
        except Exception as e:
            return json.dumps({
                "error": f"OpenAI API error: {str(e)}",
                "menu": []
            })
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "menu": []
        })

@function_tool
def analyze_market_pricing(business_type: str, location: str) -> str:
    """Analyze market pricing trends for a specific business type and location."""
    try:
        # Get OpenAI API key from environment
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return json.dumps({
                "error": "OpenAI API key not found in environment variables",
                "trends": [
                    {"category": "Coffee", "avg_price": "$3.75", "trend": "Increasing"},
                    {"category": "Sandwiches", "avg_price": "$9.50", "trend": "Stable"}
                ]
            })
        
        # Configure OpenAI client with API key
        client = openai.OpenAI(api_key=api_key)
        
        # Create a query for market pricing analysis
        query = f"current {business_type} average prices and pricing trends in {location}"
        
        try:
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "You are a market analyst specializing in pricing trends. Return information about average prices and pricing trends for different product categories."}, 
                    {"role": "user", "content": f"Research current {business_type} prices in {location}. Focus on average prices for different categories, price trends (increasing/decreasing/stable), and any seasonal factors affecting prices."}
                ],
                tools=[{"type": "web_search"}],
                tool_choice="auto"
            )
            
            # Extract the result
            result = response.choices[0].message.content
            return json.dumps({
                "business_type": business_type,
                "location": location,
                "market_analysis": result
            })
            
        except Exception as e:
            return json.dumps({
                "error": f"OpenAI API error: {str(e)}",
                "trends": []
            })
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "trends": []
        })

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
    
    First, use get_business_info to understand the business's details, particularly its name, industry, and LOCATION. The location information is crucial for finding relevant local competitors.
    
    You also have access to web search tools that allow you to find up-to-date information about competitors' menus and prices online. Use these tools to:
    - Find new competitors in the business's specific city/location that might not be in the database
    - Look up current menu prices for known competitors to compare with our prices
    - Research industry pricing trends in the business's specific region
    - Verify if competitors have recently changed their prices
    
    When searching, always include the business's specific location (city, state) in your queries, such as:
    - "[competitor name] menu prices in [city], [state]"
    - "[industry] prices in [city], [state]"
    - "best [industry] competitors in [city], [state]"
    
    Use the three search tools strategically:
    1. search_web: For general competitor information in the business's area
    2. lookup_competitor_menu: To get specific menu details for known competitors
    3. analyze_market_pricing: To understand broader pricing trends in the industry and location
    
    Combine both the database information and the web search results to provide comprehensive competitive insights.
    Include a detailed breakdown of how our prices compare to competitors, with specific examples and percentages.
    
    IMPORTANT: Any new competitor items you discover through web searches should be added to the "discovered_competitors" field in your response. For each discovered item, include:
    - competitor_name: The name of the competitor business
    - item_name: The name of the menu item
    - price: The price as a float (e.g., 4.99 not "$4.99")
    - category: The category of the item (e.g., "Beverages", "Entrees")
    - description: Brief description if available
    - similarity_score: Assign a similarity score (0-100) based on how similar this item is to items in our menu
    - url: Source URL if available
    
    This information will be automatically saved to our database for future reference and analysis.
    
    Your final analysis should help the business make informed pricing decisions based on a complete understanding of the competitive landscape.
    """,
    model="gpt-4-turbo",  # Using turbo model for web browsing capabilities
    tools=[get_business_info, get_competitor_items, get_our_items, get_price_history, search_web, lookup_competitor_menu, analyze_market_pricing],
    output_type=CompetitorAnalysis
)

# This function is now handled by DBHelper
def save_competitor_report(user_id: int, competitor_analysis: CompetitorAnalysis, db: Session) -> db_models.CompetitorReport:
    """Legacy function for backward compatibility. Use DBHelper instead."""
    from .db_helper import DBHelper
    db_helper = DBHelper(db)
    report_data = competitor_analysis.model_dump()
    return db_helper.save_competitor_report(user_id, report_data)
