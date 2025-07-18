"""
Utility functions and base classes for middleware components.

This module provides common utilities that can be used across different
middleware implementations.
"""

from fastapi import Request, Response
from typing import Callable
import time
import logging

logger = logging.getLogger(__name__)

# Try to import BaseHTTPMiddleware, but make it optional
try:
    from starlette.middleware.base import BaseHTTPMiddleware
    MIDDLEWARE_AVAILABLE = True
except ImportError:
    # If BaseHTTPMiddleware is not available, create a dummy class
    class BaseHTTPMiddleware:
        def __init__(self, app):
            self.app = app
    MIDDLEWARE_AVAILABLE = False
    logger.warning("BaseHTTPMiddleware not available. Custom middleware classes will be disabled.")


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log request processing time.
    
    This can be useful for monitoring API performance and identifying
    slow endpoints.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not MIDDLEWARE_AVAILABLE:
            return await call_next(request)
            
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        logger.info(f"{request.method} {request.url.path} - {process_time:.4f}s")
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log incoming requests.
    
    Useful for debugging and monitoring API usage.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not MIDDLEWARE_AVAILABLE:
            return await call_next(request)
            
        logger.info(f"Incoming request: {request.method} {request.url}")
        
        response = await call_next(request)
        
        logger.info(f"Response status: {response.status_code}")
        
        return response


def setup_custom_middleware(app):
    """
    Setup custom middleware for the application.
    
    This function can be called from main.py to add custom middleware
    like timing and request logging.
    """
    # Uncomment the following lines to enable custom middleware
    # app.add_middleware(TimingMiddleware)
    # app.add_middleware(RequestLoggingMiddleware)
    pass
