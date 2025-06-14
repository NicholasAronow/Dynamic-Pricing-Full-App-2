"""
Scheduler module for managing background tasks in the Adaptiv API.
This provides a simple interface for scheduling and running periodic tasks.
"""

from apscheduler.schedulers.background import BackgroundScheduler
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("scheduler")

# Create scheduler instance
scheduler = BackgroundScheduler()

# Flag to track if the scheduler is currently running (use custom attribute instead of property)
scheduler.is_running = False

# Monkey patch the scheduler's start method to set the running flag
original_start = scheduler.start
def patched_start(*args, **kwargs):
    result = original_start(*args, **kwargs)
    scheduler.is_running = True
    logger.info("Scheduler started")
    return result
    
scheduler.start = patched_start

# Monkey patch the scheduler's shutdown method to clear the running flag
original_shutdown = scheduler.shutdown
def patched_shutdown(*args, **kwargs):
    result = original_shutdown(*args, **kwargs)
    scheduler.is_running = False
    logger.info("Scheduler shutting down")
    return result

scheduler.shutdown = patched_shutdown

# You can add scheduled jobs here
# Example:
# @scheduler.scheduled_job('interval', minutes=30)
# def periodic_task():
#     # Do something periodically
#     pass

# Alternatively, jobs can be added from other modules by importing this scheduler
