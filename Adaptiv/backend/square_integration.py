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
from database import get_db
from auth import get_current_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Router
square_router = APIRouter()

# Constants
SQUARE_ENV = os.getenv("SQUARE_ENV", "production")  # 'sandbox' or 'production'
SQUARE_APP_ID = os.getenv("SQUARE_APP_ID", "")
SQUARE_APP_SECRET = os.getenv("SQUARE_APP_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://adaptiv-eight.vercel.app").rstrip('/')

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
    force_refresh: bool = False
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
                            "state_filter": {"states": ["COMPLETED"]}
                        },
                        "sort": {
                            "sort_field": "CREATED_AT",
                            "sort_order": "DESC"  # Get newest orders first
                        }
                    },
                    "limit": 100
                },
                timeout=30  # Increase timeout for potentially larger response
            )
            
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
                            "state_filter": {"states": ["COMPLETED"]}
                        }
                    },
                    "cursor": cursor
                }
                
                # Fetch additional pages until no more cursor is returned or we hit our result limit
                page_count = 1
                max_pages = 10
                total_results = len(all_orders)
                
                while cursor and page_count < max_pages and total_results < max_results:
                    try:
                        logger.info(f"Fetching page {page_count + 1} of orders with cursor")
                        
                        # Update request with cursor - explicitly create a new request to avoid reference issues
                        request_json = {
                            "location_ids": [location_id],
                            "query": {
                                "filter": {
                                    "state_filter": {"states": ["COMPLETED"]}
                                },
                                "sort": {
                                    "sort_field": "CREATED_AT",
                                    "sort_order": "ASC"
                                }
                            },
                            "limit": 100,
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
    db: Session = Depends(get_db)
):
    """Sync menu items and orders from Square to local database"""
    try:
        return await sync_initial_data(current_user.id, db)
    except Exception as e:
        logger.exception(f"Error syncing Square data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync data: {str(e)}"
        )

