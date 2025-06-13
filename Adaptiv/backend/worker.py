import os
import redis
from rq import Worker, Queue, Connection
import logging

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

# Custom exception handler to log job failures
def exception_handler(job, exc_type, exc_value, traceback):
    logger.error(f"Job {job.id} failed with exception: {exc_type.__name__}: {exc_value}")
    return False  # Let RQ's default exception handling proceed

if __name__ == '__main__':
    logger.info("Starting RQ worker...")
    with Connection(conn):
        try:
            worker = Worker(list(map(Queue, listen)), exception_handlers=[exception_handler])
            logger.info(f"Worker listening to queues: {listen}")
            logger.info(f"Worker ID: {worker.name}")
            logger.info("Starting work loop...")
            worker.work(with_scheduler=True)
        except Exception as e:
            logger.critical(f"Worker failed to start: {str(e)}")
            raise e
