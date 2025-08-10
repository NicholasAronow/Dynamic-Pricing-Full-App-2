"""
Application settings and environment variable management.
"""

import os
from typing import List, Optional
from dotenv import load_dotenv
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseSettings
    SettingsConfigDict = None

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./adaptiv.db")
    
    # Redis/Celery
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Authentication
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # External APIs
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    google_client_id: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
    google_search_engine_id: Optional[str] = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    stripe_secret_key: Optional[str] = os.getenv("STRIPE_SECRET_KEY")
    
    # Square Integration
    square_sandbox_secret: Optional[str] = os.getenv("SQUARE_SANDBOX_SECRET")
    square_sandbox_app_id: Optional[str] = os.getenv("SQUARE_SANDBOX_APP_ID")
    square_location_id: Optional[str] = os.getenv("SQUARE_LOCATION_ID")
    square_environment: str = os.getenv("SQUARE_ENVIRONMENT", "sandbox")
    
    # Knock Notifications
    knock_api_key: Optional[str] = os.getenv("KNOCK_API_KEY")
    knock_public_api_key: Optional[str] = os.getenv("KNOCK_PUBLIC_API_KEY")
    
    # Application
    app_name: str = "Adaptiv Dynamic Pricing"
    app_version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # CORS
    allowed_origins: list = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://adaptiv-frontend.vercel.app",
        "https://adaptiv-frontend-git-main-nicholasaronow.vercel.app",
        "https://adaptiv-frontend-nicholasaronow.vercel.app"
    ]
    
    # Pydantic v2 (pydantic-settings) supports SettingsConfigDict. If present, use it
    # to configure reading from .env and ignoring extra variables. Otherwise, fall
    # back to the v1-style inner Config with extra = "ignore".
    if 'SettingsConfigDict' in globals() and SettingsConfigDict is not None:
        model_config = SettingsConfigDict(
            env_file=".env",
            case_sensitive=False,
            extra="ignore",
        )
    else:
        class Config:
            env_file = ".env"
            case_sensitive = False
            extra = "ignore"

# Global settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """
    Get application settings singleton.
    
    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
