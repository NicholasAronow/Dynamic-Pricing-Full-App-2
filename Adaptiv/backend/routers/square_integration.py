"""
Square Integration Module

This module handles OAuth authentication with Square and API interactions.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import os
import secrets
import requests
from urllib.parse import urlencode
import json
import logging
import uuid

import models, schemas
from config.database import get_db
from .auth import get_current_user
from services.square_service import SquareService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Router
square_router = APIRouter()

@square_router.get("/status")
def get_square_status(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Square integration status using service layer"""
    try:
        square_service = SquareService(db)
        return square_service.get_sync_status(current_user.id)
    except Exception as e:
        logger.error(f"Error getting Square status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@square_router.post("/sync-catalog")
def sync_catalog(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync Square catalog using service layer"""
    try:
        square_service = SquareService(db)
        result = square_service.sync_square_catalog(current_user.id)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error syncing catalog: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@square_router.post("/sync-orders")
def sync_orders(
    days: int = 30,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync Square orders using service layer"""
    try:
        square_service = SquareService(db)
        result = square_service.sync_square_orders(current_user.id, days)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error syncing orders: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Constants
SQUARE_ENV = os.getenv("SQUARE_ENV", "production")  # 'sandbox' or 'production'
SQUARE_APP_ID = os.getenv("SQUARE_APP_ID", "")
SQUARE_APP_SECRET = os.getenv("SQUARE_APP_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://www.adaptiv.one").rstrip('/')

# Square hosts based on environment
SQUARE_OAUTH_HOST = "https://connect.squareupsandbox.com" if SQUARE_ENV == "sandbox" else "https://connect.squareup.com"
SQUARE_API_BASE = "https://connect.squareupsandbox.com" if SQUARE_ENV == "sandbox" else "https://connect.squareup.com"

@square_router.get("/auth")
async def square_auth(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start OAuth flow with Square by returning the authorization URL"""
    # Generate state to prevent CSRF
    state = secrets.token_hex(16)
    
    # Create redirect URL with proper URLSearchParams equivalent
    params = {
        "client_id": SQUARE_APP_ID,
        "scope": "ITEMS_READ ITEMS_WRITE ORDERS_READ MERCHANT_PROFILE_READ",
        "session": "true",  # Force login screen
        "state": state,
        "redirect_uri": f"{FRONTEND_URL}/integrations/square/callback"
    }
    
    logger.info(f"Square OAuth: Redirect URI = {FRONTEND_URL}/integrations/square/callback")
    
    # Construct the URL using urlencode
    auth_url = f"{SQUARE_OAUTH_HOST}/oauth2/authorize?{urlencode(params)}"
    logger.info(f"Square OAuth: Auth URL = {auth_url}")
    
    # Return the URL to the frontend
    return {"auth_url": auth_url}

@square_router.post("/process-callback")
async def process_square_callback(
    data: Dict[str, Any],
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process Square OAuth callback data from frontend"""
    code = data.get("code")
    state = data.get("state")
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code"
        )
    
    # Exchange code for access token
    try:
        logger.info(f"Square OAuth: Exchanging code for token - code: {code[:5]}...")
        logger.info(f"Square OAuth: Using client_id: {SQUARE_APP_ID}")
        logger.info(f"Square OAuth: Using redirect_uri: {FRONTEND_URL}/integrations/square/callback")
        
        request_data = {
            "client_id": SQUARE_APP_ID,
            "client_secret": SQUARE_APP_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": f"{FRONTEND_URL}/integrations/square/callback"
        }
        
        logger.info(f"Square OAuth: Request data: {json.dumps({k: v if k != 'client_secret' else '***' for k, v in request_data.items()})}")
        
        token_response = requests.post(
            f"{SQUARE_API_BASE}/oauth2/token",
            headers={"Content-Type": "application/json"},
            json=request_data
        )
        
        logger.info(f"Square OAuth: Token response status: {token_response.status_code}")
        logger.info(f"Square OAuth: Token response headers: {token_response.headers}")
        
        try:
            data = token_response.json()
            logger.info(f"Square OAuth: Token response body: {json.dumps({k: '***' if k in ['access_token', 'refresh_token'] else v for k, v in data.items()})}")
        except json.JSONDecodeError:
            logger.error(f"Square OAuth: Failed to parse JSON response: {token_response.text[:100]}")
            data = {}
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid response from Square API"
            )
        
        logger.info(f"Square OAuth: Token response received")
        
        if "error" in data:
            logger.error(f"Square OAuth error: {data.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth error: {data.get('error')}"
            )
            
        # Extract token data with detailed logging
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_at = None
        if "expires_in" in data:
            # Calculate expiration time
            expires_at = datetime.now() + timedelta(seconds=data.get("expires_in"))
        
        merchant_id = data.get("merchant_id")
        token_type = data.get("token_type")
        
        # Log token information for debugging
        logger.info(f"Square OAuth: Token data received - access_token present: {bool(access_token)}, refresh_token present: {bool(refresh_token)}")
        logger.info(f"Square OAuth: Merchant ID: {merchant_id}, Token type: {token_type}, Expires at: {expires_at}")
        
        # Verify we actually have the token data needed
        if not access_token:
            logger.error("Square OAuth: No access token received from Square")
            
            # Check if user already has an integration (might be a duplicate connection attempt)
            existing_integration = db.query(models.POSIntegration).filter(
                models.POSIntegration.user_id == current_user.id,
                models.POSIntegration.provider == "square"
            ).first()
            
            if existing_integration and existing_integration.access_token:
                logger.info(f"Square OAuth: User already has an active Square integration. Updating pos_connected status.")
                # Since they already have an integration, let's just update the pos_connected status
                current_user.pos_connected = True
                db.commit()
                db.refresh(current_user)
                
                return {"success": True, "message": "Your Square account is already connected", "already_connected": True}
            else:
                # No existing integration and no new token - this is a real error
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received from Square. This may be because the authorization code was already used."
                )
        
        # Check if integration already exists
        existing_integration = db.query(models.POSIntegration).filter(
            models.POSIntegration.user_id == current_user.id,
            models.POSIntegration.provider == "square"
        ).first()
        
        if existing_integration:
            # Update existing integration
            logger.info(f"Square OAuth: Updating existing integration")
            # Update with detailed logging to make sure tokens are set
            existing_integration.access_token = access_token
            existing_integration.refresh_token = refresh_token
            existing_integration.expires_at = expires_at
            existing_integration.merchant_id = merchant_id
            existing_integration.token_type = token_type
            existing_integration.updated_at = datetime.now()
            
            # Force token values to be set explicitly (debug redundancy)
            db.flush()  # Flush changes to check if they got applied
            
            # Verify tokens were saved before committing
            logger.info(f"Square OAuth: Verifying tokens were updated - access_token present: {bool(existing_integration.access_token)}")
            
            # Update user's pos_connected field to True
            current_user.pos_connected = True
            
            # Commit changes
            db.commit()
            
            # Double-check after commit
            db.refresh(existing_integration)
            db.refresh(current_user)
            logger.info(f"Square OAuth: After commit - access_token present: {bool(existing_integration.access_token)}")
            logger.info(f"Square OAuth: User pos_connected set to {current_user.pos_connected}")
            
            # Initial sync of data
            await sync_initial_data(current_user.id, db)
            
            return {"success": True, "message": "Square integration updated successfully"}
        
        # Create new integration with additional validation
        logger.info(f"Square OAuth: Creating new integration")
        new_integration = models.POSIntegration(
            user_id=current_user.id,
            provider="square",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            merchant_id=merchant_id,
            token_type=token_type
        )
        
        # Log field values explicitly
        logger.info(f"Square OAuth: Setting up new integration with token: {access_token[:5]}...")
        
        # Add to database
        db.add(new_integration)
        db.flush()  # Flush changes to DB to get the ID
        
        # Verify values were applied
        logger.info(f"Square OAuth: New integration ID: {new_integration.id}, token present: {bool(new_integration.access_token)}")
        
        # Commit changes
        db.commit()
        
        # Double-check after commit
        db.refresh(new_integration)
        logger.info(f"Square OAuth: After commit - access_token present: {bool(new_integration.access_token)}")
        
        # Update user's pos_connected field to True
        current_user.pos_connected = True
        db.commit()
        db.refresh(current_user)
        logger.info(f"Square OAuth: User pos_connected set to {current_user.pos_connected}")
        
        # Mark related action item as completed if exists
        await _update_pos_action_item(current_user.id, db)
        
        # Initial sync of data
        await sync_initial_data(current_user.id, db)
        
        return {"success": True, "message": "Square integration created successfully"}
        
    except Exception as e:
        logger.exception(f"Square OAuth error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete OAuth: {str(e)}"
        )

