# Load environment variables from .env file
import os
from dotenv import load_dotenv

# Load environment variables before any other imports
load_dotenv()

from fastapi import FastAPI
from sqlalchemy.orm import Session
from typing import List

from config.database import get_db, engine, Base
import models, schemas
from routers.auth import auth_router
from routers.login_endpoint import login_router
from routers.register_endpoint import register_router
from authentication.google_auth import google_auth_router
from middleware import setup_cors_middleware
from routers.profile import profile_router
from routers.items import items_router
from routers.price_history import price_history_router
from routers.competitor_items import competitor_items_router
from routers.competitor_entities import competitor_entities_router
from routers.orders import orders_router
from routers.dashboard import dashboard_router
from routers.item_analytics import item_analytics_router
from routers.cogs import cogs_router
from routers.action_items import action_items_router
from routers.square_integration import square_router
from routers.pricing_recommendations import pricing_recommendations_router
from dynamic_pricing_agents.api_routes import router as dynamic_pricing_router
from routers.gemini_competitor_search import gemini_competitor_router
from routers.competitor_settings import competitor_settings_router
from routers.admin_routes import admin_router
from routers.recipes import router as recipes_router
from routers.ai_suggestions import router as ai_suggestions_router
from routers.other_costs import other_costs_router
from routers.subscriptions import router as subscriptions_router
from routers.premium_analytics import router as premium_analytics_router
from routers.langgraph_routes import router as langgraph_router

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Adaptiv API")

# Setup CORS middleware
setup_cors_middleware(app)

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(login_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(register_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(google_auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(profile_router, prefix="/api/profile", tags=["Profile"])
app.include_router(items_router, prefix="/api/items", tags=["Items"])
app.include_router(price_history_router, prefix="/api/price-history", tags=["Price History"])
app.include_router(competitor_items_router, prefix="/api/competitor-items", tags=["Competitor Items"])
app.include_router(competitor_entities_router, prefix="/api/competitor-entities", tags=["Competitor Entities"])
app.include_router(orders_router, prefix="/api/orders", tags=["Orders"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(item_analytics_router, prefix="/api/item-analytics", tags=["Item Analytics"])
app.include_router(cogs_router, prefix="/api/cogs", tags=["COGS"])
app.include_router(action_items_router, prefix="/api/action-items", tags=["Action Items"])
app.include_router(square_router, prefix="/api/integrations/square", tags=["Square Integration"])
app.include_router(pricing_recommendations_router, prefix="/api/pricing", tags=["Pricing Recommendations"])
app.include_router(dynamic_pricing_router, prefix="/api/agents/dynamic-pricing", tags=["Dynamic Pricing Agents"])
app.include_router(gemini_competitor_router, prefix="/api/gemini-competitors", tags=["Gemini Competitor Search"])
app.include_router(competitor_settings_router, prefix="/api/competitor-settings", tags=["Competitor Settings"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(recipes_router, prefix="/api", tags=["Recipes and Ingredients"])
app.include_router(ai_suggestions_router, prefix="/api", tags=["AI Suggestions"])
app.include_router(other_costs_router, prefix="/api/costs/other", tags=["Fixed Costs and Employees"])
app.include_router(subscriptions_router, prefix="/api/subscriptions", tags=["Subscriptions"])
app.include_router(premium_analytics_router)
app.include_router(langgraph_router, tags=["LangGraph Multi-Agent"])

@app.get("/")
async def root():
    return {"message": "Welcome to Adaptiv API"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

# Initialize events to run when the application starts/stops
# Scheduler has been removed as per requirements

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
