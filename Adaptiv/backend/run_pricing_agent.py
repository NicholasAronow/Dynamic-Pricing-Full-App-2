#!/usr/bin/env python3
"""
Test utility for running the pricing strategy agent with full debug output
"""
import sys
import json
import os
from datetime import datetime
import logging
from sqlalchemy.orm import Session
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('pricing_agent_debug')

# Add necessary imports
from models import User, Item
from database import SessionLocal
from dynamic_pricing_agents.agents.pricing_strategy import PricingStrategyAgent

def format_json(data):
    """Format JSON data for better readability"""
    if isinstance(data, dict) or isinstance(data, list):
        return json.dumps(data, indent=2)
    return str(data)

def get_user_info(db: Session, user_id: int):
    """Get user information"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        print(f"User with ID {user_id} not found!")
        return None
    
    print(f"Running pricing agent for user: {user.email} (ID: {user_id})")
    return user

def get_items(db: Session, user_id: int, limit: int = 5):
    """Get items for the user"""
    items = db.query(Item).filter(Item.user_id == user_id).limit(limit).all()
    
    if not items:
        print(f"No items found for user {user_id}")
        return []
    
    print(f"Found {len(items)} items")
    for item in items:
        print(f"- {item.name} (ID: {item.id}): ${item.current_price:.2f}")
    
    return items

def run_pricing_agent(user_id: int, verbose: bool = True):
    """Run the pricing strategy agent and display detailed output"""
    db = SessionLocal()
    
    try:
        # Get user info
        user = get_user_info(db, user_id)
        if not user:
            return
        
        # Get some items for context
        items = get_items(db, user_id)
        if not items:
            return
        
        # Create the pricing agent
        pricing_agent = PricingStrategyAgent()
        
        # Set verbose logging manually
        pricing_agent.verbose = True
        
        # Configure a stream handler to capture the agent's log output
        if verbose:
            # Create a stream handler
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            
            # Add the handler to the logger
            pricing_agent.logger.addHandler(handler)
            pricing_agent.logger.setLevel(logging.DEBUG)
        
        print("\n" + "="*80)
        print("RUNNING PRICING STRATEGY AGENT WITH FULL DEBUG OUTPUT")
        print("="*80 + "\n")
        
        # Collect the required context data
        from dynamic_pricing_agents.agents.data_collection import DataCollectionAgent
        from dynamic_pricing_agents.agents.market_analysis import MarketAnalysisAgent
        
        # First get the data
        print("\nCollecting required data for pricing strategy agent...")
        data_agent = DataCollectionAgent()
        consolidated_data = data_agent.process({"db": db, "user_id": user_id})
        print("Data collection complete")
        
        # Then get market analysis
        print("\nRunning market analysis to inform pricing decisions...")
        market_agent = MarketAnalysisAgent()
        market_analysis = market_agent.process({"db": db, "user_id": user_id, "consolidated_data": consolidated_data})
        print("Market analysis complete")
        
        # Prepare the context for the pricing strategy agent
        context = {
            "db": db,
            "user_id": user_id,
            "consolidated_data": consolidated_data,
            "market_analysis": market_analysis
            # Let the agent use its default goals
        }
        
        # Process the pricing strategy
        print("\nRunning pricing strategy agent...")
        results = pricing_agent.process(context)
        
        print("\n" + "="*80)
        print("PRICING STRATEGY RESULTS")
        print("="*80 + "\n")
        
        # Show business type detection
        if 'business_type' in results:
            print(f"Business Type: {results['business_type']}")
            print(f"Business Type Detection Confidence: {results.get('business_type_confidence', 'N/A')}")
        
        # Show item strategies with focus on new features
        if 'item_strategies' in results and results['item_strategies']:
            print(f"\nFound {len(results['item_strategies'])} item strategies")
            
            for i, strategy in enumerate(results['item_strategies'][:10], 1):  # Show first 10
                item_name = strategy.get('item_name', f"Item #{strategy.get('item_id')}")
                
                print(f"\n{i}. {item_name}")
                print(f"   Current Price: ${strategy.get('current_price', 0):.2f} → Recommended: ${strategy.get('recommended_price', 0):.2f}")
                
                price_change = strategy.get('recommended_price', 0) - strategy.get('current_price', 0)
                price_change_pct = 0
                if strategy.get('current_price', 0) > 0:
                    price_change_pct = (price_change / strategy.get('current_price', 0)) * 100
                
                print(f"   Change: ${price_change:.2f} ({price_change_pct:.1f}%)")
                
                # Show business type
                if 'business_type' in strategy:
                    print(f"   Business Type: {strategy['business_type']}")
                
                # Show price rounding
                if 'price_rounding' in strategy:
                    print(f"   Price Rounding: {strategy['price_rounding']}")
                
                # Show reevaluation date
                if 'reevaluation_date' in strategy:
                    print(f"   Reevaluation Date: {strategy['reevaluation_date']}")
                
                # Show confidence
                if 'confidence' in strategy:
                    print(f"   Confidence: {strategy['confidence']:.2f}")
                
                # Show rationale
                if 'rationale' in strategy:
                    rationale = strategy['rationale']
                    print(f"   Rationale: {rationale[:150]}..." if len(rationale) > 150 else f"   Rationale: {rationale}")
        
        # Show category strategies
        if 'category_strategies' in results and results['category_strategies']:
            print("\nCategory Strategies:")
            for category, strategy in results['category_strategies'].items():
                print(f"   {category}: {strategy}")
        
        return results
    
    except Exception as e:
        print(f"Error running pricing agent: {str(e)}")
        traceback.print_exc()
    
    finally:
        db.close()

def main():
    """Main function"""
    if len(sys.argv) < 2:
        # Show all available users
        db = SessionLocal()
        users = db.query(User).all()
        print("Available Users:")
        for user in users:
            print(f"  User ID: {user.id}, Email: {user.email}")
        
        print("\nUsage: python3 run_pricing_agent.py [user_id]")
        print("Example: python3 run_pricing_agent.py 1")
        
        db.close()
        return
    
    try:
        user_id = int(sys.argv[1])
    except ValueError:
        print("Error: user_id must be an integer")
        return
    
    run_pricing_agent(user_id)

if __name__ == "__main__":
    main()
