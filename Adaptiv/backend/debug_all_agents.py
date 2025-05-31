#!/usr/bin/env python3
"""
Debug utility for viewing the output of all Dynamic Pricing agents
"""
import sys
import json
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from pprint import pprint
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('agent_debug')

# Import models
from models import (
    PricingRecommendation, PricingExperiment, AgentMemory, Item, User,
    MarketAnalysisSnapshot, CompetitorPriceHistory, PerformanceAnomaly, 
    PerformanceBaseline, ExperimentLearning, Order, OrderItem
)

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

def show_agent_memories(db, user_id):
    """Show all agent memories for a user"""
    print("\n===== AGENT MEMORIES =====")
    
    try:
        # Get unique agent names first
        agents = db.query(AgentMemory.agent_name).filter(
            AgentMemory.user_id == user_id
        ).distinct().all()
    except Exception as e:
        print(f"Error fetching agent memories: {str(e)}")
        print("This is likely due to database schema changes that haven't been applied.")
        return
    agent_names = [a[0] for a in agents]
    
    if not agent_names:
        print(f"No agent memories found for user {user_id}")
        return
    
    print(f"Found memories for the following agents: {', '.join(agent_names)}")
    
    for agent_name in agent_names:
        print(f"\n----- {agent_name.upper()} AGENT MEMORIES -----")
        
        memories = db.query(AgentMemory).filter(
            AgentMemory.user_id == user_id,
            AgentMemory.agent_name == agent_name
        ).order_by(desc(AgentMemory.created_at)).limit(5).all()
        
        if not memories:
            print(f"No memories found for {agent_name}")
            continue
        
        # Group by memory type
        by_type = {}
        for memory in memories:
            if memory.memory_type not in by_type:
                by_type[memory.memory_type] = []
            by_type[memory.memory_type].append(memory)
        
        for memory_type, items in by_type.items():
            print(f"\n  {memory_type} Memories:")
            for memory in items:
                print(f"    - Created: {memory.created_at}")
                if memory.content:
                    if isinstance(memory.content, dict):
                        # Extract key elements only
                        if 'business_type' in memory.content:
                            print(f"      Business Type: {memory.content['business_type']}")
                        if 'item_name' in memory.content:
                            print(f"      Item: {memory.content['item_name']}")
                        if 'current_price' in memory.content and 'recommended_price' in memory.content:
                            print(f"      Price: ${memory.content.get('current_price', 0):.2f} → ${memory.content.get('recommended_price', 0):.2f}")
                        if 'confidence' in memory.content:
                            print(f"      Confidence: {memory.content.get('confidence', 0):.2f}")
                        if 'price_rounding' in memory.content:
                            print(f"      Price Rounding: {memory.content.get('price_rounding')}")
                        if 'reevaluation_date' in memory.content:
                            print(f"      Reevaluation Date: {memory.content.get('reevaluation_date')}")
                    else:
                        # Just show summary
                        content_str = str(memory.content)
                        print(f"      Content: {content_str[:100]}..." if len(content_str) > 100 else f"      Content: {content_str}")

