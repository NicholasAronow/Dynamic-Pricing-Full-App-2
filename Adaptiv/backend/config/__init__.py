"""
Configuration package for the Adaptiv backend.

This package contains all configuration-related modules:
- database: Database connection and session management
- celery: Celery task queue configuration  
- auth: Authentication and JWT settings
- settings: Application settings and environment variables
- external_apis: External API configurations (OpenAI, Square, etc.)
"""

from .database import engine, SessionLocal, Base, get_db
from .celery_config import celery_app
from .auth_config import (
    SECRET_KEY, 
    ALGORITHM, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    verify_token,
    get_current_user
)
from .settings import Settings, get_settings
from .external_apis import (
    get_openai_client,
    get_square_client,
    GOOGLE_CLIENT_ID,
    STRIPE_SECRET_KEY
)

__all__ = [
    # Database
    "engine",
    "SessionLocal", 
    "Base",
    "get_db",
    
    # Celery
    "celery_app",
    
    # Authentication
    "SECRET_KEY",
    "ALGORITHM", 
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "create_access_token",
    "verify_token",
    "get_current_user",
    
    # Settings
    "Settings",
    "get_settings",
    
    # External APIs
    "get_openai_client",
    "get_square_client", 
    "GOOGLE_CLIENT_ID",
    "STRIPE_SECRET_KEY"
]
