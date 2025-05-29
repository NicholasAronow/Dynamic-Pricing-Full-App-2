#!/usr/bin/env python3
"""Test each agent individually to see if they're working properly"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import logging
from datetime import datetime, timezone
from database import SessionLocal
from dynamic_pricing_agents.orchestrator import DynamicPricingOrchestrator
import models
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_individual_agents():
    """Test each agent individually"""
    db = SessionLocal()
    
    try:
        # Get test user
        user = db.query(models.User).filter(models.User.email == "testprofessional@test.com").first()
        if not user:
            logger.error("Test user not found!")
            return
        
        logger.info(f"Testing with user: {user.email} (ID: {user.id})")
        
        orchestrator = DynamicPricingOrchestrator()
        
        # Test 1: Data Collection Agent (no LLM)
        logger.info("\n" + "="*50)
        logger.info("TEST 1: Data Collection Agent")
        logger.info("="*50)
        start_time = time.time()
        
        try:
            collection_results = orchestrator._run_data_collection(db, user.id)
            elapsed = time.time() - start_time
            logger.info(f"✅ Data collection completed in {elapsed:.2f} seconds")
            logger.info(f"  - Orders collected: {len(collection_results.get('pos_data', {}).get('orders', []))}")
            logger.info(f"  - Competitors found: {len(collection_results.get('competitor_data', {}).get('competitors', []))}")
            logger.info(f"  - Data quality score: {collection_results.get('data_quality', {}).get('overall_score', 0):.2f}")
        except Exception as e:
            logger.error(f"❌ Data collection failed: {str(e)}")
            collection_results = None
        
        # Test 2: Parallel Analysis (Market + Performance Analysis - uses LLM)
        if collection_results:
            logger.info("\n" + "="*50)
            logger.info("TEST 2: Parallel Analysis Agents (Market + Performance - uses LLM)")
            logger.info("="*50)
            start_time = time.time()
            
            try:
                analysis_results = orchestrator._run_parallel_analysis(db, user.id, collection_results)
                elapsed = time.time() - start_time
                
                # Check market analysis
                market_results = analysis_results.get('market_analysis', {})
                if "error" in market_results:
                    logger.error(f"❌ Market analysis returned error: {market_results['error']}")
                else:
                    logger.info(f"✅ Market analysis completed")
                    logger.info(f"  - Has insights: {'insights' in market_results}")
                
                # Check performance analysis
                perf_results = analysis_results.get('performance_monitor', {})
                if "error" in perf_results:
                    logger.error(f"❌ Performance analysis returned error: {perf_results['error']}")
                else:
                    logger.info(f"✅ Performance analysis completed")
                
                logger.info(f"Total parallel analysis time: {elapsed:.2f} seconds")
                
            except Exception as e:
                logger.error(f"❌ Parallel analysis failed: {str(e)}")
                analysis_results = None
        
        # Test 3: Pricing Strategy Agent (uses LLM)
        if collection_results and analysis_results:
            logger.info("\n" + "="*50)
            logger.info("TEST 3: Pricing Strategy Agent (uses LLM)")
            logger.info("="*50)
            start_time = time.time()
            
            try:
                strategy_results = orchestrator._run_strategy_development(
                    db, user.id, collection_results, analysis_results
                )
                elapsed = time.time() - start_time
                
                if "error" in strategy_results:
                    logger.error(f"❌ Pricing strategy returned error: {strategy_results['error']}")
                else:
                    logger.info(f"✅ Pricing strategy completed in {elapsed:.2f} seconds")
                    logger.info(f"  - Status: {strategy_results.get('status', 'unknown')}")
                    logger.info(f"  - Has strategy: {'strategy' in strategy_results}")
            except Exception as e:
                logger.error(f"❌ Pricing strategy failed: {str(e)}")
        
        logger.info("\n" + "="*50)
        logger.info("SUMMARY")
        logger.info("="*50)
        logger.info("The agents are configured to use gpt-4o-mini for cost savings.")
        logger.info("If you're seeing API quota errors, the agents will return error messages.")
        logger.info("Otherwise, they should process normally and return actual insights.")
        
    except Exception as e:
        logger.error(f"Test error: {str(e)}", exc_info=True)
    finally:
        db.close()

def debug_item_price_error():
    """Specifically debug the 'Item' object has no attribute 'price' error"""
    import traceback
    db = SessionLocal()
    
    try:
        # Get test user
        user = db.query(models.User).filter(models.User.email == "testprofessional@test.com").first()
        if not user:
            logger.error("Test user not found!")
            return
            
        logger.info("=" * 50)
        logger.info("DEBUGGING PRICE ATTRIBUTE ERROR")
        logger.info("=" * 50)
        
        # First, check Item model to confirm it uses current_price
        item = db.query(models.Item).first()
        logger.info(f"Item model attributes: {dir(item)}")
        logger.info(f"Item price attribute: {item.current_price}")
        
        # Then check CompetitorItem model
        comp_item = db.query(models.CompetitorItem).first()
        if comp_item:
            logger.info(f"CompetitorItem model attributes: {dir(comp_item)}")
            logger.info(f"CompetitorItem price attribute: {comp_item.price}")
        else:
            logger.info("No CompetitorItem found for testing")
        
        # Now debug data collection specifically
        logger.info("\nTesting data collection only...")
        orchestrator = DynamicPricingOrchestrator()
        try:
            collection_data = orchestrator._run_data_collection(db, user.id)
            logger.info("✅ Data collection successful")
        except Exception as e:
            logger.error(f"❌ Data collection failed: {str(e)}")
            logger.error(traceback.format_exc())
        
        # Debug market analysis
        logger.info("\nTesting market analysis...")
        market_results = None
        try:
            market_context = {
                "db": db,
                "user_id": user.id,
                "consolidated_data": collection_data
            }
            market_agent = orchestrator.agents['market_analysis']
            market_results = market_agent.process(market_context)
            logger.info("✅ Market analysis successful")
        except Exception as e:
            logger.error(f"❌ Market analysis failed: {str(e)}")
            logger.error(traceback.format_exc())
            
        # Debug performance monitor
        logger.info("\nTesting performance monitor...")
        perf_results = None
        try:
            perf_context = {
                "db": db,
                "user_id": user.id,
                "consolidated_data": collection_data
            }
            perf_agent = orchestrator.agents['performance_monitor']
            perf_results = perf_agent.process(perf_context)
            logger.info("✅ Performance monitor successful")
        except Exception as e:
            logger.error(f"❌ Performance monitor failed: {str(e)}")
            logger.error(traceback.format_exc())
            
        # Debug pricing strategy
        if market_results:
            logger.info("\nTesting pricing strategy...")
            try:
                strategy_context = {
                    "db": db,
                    "user_id": user.id,
                    "consolidated_data": collection_data,
                    "market_analysis": market_results,
                    "performance_data": perf_results or {}
                }
                strategy_agent = orchestrator.agents['pricing_strategy']
                strategy_results = strategy_agent.process(strategy_context)
                logger.info("✅ Pricing strategy successful")
            except Exception as e:
                logger.error(f"❌ Pricing strategy failed: {str(e)}")
                logger.error(traceback.format_exc())
        
        # Debug experimentation
        logger.info("\nTesting experimentation...")
        try:
            exp_context = {
                "db": db,
                "user_id": user.id,
                "consolidated_data": collection_data,
                "market_analysis": market_results or {},
                "pricing_strategy": strategy_results if 'strategy_results' in locals() else {}
            }
            exp_agent = orchestrator.agents['experimentation']
            exp_results = exp_agent.process(exp_context)
            logger.info("✅ Experimentation successful")
        except Exception as e:
            logger.error(f"❌ Experimentation failed: {str(e)}")
            logger.error(traceback.format_exc())
    
    except Exception as e:
        logger.error(f"Debug error: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        db.close()

if __name__ == "__main__":
    # test_individual_agents()
    debug_item_price_error()
