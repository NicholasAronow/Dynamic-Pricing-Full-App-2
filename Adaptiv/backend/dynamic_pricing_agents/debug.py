#!/usr/bin/env python3
"""
Debug utility for dynamic pricing agents - displays detailed outputs from all agents
"""
import sys
import json
import os
import inspect
from datetime import datetime, timedelta
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from pprint import pprint
import logging

# Add parent directory to path so we can import modules from there
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('agent_debug')

# Import models now that we've fixed the path
from models import (
    PricingRecommendation, PricingExperiment, AgentMemory, Item,
    MarketAnalysisSnapshot, CompetitorPriceHistory, PerformanceAnomaly, 
    PerformanceBaseline, ExperimentLearning
)

# Import agents and orchestrator - use relative imports since we're in the dynamic_pricing_agents package
from .agents.pricing_strategy import PricingStrategyAgent
from .agents.market_analysis import MarketAnalysisAgent
from .agents.experimentation import ExperimentationAgent
from .agents.performance_monitor import PerformanceMonitorAgent
from .orchestrator import DynamicPricingOrchestrator

# Import database
from database import SessionLocal, engine

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def format_json(data):
    """Format JSON data for better readability"""
    if isinstance(data, dict) or isinstance(data, list):
        return json.dumps(data, indent=2)
    return str(data)

