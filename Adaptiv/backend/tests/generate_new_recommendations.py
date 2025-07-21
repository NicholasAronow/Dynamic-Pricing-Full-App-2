#!/usr/bin/env python3
import sys
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RecommendationGenerator")

# Add the current directory to the path so we can import our models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.database import SessionLocal, engine
from models import User, Item, PricingRecommendation
from dynamic_pricing_agents.agents.pricing_strategy import PricingStrategyAgent

def generate_new_recommendations():
    """
    Generate fresh pricing recommendations to test the enhanced reevaluation date parsing
    """
    logger.info("Generating new pricing recommendations with enhanced date parsing")
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # Get the first user (for test purposes)
        user = db.query(User).first()
        if not user:
            logger.error("No users found in database")
            return
            
        logger.info(f"Using user: {user.email}")
        
        # Initialize the pricing strategy agent
        agent = PricingStrategyAgent()
        
        # Get a few items to process
        items = db.query(Item).filter(Item.user_id == user.id).limit(5).all()
        if not items:
            logger.error("No items found for this user")
            return
            
        logger.info(f"Found {len(items)} items to process")
        
        # Process each item to generate recommendations
        for item in items:
            logger.info(f"Processing item: {item.name} (Current price: ${item.current_price})")
            
            # Test price increase to ensure we get a recommendation
            test_price = item.current_price * 1.05  # 5% price increase
            
            # First calculate optimal price (we're suggesting a 5% increase for testing)
            item_data = {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "current_price": item.current_price,
                "cost": item.cost or item.current_price * 0.4
            }
            
            # For test purposes, use a small price increase to ensure we get a recommendation
            optimal_price = item.current_price * 1.05
            elasticity_data = {"elasticity_value": 0.7, "elasticity_category": "medium"}
            
            # Competitor prices should be a list of floats (actual competitor prices)
            competitor_prices = [item.current_price * 1.1, item.current_price * 1.05, item.current_price * 1.15]
            
            item_history = {"previous_prices": [], "previous_outcomes": []}
            goals = ["maximize_revenue"]
            
            # Generate the rationale with reevaluation date using the LLM
            logger.info(f"Generating rationale for {item.name} with reevaluation date")
            rationale = agent._generate_price_change_rationale(
                item_data, 
                item_data["current_price"], 
                optimal_price, 
                elasticity_data, 
                competitor_prices, 
                item_history, 
                goals
            )
            
            # IMPORTANT: The agent has updated item_data in-place with llm_pricing_analysis
            # Let's log what we have after the LLM call
            logger.info(f"After LLM call, item_data keys: {list(item_data.keys())}")
            if 'llm_pricing_analysis' in item_data:
                logger.info(f"llm_pricing_analysis keys: {list(item_data['llm_pricing_analysis'].keys())}")
            
            # Get the analysis which includes the reevaluation date
            llm_analysis = item_data.get('llm_pricing_analysis', {})
            reevaluation_date_str = llm_analysis.get('reevaluation_date')
            
            # Parse the reevaluation date string to a datetime object
            logger.info(f"Extracted reevaluation_date_str: {reevaluation_date_str}")
            
            if reevaluation_date_str:
                try:
                    # Parse the date string to a datetime object
                    from datetime import datetime
                    reevaluation_date = datetime.strptime(reevaluation_date_str, '%Y-%m-%d')
                    logger.info(f"Successfully parsed reevaluation_date: {reevaluation_date}")
                except ValueError as e:
                    logger.error(f"Error parsing reevaluation date: {e}")
                    # Default to 90 days from now if parsing fails
                    reevaluation_date = datetime.now() + timedelta(days=90)
                    logger.info(f"Using default reevaluation date: {reevaluation_date}")
            else:
                # Default to 90 days from now if no date string
                reevaluation_date = datetime.now() + timedelta(days=90)
                logger.info(f"No reevaluation_date_str found, using default: {reevaluation_date}")
            
            # Store recommendation in database
            logger.info(f"Storing recommendation for {item.name} with reevaluation date: {reevaluation_date}")
            
            # Create a batch ID for this set of recommendations
            import uuid
            batch_id = str(uuid.uuid4())
            
            # Manual recommendation creation to ensure we can verify the date is stored properly
            recommendation = models.PricingRecommendation(
                user_id=user.id,
                item_id=item.id,
                batch_id=batch_id,
                recommendation_date=datetime.utcnow(),
                current_price=item_data["current_price"],
                recommended_price=optimal_price,
                price_change_amount=optimal_price - item_data["current_price"],
                price_change_percent=((optimal_price - item_data["current_price"]) / item_data["current_price"]) * 100,
                strategy_type="optimal_pricing",
                confidence_score=llm_analysis.get('confidence', 0.8),
                rationale=rationale,
                reevaluation_date=reevaluation_date,  # Use the date parsed from LLM response
                implementation_status="pending"
            )
            
            db.add(recommendation)
            db.commit()
            
            logger.info(f"Recommendation generated for {item.name}:")
            logger.info(f"  Recommended price: ${recommendation.recommended_price:.2f}")
            logger.info(f"  Confidence score: {recommendation.confidence_score}")
            logger.info(f"  Reevaluation date: {recommendation.reevaluation_date}")
            logger.info(f"  Rationale: {recommendation.rationale[:50]}...")
            
            # The reevaluation_date should be set in the database by the agent's code
            
        logger.info("Finished generating recommendations")
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    generate_new_recommendations()
    
    # Now check if the new recommendations have unique reevaluation dates
    print("\nChecking new recommendations:")
    os.system("python3 check_latest_recommendations.py")
