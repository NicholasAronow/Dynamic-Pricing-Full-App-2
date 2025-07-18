"""
Middleware package for the Dynamic Pricing application.

This package contains all middleware components including:
- CORS configuration
- Authentication and subscription middleware
- Custom middleware utilities
"""

from .cors import setup_cors_middleware
from .subscription import require_subscription, SUBSCRIPTION_FREE, SUBSCRIPTION_PREMIUM
from .utils import setup_custom_middleware, TimingMiddleware, RequestLoggingMiddleware

__all__ = [
    'setup_cors_middleware',
    'require_subscription',
    'SUBSCRIPTION_FREE',
    'SUBSCRIPTION_PREMIUM',
    'setup_custom_middleware',
    'TimingMiddleware',
    'RequestLoggingMiddleware'
]
