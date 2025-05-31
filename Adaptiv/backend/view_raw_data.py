#!/usr/bin/env python3
"""
Simple utility to view raw agent data from the database without relying on specific models
"""
import sys
import json
import sqlite3
import os
from datetime import datetime
from pprint import pprint

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'adaptiv.db')

def format_json(data):
    """Format JSON data for better readability"""
    if isinstance(data, dict) or isinstance(data, list):
        return json.dumps(data, indent=2)
    return str(data)

def execute_query(query, params=None):
    """Execute a SQL query and return results"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        results = cursor.fetchall()
        return results
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        return []
    finally:
        conn.close()

def show_user_info(user_id):
    """Show basic user information"""
    users = execute_query("SELECT * FROM users WHERE id = ?", (user_id,))
    if not users:
        print(f"User with ID {user_id} not found!")
        return False
    
    user = users[0]
    print(f"User: {user['email']} (ID: {user_id})")
    
    # Get user's business info if available
    businesses = execute_query("SELECT * FROM business_profiles WHERE user_id = ?", (user_id,))
    if businesses:
        business = businesses[0]
        print(f"Business: {business['business_name']}")
        print(f"Location: {business['city']}, {business['state']}")
    
    return True

def show_pricing_recommendations(user_id):
    """Show recent pricing recommendations"""
    print("\n===== PRICING RECOMMENDATIONS =====")
    
    # Get table info to check available columns
    columns_info = execute_query("PRAGMA table_info(pricing_recommendations)")
    columns = [col['name'] for col in columns_info]
    
    # Build query based on available columns
    select_columns = ", ".join(columns)
    
    recommendations = execute_query(
        f"SELECT {select_columns} FROM pricing_recommendations WHERE user_id = ? ORDER BY recommendation_date DESC LIMIT 10",
        (user_id,)
    )
    
    if not recommendations:
        print("No pricing recommendations found")
        return
    
    print(f"Found {len(recommendations)} recommendations")
    
    for i, rec in enumerate(recommendations, 1):
        # Get item name
        item_id = rec['item_id']
        items = execute_query("SELECT name FROM items WHERE id = ?", (item_id,))
        item_name = items[0]['name'] if items else f"Item #{item_id}"
        
        print(f"\n{i}. {item_name} (ID: {item_id})")
        print(f"   Current Price: ${rec['current_price']:.2f} → Recommended: ${rec['recommended_price']:.2f}")
        
        # Calculate price change percentage
        if rec['current_price'] > 0:
            change_pct = ((rec['recommended_price'] - rec['current_price']) / rec['current_price']) * 100
            print(f"   Change: ${rec['recommended_price'] - rec['current_price']:.2f} ({change_pct:.1f}%)")
        
        # Show strategy type and confidence
        if 'strategy_type' in rec.keys():
            print(f"   Strategy Type: {rec['strategy_type']}")
        if 'confidence_score' in rec.keys():
            print(f"   Confidence: {rec['confidence_score']:.2f}")
        
        # Show metadata if present
        if 'metadata' in rec.keys() and rec['metadata']:
            try:
                metadata = json.loads(rec['metadata'])
                
                # Check for business type detection
                if isinstance(metadata, dict):
                    if 'business_type' in metadata:
                        print(f"   Business Type: {metadata['business_type']}")
                    
                    # Check for price rounding
                    if 'price_rounding' in metadata:
                        print(f"   Price Rounding: {metadata['price_rounding']}")
                    elif 'rounding_method' in metadata:
                        print(f"   Price Rounding: {metadata['rounding_method']}")
                    
                    # Check for reevaluation date
                    if 'reevaluation_date' in metadata:
                        print(f"   Reevaluation Date: {metadata['reevaluation_date']}")
                    
                    # Show other key factors
                    if 'key_factors' in metadata:
                        factors = metadata['key_factors']
                        if isinstance(factors, list):
                            print(f"   Key Factors: {', '.join(factors)}")
            except:
                print(f"   Metadata: {rec['metadata']}")
        
        # Show rationale
        if 'rationale' in rec.keys() and rec['rationale']:
            rationale = rec['rationale']
            print(f"   Rationale: {rationale[:150]}..." if len(rationale) > 150 else f"   Rationale: {rationale}")

def show_agent_memories(user_id):
    """Show agent memories with a focus on pricing strategy"""
    print("\n===== AGENT MEMORIES =====")
    
    # Check if the agent_memories table exists
    tables = execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_memories'")
    if not tables:
        print("Agent memories table doesn't exist in this database")
        return
    
    # Get all agent names for this user
    agents = execute_query("SELECT DISTINCT agent_name FROM agent_memories WHERE user_id = ?", (user_id,))
    
    if not agents:
        print(f"No agent memories found for user {user_id}")
        return
    
    agent_names = [agent['agent_name'] for agent in agents]
    print(f"Found memories for agents: {', '.join(agent_names)}")
    
    # Focus on pricing strategy agent
    pricing_agent_name = next((name for name in agent_names if 'pricing' in name.lower()), None)
    
    if pricing_agent_name:
        print(f"\n----- {pricing_agent_name.upper()} AGENT MEMORIES -----")
        
        memories = execute_query(
            "SELECT * FROM agent_memories WHERE user_id = ? AND agent_name = ? ORDER BY created_at DESC LIMIT 10",
            (user_id, pricing_agent_name)
        )
        
        for i, memory in enumerate(memories, 1):
            memory_type = memory['memory_type']
            created_at = memory['created_at']
            
            print(f"\n{i}. {memory_type} (Created: {created_at})")
            
            if 'content' in memory.keys() and memory['content']:
                try:
                    content = json.loads(memory['content'])
                    
                    # Extract key information
                    if isinstance(content, dict):
                        if 'item_name' in content:
                            print(f"   Item: {content['item_name']}")
                        
                        if 'current_price' in content and 'recommended_price' in content:
                            print(f"   Price: ${content['current_price']:.2f} → ${content['recommended_price']:.2f}")
                        
                        if 'business_type' in content:
                            print(f"   Business Type: {content['business_type']}")
                        
                        if 'price_rounding' in content:
                            print(f"   Price Rounding: {content['price_rounding']}")
                        
                        if 'reevaluation_date' in content:
                            print(f"   Reevaluation Date: {content['reevaluation_date']}")
                        
                        if 'rationale' in content:
                            rationale = content['rationale']
                            print(f"   Rationale: {rationale[:150]}..." if len(rationale) > 150 else f"   Rationale: {rationale}")
                except:
                    print(f"   Raw Content: {memory['content'][:100]}...")

def show_experiment_info(user_id):
    """Show experiment information"""
    print("\n===== PRICING EXPERIMENTS =====")
    
    # Check if the pricing_experiments table exists
    tables = execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name='pricing_experiments'")
    if not tables:
        print("Pricing experiments table doesn't exist in this database")
        return
    
    # Get columns
    columns_info = execute_query("PRAGMA table_info(pricing_experiments)")
    columns = [col['name'] for col in columns_info]
    
    select_columns = ", ".join(columns)
    experiments = execute_query(
        f"SELECT {select_columns} FROM pricing_experiments WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
        (user_id,)
    )
    
    if not experiments:
        print(f"No pricing experiments found for user {user_id}")
        return
    
    print(f"Found {len(experiments)} experiments")
    
    for i, exp in enumerate(experiments, 1):
        print(f"\n{i}. Experiment {exp['id']}: {exp['name']}")
        print(f"   Status: {exp['status']}")
        
        if 'started_at' in exp.keys() and exp['started_at']:
            print(f"   Started: {exp['started_at']}")
        if 'ended_at' in exp.keys() and exp['ended_at']:
            print(f"   Ended: {exp['ended_at']}")
        
        # Show experiment details
        if 'item_ids' in exp.keys() and exp['item_ids']:
            try:
                item_ids = json.loads(exp['item_ids'])
                if item_ids:
                    item_names = []
                    for item_id in item_ids:
                        items = execute_query("SELECT name FROM items WHERE id = ?", (item_id,))
                        item_names.append(items[0]['name'] if items else f"Item #{item_id}")
                    print(f"   Items: {', '.join(item_names)}")
            except:
                print(f"   Items: {exp['item_ids']}")
        
        # Show control and treatment prices
        if 'control_prices' in exp.keys() and exp['control_prices']:
            try:
                prices = json.loads(exp['control_prices'])
                print(f"   Control Prices: {format_json(prices)}")
            except:
                print(f"   Control Prices: {exp['control_prices']}")
        
        if 'treatment_prices' in exp.keys() and exp['treatment_prices']:
            try:
                prices = json.loads(exp['treatment_prices'])
                print(f"   Treatment Prices: {format_json(prices)}")
            except:
                print(f"   Treatment Prices: {exp['treatment_prices']}")
        
        # Show results
        result_field = next((col for col in columns if 'result' in col.lower()), None)
        if result_field and exp[result_field]:
            try:
                results = json.loads(exp[result_field])
                print(f"   Results: {format_json(results)}")
            except:
                print(f"   Results: {exp[result_field]}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 view_raw_data.py [user_id]")
        
        # Show all available users
        users = execute_query("SELECT id, email FROM users")
        if users:
            print("\nAvailable Users:")
            for user in users:
                print(f"  User ID: {user['id']}, Email: {user['email']}")
        return
    
    try:
        user_id = int(sys.argv[1])
    except ValueError:
        print("Error: user_id must be an integer")
        return
    
    # Show user info
    if not show_user_info(user_id):
        return
    
    # Show pricing recommendations
    show_pricing_recommendations(user_id)
    
    # Show experiment info
    show_experiment_info(user_id)
    
    # Show agent memories (focusing on pricing strategy)
    show_agent_memories(user_id)

if __name__ == "__main__":
    main()
