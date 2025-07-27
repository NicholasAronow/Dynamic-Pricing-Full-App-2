#!/usr/bin/env python3
"""
Example usage of LangGraph tools testing

This script demonstrates how to use individual tools programmatically
for development and debugging purposes.
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.langgraph_service_v2 import PricingTools, DatabaseTools
from config.database import get_db

def example_pricing_tools():
    """Example of using pricing tools"""
    print("🔧 Testing Pricing Tools\n")
    
    tools = PricingTools()
    
    # Test web search
    result = tools.search_web_for_pricing("premium coffee")
    print("Web Search Result:")
    print(result)
    print("\n" + "="*50 + "\n")
    
    # Test competitor analysis
    result = tools.search_competitor_analysis("Artisan Blend", "coffee")
    print("Competitor Analysis:")
    print(result)
    print("\n" + "="*50 + "\n")
    
    # Test market trends
    result = tools.get_market_trends("coffee")
    print("Market Trends:")
    print(result)
    print("\n" + "="*50 + "\n")
    
    # Test algorithm selection
    result = tools.select_pricing_algorithm(
        product_type="premium coffee",
        market_conditions="competitive market with price sensitivity",
        business_goals="increase market share while maintaining margins"
    )
    print("Algorithm Selection:")
    print(result)

def example_database_tools(user_id: int = 1):
    """Example of using database tools"""
    print(f"\n🗄️ Testing Database Tools for User {user_id}\n")
    
    try:
        # Get database session
        db_gen = get_db()
        db_session = next(db_gen)
        
        # Initialize database tools
        db_tools = DatabaseTools(user_id=user_id, db_session=db_session)
        
        # Test each database tool
        tools_to_test = [
            ("get_user_items_data", []),
            ("get_user_sales_data", [5]),  # limit=5
            ("get_business_profile_data", []),
            ("get_price_history_data", []),
            ("get_competitor_data", []),
        ]
        
        for tool_name, args in tools_to_test:
            print(f"Testing {tool_name}...")
            try:
                # Create the tool
                tool_creator = getattr(db_tools, f"create_{tool_name}")
                tool = tool_creator()
                
                # Call the tool
                if args:
                    result = tool(*args)
                else:
                    result = tool()
                
                print(f"✅ Success: {result[:200]}...")
                print()
                
            except Exception as e:
                print(f"❌ Error: {e}")
                print()
    
    except Exception as e:
        print(f"Failed to initialize database tools: {e}")

def main():
    """Run examples"""
    print("🧪 LangGraph Tools Example Usage\n")
    
    # Test pricing tools (these work without database)
    example_pricing_tools()
    
    # Test database tools (requires valid user_id)
    print("\n" + "="*80 + "\n")
    example_database_tools(user_id=1)  # Change this to a valid user ID

if __name__ == "__main__":
    main()
