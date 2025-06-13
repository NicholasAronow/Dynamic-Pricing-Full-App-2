import os
import sys
import time
import redis
from rq import Worker, Queue
from redis import Redis
from rq.worker import WorkerStatus
import logging
import signal
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("worker")

# Redis connection settings
listen = ['default']
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
logger.info(f"Connecting to Redis at {redis_url}")

try:
    conn = redis.from_url(redis_url)
    ping_result = conn.ping()
    logger.info(f"Redis connection test: {'SUCCESS' if ping_result else 'FAILED'}")
    logger.info(f"Redis server info: {conn.info()}")
except Exception as e:
    logger.error(f"Error connecting to Redis: {str(e)}")
    raise e

# Log environment variables (sanitized)
for env_var in ['REDIS_URL', 'GEMINI_API_KEY', 'GOOGLE_API_KEY']:
    value = os.getenv(env_var)
    if value:
        masked_value = value[:4] + '...' + value[-4:] if len(value) > 8 else '****'
        logger.info(f"Environment variable {env_var} is set: {masked_value}")
    else:
        logger.warning(f"Environment variable {env_var} is NOT set")
        
logger.info(f"Setting up Redis Queue worker with connection URL: {redis_url}")

# Signal handlers for graceful shutdown
def handle_sigterm(signum, frame):
    logger.info("Received SIGTERM signal, shutting down gracefully...")
    # Worker will be instructed to shut down in the main loop
    global shutdown_requested
    shutdown_requested = True

# Register signal handlers
signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)

# Custom exception handler to log job failures
def exception_handler(job, exc_type, exc_value, traceback):
    logger.error(f"Job {job.id} failed with exception: {exc_type.__name__}: {exc_value}")
    logger.error("Traceback: \n" + ''.join(traceback.format_tb(traceback)))
    # Update job status in the database to mark as failed
    try:
        from jobs import update_job_status, SessionLocal
        db = SessionLocal()
        update_job_status(db, job.meta.get('report_id'), "failed", str(exc_value))
        db.close()
    except Exception as e:
        logger.error(f"Error updating job status: {e}")
    return False  # Let RQ's default exception handling proceed

# Global flag for shutdown
shutdown_requested = False

# Main worker function with auto-recovery
def start_worker():
    global shutdown_requested
    max_retries = 10
    retry_count = 0
    retry_delay = 5  # seconds
    
    while not shutdown_requested and retry_count < max_retries:
        try:
            logger.info("Starting RQ worker...")
            
            # Create queues from the listen list
            queues = [Queue(name, connection=conn) for name in listen]
            
            # Create worker directly with the connection
            worker = Worker(queues, exception_handlers=[exception_handler], connection=conn)
            worker.push_exc_handler(exception_handler)
            
            logger.info(f"Worker listening to queues: {listen}")
            logger.info(f"Worker ID: {worker.name}")
            logger.info("Starting work loop...")
            
            # Reset retry count after successful startup
            retry_count = 0
            
            # Customized work loop for better handling of shutdowns
            worker.work(with_scheduler=True)
            
            if shutdown_requested:
                logger.info("Shutdown requested, exiting work loop")
                break
                    
        except redis.exceptions.ConnectionError as e:
            retry_count += 1
            logger.error(f"Redis connection error: {e}. Retry {retry_count}/{max_retries} in {retry_delay} seconds")
            time.sleep(retry_delay)
            # Increase delay with each retry
            retry_delay = min(retry_delay * 2, 60)  # Max 60 second delay
        except Exception as e:
            retry_count += 1
            logger.critical(f"Worker failed with error: {str(e)}")
            logger.critical(traceback.format_exc())
            logger.info(f"Retrying {retry_count}/{max_retries} in {retry_delay} seconds")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)  # Max 60 second delay
    
    if retry_count >= max_retries:
        logger.critical(f"Exceeded maximum retry attempts ({max_retries}). Exiting.")
        sys.exit(1)
    
    logger.info("Worker shutting down gracefully")

if __name__ == '__main__':
    try:
        start_worker()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, exiting")
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
        logger.critical(traceback.format_exc())
        sys.exit(1)