async def sync_initial_data(user_id: int, db: Session):
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
            timeout=10  # Add timeout to prevent hanging requests
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
                
            # Check if item already exists by Square ID first
            existing_item = db.query(models.Item).filter(
                models.Item.pos_id == square_item_id,
                models.Item.user_id == user_id
            ).first()
            
            # If not found by ID, try by name
            if not existing_item:
                existing_item = db.query(models.Item).filter(
                    models.Item.name == name,
                    models.Item.user_id == user_id
                ).first()
            
            if existing_item:
                # Update existing item
                if existing_item.current_price != price:
                    # Create price history
                    price_history = models.PriceHistory(
                        item_id=existing_item.id,
                        user_id=user_id,
                        previous_price=existing_item.current_price,
                        new_price=price,
                        change_reason="Updated from Square"
                    )
                    db.add(price_history)
                
                # Update item
                existing_item.current_price = price
                existing_item.description = description or existing_item.description
                existing_item.updated_at = datetime.now()
                # IMPORTANT: Store the variation ID in pos_id, not the main item ID
                # This is because price updates are done at the variation level
                existing_item.pos_id = square_variation_id if square_variation_id else square_item_id
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
                    category="From Square",  # Default category
                    current_price=price,
                    user_id=user_id,
                    pos_id=square_variation_id if square_variation_id else square_item_id  # Store variation ID for price updates
                )
                db.add(new_item)
                db.flush()  # Get ID of new item
                items_created += 1
                
                # Add to mapping
                catalog_mapping[square_item_id] = new_item.id
                if square_variation_id:
                    catalog_mapping[square_variation_id] = new_item.id
        
        # Commit catalog changes
        db.commit()
        logger.info(f"Catalog sync complete. Created: {items_created}, Updated: {items_updated}")
        
        # Sync orders from all locations
        orders_created = 0
        orders_failed = 0
        last_sync_time = None
        
        # We're no longer applying a date filter to ensure we get all historical orders
        logger.info("Retrieving all historical orders without date filtering")
        
        # Process each location
        for location in locations:
            location_id = location.get("id")
            location_name = location.get("name", "Unknown Location")
            
            logger.info(f"Syncing orders from location: {location_name} ({location_id})")
            
            # Log that we're fetching all orders
            logger.info(f"Fetching all completed orders for location {location_name}")
            
            # Build request JSON with only state filter (no date filter)
            request_json = {
                "location_ids": [location_id],
                "query": {
                    "filter": {
                        "state_filter": {"states": ["COMPLETED"]}
                    },
                    "sort": {
                        "sort_field": "CREATED_AT",
                        "sort_order": "ASC"
                    }
                },
                "limit": 100  # Square limits to 100 orders per request
            }
            
            # Get orders from Square with date filter
            orders_response = requests.post(
                f"{SQUARE_API_BASE}/v2/orders/search",
                headers={
                    "Authorization": f"Bearer {integration.access_token}",
                    "Content-Type": "application/json"
                },
                json=request_json,
                timeout=15  # Longer timeout for orders
            )
            
            if orders_response.status_code != 200:
                logger.error(f"Failed to get orders from location {location_name}: {orders_response.json().get('errors', [])}")
                orders_failed += 1
                continue
            
            orders_data = orders_response.json()
            orders = orders_data.get("orders", [])
            
            logger.info(f"Found {len(orders)} orders in location {location_name}")
            
            # Process each order
            for order in orders:
                # Get order date and ID
                created_at = order.get("created_at")
                if not created_at:
                    continue
                
                order_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                square_order_id = order.get("id")
                
                # Check if order already exists
                existing_order = db.query(models.Order).filter(
                    models.Order.user_id == user_id,
                    models.Order.pos_id == square_order_id
                ).first()
                
                if existing_order:
                    logger.debug(f"Order {square_order_id} already exists, skipping")
                    continue
                
                # Calculate total from line items
                total_amount = 0
                order_items = []
                
                line_items = order.get("line_items", [])
                for line_item in line_items:
                    # Get item details
                    name = line_item.get("name", "")
                    quantity = int(line_item.get("quantity", 1))
                    
                    # Get catalog ID from variation ID if available
                    catalog_object_id = line_item.get("catalog_object_id")
                    
                    # Extract price
                    base_price_money = line_item.get("base_price_money", {})
                    unit_price = base_price_money.get("amount", 0) / 100.0  # Convert cents to dollars
                    
                    # Calculate line item total
                    item_total = unit_price * quantity
                    total_amount += item_total
                    
                    # Find matching item in database through the catalog mapping
                    item_id = None
                    if catalog_object_id and catalog_object_id in catalog_mapping:
                        item_id = catalog_mapping[catalog_object_id]
                    
                    if not item_id:
                        # Try to find by name if not in mapping
                        item = db.query(models.Item).filter(
                            models.Item.name == name,
                            models.Item.user_id == user_id
                        ).first()
                        
                        if item:
                            item_id = item.id
                        else:
                            # Create new item if not exists
                            new_item = models.Item(
                                name=name,
                                description=f"Imported from Square - {location_name}",
                                category="From Square",  # Default category
                                current_price=unit_price,
                                user_id=user_id,
                                pos_id=catalog_object_id  # Store Square ID if available
                            )
                            db.add(new_item)
                            db.flush()  # Get ID
                            
                            item_id = new_item.id
                            if catalog_object_id:
                                catalog_mapping[catalog_object_id] = item_id
                    
                    # Add to order items list
                    order_items.append({
                        "item_id": item_id,
                        "quantity": quantity,
                        "unit_price": unit_price
                    })
                
                # Create order
                new_order = models.Order(
                    order_date=order_date,
                    total_amount=total_amount,
                    user_id=user_id,
                    pos_id=square_order_id,  # Store Square order ID
                    created_at=order_date,    # Use Square creation date
                    updated_at=order_date
                )
                db.add(new_order)
                db.flush()  # Get ID of new order
                
                # Add order items
                for item_data in order_items:
                    order_item = models.OrderItem(
                        order_id=new_order.id,
                        item_id=item_data["item_id"],
                        quantity=item_data["quantity"],
                        unit_price=item_data["unit_price"]
                    )
                    db.add(order_item)
                
                orders_created += 1
            
            # Handle pagination to fetch all orders
            cursor = orders_data.get("cursor")
            page_count = 1
            max_pages = 100  # Increased max pages to ensure we get all orders
            
            logger.info(f"Initial page has {len(orders)} orders, cursor present: {cursor is not None}")
            
            while cursor and page_count < max_pages:
                logger.info(f"Fetching additional orders with cursor for location {location_name}")
                
                # Update request JSON with cursor for next page
                request_json["cursor"] = cursor
                
                # Fetch next page of orders
                next_page_response = requests.post(
                    f"{SQUARE_API_BASE}/v2/orders/search",
                    headers={
                        "Authorization": f"Bearer {integration.access_token}",
                        "Content-Type": "application/json"
                    },
                    json=request_json,
                    timeout=30  # Increased timeout for orders
                )
                
                logger.info(f"Pagination request for page {page_count+1} status: {next_page_response.status_code}")
                
                if next_page_response.status_code != 200:
                    logger.error(f"Failed to get paginated orders from location {location_name}: {next_page_response.json().get('errors', [])}")
                    break
                
                try:
                    next_page_data = next_page_response.json()
                    next_page_orders = next_page_data.get("orders", [])
                    
                    logger.info(f"Found {len(next_page_orders)} additional orders in location {location_name} (page {page_count+1})")
                    
                    # Debug cursor information
                    new_cursor = next_page_data.get("cursor")
                    logger.info(f"New cursor received: {new_cursor is not None}")
                    
                    if cursor == new_cursor:
                        logger.error(f"Cursor did not change! Breaking pagination loop to avoid infinite loop")
                        break
                        
                    cursor = new_cursor
                except Exception as e:
                    logger.exception(f"Error parsing pagination response: {str(e)}")
                    break
                
                # Process each order in the next page
                for order in next_page_orders:
                    # Get order date and ID
                    created_at = order.get("created_at")
                    if not created_at:
                        continue
                    
                    order_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    square_order_id = order.get("id")
                    
                    # Check if order already exists
                    existing_order = db.query(models.Order).filter(
                        models.Order.user_id == user_id,
                        models.Order.pos_id == square_order_id
                    ).first()
                    
                    if existing_order:
                        logger.debug(f"Order {square_order_id} already exists, skipping")
                        continue
                    
                    # Calculate total from line items
                    total_amount = 0
                    order_items = []
                    
                    line_items = order.get("line_items", [])
                    for line_item in line_items:
                        # Get item details
                        name = line_item.get("name", "")
                        quantity = int(line_item.get("quantity", 1))
                        
                        # Get catalog ID from variation ID if available
                        catalog_object_id = line_item.get("catalog_object_id")
                        
                        # Extract price
                        base_price_money = line_item.get("base_price_money", {})
                        unit_price = base_price_money.get("amount", 0) / 100.0  # Convert cents to dollars
                        
                        # Calculate line item total
                        item_total = unit_price * quantity
                        total_amount += item_total
                        
                        # Find matching item in database through the catalog mapping
                        item_id = None
                        if catalog_object_id and catalog_object_id in catalog_mapping:
                            item_id = catalog_mapping[catalog_object_id]
                        
                        if not item_id:
                            # Try to find by name if not in mapping
                            item = db.query(models.Item).filter(
                                models.Item.name == name,
                                models.Item.user_id == user_id
                            ).first()
                            
                            if item:
                                item_id = item.id
                            else:
                                # Create new item if not exists
                                new_item = models.Item(
                                    name=name,
                                    description=f"Imported from Square - {location_name}",
                                    category="From Square",  # Default category
                                    current_price=unit_price,
                                    user_id=user_id,
                                    pos_id=catalog_object_id  # Store Square ID if available
                                )
                                db.add(new_item)
                                db.flush()  # Get ID
                                
                                item_id = new_item.id
                                if catalog_object_id:
                                    catalog_mapping[catalog_object_id] = item_id
                        
                        # Add to order items list
                        order_items.append({
                            "item_id": item_id,
                            "quantity": quantity,
                            "unit_price": unit_price
                        })
                    
                    # Create order
                    new_order = models.Order(
                        order_date=order_date,
                        total_amount=total_amount,
                        user_id=user_id,
                        pos_id=square_order_id,  # Store Square order ID
                        created_at=order_date,    # Use Square creation date
                        updated_at=order_date
                    )
                    db.add(new_order)
                    db.flush()  # Get ID of new order
                    
                    # Add order items
                    for item_data in order_items:
                        order_item = models.OrderItem(
                            order_id=new_order.id,
                            item_id=item_data["item_id"],
                            quantity=item_data["quantity"],
                            unit_price=item_data["unit_price"]
                        )
                        db.add(order_item)
                    
                    orders_created += 1
                
                # Increment page counter
                page_count += 1
                
                if not cursor:
                    logger.info("No more cursor returned. Pagination complete.")
                    break
        
        # Commit all changes
        db.commit()
        
        # Debug info about orders synced
        logger.info(f"Total sync complete: {orders_created} orders created across {len(locations)} locations")
        
        # Update integration with last sync time
        integration.last_sync_at = datetime.now()
        db.commit()
        logger.info(f"Updated last_sync_at to {integration.last_sync_at.isoformat()}")
        
        return {
            "success": True,
            "items_created": items_created,
            "items_updated": items_updated,
            "orders_created": orders_created,
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
