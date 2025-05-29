#!/usr/bin/env python3
"""Test script to diagnose agent performance issues"""
import time
import logging
from database import SessionLocal
from dynamic_pricing_agents.orchestrator import DynamicPricingOrchestrator
import models

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_agent_speed():
    """Test the speed of the dynamic pricing agents"""
    db = SessionLocal()
    
    try:
        # Get a test user
        user = db.query(models.User).filter(models.User.email == "testprofessional@test.com").first()
        if not user:
            logger.error("Test user not found")
            return
            
        logger.info(f"Testing with user: {user.email} (ID: {user.id})")
        
        # Initialize orchestrator
        orchestrator = DynamicPricingOrchestrator()
        
        # Run only data collection phase
        logger.info("Starting data collection test...")
        start_time = time.time()
        
        try:
            collection_results = orchestrator._run_data_collection(db, user.id)
            end_time = time.time()
            
            logger.info(f"Data collection completed in {end_time - start_time:.2f} seconds")
            logger.info(f"POS data orders: {len(collection_results.get('pos_data', {}).get('orders', []))}")
            logger.info(f"Competitors: {len(collection_results.get('competitor_data', {}).get('competitors', []))}")
            logger.info(f"Price history changes: {len(collection_results.get('price_history', {}).get('changes', []))}")
            
        except Exception as e:
            logger.error(f"Error during data collection: {str(e)}")
            import traceback
            traceback.print_exc()
            
    finally:
        db.close()

if __name__ == "__main__":
    test_agent_speed()
