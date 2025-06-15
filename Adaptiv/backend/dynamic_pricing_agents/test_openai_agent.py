"""
Test script for the OpenAI Agent's functionality.

This script demonstrates:
1. Parsing data collection output
2. Identifying research candidates
3. Conducting research using the OpenAI Agent with tools
"""

import json
import os
from typing import Dict, Any
from pprint import pprint

# Import the OpenAI Agent
from dynamic_pricing_agents.agents.openai_agent import (
    parse_data_collection_output, 
    identify_research_candidates,
    conduct_research,
    process_data_collection_output
)

# Sample data collection output (mock data)
SAMPLE_DATA = {
    "items": [
        {
            "item_id": "1",
            "item_name": "Espresso",
            "current_price": 2.95,
            "cost_price": 0.85,
            "sales_volume": 780,
            "price_elasticity": -2.3,  # High elasticity (price sensitive)
            "competitor_price_position": 0.1,  # Slightly above competitors
            "price_optimization_signal": 0.2,  # Moderate upward signal
            "cost_change_velocity": 0.05,  # Slow cost increase
            "inventory_level": "normal",
            "seasonal_factor": 1.0
        },
        {
            "item_id": "5",
            "item_name": "Latte",
            "current_price": 4.25,
            "cost_price": 1.15,
            "sales_volume": 950,
            "price_elasticity": -1.1,  # Low elasticity (less price sensitive)
            "competitor_price_position": -0.15,  # Below competitors
            "price_optimization_signal": 0.5,  # Strong upward signal
            "cost_change_velocity": 0.12,  # Moderate cost increase
            "inventory_level": "normal",
            "seasonal_factor": 0.9
        },
        {
            "item_id": "12",
            "item_name": "Iced Coffee",
            "current_price": 3.75,
            "cost_price": 0.90,
            "sales_volume": 420,
            "price_elasticity": -1.8,  # Moderate elasticity
            "competitor_price_position": 0.05,  # At par with competitors
            "price_optimization_signal": -0.1,  # Slight downward signal
            "cost_change_velocity": 0.02,  # Very slow cost increase
            "inventory_level": "high",
            "seasonal_factor": 1.4  # Season-dependent
        },
        {
            "item_id": "36",
            "item_name": "Matcha Latte",
            "current_price": 4.95,
            "cost_price": 1.85,
            "sales_volume": 380,
            "price_elasticity": -0.8,  # Very low elasticity (premium item)
            "competitor_price_position": -0.2,  # Below competitors
            "price_optimization_signal": 0.4,  # Strong upward signal
            "cost_change_velocity": 0.25,  # Rapid cost increase
            "inventory_level": "low",
            "seasonal_factor": 1.0
        }
    ],
    "market_conditions": {
        "overall_inflation": 0.03,
        "industry_growth": 0.02,
        "consumer_sentiment": 0.6  # Moderate positive
    },
    "timestamp": "2023-07-15T08:30:00Z"
}

def main():
    """Run a test of the OpenAI Agent functionality"""
    print("=" * 80)
    print("TESTING OPENAI AGENT FOR DYNAMIC PRICING")
    print("=" * 80)
    
    # Check if OpenAI API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY environment variable is not set.")
        print("The OpenAI Agent may not function correctly without it.")
        print("Consider setting this environment variable before running this test.")
        print()
        
    # STEP 1: Parse the data collection output
    print("STEP 1: Parsing data collection output...")
    parsed_data = parse_data_collection_output(SAMPLE_DATA)
    print(f"Successfully parsed data for {len(parsed_data['items'])} items")
    print()
    
    # STEP 2: Identify items that need further research
    print("STEP 2: Identifying research candidates...")
    research_items = identify_research_candidates(parsed_data)
    print(f"Identified {len(research_items)} items for further research:")
    for item in research_items:
        print(f"- {item.item_name} (ID: {item.item_id})")
        print(f"  Reason: {item.research_reason}")
        print(f"  Focus areas: {', '.join(item.research_focus)}")
    print()
    
    # STEP 3: Process data collection output (combines steps 1 & 2)
    print("STEP 3: Testing combined data processing...")
    processed_items = process_data_collection_output(SAMPLE_DATA)
    print(f"Combined processing identified {len(processed_items)} items for research")
    print()
    
    # STEP 4: Conduct research (this will call the actual OpenAI agent)
    print("STEP 4: Conducting research using the OpenAI agent...")
    print("NOTE: This step will use the OpenAI API and may take some time.")
    print("      It requires a valid OPENAI_API_KEY environment variable.")
    
    try_research = False  # Set to True to actually run the agent
    
    if try_research:
        print("Initiating research...")
        results = conduct_research(research_items[:1])  # Only research the first item as a test
        
        print("\nRESEARCH RESULTS:")
        print(f"Summary: {results.summary}")
        
        if results.research_results:
            for result in results.research_results:
                print(f"\nResults for {result.item_name} (ID: {result.item_id}):")
                print(f"Market trends: {result.market_trends}")
                print(f"Supply chain insights: {result.supply_chain_insights}")
                print(f"Competitor analysis: {result.competitor_analysis}")
                print(f"Upcoming events: {result.upcoming_events}")
                print(f"Recommendation: {result.recommendation}")
                print(f"Confidence: {result.confidence}")
                print(f"Sources: {', '.join(result.sources)}")
    else:
        print("Research step skipped. Set try_research=True to run the actual agent.")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    main()
