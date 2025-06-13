#!/bin/bash

# This script starts the Redis Queue worker process for background job processing
set -e  # Exit on any error

echo "===== Starting Worker Deployment ====="
echo "Current directory: $(pwd)"
echo "Python version: $(python3 --version)"

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# Install specific versions of critical packages
echo "Installing specific versions of critical packages..."
pip install redis==4.5.1 rq==1.15.1 google-generativeai==0.3.1 sqlalchemy==2.0.23

# Verify environment variables
echo "Checking environment variables..."
if [ -z "$REDIS_URL" ]; then
    echo "WARNING: REDIS_URL environment variable is not set!"
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo "WARNING: GEMINI_API_KEY environment variable is not set!"
fi

if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL environment variable is not set!"
fi

echo "Setting up worker..."

# Create a heartbeat file that can be monitored
STATUS_FILE="worker_status.txt"
echo "Worker starting at $(date)" > $STATUS_FILE

# Start the worker with proper resilience
echo "Starting RQ worker..."
exec python3 worker.py

# Note: 'exec' replaces the shell with the worker process
# This ensures proper signal handling and health checks
