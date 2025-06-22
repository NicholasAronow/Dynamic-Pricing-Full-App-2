#!/usr/bin/env python3
"""
Daily Pricing Agent Runner

This script is designed to run as a Render cron job at 12:01am each day.
It fetches all active user accounts and runs the AggregatePricingAgent's process
function for each account through the existing Celery task framework.

To set up in Render:
1. Add this script to your repository
2. In Render dashboard, create a cron job service
3. Set the schedule to "1 0 * * *" (12:01am daily)
4. Set the command to "cd /opt/render/project/src/Adaptiv/backend && python run_daily_pricing_agent.py"
"""

import logging
import sys
import os
import time
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("daily_pricing_agent")

# Add the current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import database models and Celery task
from database import SessionLocal
import models
from tasks import run_dynamic_pricing_analysis_task

def get_active_users() -> List[Dict[str, Any]]:
    """
    Get all active users from the database
    
    Returns:
        List of user dictionaries with id and email
    """
    db = SessionLocal()
    try:
        users = db.query(models.User).filter(models.User.is_active == True).all()
        return [{"id": user.id, "email": user.email} for user in users]
    except Exception as e:
        logger.error(f"Error fetching active users: {str(e)}")
        return []
    finally:
        db.close()

def main():
    """Main function to run the AggregatePricingAgent for all active users"""
    
    start_time = time.time()
    logger.info(f"Starting daily pricing agent run at {datetime.now().isoformat()}")
    
    # Get all active users
    users = get_active_users()
    logger.info(f"Found {len(users)} active users")
    
    # Track success and failures
    successes = 0
    failures = 0
    
    # Run the pricing agent for each user
    for user in users:
        user_id = user["id"]
        user_email = user["email"]
        
        try:
            logger.info(f"Running pricing agent for user {user_id} ({user_email})")
            
            # Run the task
            # Note: This runs the task synchronously within this process
            # If we were using Celery workers, we'd use .delay() instead
            result = run_dynamic_pricing_analysis_task(user_id)
            
            if result.get("success"):
                batch_id = result.get("batch_id")
                recommendations_count = len(result.get("pricing_recommendations", []))
                logger.info(f"✅ Success for user {user_id}: Generated {recommendations_count} recommendations (batch_id: {batch_id})")
                successes += 1
            else:
                logger.error(f"❌ Task for user {user_id} returned error: {result.get('error')}")
                failures += 1
                
        except Exception as e:
            logger.error(f"❌ Error processing user {user_id}: {str(e)}")
            failures += 1
    
    # Log summary
    end_time = time.time()
    duration = end_time - start_time
    logger.info(f"Daily pricing agent run completed in {duration:.2f} seconds")
    logger.info(f"Summary: {successes} successes, {failures} failures out of {len(users)} users")

if __name__ == "__main__":
    main()
