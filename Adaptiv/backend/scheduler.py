"""
Scheduler Module

This module provides scheduling capabilities for recurring tasks like data synchronization.
"""
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from database import SessionLocal
from square_integration import sync_initial_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_all_square_data():
    """
    Synchronize all users' Square data
    This is run automatically at 12:01 AM daily
    """
    try:
        logger.info(f"Starting scheduled Square data sync at {datetime.now()}")
        
        # Create a new database session
        db = SessionLocal()
        
        try:
            # Get all users with Square integration
            from models import User, POSIntegration
            users_with_integration = (
                db.query(User.id)
                .join(POSIntegration, POSIntegration.user_id == User.id)
                .filter(POSIntegration.provider == "square")
                .filter(POSIntegration.access_token != None)
                .all()
            )
            
            logger.info(f"Found {len(users_with_integration)} users with Square integration")
            
            # Sync data for each user
            for user_id_tuple in users_with_integration:
                user_id = user_id_tuple[0]
                try:
                    logger.info(f"Syncing Square data for user {user_id}")
                    sync_initial_data(user_id, db)
                    logger.info(f"Successfully synced Square data for user {user_id}")
                except Exception as e:
                    logger.error(f"Error syncing Square data for user {user_id}: {str(e)}")
                    continue
            
            logger.info(f"Completed scheduled Square data sync at {datetime.now()}")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.exception(f"Failed to run scheduled Square sync: {str(e)}")

def create_scheduler():
    """Create and configure the scheduler"""
    scheduler = BackgroundScheduler()
    
    # Schedule Square data sync to run at 12:01 AM daily
    scheduler.add_job(
        sync_all_square_data,
        CronTrigger(hour=0, minute=1),  # 12:01 AM
        id='square_daily_sync',
        name='Daily Square Data Synchronization',
        replace_existing=True
    )
    
    return scheduler

# Create scheduler instance
scheduler = create_scheduler()
