#!/usr/bin/env python3
"""
Debug utility for viewing agent outputs and detailed processing steps
"""
import sys
import json
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from pprint import pprint

# Import models and agents
from models import (
    PricingRecommendation, PricingExperiment, AgentMemory, 
    Item, AgentTask, MarketAnalysisSnapshot, CompetitorPriceHistory,
    PerformanceAnomaly, PerformanceBaseline, ExperimentLearning
)
from database import get_db
from dynamic_pricing_agents.agents.pricing_strategy import PricingStrategyAgent
from dynamic_pricing_agents.agents.market_analysis import MarketAnalysisAgent
from dynamic_pricing_agents.agents.experimentation import ExperimentationAgent
from dynamic_pricing_agents.agents.performance_monitor import PerformanceMonitorAgent

def get_session():
    """Create a database session"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.db')
    engine = create_engine(f'sqlite:///{db_path}')
    Session = sessionmaker(bind=engine)
    return Session()

def format_json(data):
    """Format JSON data for better readability"""
    if isinstance(data, dict) or isinstance(data, list):
        return json.dumps(data, indent=2)
    return str(data)

def show_pricing_recommendations(count=10):
    """Show recent pricing recommendations with detailed information"""
    session = get_session()
    
    print("\n===== PRICING RECOMMENDATIONS =====")
    print(f"Showing the {count} most recent pricing recommendations:")
    
    recommendations = session.query(PricingRecommendation).order_by(
        desc(PricingRecommendation.recommendation_date)
    ).limit(count).all()
    
    for i, rec in enumerate(recommendations, 1):
        item = session.query(Item).filter(Item.id == rec.item_id).first()
        item_name = item.name if item else f"Item #{rec.item_id}"
        
        print(f"\n{i}. {item_name} (ID: {rec.item_id})")
        print(f"   Current Price: ${rec.current_price:.2f} → Recommended: ${rec.recommended_price:.2f} ({rec.price_change_percent:.1f}%)")
        print(f"   Strategy Type: {rec.strategy_type}")
        print(f"   Confidence: {rec.confidence_score:.2f}")
        print(f"   Reevaluation Date: {rec.reevaluation_date}")
        
        if rec.metadata:
            if isinstance(rec.metadata, str):
                try:
                    metadata = json.loads(rec.metadata)
                except:
                    metadata = {"raw": rec.metadata}
            else:
                metadata = rec.metadata
                
            # Extract business type
            business_type = metadata.get('business_type', 'Not specified')
            print(f"   Business Type: {business_type}")
            
            # Extract key factors if available
            key_factors = metadata.get('key_factors', [])
            if key_factors:
                print(f"   Key Factors: {', '.join(key_factors)}")
        
        # Show rationale
        if rec.rationale:
            print(f"   Rationale: {rec.rationale[:150]}..." if len(rec.rationale) > 150 else f"   Rationale: {rec.rationale}")

def show_experiments(count=5):
    """Show recent pricing experiments"""
    session = get_session()
    
    print("\n===== PRICING EXPERIMENTS =====")
    print(f"Showing the {count} most recent pricing experiments:")
    
    experiments = session.query(PricingExperiment).order_by(
        desc(PricingExperiment.created_at)
    ).limit(count).all()
    
    for i, exp in enumerate(experiments, 1):
        print(f"\n{i}. Experiment {exp.id}: {exp.name}")
        print(f"   Status: {exp.status}")
        print(f"   Started: {exp.started_at} → Ended: {exp.ended_at or 'Ongoing'}")
        print(f"   Items: {exp.item_ids}")
        
        # Show control and treatment prices
        if exp.control_prices:
            print(f"   Control Prices: {format_json(exp.control_prices)}")
        if exp.treatment_prices:
            print(f"   Treatment Prices: {format_json(exp.treatment_prices)}")
        
        # Show results if available
        if exp.results:
            print(f"   Results: {format_json(exp.results)}")

def show_agent_tasks(count=10):
    """Show recent agent tasks and their outputs"""
    session = get_session()
    
    print("\n===== AGENT TASKS =====")
    print(f"Showing the {count} most recent agent tasks:")
    
    tasks = session.query(AgentTask).order_by(
        desc(AgentTask.created_at)
    ).limit(count).all()
    
    if not tasks:
        print("No agent tasks found.")
        return
    
    for i, task in enumerate(tasks, 1):
        print(f"\n{i}. Task {task.id}: {task.agent_type}")
        print(f"   Status: {task.status}")
        print(f"   Created: {task.created_at} → Completed: {task.completed_at or 'Pending'}")
        
        if task.results:
            # Extract a summary of the results
            results_data = None
            if isinstance(task.results, str):
                try:
                    results_data = json.loads(task.results)
                except:
                    results_data = None
                    print(f"   Results: {task.results[:150]}..." if len(task.results) > 150 else f"   Results: {task.results}")
            else:
                results_data = task.results
            
            if results_data and isinstance(results_data, dict):
                # Show keys but not full content for brevity
                print(f"   Results Keys: {', '.join(results_data.keys())}")
                
                # Show business type detection if present
                if 'business_type' in results_data:
                    print(f"   Business Type: {results_data['business_type']}")
                
                # Show number of strategies if present
                if 'item_strategies' in results_data and isinstance(results_data['item_strategies'], list):
                    print(f"   Number of Item Strategies: {len(results_data['item_strategies'])}")
                    
                    # Show sample of strategies
                    if len(results_data['item_strategies']) > 0:
                        sample = results_data['item_strategies'][0]
                        print(f"   Sample Strategy:")
                        print(f"     Item: {sample.get('item_name', 'Unknown')}")
                        print(f"     Current: ${sample.get('current_price', 0):.2f} → Recommended: ${sample.get('recommended_price', 0):.2f}")
                        if 'confidence' in sample:
                            print(f"     Confidence: {sample.get('confidence'):.2f}")
                        if 'price_rounding' in sample:
                            print(f"     Price Rounding: {sample.get('price_rounding')}")
                
                # Show detailed category strategies if present
                if 'category_strategies' in results_data and isinstance(results_data['category_strategies'], dict):
                    print(f"   Category Strategies: {format_json(results_data['category_strategies'])}")
                
                # Performance monitoring specific data
                if 'performance_metrics' in results_data:
                    print(f"   Performance Metrics Summary: {format_json(results_data['performance_metrics'])}")
                
                # Experimentation specific data
                if 'experiments' in results_data and isinstance(results_data['experiments'], list):
                    print(f"   Experiment Count: {len(results_data['experiments'])}")
                    if results_data['experiments']:
                        print(f"   First Experiment: {format_json(results_data['experiments'][0])}")
                
                # Market analysis specific data
                if 'market_trends' in results_data:
                    print(f"   Market Trends: {format_json(results_data['market_trends'])}")
                if 'seasonality' in results_data:
                    print(f"   Seasonality: {format_json(results_data['seasonality'])}")
            
            elif results_data:
                print(f"   Results: {format_json(results_data)}")

def show_agent_memories(agent_name=None, memory_type=None, count=10):
    """Show agent memories"""
    session = get_session()
    
    print("\n===== AGENT MEMORIES =====")
    query = session.query(AgentMemory).order_by(desc(AgentMemory.created_at))
    
    if agent_name:
        query = query.filter(AgentMemory.agent_name == agent_name)
        print(f"Showing the {count} most recent memories for agent: {agent_name}")
    else:
        print(f"Showing the {count} most recent memories across all agents")
    
    if memory_type:
        query = query.filter(AgentMemory.memory_type == memory_type)
        print(f"Filtered by memory type: {memory_type}")
    
    memories = query.limit(count).all()
    
    for i, memory in enumerate(memories, 1):
        print(f"\n{i}. Memory {memory.id}: {memory.agent_name} - {memory.memory_type}")
        print(f"   Created: {memory.created_at}")
        
        if memory.content:
            if isinstance(memory.content, str):
                try:
                    content = json.loads(memory.content)
                    print(f"   Content: {format_json(content)}")
                except:
                    print(f"   Content: {memory.content[:150]}..." if len(memory.content) > 150 else f"   Content: {memory.content}")
            else:
                print(f"   Content: {format_json(memory.content)}")
        
        if memory.memory_metadata:
            if isinstance(memory.memory_metadata, str):
                try:
                    metadata = json.loads(memory.memory_metadata)
                    print(f"   Metadata: {format_json(metadata)}")
                except:
                    print(f"   Metadata: {memory.memory_metadata}")
            else:
                print(f"   Metadata: {format_json(memory.memory_metadata)}")

def show_market_analysis(count=5):
    """Show recent market analysis results"""
    session = get_session()
    
    print("\n===== MARKET ANALYSIS =====")
    print(f"Showing the {count} most recent market analyses:")
    
    analyses = session.query(MarketAnalysisSnapshot).order_by(
        desc(MarketAnalysisSnapshot.analysis_date)
    ).limit(count).all()
    
    for i, analysis in enumerate(analyses, 1):
        print(f"\n{i}. Market Analysis {analysis.id}")
        print(f"   Date: {analysis.analysis_date}")
        print(f"   Market Position: {analysis.market_position}")
        print(f"   Avg Price vs Market: {analysis.avg_price_vs_market}")
        print(f"   Avg Elasticity: {analysis.avg_elasticity}")
        print(f"   Elastic/Inelastic Items: {analysis.elastic_items_count}/{analysis.inelastic_items_count}")
        
        if analysis.market_trends:
            print(f"   Market Trends: {format_json(analysis.market_trends)}")
        if analysis.seasonal_patterns:
            print(f"   Seasonal Patterns: {format_json(analysis.seasonal_patterns)}")
        if analysis.key_insights:
            print(f"   Key Insights: {format_json(analysis.key_insights)}")
        if analysis.strategic_recommendations:
            print(f"   Strategic Recommendations: {format_json(analysis.strategic_recommendations)}")

def show_competitor_analysis(count=10):
    """Show recent competitor price history"""
    session = get_session()
    
    print("\n===== COMPETITOR ANALYSIS =====")
    print(f"Showing the {count} most recent competitor price entries:")
    
    competitor_prices = session.query(CompetitorPriceHistory).order_by(
        desc(CompetitorPriceHistory.captured_at)
    ).limit(count).all()
    
    if not competitor_prices:
        print("No competitor price history found.")
        return
    
    # Group by competitor
    competitors = {}
    for price in competitor_prices:
        if price.competitor_name not in competitors:
            competitors[price.competitor_name] = []
        competitors[price.competitor_name].append(price)
    
    for competitor, prices in competitors.items():
        print(f"\n- Competitor: {competitor}")
        for i, price in enumerate(prices[:5], 1):  # Show just top 5 per competitor
            print(f"   {i}. Item: {price.item_name}")
            print(f"      Price: ${price.price:.2f}")
            print(f"      Category: {price.category}")
            print(f"      Similarity Score: {price.similarity_score}")
            print(f"      Captured: {price.captured_at}")
            if price.price_change_from_last:
                print(f"      Change: ${price.price_change_from_last:.2f} ({price.percent_change_from_last:.1f}%)")
        if len(prices) > 5:
            print(f"   ... and {len(prices) - 5} more items")

def show_performance_monitoring(count=5):
    """Show performance monitoring data"""
    session = get_session()
    
    print("\n===== PERFORMANCE MONITORING =====")
    print(f"Showing the {count} most recent performance anomalies:")
    
    anomalies = session.query(PerformanceAnomaly).order_by(
        desc(PerformanceAnomaly.detected_at)
    ).limit(count).all()
    
    if anomalies:
        for i, anomaly in enumerate(anomalies, 1):
            print(f"\n{i}. Anomaly {anomaly.id}")
            print(f"   Detected: {anomaly.detected_at}")
            print(f"   Type: {anomaly.anomaly_type}")
            print(f"   Severity: {anomaly.severity}")
            print(f"   Metric: {anomaly.metric_name}")
            print(f"   Expected: {anomaly.expected_value} vs Actual: {anomaly.actual_value} ({anomaly.deviation_percent:.1f}%)")
            print(f"   Description: {anomaly.description}")
            if anomaly.potential_causes:
                print(f"   Potential Causes: {format_json(anomaly.potential_causes)}")
            if anomaly.recommended_actions:
                print(f"   Recommended Actions: {format_json(anomaly.recommended_actions)}")
    else:
        print("No performance anomalies found.")
    
    print("\nPerformance Baselines:")
    baselines = session.query(PerformanceBaseline).order_by(
        desc(PerformanceBaseline.baseline_date)
    ).limit(count).all()
    
    if baselines:
        for i, baseline in enumerate(baselines, 1):
            print(f"\n{i}. Baseline {baseline.id}")
            print(f"   Date: {baseline.baseline_date}")
            print(f"   Period: {baseline.period_start} to {baseline.period_end}")
            print(f"   Avg Daily Revenue: ${baseline.avg_daily_revenue:.2f}")
            print(f"   Avg Daily Orders: {baseline.avg_daily_orders}")
            print(f"   Avg Order Value: ${baseline.avg_order_value:.2f}")
            if baseline.item_baselines:
                print(f"   Item Baselines: {format_json(baseline.item_baselines)}")
    else:
        print("No performance baselines found.")

def show_experiment_learnings(count=5):
    """Show experiment learnings"""
    session = get_session()
    
    print("\n===== EXPERIMENT LEARNINGS =====")
    print(f"Showing the {count} most recent experiment learnings:")
    
    learnings = session.query(ExperimentLearning).order_by(
        desc(ExperimentLearning.created_at)
    ).limit(count).all()
    
    if learnings:
        for i, learning in enumerate(learnings, 1):
            print(f"\n{i}. Learning {learning.id}")
            print(f"   Experiment ID: {learning.experiment_id}")
            print(f"   Type: {learning.learning_type}")
            print(f"   Confidence: {learning.confidence_level}")
            print(f"   Insight: {learning.insight}")
            print(f"   Recommended Action: {learning.recommended_action}")
            if learning.applicable_to_items:
                print(f"   Applicable Items: {format_json(learning.applicable_to_items)}")
            if learning.validation_result:
                print(f"   Validation Result: {format_json(learning.validation_result)}")
    else:
        print("No experiment learnings found.")

def main():
    """Main function to run the debug utility"""
    if len(sys.argv) < 2:
        print("Usage: python3 debug_agents.py [option]")
        print("Options:")
        print("  recommendations - Show pricing recommendations")
        print("  experiments - Show pricing experiments")
        print("  tasks - Show agent tasks")
        print("  memories - Show agent memories (optional agent name as second argument)")
        print("  market - Show market analysis")
        print("  competitors - Show competitor analysis")
        print("  performance - Show performance monitoring")
        print("  learnings - Show experiment learnings")
        print("  agent [agent_name] - Show outputs for a specific agent")
        print("  all - Show everything")
        return
    
    option = sys.argv[1]
    
    if option == "recommendations" or option == "all":
        show_pricing_recommendations()
    
    if option == "experiments" or option == "all":
        show_experiments()
    
    if option == "tasks" or option == "all":
        show_agent_tasks()
    
    if option == "memories" or option == "all":
        if len(sys.argv) > 2:
            show_agent_memories(agent_name=sys.argv[2])
        else:
            show_agent_memories()
    
    if option == "market" or option == "all":
        show_market_analysis()
    
    if option == "competitors" or option == "all":
        show_competitor_analysis()
    
    if option == "performance" or option == "all":
        show_performance_monitoring()
    
    if option == "learnings" or option == "all":
        show_experiment_learnings()
    
    if option == "agent" and len(sys.argv) > 2:
        agent_name = sys.argv[2]
        print(f"\n===== OUTPUTS FOR {agent_name.upper()} AGENT =====")
        
        # Show agent-specific outputs
        if agent_name.lower() == "pricing" or agent_name.lower() == "pricing_strategy":
            show_pricing_recommendations()
        elif agent_name.lower() == "experiment" or agent_name.lower() == "experimentation":
            show_experiments()
            show_experiment_learnings()
        elif agent_name.lower() == "market" or agent_name.lower() == "market_analysis":
            show_market_analysis()
        elif agent_name.lower() == "competitor" or agent_name.lower() == "competitor_analysis":
            show_competitor_analysis()
        elif agent_name.lower() == "performance" or agent_name.lower() == "performance_monitor":
            show_performance_monitoring()
        
        # Show memories for this agent
        show_agent_memories(agent_name=agent_name)

if __name__ == "__main__":
    main()