def show_pricing_recommendations(db, user_id, count=10):
    """Show recent pricing recommendations with detailed information"""
    print("\n===== PRICING RECOMMENDATIONS =====")
    
    try:
        recommendations = db.query(PricingRecommendation).filter(
            PricingRecommendation.user_id == user_id
        ).order_by(desc(PricingRecommendation.recommendation_date)).limit(count).all()
    except Exception as e:
        print(f"Error fetching pricing recommendations: {str(e)}")
        print("This may be due to database schema changes that haven't been migrated yet.")
        print("Let's look at other agent outputs instead.")
        return
    
    if not recommendations:
        print(f"No pricing recommendations found for user {user_id}")
        return
    
    print(f"Found {len(recommendations)} recommendations")
    
    for i, rec in enumerate(recommendations, 1):
        item = db.query(Item).filter(Item.id == rec.item_id).first()
        item_name = item.name if item else f"Item #{rec.item_id}"
        
        print(f"\n{i}. {item_name} (ID: {rec.item_id})")
        print(f"   Current Price: ${rec.current_price:.2f} → Recommended: ${rec.recommended_price:.2f} ({rec.price_change_percent:.1f}%)")
        print(f"   Strategy Type: {rec.strategy_type}")
        print(f"   Confidence: {rec.confidence_score:.2f}")
        
        # Check if reevaluation_date attribute exists before trying to access it
        if hasattr(rec, 'reevaluation_date') and rec.reevaluation_date:
            print(f"   Reevaluation Date: {rec.reevaluation_date}")
        elif rec.metadata and isinstance(rec.metadata, dict) and 'reevaluation_date' in rec.metadata:
            print(f"   Reevaluation Date: {rec.metadata['reevaluation_date']}")
        
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
            
            # Extract price rounding
            price_rounding = metadata.get('price_rounding', None)
            if price_rounding:
                print(f"   Price Rounding: {price_rounding}")
            
            # Extract key factors if available
            key_factors = metadata.get('key_factors', [])
            if key_factors:
                print(f"   Key Factors: {', '.join(key_factors)}")
        
        # Show rationale
        if rec.rationale:
            print(f"   Rationale: {rec.rationale[:150]}..." if len(rec.rationale) > 150 else f"   Rationale: {rec.rationale}")

def show_experiments(db, user_id, count=5):
    """Show recent pricing experiments"""
    print("\n===== PRICING EXPERIMENTS =====")
    
    try:
        experiments = db.query(PricingExperiment).filter(
            PricingExperiment.user_id == user_id
        ).order_by(desc(PricingExperiment.created_at)).limit(count).all()
    except Exception as e:
        print(f"Error fetching pricing experiments: {str(e)}")
        print("Continuing with other agent outputs...")
        return
    
    if not experiments:
        print(f"No pricing experiments found for user {user_id}")
        return
    
    print(f"Found {len(experiments)} experiments")
    
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
        
        # Show learnings if available
        learnings = db.query(ExperimentLearning).filter(
            ExperimentLearning.experiment_id == exp.experiment_id
        ).order_by(desc(ExperimentLearning.created_at)).all()
        
        if learnings:
            print(f"   Learnings:")
            for j, learning in enumerate(learnings, 1):
                print(f"     {j}. {learning.learning_type}: {learning.insight}")
                if learning.recommended_action:
                    print(f"        Recommended Action: {learning.recommended_action}")

def show_market_analysis(db, user_id, count=3):
    """Show recent market analysis results"""
    print("\n===== MARKET ANALYSIS =====")
    
    try:
        analyses = db.query(MarketAnalysisSnapshot).filter(
            MarketAnalysisSnapshot.user_id == user_id
        ).order_by(desc(MarketAnalysisSnapshot.analysis_date)).limit(count).all()
    except Exception as e:
        print(f"Error fetching market analyses: {str(e)}")
        print("Continuing with other agent outputs...")
        return
    
    if not analyses:
        print(f"No market analyses found for user {user_id}")
        return
    
    print(f"Found {len(analyses)} market analyses")
    
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

def show_competitor_analysis(db, user_id, count=5):
    """Show recent competitor price history"""
    print("\n===== COMPETITOR ANALYSIS =====")
    
    try:
        competitor_prices = db.query(CompetitorPriceHistory).filter(
            CompetitorPriceHistory.user_id == user_id
        ).order_by(desc(CompetitorPriceHistory.captured_at)).limit(count).all()
    except Exception as e:
        print(f"Error fetching competitor price history: {str(e)}")
        print("Continuing with other agent outputs...")
        return
    
    if not competitor_prices:
        print(f"No competitor price history found for user {user_id}")
        return
    
    # Group by competitor
    competitors = {}
    for price in competitor_prices:
        if price.competitor_name not in competitors:
            competitors[price.competitor_name] = []
        competitors[price.competitor_name].append(price)
    
    print(f"Found price data for {len(competitors)} competitors")
    
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

