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
conn = redis.from_url(redis_url)

logger.info(f"Setting up Redis Queue worker with connection URL: {redis_url}")

if __name__ == '__main__':
    logger.info("Starting RQ worker...")
    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        logger.info(f"Worker listening to queues: {listen}")
        worker.work(with_scheduler=True)
