from sqlalchemy.orm import Session
from sqlalchemy import and_
import models
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
import logging
import requests
import os
import json
from utils.redis_client import redis_client

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
        self.square_app_id = (os.getenv('SQUARE_APP_ID_SANDBOX') if self.square_env == 'sandbox' else os.getenv('SQUARE_APP_ID'))
        self.square_app_secret = (os.getenv('SQUARE_APP_SECRET_SANDBOX') if self.square_env == 'sandbox' else os.getenv('SQUARE_APP_SECRET'))
        
    
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
            error_details = ""
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = f" - Response: {e.response.text}"
                except:
                    error_details = " - Could not read response text"
            logger.error(f"Square API request failed: {e}{error_details}")
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
    
    # ----------------------
    # Persistent sync metadata helpers
    # ----------------------
    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in update.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                self._deep_merge(base[k], v)
            else:
                base[k] = v
        return base
    
    def _read_sync_meta(self, integration: models.POSIntegration) -> Dict[str, Any]:
        try:
            return dict(integration.sync_metadata or {})
        except Exception:
            return {}
    
    def start_active_sync(self, user_id: int, task_id: str, stage: str = "initializing", progress: int = 0) -> Dict[str, Any]:
        integration = self.get_user_square_integration(user_id)
        if not integration:
            raise ValueError("Square integration not found for user")
        meta = self._read_sync_meta(integration)
        started_at = self._now_iso()
        meta['active_sync'] = {
            'task_id': task_id,
            'started_at': started_at,
            'stage': stage,
            'progress': progress,
            'active': True,
            'items_processed': 0,
            'orders_created': 0,
            'orders_updated': 0,
            'per_location': {}
        }
        integration.sync_metadata = meta
        integration.updated_at = datetime.now()
        self.db.commit()
        
        # Also store in Redis for real-time visibility
        try:
            redis_data = {
                'active': True,
                'stage': stage,
                'progress': progress,
                'orders_created': 0,
                'orders_updated': 0,
                'pages_processed': 0,
                'started_at': started_at,
                'task_id': task_id
            }
            redis_client.set_sync_progress(user_id, redis_data)
        except Exception as e:
            logger.warning(f"Failed to set initial Redis sync progress: {e}")
        
        return meta.get('active_sync', {})
    
    def update_active_sync(self, user_id: int, update_dict: Dict[str, Any]) -> Dict[str, Any]:
        integration = self.get_user_square_integration(user_id)
        if not integration:
            raise ValueError("Square integration not found for user")
        meta = self._read_sync_meta(integration)
        active = meta.get('active_sync', {})
        if not active:
            # initialize a minimal structure if missing
            active = {'active': True, 'started_at': self._now_iso(), 'per_location': {}}
        self._deep_merge(active, update_dict)
        meta['active_sync'] = active
        integration.sync_metadata = meta
        integration.updated_at = datetime.now()
        self.db.commit()
        
        # Also update Redis for real-time cross-process visibility
        try:
            redis_data = {
                'active': True,
                'stage': active.get('stage', 'syncing'),
                'progress': active.get('progress', 0),
                'orders_created': active.get('orders_created', 0),
                'orders_updated': active.get('orders_updated', 0),
                'pages_processed': active.get('pages_processed', 0),
                'started_at': active.get('started_at'),
                'task_id': active.get('task_id')
            }
            redis_client.set_sync_progress(user_id, redis_data)
        except Exception as e:
            logger.warning(f"Failed to update Redis sync progress: {e}")
        
        return active
    
    def update_location_sync_state(self, user_id: int, location_id: str, partial: Dict[str, Any]) -> Dict[str, Any]:
        integration = self.get_user_square_integration(user_id)
        if not integration:
            raise ValueError("Square integration not found for user")
        meta = self._read_sync_meta(integration)
        active = meta.setdefault('active_sync', {'active': True, 'started_at': self._now_iso(), 'per_location': {}})
        per_location = active.setdefault('per_location', {})
        current = per_location.get(location_id, {'location_id': location_id})
        self._deep_merge(current, partial)
        current['location_id'] = location_id
        per_location[location_id] = current
        active['per_location'] = per_location
        meta['active_sync'] = active
        integration.sync_metadata = meta
        integration.updated_at = datetime.now()
        self.db.commit()
        return current
    
    def finalize_active_sync(self, user_id: int, success: bool, summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        integration = self.get_user_square_integration(user_id)
        if not integration:
            raise ValueError("Square integration not found for user")
        meta = self._read_sync_meta(integration)
        active = meta.get('active_sync', {})
        active['active'] = False
        active['ended_at'] = self._now_iso()
        active['status'] = 'completed' if success else 'failed'
        meta['active_sync'] = active
        key = 'last_success' if success else 'last_failure'
        meta[key] = {
            'started_at': active.get('started_at'),
            'ended_at': active.get('ended_at'),
            'summary': summary or {}
        }
        if success:
            integration.last_sync_at = datetime.now(timezone.utc)
        integration.sync_metadata = meta
        integration.updated_at = datetime.now()
        self.db.commit()
        
        # Clear Redis sync progress on completion
        try:
            redis_client.delete_sync_progress(user_id)
        except Exception as e:
            logger.warning(f"Failed to clear Redis sync progress: {e}")
        
        return meta
    
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
                'client_id': self.square_app_id,
                'client_secret': self.square_app_secret,
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
            
            # Get the most recent order date to avoid re-processing
            latest_order = self.db.query(models.Order).filter(
                models.Order.user_id == user_id
            ).order_by(models.Order.order_date.desc()).first()
            
            # Determine start date for sync
            if latest_order and latest_order.order_date:
                # Add a small buffer (1 hour) to account for any timezone issues
                start_date = latest_order.order_date - timedelta(hours=1)
                logger.info(f"Starting incremental sync from {start_date.isoformat()}")
            else:
                # No existing orders, get from the last N days
                start_date = datetime.now() - timedelta(days=days)
                logger.info(f"Starting full sync from {start_date.isoformat()}")
            # Identify whether this is an initial (full) sync
            initial_sync = not (latest_order and latest_order.order_date)
            
            # Build search query with date filter
            # Format the date properly for Square API (ISO 8601 with timezone)
            start_date_str = start_date.strftime('%Y-%m-%dT%H:%M:%S+00:00')
            
            request_body = {
                'query': {
                    'filter': {
                        'date_time_filter': {
                            'closed_at': {
                                'start_at': start_date_str
                            }
                        },
                        'state_filter': {
                            'states': ['COMPLETED']
                        }
                    },
                    'sort': {
                        'sort_field': 'CLOSED_AT',
                        'sort_order': 'ASC'
                    }
                },
                # Be explicit about entries vs orders array
                'return_entries': False
            }
            # Explicitly control page size during initial sync to avoid huge pages
            request_body['limit'] = 10
            
            # Get all location IDs for multi-location support
            location_ids = self.get_all_location_ids(user_id)
            
            if not location_ids:
                logger.info(f"No location_ids found for user {user_id}, attempting to fetch from Square API")
                if not self.fetch_and_update_location_id(user_id):
                    logger.error(f"Failed to fetch location_id for user {user_id}")
                    return {'orders_created': 0, 'orders_updated': 0, 'error': 'Failed to fetch location_id'}
                
                location_ids = self.get_all_location_ids(user_id)
                if not location_ids:
                    logger.error(f"Still no location_ids after fetch attempt for user {user_id}")
                    return {'orders_created': 0, 'orders_updated': 0, 'error': 'No location_id available'}
            
            request_body['location_ids'] = location_ids
            logger.info(f"Searching orders for user {user_id} across {len(location_ids)} location(s): {location_ids}")
            
            # Pre-fetch all existing orders to avoid N+1 queries
            existing_order_ids = set()
            existing_orders_query = self.db.query(models.Order.pos_id).filter(
                models.Order.user_id == user_id,
                models.Order.pos_id.isnot(None)
            )
            for order in existing_orders_query:
                existing_order_ids.add(order.pos_id)
            
            # Pre-fetch all items for this user to create a mapping
            items_map = {}
            user_items = self.db.query(models.Item).filter(
                models.Item.user_id == user_id
            ).all()
            for item in user_items:
                if item.pos_id:
                    items_map[item.pos_id] = item
            
            orders_created = 0
            orders_updated = 0
            cursor = None
            page_count = 0
            oldest_processed_at: Optional[datetime] = None
            
            # Batch operations
            new_orders = []
            new_order_items = []
            
            # Handle pagination
            while True:
                page_count += 1
                
                current_request = request_body.copy()
                if cursor:
                    current_request['cursor'] = cursor
                # Ensure limit is applied on every page request during initial sync
                if initial_sync:
                    current_request['limit'] = 10
                
                logger.info(f"Fetching orders page {page_count} for user {user_id}")
                # Elevate to INFO so we can verify 'limit' is present in production logs
                logger.info(f"SearchOrders request body: {json.dumps(current_request, indent=2)}")
                
                response = self._make_square_request_with_refresh(
                    '/v2/orders/search',
                    user_id,
                    method='POST',
                    data=current_request
                )
                
                orders_in_page = response.get('orders', [])
                logger.info(f"Processing {len(orders_in_page)} orders from page {page_count}")
                
                if not orders_in_page:
                    logger.info(f"No orders found on page {page_count}, stopping pagination")
                    break
                
                # Track per-location stats for this page
                per_location_page: Dict[str, Dict[str, Any]] = {}
                
                # Process orders in batch
                for order_data in orders_in_page:
                    order_id = order_data.get('id')
                    
                    # Skip if order already exists
                    if order_id in existing_order_ids:
                        orders_updated += 1
                        # update per-location page counters
                        loc = order_data.get('location_id')
                        if loc:
                            stats = per_location_page.setdefault(loc, {'orders_created': 0, 'orders_updated': 0, 'last_synced_at': None})
                            stats['orders_updated'] += 1
                            # Prefer closed_at when available, fallback to created_at
                            ts_str = order_data.get('closed_at') or order_data.get('created_at')
                            if ts_str:
                                try:
                                    dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                                    stats['last_synced_at'] = max(stats['last_synced_at'], dt) if stats['last_synced_at'] else dt
                                    # Track overall oldest processed timestamp for progress proxy
                                    oldest_processed_at = min(oldest_processed_at, dt) if oldest_processed_at else dt
                                except Exception:
                                    pass
                        continue
                    
                    order_location_id = order_data.get('location_id')
                    order_date = datetime.fromisoformat(
                        order_data.get('created_at', '').replace('Z', '+00:00')
                    )
                    # Track overall oldest processed timestamp using closed_at if possible
                    ts_str2 = order_data.get('closed_at') or order_data.get('created_at')
                    if ts_str2:
                        try:
                            ts2 = datetime.fromisoformat(ts_str2.replace('Z', '+00:00'))
                            oldest_processed_at = min(oldest_processed_at, ts2) if oldest_processed_at else ts2
                        except Exception:
                            pass
                    
                    total_money = order_data.get('total_money', {})
                    total_amount = float(total_money.get('amount', 0)) / 100 if total_money.get('amount') else 0
                    
                    # Create new order object (don't add to DB yet)
                    new_order = models.Order(
                        user_id=user_id,
                        pos_id=order_id,
                        location_id=order_location_id,
                        order_date=order_date,
                        total_amount=total_amount,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    new_orders.append(new_order)
                    
                    # Process line items
                    line_items = order_data.get('line_items', [])
                    for line_item in line_items:
                        catalog_object_id = line_item.get('catalog_object_id')
                        if not catalog_object_id or catalog_object_id not in items_map:
                            continue
                        
                        item = items_map[catalog_object_id]
                        quantity = int(line_item.get('quantity', 1))
                        unit_price = float(line_item.get('base_price_money', {}).get('amount', 0)) / 100
                        
                        # Store order item data for batch insert
                        new_order_items.append({
                            'order': new_order,
                            'item_id': item.id,
                            'quantity': quantity,
                            'unit_price': unit_price
                        })
                    
                    orders_created += 1
                    # update per-location page counters
                    if order_location_id:
                        stats = per_location_page.setdefault(order_location_id, {'orders_created': 0, 'orders_updated': 0, 'last_synced_at': None})
                        stats['orders_created'] += 1
                        stats['last_synced_at'] = max(stats['last_synced_at'], order_date) if stats['last_synced_at'] else order_date
                
                # Persist progress after each page
                try:
                    # Compute progress using date-based proxy: how far we've advanced from start_date toward now
                    # Ensure timezone-aware calculations
                    start_dt = start_date
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                    else:
                        start_dt = start_dt.astimezone(timezone.utc)

                    now_utc = datetime.now(timezone.utc)
                    denom = max((now_utc - start_dt).total_seconds(), 1.0)
                    if oldest_processed_at is not None:
                        processed_utc = oldest_processed_at.astimezone(timezone.utc)
                        # How much of the window (start..now) have we covered from the now-side backwards?
                        num = max((now_utc - processed_utc).total_seconds(), 0.0)
                        ratio = max(0.0, min(1.0, num / denom))
                    else:
                        ratio = 0.0

                    # Map ratio into a bounded range so finalization can complete to 100%
                    if initial_sync:
                        base = 40.0  # after catalog/validation stages
                        cap = 90.0   # leave headroom for finalization
                    else:
                        base = 60.0
                        cap = 95.0
                    progress = int(min(cap, max(base, base + ratio * (cap - base))))

                    self.update_active_sync(user_id, {
                        'stage': 'syncing_orders',
                        'progress': progress,
                        'orders_created': orders_created,
                        'orders_updated': orders_updated,
                        'pages_processed': page_count
                    })
                    # Update per-location states
                    for loc_id, s in per_location_page.items():
                        partial = {
                            'orders_created': s.get('orders_created', 0),
                            'orders_updated': s.get('orders_updated', 0)
                        }
                        if s.get('last_synced_at'):
                            partial['last_synced_at'] = s['last_synced_at'].astimezone(timezone.utc).isoformat()
                        self.update_location_sync_state(user_id, loc_id, partial)
                except Exception as meta_err:
                    logger.warning(f"Failed to persist sync metadata for user {user_id}: {meta_err}")
                
                # Check for next page (after persisting progress for this page)
                cursor = response.get('cursor')
                if not cursor:
                    logger.info(f"No more pages available, pagination complete for user {user_id}")
                    break
            
            # Bulk insert all new orders
            if new_orders:
                self.db.bulk_save_objects(new_orders)
                self.db.flush()  # Get IDs for the orders
                
                # Now create OrderItem objects with proper order IDs
                order_item_objects = []
                for item_data in new_order_items:
                    order_item = models.OrderItem(
                        order_id=item_data['order'].id,
                        item_id=item_data['item_id'],
                        quantity=item_data['quantity'],
                        unit_price=item_data['unit_price']
                    )
                    order_item_objects.append(order_item)
                
                # Bulk insert order items
                if order_item_objects:
                    self.db.bulk_save_objects(order_item_objects)
            
            self.db.commit()
            logger.info(f"Orders sync completed for user {user_id}: {orders_created} created, {orders_updated} updated across {page_count} pages")
            
            return {
                'orders_created': orders_created,
                'orders_updated': orders_updated,
                'total_processed': orders_created + orders_updated,
                'pages_processed': page_count
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
            is_active = (
                integration.access_token is not None and 
                integration.access_token.strip() != "" and
                (integration.expires_at is None or integration.expires_at > datetime.now(timezone.utc))
            )
            
            # Include current persistent sync metadata (if any)
            meta = integration.sync_metadata or {}
            result = {
                'status': 'connected',
                'integration_id': integration.id,
                'merchant_id': integration.merchant_id,
                'location_id': integration.pos_id,  # Use pos_id as location identifier
                'last_sync': integration.updated_at.isoformat() if integration.updated_at else None,
                'synced_items': item_count,
                'synced_orders_30_days': order_count,
                'is_active': is_active
            }
            if meta:
                result['sync_metadata'] = meta
            return result
            
        except Exception as e:
            logger.error(f"Error getting sync status: {str(e)}")
            raise
