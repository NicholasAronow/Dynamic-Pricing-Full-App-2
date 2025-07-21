"""
Celery configuration for background task processing.
"""

from celery import Celery
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set Redis URL from environment variable or use default
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "adaptiv",
    broker=redis_url,
    backend=redis_url,
    include=["tasks"]  # This tells Celery to import the tasks module
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/New_York",  # Eastern Time Zone (EST/EDT)
    enable_utc=False,  # Don't use UTC
    worker_concurrency=2,  # Adjust based on your server capacity
    task_track_started=True,
    task_time_limit=600,    # 10 minutes timeout for tasks
)

if __name__ == "__main__":
    celery_app.start()
