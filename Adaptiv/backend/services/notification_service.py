"""
Notification service for sending various types of notifications
"""
import os
from typing import List, Dict, Any, Union
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """
    A service for sending notifications via various channels (Knock, email, etc.)
    """
    def __init__(self):
        self.knock_api_key = os.environ.get("KNOCK_API_KEY")
        if not self.knock_api_key:
            logger.warning("KNOCK_API_KEY environment variable not set. Email notifications will not be sent.")
    
    def is_configured(self) -> bool:
        """Check if notification service is properly configured"""
        return self.knock_api_key is not None
    
    async def send_pricing_report_notification(self, 
                                        recipients: List[str], 
                                        report_data: Dict[str, Any],
                                        user_id: int = None) -> bool:
        """
        Send a notification when a new pricing report is ready
        
        Args:
            recipients: List of recipient email addresses
            report_data: Data about the pricing report to include in notification
            user_id: Optional user ID associated with this notification
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("KNOCK_API_KEY environment variable not set. Email notifications will not be sent.")
            return False
        
        try:
            # Import httpx inside the method to avoid errors if package is not installed
            import httpx
            
            # Format the data for Knock's API
            workflow_key = "pricing-report-ready"
            
            # Extract pricing recommendations directly from results
            pricing_recommendations = report_data.get("results", {}).get("pricing_recommendations", [])
            
            # Calculate summary stats
            total_recommendations = len(pricing_recommendations)
            high_confidence_count = sum(1 for rec in pricing_recommendations if rec.get("confidence_score", 0) >= 0.8)
            
            # Calculate potential revenue impact
            potential_revenue_increase = sum(
                rec.get("projected_revenue_impact", {}).get("monthly", 0) 
                for rec in pricing_recommendations
                if rec.get("projected_revenue_impact", {}).get("monthly", 0) > 0
            )
            
            # Format the notification data
            notification_data = {
                "total_recommendations": total_recommendations,
                "high_confidence_recommendations": high_confidence_count,
                "potential_monthly_revenue_increase": round(potential_revenue_increase, 2),
                "report_generated_at": report_data.get("generated_at", ""),
                "top_recommendations": pricing_recommendations[:3] if pricing_recommendations else []
            }
            
            # Send notification to each recipient
            async with httpx.AsyncClient() as client:
                for recipient in recipients:
                    response = await client.post(
                        "https://api.knock.app/v1/workflows/trigger",
                        headers={
                            "Authorization": f"Bearer {self.knock_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "key": workflow_key,
                            "recipients": [recipient],
                            "data": notification_data
                        }
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"Failed to send notification to {recipient}: {response.text}")
                        return False
                        
            logger.info(f"Successfully sent pricing report notifications to {len(recipients)} recipients")
            return True
            
        except ImportError:
            logger.error("httpx package not installed. Cannot send notifications.")
            return False
        except Exception as e:
            logger.error(f"Error sending pricing report notification: {str(e)}")
            return False
    
    async def send_experiment_results_notification(self,
                                            recipients: List[str],
                                            experiment_data: Dict[str, Any],
                                            user_id: int = None) -> bool:
        """
        Send a notification when experiment results are ready
        
        Args:
            recipients: List of recipient email addresses
            experiment_data: Data about the experiment results
            user_id: Optional user ID associated with this notification
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Notification service not configured. Skipping notification.")
            return False
        
        try:
            import httpx
            
            workflow_key = "experiment-results-ready"
            
            # Format experiment data for notification
            notification_data = {
                "experiment_name": experiment_data.get("name", "Pricing Experiment"),
                "experiment_duration": experiment_data.get("duration_days", 0),
                "control_performance": experiment_data.get("control_metrics", {}),
                "treatment_performance": experiment_data.get("treatment_metrics", {}),
                "statistical_significance": experiment_data.get("statistical_significance", False),
                "recommendation": experiment_data.get("recommendation", ""),
                "results_generated_at": experiment_data.get("generated_at", "")
            }
            
            # Send notification
            async with httpx.AsyncClient() as client:
                for recipient in recipients:
                    response = await client.post(
                        "https://api.knock.app/v1/workflows/trigger",
                        headers={
                            "Authorization": f"Bearer {self.knock_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "key": workflow_key,
                            "recipients": [recipient],
                            "data": notification_data
                        }
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"Failed to send experiment notification to {recipient}: {response.text}")
                        return False
                        
            logger.info(f"Successfully sent experiment results notifications to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Error sending experiment results notification: {str(e)}")
            return False

# Create a singleton instance for use throughout the application
notification_service = NotificationService()