def show_performance_monitoring(db, user_id, count=3):
    """Show performance monitoring data"""
    print("\n===== PERFORMANCE MONITORING =====")
    
    # Show anomalies
    try:
        anomalies = db.query(PerformanceAnomaly).filter(
            PerformanceAnomaly.user_id == user_id
        ).order_by(desc(PerformanceAnomaly.detected_at)).limit(count).all()
    except Exception as e:
        print(f"Error fetching performance anomalies: {str(e)}")
        anomalies = []
    
    if anomalies:
        print(f"Found {len(anomalies)} performance anomalies")
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
        print("No performance anomalies found")
    
    # Show baselines
    try:
        baselines = db.query(PerformanceBaseline).filter(
            PerformanceBaseline.user_id == user_id
        ).order_by(desc(PerformanceBaseline.baseline_date)).limit(count).all()
    except Exception as e:
        print(f"Error fetching performance baselines: {str(e)}")
        baselines = []
    
    if baselines:
        print(f"\nFound {len(baselines)} performance baselines")
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
        print("\nNo performance baselines found")

def show_order_summary(db, user_id):
    """Show a summary of recent orders for context"""
    print("\n===== ORDER SUMMARY =====")
    
    try:
        # Count total orders
        order_count = db.query(Order).filter(Order.user_id == user_id).count()
        
        if order_count == 0:
            print(f"No orders found for user {user_id}")
            return
        
        print(f"Total orders: {order_count}")
    except Exception as e:
        print(f"Error counting orders: {str(e)}")
        print("Continuing with debug output...")
    
    # Get date range
    first_order = db.query(Order).filter(Order.user_id == user_id).order_by(Order.order_date).first()
    last_order = db.query(Order).filter(Order.user_id == user_id).order_by(desc(Order.order_date)).first()
    
    if first_order and last_order:
        print(f"Date range: {first_order.order_date} to {last_order.order_date}")
    
    # Get most recent orders
    recent_orders = db.query(Order).filter(Order.user_id == user_id).order_by(
        desc(Order.order_date)
    ).limit(5).all()
    
    print("\nMost Recent Orders:")
    for i, order in enumerate(recent_orders, 1):
        print(f"{i}. Order {order.id} - {order.order_date} - ${order.total_amount:.2f}")
        
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        if order_items:
            print(f"   Items: {len(order_items)}")
            for j, item in enumerate(order_items[:3], 1):  # Show just the first 3
                item_record = db.query(Item).filter(Item.id == item.item_id).first()
                item_name = item_record.name if item_record else f"Item #{item.item_id}"
                print(f"   {j}. {item_name} - {item.quantity} × ${item.unit_price:.2f}")
            if len(order_items) > 3:
                print(f"   ... and {len(order_items) - 3} more items")

def main():
    """Main function to run the debug utility"""
    if len(sys.argv) < 2:
        # Show available users
        db = get_db()
        users = db.query(User).all()
        print("Available Users:")
        for user in users:
            print(f"  User ID: {user.id}, Email: {user.email}")
        
        print("\nUsage: python3 debug_all_agents.py [user_id]")
        print("Example: python3 debug_all_agents.py 1")
        return
    
    try:
        user_id = int(sys.argv[1])
    except ValueError:
        print("Error: user_id must be an integer")
        return
    
    db = get_db()
    
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        print(f"Error: User with ID {user_id} not found")
        return
    
    print(f"Showing debug output for user: {user.email} (ID: {user_id})")
    
    # Show order summary for context
    show_order_summary(db, user_id)
    
    # Show all agent outputs
    show_pricing_recommendations(db, user_id)
    show_experiments(db, user_id)
    show_market_analysis(db, user_id)
    show_competitor_analysis(db, user_id)
    show_performance_monitoring(db, user_id)
    
    # Show agent memories last (usually most detailed)
    show_agent_memories(db, user_id)
    
    db.close()

if __name__ == "__main__":
    main()
