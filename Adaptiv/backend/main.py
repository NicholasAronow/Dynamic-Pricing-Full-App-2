# Load environment variables from .env file
import os
from dotenv import load_dotenv

# Load environment variables before any other imports
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from database import get_db, engine
import models, schemas
from auth import auth_router
from login_endpoint import login_router
from register_endpoint import register_router
from profile import profile_router
from items import items_router
from price_history import price_history_router
from competitor_items import competitor_items_router
from orders import orders_router
from dashboard import dashboard_router
from item_analytics import item_analytics_router
from cogs import cogs_router
from action_items import action_items_router
from square_integration import square_router

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Adaptiv API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*", 
        "https://*.vercel.app",
        "https://adaptiv-dynamic-pricing.vercel.app",
        "https://adaptiv-eight.vercel.app",
        "https://adaptiv-l9z8a1e32-nicholasaronows-projects.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(login_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(register_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(profile_router, prefix="/api/profile", tags=["Profile"])
app.include_router(items_router, prefix="/api/items", tags=["Items"])
app.include_router(price_history_router, prefix="/api/price-history", tags=["Price History"])
app.include_router(competitor_items_router, prefix="/api/competitor-items", tags=["Competitor Items"])
app.include_router(orders_router, prefix="/api/orders", tags=["Orders"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(item_analytics_router, prefix="/api/item-analytics", tags=["Item Analytics"])
app.include_router(cogs_router, prefix="/api/cogs", tags=["COGS"])
app.include_router(action_items_router, prefix="/api/action-items", tags=["Action Items"])
app.include_router(square_router, prefix="/api/integrations/square", tags=["Square Integration"])

@app.get("/")
async def root():
    return {"message": "Welcome to Adaptiv API"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
