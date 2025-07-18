from fastapi import Depends, HTTPException, status
from typing import List, Optional
from functools import wraps

from auth import get_current_user
from models import User

# Define subscription tiers as constants
SUBSCRIPTION_FREE = "free"
SUBSCRIPTION_PREMIUM = "premium"

# Define subscription hierarchy (higher index = higher tier)
SUBSCRIPTION_TIERS = [SUBSCRIPTION_FREE, SUBSCRIPTION_PREMIUM]


def require_subscription(required_tier: str):
    """
    Dependency that requires the user to have at least the specified subscription tier
    
    Usage example:
    @router.get("/premium-feature", dependencies=[Depends(require_subscription(SUBSCRIPTION_PREMIUM))])
    async def premium_feature():
        return {"message": "This is a premium feature"}
    """
    async def subscription_dependency(current_user: User = Depends(get_current_user)):
        # Get user's subscription tier, default to 'free' if not set
        user_tier = current_user.subscription_tier or SUBSCRIPTION_FREE
        
        # Check if user's tier is sufficient
        if not _has_tier_access(user_tier, required_tier):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires {required_tier} subscription or higher"
            )
        return current_user
    
    return subscription_dependency


def _has_tier_access(user_tier: str, required_tier: str) -> bool:
    """Check if the user's subscription tier provides access to the required tier"""
    try:
        # Get the index values for both tiers
        user_tier_index = SUBSCRIPTION_TIERS.index(user_tier.lower())
        required_tier_index = SUBSCRIPTION_TIERS.index(required_tier.lower())
        
        # User has access if their tier is equal or higher (higher index)
        return user_tier_index >= required_tier_index
    except ValueError:
        # If any tier is not found in the list, deny access
        return False


def tier_limited_router(router, path: str, required_tier: str):
    """
    Apply subscription tier requirement to a router for a specific path
    
    Usage example:
    tier_limited_router(router, "/analytics/advanced", SUBSCRIPTION_BASIC)
    """
    # Get all routes from the router
    for route in router.routes:
        # Check if the route path matches the specified path
        if hasattr(route, 'path') and route.path == path:
            # Add the subscription dependency to the route
            if hasattr(route, 'dependencies'):
                route.dependencies.append(Depends(require_subscription(required_tier)))
            else:
                route.dependencies = [Depends(require_subscription(required_tier))]
