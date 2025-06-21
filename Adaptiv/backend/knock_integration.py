"""
Knock integration for sending notifications
"""
import os
from typing import List, Dict, Any, Union
import logging

logger = logging.getLogger(__name__)

class KnockClient:
    """
    A client for interacting with the Knock API to send notifications
    """
    def __init__(self):
        self.api_key = os.environ.get("KNOCK_API_KEY")
        if not self.api_key:
            logger.warning("KNOCK_API_KEY environment variable not set. Email notifications will not be sent.")
    
    def is_configured(self) -> bool:
        """Check if Knock is properly configured with an API key"""
        return self.api_key is not None
    
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
            pricing_changes_count = len(pricing_recommendations)
            
            # Prepare detailed pricing data for each recommendation
            pricing_details = []
            for rec in pricing_recommendations:
                # Extract price information directly from the recommendation object
                item_name = rec.get("item_name", "Unknown Item")
                current_price = rec.get("current_price", 0)
                recommended_price = rec.get("recommended_price", 0)
                price_change_percent = rec.get("price_change_percent", 0)
                
                # Format price change display
                change_direction = "increase" if price_change_percent >= 0 else "decrease"
                change_display = f"{abs(price_change_percent):.1f}% {change_direction}"
                
                # Get rationale
                rationale = rec.get("rationale", "Improved pricing alignment")
                
                # Add to pricing details list
                pricing_details.append({
                    "item_name": item_name,
                    "old_price": f"${current_price:.2f}",
                    "new_price": f"${recommended_price:.2f}",
                    "change": change_display,
                    "rationale": rationale
                })
            
            # Prepare recipients in the format expected by Knock API
            # Knock requires recipients to have both 'collection' and 'id' fields
            formatted_recipients = []
            for i, email in enumerate(recipients):
                formatted_recipients.append({
                    "collection": "users",
                    "id": f"user-{i+1}",  # Generate a unique ID for each recipient
                    "email": email  # Include email as a property
                })
            
            # Extract useful data for the notification
            data = {
                "report_id": report_data.get("task_id", ""),
                "report_date": report_data.get("completed_at", ""),
                "report_url": f"/dynamic-pricing",  # Adjust based on your frontend URL structure
                "pricing_changes_count": pricing_changes_count,
                "email_subject": f"{pricing_changes_count} New Price Recommendations Available",
                "pricing_details": pricing_details,
                "user_id": user_id
            }
            
            # Make the API request to Knock
            url = f"https://api.knock.app/v1/workflows/{workflow_key}/trigger"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "recipients": formatted_recipients,
                "data": data
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code >= 400:
                logger.error(f"Failed to send Knock notification: {response.status_code} - {response.text}")
                return False
                
            logger.info(f"Successfully sent pricing report notification to {len(recipients)} recipient(s)")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Knock notification: {str(e)}")
            return False


# Create a singleton instance for use throughout the application
knock_client = KnockClient()
