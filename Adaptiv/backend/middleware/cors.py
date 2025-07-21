from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import get_settings


def setup_cors_middleware(app: FastAPI):
    """
    Configure CORS middleware for the FastAPI application.
    
    This function centralizes CORS configuration to make it easier to manage
    allowed origins, methods, and headers.
    """
    settings = get_settings()
    
    # Extend default origins with additional production URLs
    allowed_origins = settings.allowed_origins + [
        "https://*.vercel.app",
        "https://adaptiv-dynamic-pricing.vercel.app",
        "https://adaptiv-eight.vercel.app",
        "https://www.adaptiv.one",
        "https://adaptiv-l9z8a1e32-nicholasaronows-projects.vercel.app"
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
