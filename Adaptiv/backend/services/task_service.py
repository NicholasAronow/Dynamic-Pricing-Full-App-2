from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
import models
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from services.square_service import SquareService

logger = logging.getLogger(__name__)

class TaskService:
    def __init__(self, db: Session):
        self.db = db
    
    def sync_square_data(self, user_id: int, force_sync: bool = False) -> Dict[str, Any]:
        """
        Comprehensive Square data sync including catalog and orders.
        This contains the business logic extracted from the Celery task.
        """
        try:
            logger.info(f"Starting Square sync for user {user_id}, force_sync={force_sync}")
            
            square_service = SquareService(self.db)
            
            # Check if integration exists
            integration = square_service.get_user_square_integration(user_id)
            if not integration:
                raise ValueError("Square integration not found for user")
            
            results = {
                'user_id': user_id,
                'sync_started': datetime.now().isoformat(),
                'catalog_sync': None,
                'orders_sync': None,
                'total_items_processed': 0,
                'total_orders_processed': 0,
                'errors': []
            }
            
            # Step 1: Sync catalog (20% progress)
            try:
                logger.info(f"Syncing catalog for user {user_id}")
                catalog_result = square_service.sync_square_catalog(user_id)
                results['catalog_sync'] = catalog_result
                results['total_items_processed'] = catalog_result.get('total_processed', 0)
                logger.info(f"Catalog sync completed: {catalog_result}")
            except Exception as e:
                error_msg = f"Catalog sync failed: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
            
            # Step 2: Sync orders (50-90% progress)
            try:
                logger.info(f"Syncing orders for user {user_id}")
                # Sync last 30 days by default, or more if force_sync
                days = 90 if force_sync else 30
                orders_result = square_service.sync_square_orders(user_id, days)
                results['orders_sync'] = orders_result
                results['total_orders_processed'] = orders_result.get('total_processed', 0)
                logger.info(f"Orders sync completed: {orders_result}")
            except Exception as e:
                error_msg = f"Orders sync failed: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
            
            # Final results
            results['sync_completed'] = datetime.now().isoformat()
            results['success'] = len(results['errors']) == 0
            
            logger.info(f"Square sync completed for user {user_id}: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Square sync failed for user {user_id}: {str(e)}")
            raise
    
    def get_sync_progress(self, task_id: str) -> Dict[str, Any]:
        """
        Get sync progress for a task. This would integrate with Celery result backend.
        """
        try:
            from celery.result import AsyncResult
            
            result = AsyncResult(task_id)
            
            if result.state == 'PENDING':
                return {
                    'task_id': task_id,
                    'state': 'PENDING',
                    'progress': 0,
                    'status': 'Task is waiting to be processed'
                }
            elif result.state == 'PROGRESS':
                return {
                    'task_id': task_id,
                    'state': 'PROGRESS',
                    'progress': result.info.get('progress', 0),
                    'status': result.info.get('status', 'Processing...')
                }
            elif result.state == 'SUCCESS':
                return {
                    'task_id': task_id,
                    'state': 'SUCCESS',
                    'progress': 100,
                    'status': 'Sync completed successfully',
                    'result': result.result
                }
            else:
                return {
                    'task_id': task_id,
                    'state': result.state,
                    'progress': 0,
                    'status': f'Task failed: {str(result.info)}'
                }
                
        except Exception as e:
            logger.error(f"Error getting sync progress: {str(e)}")
            return {
                'task_id': task_id,
                'state': 'FAILURE',
                'progress': 0,
                'status': f'Error getting task status: {str(e)}'
            }
    
    def cleanup_old_sync_data(self, user_id: int, days: int = 90) -> Dict[str, Any]:
        """
        Clean up old sync data and competitor information.
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Clean up old competitor data
            old_competitors = self.db.query(models.CompetitorItem).filter(
                models.CompetitorItem.last_updated < cutoff_date
            ).count()
            
            self.db.query(models.CompetitorItem).filter(
                models.CompetitorItem.last_updated < cutoff_date
            ).delete()
            
            # Clean up old price history (keep more recent data)
            price_history_cutoff = datetime.now() - timedelta(days=days * 2)
            old_price_history = self.db.query(models.PriceHistory).filter(
                and_(
                    models.PriceHistory.user_id == user_id,
                    models.PriceHistory.changed_at < price_history_cutoff
                )
            ).count()
            
            self.db.query(models.PriceHistory).filter(
                and_(
                    models.PriceHistory.user_id == user_id,
                    models.PriceHistory.changed_at < price_history_cutoff
                )
            ).delete()
            
            self.db.commit()
            
            return {
                'cleaned_competitors': old_competitors,
                'cleaned_price_history': old_price_history,
                'cutoff_date': cutoff_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {str(e)}")
            self.db.rollback()
            raise
    
    def get_user_sync_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Get sync statistics for a user.
        """
        try:
            # Get Square integration status
            square_service = SquareService(self.db)
            square_status = square_service.get_sync_status(user_id)
            
            # Get recent sync activity (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            # Count items with Square IDs
            square_items = self.db.query(models.Item).filter(
                and_(
                    models.Item.user_id == user_id,
                    models.Item.square_item_id.isnot(None)
                )
            ).count()
            
            # Count orders with Square IDs
            square_orders = self.db.query(models.Order).filter(
                and_(
                    models.Order.user_id == user_id,
                    models.Order.square_order_id.isnot(None),
                    models.Order.order_date >= thirty_days_ago
                )
            ).count()
            
            # Count competitor data
            competitor_items = self.db.query(models.CompetitorItem).filter(
                models.CompetitorItem.last_updated >= thirty_days_ago
            ).count()
            
            # Count recent price changes
            price_changes = self.db.query(models.PriceHistory).filter(
                and_(
                    models.PriceHistory.user_id == user_id,
                    models.PriceHistory.changed_at >= thirty_days_ago
                )
            ).count()
            
            return {
                'user_id': user_id,
                'square_integration': square_status,
                'sync_statistics': {
                    'square_items': square_items,
                    'square_orders_30_days': square_orders,
                    'competitor_items_30_days': competitor_items,
                    'price_changes_30_days': price_changes
                },
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting user sync statistics: {str(e)}")
            raise
    
    def schedule_regular_sync(self, user_id: int, sync_frequency: str = 'daily') -> Dict[str, Any]:
        """
        Schedule regular sync for a user. This would integrate with Celery beat scheduler.
        """
        try:
            # This is a placeholder for scheduling logic
            # In a real implementation, this would interact with Celery beat
            
            schedule_info = {
                'user_id': user_id,
                'sync_frequency': sync_frequency,
                'next_sync': None,
                'scheduled': False
            }
            
            if sync_frequency == 'daily':
                # Schedule daily sync at 2 AM
                schedule_info['next_sync'] = 'Daily at 2:00 AM'
                schedule_info['scheduled'] = True
            elif sync_frequency == 'weekly':
                # Schedule weekly sync on Sundays
                schedule_info['next_sync'] = 'Weekly on Sundays at 2:00 AM'
                schedule_info['scheduled'] = True
            elif sync_frequency == 'manual':
                schedule_info['next_sync'] = 'Manual sync only'
                schedule_info['scheduled'] = False
            
            logger.info(f"Scheduled sync for user {user_id}: {schedule_info}")
            return schedule_info
            
        except Exception as e:
            logger.error(f"Error scheduling sync: {str(e)}")
            raise
    
    def validate_sync_prerequisites(self, user_id: int) -> Dict[str, Any]:
        """
        Validate that all prerequisites for sync are met.
        """
        try:
            validation_results = {
                'user_id': user_id,
                'valid': True,
                'checks': {},
                'errors': []
            }
            
            # Check if user exists
            user = self.db.query(models.User).filter(models.User.id == user_id).first()
            validation_results['checks']['user_exists'] = user is not None
            if not user:
                validation_results['errors'].append("User not found")
                validation_results['valid'] = False
            
            # Check Square integration
            square_service = SquareService(self.db)
            integration = square_service.get_user_square_integration(user_id)
            validation_results['checks']['square_integration'] = integration is not None
            if not integration:
                validation_results['errors'].append("Square integration not found")
                validation_results['valid'] = False
            elif not integration.access_token:
                validation_results['errors'].append("Square access token missing")
                validation_results['valid'] = False
            
            # Check if integration is active (has access token and not expired)
            if integration:
                from datetime import datetime, timezone
                is_active = (
                    integration.access_token is not None and 
                    integration.access_token.strip() != "" and
                    (integration.expires_at is None or integration.expires_at > datetime.now(timezone.utc))
                )
                validation_results['checks']['integration_active'] = is_active
                if not is_active:
                    validation_results['errors'].append("Square integration is inactive or expired")
                    validation_results['valid'] = False
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Error validating sync prerequisites: {str(e)}")
            raise
