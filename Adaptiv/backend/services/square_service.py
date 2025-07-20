from sqlalchemy.orm import Session
from sqlalchemy import and_
import models
from datetime import datetime, timedelta
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
                existing_integration.location_id = location_id
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
                    location_id=location_id,
                    is_active=True,
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
    
    def sync_square_catalog(self, user_id: int) -> Dict[str, Any]:
        """
        Sync Square catalog items to local database.
        """
        try:
            integration = self.get_user_square_integration(user_id)
            if not integration:
                raise ValueError("Square integration not found for user")
            
            # Get catalog items from Square using HTTP request
            response = self._make_square_request(
                '/v2/catalog/list?types=ITEM',
                integration.access_token
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
                            models.Item.square_item_id == catalog_object.get('id')
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
                            square_item_id=catalog_object.get('id'),
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
            search_query = {
                'filter': {
                    'date_time_filter': {
                        'created_at': {
                            'start_at': start_date.isoformat() + 'Z'
                        }
                    }
                }
            }
            
            if integration.location_id:
                search_query['location_ids'] = [integration.location_id]
            
            # Make API request to search orders
            response = self._make_square_request(
                '/v2/orders/search',
                integration.access_token,
                method='POST',
                data={'query': search_query}
            )
            
            orders_created = 0
            orders_updated = 0
            
            for order_data in response.get('orders', []):
                order_id = order_data.get('id')
                
                # Check if order already exists
                existing_order = self.db.query(models.Order).filter(
                    and_(
                        models.Order.user_id == user_id,
                        models.Order.square_order_id == order_id
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
                    existing_order.updated_at = datetime.now()
                    orders_updated += 1
                    order_obj = existing_order
                else:
                    # Create new order
                    order_obj = models.Order(
                        user_id=user_id,
                        square_order_id=order_id,
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
                            models.Item.square_item_id == catalog_object_id
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
                    models.Item.square_item_id.isnot(None)
                )
            ).count()
            
            # Get order count (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            order_count = self.db.query(models.Order).filter(
                and_(
                    models.Order.user_id == user_id,
                    models.Order.square_order_id.isnot(None),
                    models.Order.order_date >= thirty_days_ago
                )
            ).count()
            
            return {
                'status': 'connected',
                'integration_id': integration.id,
                'merchant_id': integration.merchant_id,
                'location_id': integration.location_id,
                'last_sync': integration.updated_at.isoformat() if integration.updated_at else None,
                'synced_items': item_count,
                'synced_orders_30_days': order_count,
                'is_active': integration.is_active
            }
            
        except Exception as e:
            logger.error(f"Error getting sync status: {str(e)}")
            raise
