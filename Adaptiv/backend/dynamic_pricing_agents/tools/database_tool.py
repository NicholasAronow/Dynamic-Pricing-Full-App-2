"""
Database Tool for OpenAI Agent SDK integration

This tool allows the OpenAI Agent to query the database for competitor information and other relevant data.
"""

from typing import Dict, Any, List, Optional
import logging
import json
from pydantic import BaseModel, Field

class DatabaseTool:
    """
    Tool for querying the database for competitor pricing and other relevant information.
    Designed to be compatible with the OpenAI Agent SDK.
    """
    
    def __init__(self, db_session=None):
        """
        Initialize the database tool
        
        Args:
            db_session: SQLAlchemy session or equivalent database connection
        """
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
    
    def to_function_definition(self) -> dict:
        """
        Convert this tool to an OpenAI function definition
        
        Returns:
            Dictionary representing the function definition for this tool
        """
        return {
            "name": "query_competitor_data",
            "description": "Query the database for competitor pricing and market information for specific products",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string", 
                        "description": "ID of the item to get competitor data for"
                    },
                    "item_name": {
                        "type": "string",
                        "description": "Name of the item (use if ID is not available)"
                    },
                    "include_historical": {
                        "type": "boolean", 
                        "description": "Whether to include historical price data"
                    }
                },
                "required": ["item_id"]
            }
        }
    
    def __call__(self, item_id: str, item_name: Optional[str] = None, include_historical: bool = False) -> Dict[str, Any]:
        """
        Call the database tool to fetch competitor data
        
        Args:
            item_id: ID of the item to get data for
            item_name: Name of the item (optional)
            include_historical: Whether to include historical price data
        
        Returns:
            Dictionary containing competitor data for the specified item
        """
        try:
            self.logger.info(f"Querying competitor data for item {item_id}")
            
            if self.db_session is None:
                # Return mock data for demonstration if no DB connection
                return self._get_mock_competitor_data(item_id, include_historical)
            
            # In a real implementation, you would query the database here
            # Example query for competitor pricing:
            # results = self.db_session.query(CompetitorPriceHistory)
            #     .filter(CompetitorPriceHistory.item_id == item_id)
            #     .order_by(CompetitorPriceHistory.date.desc())
            #     .limit(10 if include_historical else 1)
            #     .all()
            #
            # competitor_data = {
            #     "current_prices": [{"competitor": r.competitor_name, "price": r.price} for r in results[:1]],
            #     "historical_prices": [{"competitor": r.competitor_name, "price": r.price, "date": r.date} for r in results] if include_historical else []
            # }
            #
            # return competitor_data
            
            # For now, use mock data
            return self._get_mock_competitor_data(item_id, include_historical)
            
        except Exception as e:
            self.logger.error(f"Error querying competitor data: {str(e)}")
            return {"error": f"Failed to retrieve competitor data: {str(e)}"}
    
    def _get_mock_competitor_data(self, item_id: str, include_historical: bool = False) -> Dict[str, Any]:
        """
        Generate mock competitor data for demonstration
        
        Args:
            item_id: ID of the item to generate data for
            include_historical: Whether to include historical price data
        
        Returns:
            Mock competitor data
        """
        # Sample mock data based on item_id
        mock_data = {
            "1": {  # Espresso
                "current_prices": [
                    {"competitor": "Starbucks", "price": 3.25},
                    {"competitor": "Peet's Coffee", "price": 2.95},
                    {"competitor": "Local Café", "price": 2.85}
                ],
                "market_share": {"our_share": 0.15, "leading_competitor_share": 0.35},
                "trend": "Stable pricing across competitors with seasonal promotions"
            },
            "5": {  # Latte
                "current_prices": [
                    {"competitor": "Starbucks", "price": 4.95},
                    {"competitor": "Peet's Coffee", "price": 4.25},
                    {"competitor": "Local Café", "price": 4.00}
                ],
                "market_share": {"our_share": 0.12, "leading_competitor_share": 0.40},
                "trend": "Premium pricing by major chains, with independents undercutting"
            },
            "12": {  # Iced Coffee
                "current_prices": [
                    {"competitor": "Starbucks", "price": 4.45},
                    {"competitor": "Peet's Coffee", "price": 4.25},
                    {"competitor": "Local Café", "price": 3.95}
                ],
                "market_share": {"our_share": 0.18, "leading_competitor_share": 0.32},
                "trend": "Seasonal pricing with 15-20% summer premium"
            },
            "36": {  # Matcha Latte
                "current_prices": [
                    {"competitor": "Starbucks", "price": 5.45},
                    {"competitor": "Peet's Coffee", "price": 4.95},
                    {"competitor": "Local Café", "price": 4.75}
                ],
                "market_share": {"our_share": 0.22, "leading_competitor_share": 0.30},
                "trend": "Growing category with premium positioning and rising prices"
            }
        }
        
        # Historical data if requested
        if include_historical:
            historical_data = {
                "1": [  # Espresso historical data
                    {"date": "2025-05-15", "competitor": "Starbucks", "price": 3.25},
                    {"date": "2025-04-15", "competitor": "Starbucks", "price": 3.15},
                    {"date": "2025-03-15", "competitor": "Starbucks", "price": 3.15},
                ],
                "5": [  # Latte historical data
                    {"date": "2025-05-15", "competitor": "Starbucks", "price": 4.95},
                    {"date": "2025-04-15", "competitor": "Starbucks", "price": 4.75},
                    {"date": "2025-03-15", "competitor": "Starbucks", "price": 4.75},
                ],
                "12": [  # Iced Coffee historical data
                    {"date": "2025-05-15", "competitor": "Starbucks", "price": 4.45},
                    {"date": "2025-04-15", "competitor": "Starbucks", "price": 4.25},
                    {"date": "2025-03-15", "competitor": "Starbucks", "price": 4.25},
                ],
                "36": [  # Matcha Latte historical data
                    {"date": "2025-05-15", "competitor": "Starbucks", "price": 5.45},
                    {"date": "2025-04-15", "competitor": "Starbucks", "price": 5.25},
                    {"date": "2025-03-15", "competitor": "Starbucks", "price": 5.15},
                ]
            }
            
            # Add historical data if available for this item
            if item_id in historical_data:
                mock_data[item_id]["historical_prices"] = historical_data[item_id]
        
        # Return data for the requested item, or a default message if not found
        return mock_data.get(item_id, {
            "current_prices": [],
            "market_share": {"our_share": 0, "leading_competitor_share": 0},
            "trend": "No competitor data available for this item",
            "note": "This is a mock response. In production, this would query real database data."
        })