def run_agent_with_debug(agent_name, user_id):
    """Run a specific agent with debug output enabled"""
    print(f"\n{'=' * 80}")
    print(f"RUNNING {agent_name.upper()} AGENT WITH DEBUG OUTPUT")
    print(f"{'=' * 80}")
    
    db = get_db()
    orchestrator = DynamicPricingOrchestrator()
    
    # Extract just the agent we want to run
    agent = orchestrator.agents.get(agent_name)
    if not agent:
        print(f"Agent '{agent_name}' not found. Available agents: {list(orchestrator.agents.keys())}")
        return
    
    # Enable debug mode for the agent
    agent.debug_mode = True
    
    # Run the agent directly based on type
    try:
        if agent_name == 'pricing_strategy':
            # First collect data if needed
            data_agent = orchestrator.agents['data_collection']
            print("Collecting necessary data for pricing strategy agent...")
            collection_data = data_agent.process(db, user_id)
            
            # Then run market analysis if needed
            market_agent = orchestrator.agents['market_analysis']
            print("Running market analysis to inform pricing decisions...")
            market_data = market_agent.process(db, user_id)
            
            # Then run the pricing strategy agent
            print("\nRunning pricing strategy agent with full debug output...\n")
            results = agent.process(db, user_id)
            
            # Show the item strategies in detail
            if 'item_strategies' in results and results['item_strategies']:
                print(f"\nFound {len(results['item_strategies'])} item strategies")
                for i, strategy in enumerate(results['item_strategies'][:5], 1):  # Show first 5
                    item = db.query(Item).filter(Item.id == strategy.get('item_id')).first()
                    item_name = item.name if item else f"Item #{strategy.get('item_id')}"
                    
                    print(f"\n{i}. {item_name}")
                    print(f"   Current Price: ${strategy.get('current_price', 0):.2f} → Recommended: ${strategy.get('recommended_price', 0):.2f}")
                    print(f"   Change: ${strategy.get('price_change', 0):.2f} ({strategy.get('price_change_percent', 0):.1f}%)")
                    print(f"   Business Type: {strategy.get('business_type', 'Unknown')}")
                    print(f"   Price Rounding: {strategy.get('price_rounding', 'None')}")
                    print(f"   Confidence: {strategy.get('confidence', 0):.2f}")
                    
                    if 'rationale' in strategy:
                        print(f"   Rationale: {strategy['rationale'][:150]}..." if len(strategy['rationale']) > 150 else f"   Rationale: {strategy['rationale']}")
                    
                    if 'reevaluation_date' in strategy:
                        print(f"   Reevaluation Date: {strategy['reevaluation_date']}")
                
                if len(results['item_strategies']) > 5:
                    print(f"\n... and {len(results['item_strategies']) - 5} more item strategies")
                
            # Show category strategies
            if 'category_strategies' in results and results['category_strategies']:
                print("\nCategory Strategies:")
                for category, strategy in results['category_strategies'].items():
                    print(f"   {category}: {strategy}")
                    
            # Show comprehensive strategy
            if 'comprehensive_strategy' in results:
                print("\nComprehensive Strategy:")
                print(format_json(results['comprehensive_strategy']))
        
        elif agent_name == 'market_analysis':
            print("\nRunning market analysis agent with full debug output...\n")
            results = agent.process(db, user_id)
            
            # Show detailed market analysis results
            print("\nMarket Analysis Results:")
            print(format_json(results))
            
            # Show the most recent saved market analysis
            market_analysis = db.query(MarketAnalysisSnapshot).filter(
                MarketAnalysisSnapshot.user_id == user_id
            ).order_by(desc(MarketAnalysisSnapshot.analysis_date)).first()
            
            if market_analysis:
                print("\nSaved Market Analysis:")
                print(f"Date: {market_analysis.analysis_date}")
                print(f"Market Position: {market_analysis.market_position}")
                print(f"Avg Price vs Market: {market_analysis.avg_price_vs_market}")
                print(f"Elasticity: {market_analysis.avg_elasticity} (Elastic: {market_analysis.elastic_items_count}, Inelastic: {market_analysis.inelastic_items_count})")
                
                if market_analysis.market_trends:
                    print(f"Market Trends: {format_json(market_analysis.market_trends)}")
                if market_analysis.seasonal_patterns:
                    print(f"Seasonal Patterns: {format_json(market_analysis.seasonal_patterns)}")
        
        elif agent_name == 'experimentation':
            print("\nRunning experimentation agent with full debug output...\n")
            
            # First get pricing strategy results if needed
            pricing_agent = orchestrator.agents['pricing_strategy']
            pricing_results = pricing_agent.process(db, user_id)
            
            # Then run the experimentation agent
            results = agent.process(db, user_id, item_strategies=pricing_results.get('item_strategies', []))
            
            # Show experiment designs
            if 'experiments' in results and results['experiments']:
                print(f"\nFound {len(results['experiments'])} experiment designs")
                for i, exp in enumerate(results['experiments'], 1):
                    print(f"\nExperiment {i}: {exp.get('name', 'Unnamed')}")
                    print(f"Type: {exp.get('type')}")
                    print(f"Items: {exp.get('items')}")
                    print(f"Duration: {exp.get('duration_days')} days")
                    print(f"Success Metrics: {exp.get('success_metrics')}")
                    
                    if 'test_prices' in exp:
                        print("Test Prices:")
                        for item_id, prices in exp['test_prices'].items():
                            print(f"  Item {item_id}: Control=${prices.get('control', 0):.2f}, Treatment=${prices.get('treatment', 0):.2f}")
            
            # Show experiment history
            experiments = db.query(PricingExperiment).filter(
                PricingExperiment.user_id == user_id
            ).order_by(desc(PricingExperiment.created_at)).limit(3).all()
            
            if experiments:
                print("\nRecent Experiment History:")
                for exp in experiments:
                    print(f"\n- {exp.name} (ID: {exp.experiment_id})")
                    print(f"  Status: {exp.status}")
                    print(f"  Started: {exp.started_at}, Ended: {exp.ended_at}")
                    print(f"  Items: {exp.item_ids}")
                    
                    if exp.results:
                        print(f"  Results Summary: {exp.results}")
        
        elif agent_name == 'performance_monitor':
            print("\nRunning performance monitor agent with full debug output...\n")
            results = agent.process(db, user_id)
            
            # Show performance monitoring results
            print("\nPerformance Monitoring Results:")
            if 'performance_metrics' in results:
                print("Performance Metrics:")
                print(format_json(results['performance_metrics']))
            
            if 'anomalies' in results:
                print(f"\nDetected {len(results['anomalies'])} anomalies:")
                for i, anomaly in enumerate(results['anomalies'], 1):
                    print(f"\nAnomaly {i}:")
                    print(f"Type: {anomaly.get('type')}")
                    print(f"Severity: {anomaly.get('severity')}")
                    print(f"Metric: {anomaly.get('metric')}")
                    print(f"Expected: {anomaly.get('expected')} vs Actual: {anomaly.get('actual')}")
                    print(f"Description: {anomaly.get('description')}")
        
        else:
            print(f"\nRunning {agent_name} agent...")
            results = agent.process(db, user_id)
            print("\nResults:")
            print(format_json(results))
        
        print("\nAgent memories:")
        memories = db.query(AgentMemory).filter(
            AgentMemory.user_id == user_id,
            AgentMemory.agent_name == agent_name
        ).order_by(desc(AgentMemory.created_at)).limit(3).all()
        
        if memories:
            for memory in memories:
                print(f"\n- {memory.memory_type} (Created: {memory.created_at})")
                if memory.content:
                    print(f"  Content: {format_json(memory.content)}")
        else:
            print("No memories found for this agent.")
            
        return results
        
    except Exception as e:
        print(f"Error running {agent_name} agent: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def debug_all_agents(user_id):
    """Run all agents with debug output"""
    agents = [
        'pricing_strategy',
        'market_analysis',
        'experimentation',
        'performance_monitor'
    ]
    
    for agent_name in agents:
        run_agent_with_debug(agent_name, user_id)

def main():
    """Main function to run the debug utility"""
    if len(sys.argv) < 2:
        print("Usage: python3 debug.py [user_id] [agent_name]")
        print("Example: python3 debug.py 1 pricing_strategy")
        print("\nAvailable agents:")
        print("  pricing_strategy - Price recommendation agent")
        print("  market_analysis - Market analysis agent")
        print("  experimentation - Experiment design agent")
        print("  performance_monitor - Performance monitoring agent")
        print("  all - Run all agents")
        return
    
    try:
        user_id = int(sys.argv[1])
    except ValueError:
        print("Error: user_id must be an integer")
        return
    
    if len(sys.argv) > 2:
        agent_name = sys.argv[2].lower()
        if agent_name == 'all':
            debug_all_agents(user_id)
        else:
            run_agent_with_debug(agent_name, user_id)
    else:
        debug_all_agents(user_id)

if __name__ == "__main__":
    main()