async def _update_pos_action_item(user_id: int, db: Session):
    """Mark POS integration action item as completed"""
    pos_action_item = db.query(models.ActionItem).filter(
        models.ActionItem.user_id == user_id,
        models.ActionItem.title == "Connect POS provider",
        models.ActionItem.status != "completed"
    ).first()
    
    if pos_action_item:
        pos_action_item.status = "completed"
        pos_action_item.completed_at = datetime.now()
        db.commit()

@square_router.post("/update-price")
async def update_square_price(
    data: Dict[str, Any],
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the price of an item in Square"""
    try:
        # Extract parameters from request body
        item_id = data.get("item_id")
        new_price = data.get("new_price")
        
        if not item_id or new_price is None:
            return {"error": "Missing item_id or new_price", "success": False}
            
        # Convert price to cents for Square API
        price_amount = int(float(new_price) * 100)
        
        # Get the Square integration
        integration = await _get_integration(current_user.id, db)
        
        # Fetch item details from database to get Square catalog ID (stored in pos_id)
        item = db.query(models.Item).filter(models.Item.id == item_id).first()
        
        if not item:
            return {"error": "Item not found", "success": False}
            
        if not item.pos_id:  
            logger.error(f"Cannot update item {item.id} ({item.name}) in Square because it has no pos_id (Square catalog ID)")
            return {"error": "Cannot update price in Square because this item is not linked to your Square catalog", 
                    "details": "This item needs to be synced with Square first. Try running a full Square sync.",
                    "success": False}
        
        # We need to find both the variation and its parent item
        logger.info(f"Searching for catalog object with variation ID: {item.pos_id}")
        
        # First, search for the item variation to get its parent item ID
        search_response = requests.post(
            f"{SQUARE_API_BASE}/v2/catalog/search",
            headers={
                "Authorization": f"Bearer {integration.access_token}",
                "Content-Type": "application/json"
            },
            json={
                "object_types": ["ITEM"],
                "include_related_objects": True
            }
        )
        
        # Debug logging
        logger.info(f"Square catalog search response status: {search_response.status_code}")
        
        if search_response.status_code != 200:
            logger.error(f"Failed to search catalog: {search_response.text}")
            return {
                "error": "Failed to fetch Square catalog data",
                "details": search_response.json().get('errors', []),
                "success": False
            }
            
        search_data = search_response.json()
        catalog_objects = search_data.get("objects", [])
        
        # Find the parent item for our variation ID
        target_item = None
        target_variation = None
        variation_version = 1
        
        for catalog_item in catalog_objects:
            if catalog_item.get("type") != "ITEM":
                continue
                
            item_data = catalog_item.get("item_data", {})
            variations = item_data.get("variations", [])
            
            # Look through all variations to find our target
            for variation in variations:
                variation_id = variation.get("id")
                if variation_id == item.pos_id:
                    target_item = catalog_item
                    target_variation = variation
                    variation_version = variation.get("version", 1)
                    logger.info(f"Found variation {variation_id} in item {target_item.get('id')}")
                    break
                    
            if target_item:
                break
                
        if not target_item or not target_variation:
            logger.error(f"Variation ID {item.pos_id} not found in any catalog item")
            
            # Clear the invalid ID
            item.pos_id = None
            db.commit()
            db.refresh(item)
            
            return {
                "error": "This item variation no longer exists in Square. The database has been updated.",
                "details": "The item variation may have been deleted from Square or the ID is invalid.",
                "success": False
            }
            
        # Get the current version - this is crucial for Square API
        current_version = variation_version
        logger.info(f"Found variation with version: {current_version}")
        
        # Also save the parent item ID for future reference
        parent_item_id = target_item.get("id")
        parent_item_version = target_item.get("version", 1)
        logger.info(f"Parent item ID: {parent_item_id}, version: {parent_item_version}")
        
        # For debugging, also log the variation details
        variation_data = target_variation.get("item_variation_data", {})
        logger.info(f"Variation details: {json.dumps(variation_data, indent=2)}")
        
        # Store these important IDs and versions for the update
        
        # Create the correct price update payload based on the item structure we found
        # We need to update the variation within its parent item
        
        # Copy the existing variation data to preserve all fields
        updated_variation = target_variation.copy()
        
        # Update just the price in the variation data
        if "item_variation_data" not in updated_variation:
            updated_variation["item_variation_data"] = {}
            
        if "price_money" not in updated_variation["item_variation_data"]:
            updated_variation["item_variation_data"]["price_money"] = {}
            
        # Set the new price
        updated_variation["item_variation_data"]["price_money"] = {
            "amount": price_amount,
            "currency": "USD"
        }
        
        # Use version from our lookup
        updated_variation["version"] = current_version
        
        # Create a complete object update using the parent item structure
        price_data = {
            "idempotency_key": str(uuid.uuid4()),
            "object": {
                "id": parent_item_id,
                "type": "ITEM",
                "version": parent_item_version,
                "item_data": target_item.get("item_data", {})
            }
        }
        
        # Replace the target variation with our updated one in the variations array
        variations = price_data["object"]["item_data"].get("variations", [])
        if not variations:
            # If no variations array existed, create a new one with just our variation
            price_data["object"]["item_data"]["variations"] = [updated_variation]
        else:
            # Replace the specific variation in the array
            for i, variation in enumerate(variations):
                if variation.get("id") == item.pos_id:
                    variations[i] = updated_variation
                    break
            else:
                # If we didn't find the variation, append it
                variations.append(updated_variation)
            price_data["object"]["item_data"]["variations"] = variations
        
        # Debug logging
        logger.info(f"Updating Square item with pos_id: {item.pos_id}")
        logger.info(f"Price data payload: {price_data}")
        logger.info(f"Using Square POST API endpoint with correct version {current_version}")
        
        # Call Square Catalog API to update price
        # Use POST to /v2/catalog/object instead of PUT to /{id}
        update_response = requests.post(
            f"{SQUARE_API_BASE}/v2/catalog/object",
            headers={
                "Authorization": f"Bearer {integration.access_token}",
                "Content-Type": "application/json"
            },
            json=price_data
        )
        
        # Log the response
        logger.info(f"Square API response status: {update_response.status_code}")
        logger.info(f"Square API response body: {update_response.text}")
        
        # Check response
        if update_response.status_code not in [200, 201]:
            error_details = None
            user_message = "Failed to update price in Square"
            
            try:
                error_details = update_response.json().get('errors', [])
                
                # Handle common error cases with better messaging
                if update_response.status_code == 404:
                    user_message = "The item could not be found in your Square catalog"
                    logger.error(f"Square API returned 404 for item with pos_id: {item.pos_id}")
                    
                    # Mark the pos_id as potentially invalid
                    item.pos_id = None
                    db.commit()
                    db.refresh(item)
                elif update_response.status_code == 409:
                    user_message = "Price update conflict - the item may have been modified elsewhere"
                    logger.error(f"Version conflict when updating item {item.pos_id}")
                
                # Extract specific error codes for better handling
                if error_details and isinstance(error_details, list) and len(error_details) > 0:
                    error_code = error_details[0].get('code', '')
                    error_detail = error_details[0].get('detail', '')
                    
                    if error_code == 'NOT_FOUND':
                        user_message = f"Item not found in Square catalog. The connection may be broken."
                    elif error_code == 'UNAUTHORIZED':
                        user_message = "Square authorization failed. Please reconnect your Square account."
                    elif error_code == 'INVALID_REQUEST_ERROR':
                        user_message = f"Invalid request: {error_detail}"
                    elif error_detail:
                        user_message = f"Square error: {error_detail}"
            except:
                error_details = update_response.text
                
            logger.error(f"Square API error: Failed to update price - {error_details}")
            return {
                "error": user_message,
                "square_error": error_details,
                "success": False
            }
            
        # Update price in our database
        item.current_price = str(new_price)  # Store as string for consistency
        item.updated_at = datetime.now()
        db.commit()
        
        # Record price change in price history table if PriceHistory model exists
        try:
            from models import PriceHistory
            price_history = PriceHistory(
                item_id=item_id,
                previous_price=item.current_price,  # Use the original price as previous_price
                new_price=str(new_price),  # Use new_price instead of price
                user_id=current_user.id,
                change_reason="Updated via Square price update"  # Use change_reason instead of change_type/notes
            )
            db.add(price_history)
            db.commit()
        except (ImportError, AttributeError) as e:
            logger.warning(f"Error creating price history record: {str(e)}")
            logger.warning("Make sure your PriceHistory model fields match the constructor arguments")
        
        return {"message": "Price updated successfully", "success": True}
        
    except Exception as e:
        logger.exception(f"Error updating price: {str(e)}")
        return {"error": f"Failed to update price: {str(e)}", "success": False}


async def _handle_missing_catalog_item(item, integration, price_amount, user_id, db):
    """Handle case where catalog item is not found - try to find it by name"""
    logger.info(f"Attempting to find item '{item.name}' in Square catalog by name")
    
    try:
        # Search catalog by name
        search_response = requests.post(
            f"{SQUARE_API_BASE}/v2/catalog/search",
            headers={
                "Authorization": f"Bearer {integration.access_token}",
                "Content-Type": "application/json"
            },
            json={
                "object_types": ["ITEM"],
                "query": {
                    "text_query": {
                        "keywords": [item.name]
                    }
                }
            }
        )
        
        if search_response.status_code == 200:
            search_data = search_response.json()
            objects = search_data.get("objects", [])
            
            # Find exact name match
            for obj in objects:
                if obj.get("type") == "ITEM":
                    item_data = obj.get("item_data", {})
                    if item_data.get("name", "").lower() == item.name.lower():
                        # Found the item! Get the variation ID
                        variations = item_data.get("variations", [])
                        if variations:
                            variation = variations[0]  # Take first variation
                            new_pos_id = variation.get("id")
                            logger.info(f"Found item variation in catalog with ID: {new_pos_id}")
                            
                            # Update our database with the correct variation ID
                            item.pos_id = new_pos_id
                            db.commit()
                            db.refresh(item)
                            
                            return {"message": "Item was found by name. Square ID has been updated. Try the price update again.", "success": True}
        
        # If we get here, item truly doesn't exist
        return {
            "error": "This item could not be found in your Square catalog",
            "details": "The item may not exist in Square. Verify the item exists in your Square dashboard.",
            "success": False
        }
        
    except Exception as e:
        logger.exception(f"Error searching for catalog item: {str(e)}")
        return {"error": "Failed to search for item in Square catalog", "success": False}


@square_router.get("/orders")
async def get_square_orders(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    force_refresh: bool = False,
    debug: bool = False
):
    """Get orders from Square"""
    try:
        # Check if integration exists directly first with detailed logging
        logger.info(f"Checking Square integration for user_id: {current_user.id}")
        integration = db.query(models.POSIntegration).filter(
            models.POSIntegration.user_id == current_user.id,
            models.POSIntegration.provider == "square"
        ).first()
        
        if not integration:
            logger.error(f"No Square integration found for user {current_user.id}")
            # Try to get information about the user's OAuth status
            return {
                "error": "Square integration not found",
                "message": "Please connect your Square account first.",
                "connected": False
            }
            
        logger.info(f"Found Square integration: {integration.id} for user {current_user.id}")
        
        # Check if we have a valid access token
        if not integration.access_token:
            logger.error(f"No access token found for integration {integration.id}")
            return {
                "error": "Invalid integration",
                "message": "Your Square integration is missing authentication tokens. Please reconnect your account.",
                "connected": False
            }
        
        # Get merchant's location ID first
        logger.info("Square API: Fetching locations")
        try:
            locations_response = requests.get(
                f"{SQUARE_API_BASE}/v2/locations",
                headers={
                    "Authorization": f"Bearer {integration.access_token}",
                    "Content-Type": "application/json"
                },
                timeout=10  # Add timeout to prevent hanging requests
            )
            
            # Try to parse the JSON response
            try:
                locations_data = locations_response.json()
            except Exception as e:
                logger.error(f"Square API error: Failed to parse locations response - {str(e)}")
                return {
                    "error": "Failed to parse Square response",
                    "message": "Could not retrieve location data from Square. Please try again later.",
                    "connected": True,
                    "auth_status": "valid",
                    "status_code": locations_response.status_code,
                    "response_text": locations_response.text[:200],  # Truncate long responses
                    "orders": []
                }
            
            if locations_response.status_code != 200 or "locations" not in locations_data:
                logger.error(f"Square API error: Failed to get locations - {locations_data.get('errors', [])}")
                return {
                    "error": "Failed to get Square locations",
                    "message": f"Error fetching locations from Square: {locations_data.get('errors', [])}",
                    "connected": True,
                    "auth_status": "valid" if locations_response.status_code != 401 else "invalid",
                    "orders": []
                }
        except Exception as e:
            logger.exception(f"Square API request error: {str(e)}")
            return {
                "error": "Square API request failed",
                "message": f"Could not connect to Square API: {str(e)}",
                "connected": True,
                "auth_status": "unknown",
                "orders": []
            }
        
        # If we get here, we have locations data. Extract the first location ID to use for orders.
        if len(locations_data.get("locations", [])) == 0:
            return {
                "error": "No locations found",
                "message": "No locations found in your Square account",
                "connected": True,
                "auth_status": "valid",
                "orders": []
            }
        
        location_id = locations_data["locations"][0]["id"]
        logger.info(f"Square API: Using location ID {location_id}")
        
        # Get orders for this location
        logger.info("Square API: Fetching orders")
        try:
            # Check if we should try to fetch all orders regardless of date
            if force_refresh:
                logger.info("Force refresh requested - retrieving all orders without pagination limit")
                max_results = 1000
            else:
                max_results = 200
                
            # Initial request without cursor
            orders_response = requests.post(
                f"{SQUARE_API_BASE}/v2/orders/search",
                headers={
                    "Authorization": f"Bearer {integration.access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "location_ids": [location_id],
                    "query": {
                        "filter": {
                            "state_filter": {"states": ["COMPLETED", "OPEN"]}
                        },
                        "sort": {
                            "sort_field": "CREATED_AT",
                            "sort_order": "DESC"  # Get newest orders first
                        }
                    },
                    "limit": 1000
                },
                timeout=30  # Increase timeout for potentially larger response
            )
            
            # If debug mode, log the actual request being sent
            if debug:
                logger.info(f"Square API request: {json.dumps({k: v for k, v in request_json.items()})}")
            
            # Try to parse the JSON response
            try:
                orders_data = orders_response.json()
            except Exception as e:
                logger.error(f"Square API error: Failed to parse orders response - {str(e)}")
                return {
                    "error": "Failed to parse orders response",
                    "message": "Could not read order data from Square. Please try again later.",
                    "connected": True,
                    "auth_status": "valid",
                    "status_code": orders_response.status_code,
                    "response_text": orders_response.text[:200],  # Truncate long responses
                    "orders": []
                }
            
            if orders_response.status_code != 200:
                logger.error(f"Square API error: Failed to get orders - {orders_data.get('errors', [])}")
                return {
                    "error": "Failed to get Square orders",
                    "message": f"Error fetching orders from Square: {orders_data.get('errors', [])}",
                    "connected": True,
                    "auth_status": "valid" if orders_response.status_code != 401 else "invalid",
                    "orders": []
                }
            
            # Get initial orders from the response
            all_orders = orders_data.get("orders", [])
            initial_count = len(all_orders)
            logger.info(f"Initial fetch returned {initial_count} orders")
            
            # Check for pagination
            cursor = orders_data.get("cursor")
            if cursor:
                logger.info("Additional orders available, fetching via pagination")
                
                # Construct request JSON for pagination
                request_json = {
                    "location_ids": [location_id],
                    "query": {
                        "filter": {
                            "state_filter": {"states": ["COMPLETED", "OPEN"]}
                        }
                    },
                    "cursor": cursor
                }
                
                # Fetch additional pages until no more cursor is returned or we hit our result limit
                page_count = 1
                max_pages = 1000
                total_results = len(all_orders)
                
                while cursor and page_count < max_pages and total_results < max_results:
                    try:
                        logger.info(f"Fetching page {page_count + 1} of orders with cursor")
                        
                        # Update request with cursor - explicitly create a new request to avoid reference issues
                        request_json = {
                            "location_ids": [location_id],
                            "query": {
                                "filter": {
                                    "state_filter": {"states": ["COMPLETED", "OPEN"]}
                                },
                                "sort": {
                                    "sort_field": "CREATED_AT",
                                    "sort_order": "ASC"
                                }
                            },
                            "limit": 1000,
                            "cursor": cursor
                        }
                        
                        # Fetch next page
                        page_response = requests.post(
                            f"{SQUARE_API_BASE}/v2/orders/search",
                            headers={
                                "Authorization": f"Bearer {integration.access_token}",
                                "Content-Type": "application/json"
                            },
                            json=request_json,
                            timeout=15
                        )
                        
                        if page_response.status_code != 200:
                            logger.error(f"Failed to get page {page_count + 1}: {page_response.status_code}")
                            break
                            
                        page_data = page_response.json()
                        page_orders = page_data.get("orders", [])
                        
                        # Add this page's orders to our collection
                        all_orders.extend(page_orders)
                        logger.info(f"Added {len(page_orders)} orders from page {page_count + 1}")
                        total_results += len(page_orders)
                        
                        # Check if we have hit our result limit
                        if total_results >= max_results and not force_refresh:
                            logger.info(f"Reached max results limit of {max_results}. Add force_refresh=true to get more.")
                            break
                        
                        # Get cursor for next page
                        cursor = page_data.get("cursor")
                        
                        # Increment page counter
                        page_count += 1
                        
                        if not cursor:
                            logger.info("No more pages available")
                            break
                            
                    except Exception as e:
                        logger.exception(f"Error fetching paginated orders: {str(e)}")
                        break
            
            # Return all orders
            total_count = len(all_orders)
            logger.info(f"Returning {total_count} total orders after pagination")
            
            return {
                "success": True,
                "connected": True,
                "auth_status": "valid",
                "orders": all_orders,
                "count": total_count,
                "pagination_info": {
                    "initial_page_count": initial_count,
                    "total_pages_fetched": 1 if not cursor else page_count,
                    "has_more": cursor is not None
                },
                "location": {
                    "id": location_id,
                    "name": locations_data["locations"][0].get("name", "Unknown Location")
                }
            }
            
        except Exception as e:
            logger.exception(f"Square API orders request error: {str(e)}")
            return {
                "error": "Square API orders request failed",
                "message": f"Could not fetch orders from Square: {str(e)}",
                "connected": True,
                "auth_status": "unknown",
                "orders": []
            }
            
    except Exception as e:
        logger.exception(f"Error getting Square orders: {str(e)}")
        return {
            "error": "Unexpected error",
            "message": f"An unexpected error occurred: {str(e)}",
            "connected": False,
            "auth_status": "unknown",
            "orders": []
        }

@square_router.post("/sync")
async def sync_square_data(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    force_sync: bool = False  # Add force_sync parameter
):
    """Start Square sync as background task to prevent RAM issues"""
    try:
        from tasks import sync_square_data_task
        
        logger.info(f"Starting Square sync background task for user {current_user.id}, force_sync={force_sync}")
        
        # Start the background task
        task = sync_square_data_task.delay(current_user.id, force_sync)
        
        return {
            "success": True,
            "message": "Square sync started in background",
            "task_id": task.id,
            "status": "PENDING"
        }
        
    except Exception as e:
        logger.exception(f"Error starting Square sync task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start sync task: {str(e)}"
        )


@square_router.get("/sync/status/{task_id}")
async def get_sync_status(
    task_id: str,
    current_user: models.User = Depends(get_current_user)
):
    """Get the status of a Square sync background task"""
    try:
        from tasks import get_square_sync_status
        
        # Get task status
        status_result = get_square_sync_status(task_id, current_user.id)
        return status_result
        
    except Exception as e:
        logger.exception(f"Error getting sync status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync status: {str(e)}"
        )

async def sync_initial_data(user_id: int, db: Session, force_sync: bool = False):
    """Sync catalog and orders from Square"""
    try:
        # Get integration for user
        integration = await _get_integration(user_id, db)
        catalog_mapping = {}  # Maps Square catalog IDs to local item IDs
        
        # Get merchant's locations
        logger.info("Square API: Fetching locations for sync")
        locations_response = requests.get(
            f"{SQUARE_API_BASE}/v2/locations",
            headers={
                "Authorization": f"Bearer {integration.access_token}",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        locations_data = locations_response.json()
        
        if locations_response.status_code != 200 or "locations" not in locations_data:
            return {"success": False, "error": "Failed to get locations"}
        
        if not locations_data.get("locations"):
            return {"success": False, "error": "No locations found"}
        
        # Get all locations for later use
        locations = locations_data.get("locations", [])
        if not locations:
            return {"success": False, "error": "No locations found"}
            
        # Sync catalog items
        items_created = 0
        items_updated = 0
        
        # Get catalog from Square
        logger.info("Square API: Fetching catalog items")
        catalog_response = requests.get(
            f"{SQUARE_API_BASE}/v2/catalog/list?types=ITEM",
            headers={
                "Authorization": f"Bearer {integration.access_token}",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        if catalog_response.status_code != 200:
            return {"success": False, "error": "Failed to get catalog"}
            
        catalog_data = catalog_response.json()
        items = catalog_data.get("objects", [])
        
        logger.info(f"Found {len(items)} items in Square catalog")
        
        # Pre-load all existing items for this user to avoid N+1 queries
        existing_items_by_pos_id = {}
        existing_items_by_name = {}
        for item in db.query(models.Item).filter(models.Item.user_id == user_id).all():
            if item.pos_id:
                existing_items_by_pos_id[item.pos_id] = item
            existing_items_by_name[item.name.lower()] = item
        
        # Batch operations for catalog items
        new_items = []
        items_to_update = []
        price_history_records = []
        
        # Process each catalog item
        for item_obj in items:
            if item_obj.get("type") != "ITEM":
                continue
                
            square_item_id = item_obj.get("id")
            item_data = item_obj.get("item_data", {})
            name = item_data.get("name", "")
            description = item_data.get("description", "")
            
            # Skip items without name
            if not name:
                continue
                
            # Get price from first variation
            variations = item_data.get("variations", [])
            price = None
            square_variation_id = None
            
            if variations:
                variation = variations[0]
                square_variation_id = variation.get("id")
                variation_data = variation.get("item_variation_data", {})
                price_money = variation_data.get("price_money", {})
                if price_money:
                    # Convert cents to dollars
                    price = price_money.get("amount", 0) / 100.0
            
            # Skip items without price
            if price is None:
                continue
                
            # Check if item already exists using pre-loaded data
            existing_item = existing_items_by_pos_id.get(square_item_id) or \
                           existing_items_by_pos_id.get(square_variation_id) or \
                           existing_items_by_name.get(name.lower())
            
            if existing_item:
                # Update existing item
                if existing_item.current_price != price:
                    # Create price history record (will batch insert later)
                    price_history_records.append(models.PriceHistory(
                        item_id=existing_item.id,
                        user_id=user_id,
                        previous_price=existing_item.current_price,
                        new_price=price,
                        change_reason="Updated from Square"
                    ))
                
                # Update item
                existing_item.current_price = price
                existing_item.description = description or existing_item.description
                existing_item.updated_at = datetime.now()
                existing_item.pos_id = square_variation_id if square_variation_id else square_item_id
                items_to_update.append(existing_item)
                items_updated += 1
                
                # Add to mapping
                catalog_mapping[square_item_id] = existing_item.id
                if square_variation_id:
                    catalog_mapping[square_variation_id] = existing_item.id
            else:
                # Create new item
                new_item = models.Item(
                    name=name,
                    description=description,
                    category="From Square",
                    current_price=price,
                    user_id=user_id,
                    pos_id=square_variation_id if square_variation_id else square_item_id
                )
                new_items.append(new_item)
                items_created += 1
        
        # Bulk insert new items
        if new_items:
            db.bulk_save_objects(new_items, return_defaults=True)
            db.flush()
            
            # Add new items to mapping
            for item in new_items:
                if item.pos_id:
                    catalog_mapping[item.pos_id] = item.id
                catalog_mapping[item.name] = item.id
        
        # Bulk insert price history records
        if price_history_records:
            db.bulk_save_objects(price_history_records)
        
        # Commit catalog changes
        db.commit()
        logger.info(f"Catalog sync complete. Created: {items_created}, Updated: {items_updated}")
        
        # Get the most recent order to determine sync start date
        latest_order = db.query(models.Order).filter(
            models.Order.user_id == user_id
        ).order_by(models.Order.order_date.desc()).first()
        
        if latest_order and latest_order.order_date and not force_sync:
            # Incremental sync - only get orders after the latest one
            start_date = latest_order.order_date - timedelta(hours=1)  # 1 hour buffer
            logger.info(f"Incremental sync: Getting orders after {start_date.isoformat()}")
        else:
            # Full sync - no date filter
            start_date = None
            logger.info("Full sync: Getting all historical orders")
        
        # Pre-load existing orders to check for duplicates
        existing_order_ids = set()
        if not force_sync:
            existing_orders = db.query(models.Order.pos_id).filter(
                models.Order.user_id == user_id,
                models.Order.pos_id.isnot(None)
            ).all()
            existing_order_ids = {order.pos_id for order in existing_orders}
            logger.info(f"Found {len(existing_order_ids)} existing orders to skip")
        
        # Batch collections for bulk operations
        all_new_orders = []
        all_new_order_items = []
        orders_created = 0
        orders_skipped = 0
        orders_failed = 0
        
        # Process each location
        for location in locations:
            location_id = location.get("id")
            location_name = location.get("name", "Unknown Location")
            
            logger.info(f"Syncing orders from location: {location_name} ({location_id})")
            
            # Build request with optional date filter
            request_json = {
                "location_ids": [location_id],
                "query": {
                    "filter": {
                        "state_filter": {"states": ["COMPLETED", "OPEN"]}
                    },
                    "sort": {
                        "sort_field": "CREATED_AT",
                        "sort_order": "ASC"
                    }
                },
                "limit": 1000
            }
            
            # Add date filter if doing incremental sync
            if start_date:
                request_json["query"]["filter"]["date_time_filter"] = {
                    "created_at": {
                        "start_at": start_date.isoformat() + 'Z'
                    }
                }
            
            # Process with pagination
            cursor = None
            location_page = 0
            
            while True:
                location_page += 1
                
                if cursor:
                    request_json["cursor"] = cursor
                
                orders_response = requests.post(
                    f"{SQUARE_API_BASE}/v2/orders/search",
                    headers={
                        "Authorization": f"Bearer {integration.access_token}",
                        "Content-Type": "application/json"
                    },
                    json=request_json,
                    timeout=30
                )
                
                if orders_response.status_code != 200:
                    logger.error(f"Failed to get orders from location {location_name}: {orders_response.json().get('errors', [])}")
                    orders_failed += 1
                    break
                
                orders_data = orders_response.json()
                orders = orders_data.get("orders", [])
                
                if not orders:
                    break
                
                logger.info(f"Processing {len(orders)} orders from location {location_name} (page {location_page})")
                
                # Process orders in this batch
                for order in orders:
                    square_order_id = order.get("id")
                    
                    # Skip if already exists
                    if square_order_id in existing_order_ids:
                        orders_skipped += 1
                        continue
                    
                    created_at = order.get("created_at")
                    if not created_at:
                        continue
                    
                    order_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    
                    # Calculate total
                    total_amount = 0
                    order_items_data = []
                    
                    line_items = order.get("line_items", [])
                    for line_item in line_items:
                        name = line_item.get("name", "")
                        quantity = int(line_item.get("quantity", 1))
                        catalog_object_id = line_item.get("catalog_object_id")
                        
                        base_price_money = line_item.get("base_price_money", {})
                        unit_price = base_price_money.get("amount", 0) / 100.0
                        
                        item_total = unit_price * quantity
                        total_amount += item_total
                        
                        # Find item ID from catalog mapping
                        item_id = None
                        if catalog_object_id and catalog_object_id in catalog_mapping:
                            item_id = catalog_mapping[catalog_object_id]
                        elif name:
                            # Try to find by name if not in mapping - but cache the result
                            if name not in catalog_mapping:
                                item = existing_items_by_name.get(name.lower())
                                
                                if item:
                                    catalog_mapping[name] = item.id
                                    item_id = item.id
                                else:
                                    # Create new item
                                    new_item = models.Item(
                                        name=name,
                                        description=f"Imported from Square - {location_name}",
                                        category="From Square",
                                        current_price=unit_price,
                                        user_id=user_id,
                                        pos_id=catalog_object_id
                                    )
                                    db.add(new_item)
                                    db.flush()
                                    catalog_mapping[name] = new_item.id
                                    if catalog_object_id:
                                        catalog_mapping[catalog_object_id] = new_item.id
                                    item_id = new_item.id
                            else:
                                item_id = catalog_mapping[name]
                        
                        if item_id:
                            order_items_data.append({
                                "item_id": item_id,
                                "quantity": quantity,
                                "unit_price": unit_price
                            })
                    
                    # Create order object
                    new_order = models.Order(
                        order_date=order_date,
                        total_amount=total_amount,
                        user_id=user_id,
                        pos_id=square_order_id,
                        location_id=location_id,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    all_new_orders.append(new_order)
                    
                    # Store order items data for later
                    all_new_order_items.append((new_order, order_items_data))
                    orders_created += 1
                    
                    # Add to existing set to avoid duplicates in same sync
                    existing_order_ids.add(square_order_id)
                
                # Get next cursor
                cursor = orders_data.get("cursor")
                if not cursor:
                    break
        
        # Bulk insert all orders at once
        if all_new_orders:
            logger.info(f"Bulk inserting {len(all_new_orders)} new orders...")
            db.bulk_save_objects(all_new_orders, return_defaults=True)
            db.flush()  # Get IDs
            
            # Now create all order items
            order_item_objects = []
            for order, items_data in all_new_order_items:
                for item_data in items_data:
                    order_item = models.OrderItem(
                        order_id=order.id,
                        item_id=item_data["item_id"],
                        quantity=item_data["quantity"],
                        unit_price=item_data["unit_price"]
                    )
                    order_item_objects.append(order_item)
            
            if order_item_objects:
                logger.info(f"Bulk inserting {len(order_item_objects)} order items...")
                db.bulk_save_objects(order_item_objects)
        
        # Commit all changes at once
        db.commit()
        logger.info(f"Orders sync complete: {orders_created} created, {orders_skipped} skipped")
        
        # Update integration with last sync time
        integration.last_sync_at = datetime.now()
        db.commit()
        logger.info(f"Updated last_sync_at to {integration.last_sync_at.isoformat()}")
        
        return {
            "success": True,
            "items_created": items_created,
            "items_updated": items_updated,
            "orders_created": orders_created,
            "orders_skipped": orders_skipped,
            "locations_processed": len(locations),
            "locations_failed": orders_failed
        }
    except Exception as e:
        logger.exception(f"Error syncing Square data: {str(e)}")
        db.rollback()
        return {"success": False, "error": str(e)}
    
async def _get_integration(user_id: int, db: Session) -> models.POSIntegration:
    """Get Square integration for user or raise exception"""
    integration = db.query(models.POSIntegration).filter(
        models.POSIntegration.user_id == user_id,
        models.POSIntegration.provider == "square"
    ).first()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Square integration not found. Please connect your Square account first."
        )
    
    # Check if token is expired and needs refresh
    if integration.expires_at and integration.expires_at < datetime.now() and integration.refresh_token:
        # Refresh token
        try:
            logger.info(f"Square OAuth: Refreshing expired token")
            refresh_response = requests.post(
                f"{SQUARE_API_BASE}/oauth2/token",
                headers={"Content-Type": "application/json"},
                json={
                    "client_id": SQUARE_APP_ID,
                    "client_secret": SQUARE_APP_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": integration.refresh_token
                }
            )
            
            refresh_data = refresh_response.json()
            
            if "error" not in refresh_data:
                # Update token
                integration.access_token = refresh_data.get("access_token")
                integration.refresh_token = refresh_data.get("refresh_token", integration.refresh_token)
                
                if "expires_in" in refresh_data:
                    integration.expires_at = datetime.now() + timedelta(seconds=refresh_data.get("expires_in"))
                    
                integration.updated_at = datetime.now()
                db.commit()
        except Exception as e:
            logger.exception(f"Error refreshing token: {str(e)}")
            # Continue with existing token
    
    return integration
