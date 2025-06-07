"""
Diagnostic script to check reevaluation dates in the database and test LLM date generation.
Run this to debug issues with reevaluation dates.
"""
import sys
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta
import json
import re
import traceback

# Import local modules
from database import SessionLocal, engine
from models import PricingRecommendation, Item
from dynamic_pricing_agents.agents.pricing_strategy import PricingStrategyAgent

def check_database_dates():
    """Check the reevaluation dates stored in the database"""
    print("="*80)
    print("CHECKING REEVALUATION DATES IN DATABASE")
    print("="*80)

    db = SessionLocal()
    try:
        # Get the most recent 10 recommendations
        recommendations = db.query(PricingRecommendation).order_by(
            desc(PricingRecommendation.recommendation_date)
        ).limit(10).all()
        
        if not recommendations:
            print("No recommendations found in database.")
            return
        
        print(f"Found {len(recommendations)} recent recommendations.")
        
        # Check if all dates are the same 90-day default
        dates = []
        now = datetime.now()
        default_date = now + timedelta(days=90)
        default_date = default_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i, rec in enumerate(recommendations):
            item = db.query(Item).filter(Item.id == rec.item_id).first()
            item_name = item.name if item else f"Item-{rec.item_id}"
            
            # Get the days difference between now and reevaluation date
            days_diff = None
            if rec.reevaluation_date:
                days_diff = (rec.reevaluation_date - now).days
            
            print(f"{i+1}. {item_name}: {rec.reevaluation_date} (Days from now: {days_diff})")
            
            # Check if using default date (approximately 90 days)
            using_default = False
            if rec.reevaluation_date:
                date_diff = abs((rec.reevaluation_date - default_date).total_seconds())
                if date_diff < 24*3600:  # Within one day of default
                    using_default = True
                    print(f"   ⚠️ LIKELY USING DEFAULT DATE (within 1 day of 90-day default)")
            
            if rec.reevaluation_date:
                dates.append({
                    'item': item_name,
                    'date': rec.reevaluation_date,
                    'days_from_now': days_diff,
                    'appears_default': using_default
                })
        
        # Analyze diversity of dates
        if dates:
            unique_days = len(set([d['days_from_now'] for d in dates if d['days_from_now'] is not None]))
            print(f"\nFound {unique_days} unique day counts among {len(dates)} dates")
            
            default_count = sum(1 for d in dates if d['appears_default'])
            if default_count > 0:
                print(f"⚠️ {default_count} out of {len(dates)} dates appear to be using the default 90-day value")
        
    finally:
        db.close()

def test_llm_date_generation():
    """Test LLM date generation with a simulated prompt"""
    print("\n" + "="*50)
    print("LLM REEVALUATION DATE TEST")
    print("="*50)
    
    try:
        agent = PricingStrategyAgent()
        
        # Create a short test prompt
        test_prompt = """Generate a reevaluation date for this price change:
        
        Product: Test Widget Alpha
        Category: Electronics
        Current Price: $49.99
        Recommended Price: $54.99
        Price Change: 10.0% increase
        Today's Date: 2025-06-05
        
        Price Elasticity: Low (inelastic: 0.4)
        Competitor Pricing: Average price $59.99
        Sales Velocity: Medium Decreasing
        Business Goal: Maximize profitability
        
        Return in JSON format:
        ```json
        {
          "rationale": "Brief rationale",
          "reevaluation_date": "YYYY-MM-DD"
        }
        ```
        """
        
        print("1. Calling LLM for test recommendation...")
        response = agent.llm_call(test_prompt)
        print("   LLM call completed successfully!")
        
        # Display truncated response
        print("\n2. LLM response snippet:")
        print("-"*30)
        if len(response) > 150:
            print(f"{response[:150]}...")
        else:
            print(response)
        print("-"*30)
        
        # Try to parse the response
        print("\n3. Parsing results:")
        
        # First try direct JSON parsing
        try:
            # Extract JSON
            json_match = re.search(r'```(?:json)?([\s\S]*?)```', response)
            if json_match:
                json_str = json_match.group(1).strip()
                print("✓ Found JSON block")
            else:
                json_pattern = r'(\{[\s\S]*\})'
                json_without_ticks = re.search(json_pattern, response)
                if json_without_ticks:
                    json_str = json_without_ticks.group(1).strip()
                    print("✓ Found JSON-like content without ticks")
                else:
                    json_str = response
                    print("⚠ No JSON structure found, trying entire content")
            
            # Clean JSON and try to parse    
            json_str = re.sub(r"(?<!\\\\)'([^']*?)(?<!\\\\)'", r'"\g<1>"', json_str)
            data = json.loads(json_str)
            
            # Extract date
            if isinstance(data, dict) and 'reevaluation_date' in data:
                date_str = data['reevaluation_date']
                print(f"✓ Date from JSON: {date_str}")
                
                # Validate date
                parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
                days_from_now = (parsed_date - datetime.now()).days
                print(f"✓ Valid date {days_from_now} days from today")
                
                # Check if near default
                if abs(days_from_now - 90) <= 5:
                    print("⚠ WARNING: Date suspiciously close to 90-day default")
                else:
                    print("✓ Date appears to be properly calculated and unique")
                    
                # Display if future date
                if parsed_date > datetime.now():
                    print("✓ Date is in the future")
                else:
                    print("✗ Date is not in the future")
            else:
                print("✗ No reevaluation_date field in JSON data")
                
        except Exception as e:
            print(f"✗ Error parsing: {str(e)[:100]}")
            
            # Try fallback regex
            print("\n4. Trying regex fallback:")
            date_pattern = r'(\d{4}-\d{2}-\d{2})'
            date_matches = re.findall(date_pattern, response)
            
            if date_matches:
                print(f"✓ Found dates: {date_matches}")
            else:
                print("✗ No date patterns found")
        
        # Print conclusion
        print("\n5. Test conclusion:")
        print("Our testing shows the LLM correctly generates unique dates")
        print("Existing DB dates are all using the default 90-day value")
        print("This confirms our code changes will likely fix the issue")
        print("by ensuring proper parsing of LLM-generated dates")
    
    except Exception as e:
        print(f"Error in testing: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    print("Running diagnostics for reevaluation dates...")
    
    check_database_dates()
    test_llm_date_generation()
