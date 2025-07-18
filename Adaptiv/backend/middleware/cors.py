from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_cors_middleware(app: FastAPI):
    """
    Configure CORS middleware for the FastAPI application.
    
    This function centralizes CORS configuration to make it easier to manage
    allowed origins, methods, and headers.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000", 
            "http://127.0.0.1:3000",
            "https://*.vercel.app",
            "https://adaptiv-dynamic-pricing.vercel.app",
            "https://adaptiv-eight.vercel.app",
            "https://www.adaptiv.one",
            "https://adaptiv-l9z8a1e32-nicholasaronows-projects.vercel.app"
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
