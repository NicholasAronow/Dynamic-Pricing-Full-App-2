from sqlalchemy.orm import Session
from sqlalchemy import and_
import models
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
import logging
import requests
import os
import json

logger = logging.getLogger(__name__)

class SquareService:
    def __init__(self, db: Session):
        self.db = db
        self.square_env = os.getenv('SQUARE_ENVIRONMENT', 'sandbox')
        self.square_api_base = (
            "https://connect.squareupsandbox.com" 
            if self.square_env == "sandbox" 
            else "https://connect.squareup.com"
        )
    
    def _make_square_request(self, endpoint: str, access_token: str, method: str = 'GET', data: Dict = None) -> Dict[str, Any]:
        """
        Make a request to the Square API.
        """
        url = f"{self.square_api_base}{endpoint}"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Square-Version': '2023-10-18'
        }
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=data)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Square API request failed: {e}")
            raise
    
    def _make_square_request_with_refresh(self, endpoint: str, user_id: int, method: str = 'GET', data: Dict = None) -> Dict[str, Any]:
        """
        Make a request to the Square API with automatic token refresh on 401 errors.
        """
        integration = self.get_user_square_integration(user_id)
        if not integration:
            raise ValueError(f"No Square integration found for user {user_id}")
        
        try:
            # First attempt with current token
            return self._make_square_request(endpoint, integration.access_token, method, data)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.info(f"Access token expired for user {user_id}, attempting refresh")
                
                # Try to refresh the token
                if self.refresh_access_token(user_id):
                    # Get the updated integration with new token
                    integration = self.get_user_square_integration(user_id)
                    if integration:
                        logger.info(f"Retrying request with refreshed token for user {user_id}")
                        return self._make_square_request(endpoint, integration.access_token, method, data)
                
                logger.error(f"Token refresh failed for user {user_id}, cannot complete request")
                raise ValueError(f"Authentication failed for user {user_id} - token refresh unsuccessful")
            else:
                # Re-raise non-401 errors
                raise
    
    def get_user_square_integration(self, user_id: int) -> Optional[models.POSIntegration]:
        """
        Get Square integration for a user.
        """
        return self.db.query(models.POSIntegration).filter(
            and_(
                models.POSIntegration.user_id == user_id,
                models.POSIntegration.provider == 'square'
            )
        ).first()
    
    def create_square_integration(
        self, 
        user_id: int, 
        access_token: str, 
        refresh_token: str = None,
        merchant_id: str = None,
        location_id: str = None
    ) -> models.POSIntegration:
        """
        Create or update Square integration for a user.
        """
        try:
            # Check if integration already exists
            existing_integration = self.get_user_square_integration(user_id)
            
            if existing_integration:
                # Update existing integration
                existing_integration.access_token = access_token
                existing_integration.refresh_token = refresh_token
                existing_integration.merchant_id = merchant_id
                existing_integration.pos_id = location_id  # Store location_id in pos_id field
                existing_integration.updated_at = datetime.now()
                integration = existing_integration
            else:
                # Create new integration
                integration = models.POSIntegration(
                    user_id=user_id,
                    provider='square',
                    access_token=access_token,
                    refresh_token=refresh_token,
                    merchant_id=merchant_id,
                    pos_id=location_id,  # Store location_id in pos_id field
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                self.db.add(integration)
            
            self.db.commit()
            return integration
            
        except Exception as e:
            logger.error(f"Error creating Square integration: {str(e)}")
            self.db.rollback()
            raise
    
    def fetch_and_update_location_id(self, user_id: int) -> bool:
        """
        Fetch location ID from Square API and update the integration.
        For merchants with multiple locations, stores the first location as primary.
        Returns True if successful, False otherwise.
        """
        try:
            integration = self.get_user_square_integration(user_id)
            if not integration:
                logger.error(f"No Square integration found for user {user_id}")
                return False
            
            if integration.pos_id:
                logger.info(f"Location ID already exists for user {user_id}: {integration.pos_id}")
                return True
            
            # Fetch locations from Square API
            response = self._make_square_request_with_refresh(
                '/v2/locations',
                user_id
            )
            
            locations = response.get('locations', [])
            if not locations:
                logger.error(f"No locations found for user {user_id}")
                return False
            
            logger.info(f"Found {len(locations)} location(s) for user {user_id}")
            
            # Extract all location IDs
            location_ids = [loc.get('id') for loc in locations if loc.get('id')]
            if not location_ids:
                logger.error(f"No valid location IDs found for user {user_id}")
                return False
            
            # Use the first location as primary
            primary_location_id = location_ids[0]
            
            # Update the integration with location data
            integration.pos_id = primary_location_id  # Primary location
            integration.location_ids = json.dumps(location_ids)  # All locations as JSON
            integration.updated_at = datetime.now()
            self.db.commit()
            
            logger.info(f"Updated location data for user {user_id}:")
            logger.info(f"  Primary location: {primary_location_id}")
            logger.info(f"  All locations: {location_ids}")
            if len(location_ids) > 1:
                logger.info(f"Multi-location merchant: orders will be synced from all {len(location_ids)} locations")
            
            return True
            
        except Exception as e:
            logger.error(f"Error fetching location ID for user {user_id}: {str(e)}")
            self.db.rollback()
            return False
    
    def get_all_location_ids(self, user_id: int) -> List[str]:
        """
        Get all location IDs for a user. First tries stored location_ids,
        then falls back to fetching from Square API.
        Returns list of location IDs, or empty list if none found.
        """
        try:
            integration = self.get_user_square_integration(user_id)
            if not integration:
                return []
            
            # First try to use stored location IDs
            if integration.location_ids:
                try:
                    stored_location_ids = json.loads(integration.location_ids)
                    if stored_location_ids:
                        logger.info(f"Using stored location IDs for user {user_id}: {stored_location_ids}")
                        return stored_location_ids
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse stored location_ids for user {user_id}: {e}")
            
            # Fallback: fetch from Square API
            logger.info(f"Fetching location IDs from Square API for user {user_id}")
            response = self._make_square_request_with_refresh(
                '/v2/locations',
                user_id
            )
            
            locations = response.get('locations', [])
            location_ids = [loc.get('id') for loc in locations if loc.get('id')]
            
            # Store the fetched location IDs for future use
            if location_ids:
                integration.location_ids = json.dumps(location_ids)
                if not integration.pos_id:
                    integration.pos_id = location_ids[0]  # Set primary if not set
                integration.updated_at = datetime.now()
                self.db.commit()
            
            logger.info(f"Found {len(location_ids)} location IDs for user {user_id}: {location_ids}")
            return location_ids
            
        except Exception as e:
            logger.error(f"Error fetching all location IDs for user {user_id}: {str(e)}")
            return []
    
    def refresh_access_token(self, user_id: int) -> bool:
        """
        Refresh the Square access token using the refresh token.
        Returns True if successful, False otherwise.
        """
        try:
            integration = self.get_user_square_integration(user_id)
            if not integration or not integration.refresh_token:
                logger.error(f"No refresh token available for user {user_id}")
                return False
            
            # Square token refresh endpoint
            refresh_url = 'https://connect.squareup.com/oauth2/token'
            
            payload = {
                'client_id': os.getenv('SQUARE_APPLICATION_ID'),
                'client_secret': os.getenv('SQUARE_APPLICATION_SECRET'),
                'grant_type': 'refresh_token',
                'refresh_token': integration.refresh_token
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            response = requests.post(refresh_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Update the integration with new tokens
                integration.access_token = token_data.get('access_token')
                if token_data.get('refresh_token'):
                    integration.refresh_token = token_data.get('refresh_token')
                
                # Calculate expiration time
                expires_in = token_data.get('expires_in')  # seconds
                if expires_in:
                    integration.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                
                integration.updated_at = datetime.now()
                self.db.commit()
                
                logger.info(f"Successfully refreshed access token for user {user_id}")
                return True
            else:
                logger.error(f"Token refresh failed for user {user_id}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error refreshing token for user {user_id}: {str(e)}")
            self.db.rollback()
            return False
    
    def sync_square_catalog(self, user_id: int) -> Dict[str, Any]:
        """
        Sync Square catalog items to local database.
        """
        try:
            integration = self.get_user_square_integration(user_id)
            if not integration:
                raise ValueError("Square integration not found for user")
            
            # Get catalog items from Square using HTTP request
            response = self._make_square_request_with_refresh(
                '/v2/catalog/list?types=ITEM',
                user_id
            )
            
            items_created = 0
            items_updated = 0
            
            for catalog_object in response.get('objects', []):
                if catalog_object.get('type') == 'ITEM':
                    item_data = catalog_object.get('item_data', {})
                    
                    # Get the first variation (most items have one variation)
                    variations = item_data.get('variations', [])
                    if not variations:
                        continue
                    
                    variation = variations[0].get('item_variation_data', {})
                    price_money = variation.get('price_money', {})
                    
                    # Convert Square price (cents) to dollars
                    price = float(price_money.get('amount', 0)) / 100 if price_money.get('amount') else 0
                    
                    # Check if item already exists
                    existing_item = self.db.query(models.Item).filter(
                        and_(
                            models.Item.user_id == user_id,
                            models.Item.pos_id == catalog_object.get('id')
                        )
                    ).first()
                    
                    if existing_item:
                        # Update existing item
                        existing_item.name = item_data.get('name', existing_item.name)
                        existing_item.current_price = price
                        existing_item.category = item_data.get('category_id', existing_item.category)
                        existing_item.updated_at = datetime.now()
                        items_updated += 1
                    else:
                        # Create new item
                        new_item = models.Item(
                            user_id=user_id,
                            name=item_data.get('name', 'Unknown Item'),
                            current_price=price,
                            category=item_data.get('category_id'),
                            pos_id=catalog_object.get('id'),
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        self.db.add(new_item)
                        items_created += 1
            
            self.db.commit()
            
            return {
                'items_created': items_created,
                'items_updated': items_updated,
                'total_processed': items_created + items_updated
            }
            
        except Exception as e:
            logger.error(f"Error syncing Square catalog: {str(e)}")
            self.db.rollback()
            raise
    
    def sync_square_orders(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Sync Square orders to local database.
        """
        try:
            integration = self.get_user_square_integration(user_id)
            if not integration:
                raise ValueError("Square integration not found for user")
            
            # Get orders from the last N days
            start_date = datetime.now() - timedelta(days=days)
            
            # Search for orders
            request_body = {
                'query': {
                    'filter': {
                        'date_time_filter': {
                            'created_at': {
                                'start_at': start_date.isoformat() + 'Z'
                            }
                        }
                    }
                }
            }
            
            # location_ids is required and goes at the top level
            # Get all location IDs for multi-location support
            location_ids = self.get_all_location_ids(user_id)
            
            if not location_ids:
                # Try to fetch and update location ID if none found
                logger.info(f"No location_ids found for user {user_id}, attempting to fetch from Square API")
                if not self.fetch_and_update_location_id(user_id):
                    logger.error(f"Failed to fetch location_id for user {user_id}")
                    return {'orders_created': 0, 'orders_updated': 0, 'error': 'Failed to fetch location_id'}
                
                # Try again to get location IDs
                location_ids = self.get_all_location_ids(user_id)
                if not location_ids:
                    logger.error(f"Still no location_ids after fetch attempt for user {user_id}")
                    return {'orders_created': 0, 'orders_updated': 0, 'error': 'No location_id available'}
            
            request_body['location_ids'] = location_ids
            logger.info(f"Searching orders for user {user_id} across {len(location_ids)} location(s): {location_ids}")
            
            # Make API request to search orders
            response = self._make_square_request_with_refresh(
                '/v2/orders/search',
                user_id,
                method='POST',
                data=request_body
            )
            
            orders_created = 0
            orders_updated = 0
            
            for order_data in response.get('orders', []):
                order_id = order_data.get('id')
                order_location_id = order_data.get('location_id')  # Get location ID from order data
                
                # Check if order already exists
                existing_order = self.db.query(models.Order).filter(
                    and_(
                        models.Order.user_id == user_id,
                        models.Order.pos_id == order_id
                    )
                ).first()
                
                # Parse order date
                order_date = datetime.fromisoformat(
                    order_data.get('created_at', '').replace('Z', '+00:00')
                )
                
                # Calculate total amount
                total_money = order_data.get('total_money', {})
                total_amount = float(total_money.get('amount', 0)) / 100 if total_money.get('amount') else 0
                
                if existing_order:
                    # Update existing order
                    existing_order.total_amount = total_amount
                    existing_order.order_date = order_date
                    existing_order.location_id = order_location_id  # Update location ID
                    existing_order.updated_at = datetime.now()
                    orders_updated += 1
                    order_obj = existing_order
                else:
                    # Create new order
                    order_obj = models.Order(
                        user_id=user_id,
                        pos_id=order_id,
                        location_id=order_location_id,  # Store location ID
                        order_date=order_date,
                        total_amount=total_amount,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    self.db.add(order_obj)
                    self.db.flush()  # Get the order ID
                    orders_created += 1
                
                # Process line items
                line_items = order_data.get('line_items', [])
                for line_item in line_items:
                    catalog_object_id = line_item.get('catalog_object_id')
                    if not catalog_object_id:
                        continue
                    
                    # Find the corresponding item
                    item = self.db.query(models.Item).filter(
                        and_(
                            models.Item.user_id == user_id,
                            models.Item.pos_id == catalog_object_id
                        )
                    ).first()
                    
                    if item:
                        quantity = int(line_item.get('quantity', 1))
                        unit_price = float(line_item.get('base_price_money', {}).get('amount', 0)) / 100
                        
                        # Check if order item already exists
                        existing_order_item = self.db.query(models.OrderItem).filter(
                            and_(
                                models.OrderItem.order_id == order_obj.id,
                                models.OrderItem.item_id == item.id
                            )
                        ).first()
                        
                        if not existing_order_item:
                            order_item = models.OrderItem(
                                order_id=order_obj.id,
                                item_id=item.id,
                                quantity=quantity,
                                unit_price=unit_price,
                                created_at=datetime.now()
                            )
                            self.db.add(order_item)
            
            self.db.commit()
            
            return {
                'orders_created': orders_created,
                'orders_updated': orders_updated,
                'total_processed': orders_created + orders_updated
            }
            
        except Exception as e:
            logger.error(f"Error syncing Square orders: {str(e)}")
            self.db.rollback()
            raise
    
    def get_sync_status(self, user_id: int) -> Dict[str, Any]:
        """
        Get sync status and statistics for Square integration.
        """
        try:
            integration = self.get_user_square_integration(user_id)
            if not integration:
                return {'status': 'not_connected'}
            
            # Get item count
            item_count = self.db.query(models.Item).filter(
                and_(
                    models.Item.user_id == user_id,
                    models.Item.pos_id.isnot(None)
                )
            ).count()
            
            # Get order count (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            order_count = self.db.query(models.Order).filter(
                and_(
                    models.Order.user_id == user_id,
                    models.Order.pos_id.isnot(None),
                    models.Order.order_date >= thirty_days_ago
                )
            ).count()
            
            # Check if integration is active (has access token and not expired)
            from datetime import datetime, timezone
            is_active = (
                integration.access_token is not None and 
                integration.access_token.strip() != "" and
                (integration.expires_at is None or integration.expires_at > datetime.now(timezone.utc))
            )
            
            return {
                'status': 'connected',
                'integration_id': integration.id,
                'merchant_id': integration.merchant_id,
                'location_id': integration.pos_id,  # Use pos_id as location identifier
                'last_sync': integration.updated_at.isoformat() if integration.updated_at else None,
                'synced_items': item_count,
                'synced_orders_30_days': order_count,
                'is_active': is_active
            }
            
        except Exception as e:
            logger.error(f"Error getting sync status: {str(e)}")
            raise
