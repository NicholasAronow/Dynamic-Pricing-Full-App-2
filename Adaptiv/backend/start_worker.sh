#!/bin/bash

# Start the RQ worker for processing background jobs
# Install dependencies if needed
pip install -r requirements.txt

# Set environment variables if they aren't already set in the environment
# export REDIS_URL="redis://localhost:6379"
# export GEMINI_API_KEY="your_gemini_api_key_here"

# Start the worker with specified queue, worker count, and timeout
echo "Starting RQ worker for menu extraction tasks..."
python worker.py
