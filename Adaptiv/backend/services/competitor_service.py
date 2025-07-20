from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
import models
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import requests
import os
import google.generativeai as genai

logger = logging.getLogger(__name__)

class CompetitorService:
    def __init__(self, db: Session):
        self.db = db
        self._setup_gemini()
    
    def _setup_gemini(self):
        """Setup Gemini AI client"""
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            self.model = None
            logger.warning("GEMINI_API_KEY not found, competitor search will be limited")
    
    def search_competitors(self, item_name: str, user_id: int, location: str = None) -> Dict[str, Any]:
        """
        Search for competitor pricing using AI-powered search.
        """
        try:
            if not self.model:
                raise ValueError("Gemini AI not configured")
            
            # Create search prompt
            location_context = f" in {location}" if location else ""
            prompt = f"""
            Find competitor pricing information for the product: "{item_name}"{location_context}.
            
            Please search for similar products from major retailers and provide:
            1. Product name variations
            2. Current prices from different sources
            3. Average market price
            4. Price range (min-max)
            5. Source reliability
            
            Format the response as JSON with the following structure:
            {{
                "competitors": [
                    {{
                        "source": "retailer name",
                        "product_name": "exact product name found",
                        "price": 0.00,
                        "url": "product url if available",
                        "last_updated": "date"
                    }}
                ],
                "market_analysis": {{
                    "average_price": 0.00,
                    "price_range": {{"min": 0.00, "max": 0.00}},
                    "confidence": "high/medium/low"
                }}
            }}
            """
            
            response = self.model.generate_content(prompt)
            
            # Parse AI response (this would need more robust parsing in production)
            competitor_data = self._parse_competitor_response(response.text, item_name, user_id)
            
            return competitor_data
            
        except Exception as e:
            logger.error(f"Error searching competitors: {str(e)}")
            raise
    
    def _parse_competitor_response(self, response_text: str, item_name: str, user_id: int) -> Dict[str, Any]:
        """
        Parse AI response and store competitor data.
        """
        try:
            import json
            import re
            
            # Extract JSON from response (AI responses might have extra text)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                # Fallback if no JSON found
                data = {
                    "competitors": [],
                    "market_analysis": {
                        "average_price": 0.00,
                        "price_range": {"min": 0.00, "max": 0.00},
                        "confidence": "low"
                    }
                }
            
            # Store competitor data in database
            for competitor in data.get('competitors', []):
                existing_competitor = self.db.query(models.CompetitorItem).filter(
                    and_(
                        models.CompetitorItem.item_name.ilike(f"%{item_name}%"),
                        models.CompetitorItem.source == competitor.get('source', 'Unknown')
                    )
                ).first()
                
                if existing_competitor:
                    # Update existing
                    existing_competitor.price = competitor.get('price', 0)
                    existing_competitor.last_updated = datetime.now()
                else:
                    # Create new
                    new_competitor = models.CompetitorItem(
                        item_name=competitor.get('product_name', item_name),
                        price=competitor.get('price', 0),
                        source=competitor.get('source', 'Unknown'),
                        url=competitor.get('url'),
                        last_updated=datetime.now(),
                        created_at=datetime.now()
                    )
                    self.db.add(new_competitor)
            
            self.db.commit()
            return data
            
        except Exception as e:
            logger.error(f"Error parsing competitor response: {str(e)}")
            # Return empty data structure on parsing error
            return {
                "competitors": [],
                "market_analysis": {
                    "average_price": 0.00,
                    "price_range": {"min": 0.00, "max": 0.00},
                    "confidence": "low"
                }
            }
    
    def get_competitor_data(self, item_name: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get stored competitor data for an item.
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            competitors = self.db.query(models.CompetitorItem).filter(
                and_(
                    models.CompetitorItem.item_name.ilike(f"%{item_name}%"),
                    models.CompetitorItem.last_updated >= start_date
                )
            ).order_by(desc(models.CompetitorItem.last_updated)).all()
            
            return [
                {
                    'id': comp.id,
                    'item_name': comp.item_name,
                    'price': float(comp.price or 0),
                    'source': comp.source,
                    'url': comp.url,
                    'last_updated': comp.last_updated.isoformat() if comp.last_updated else None,
                    'created_at': comp.created_at.isoformat() if comp.created_at else None
                }
                for comp in competitors
            ]
            
        except Exception as e:
            logger.error(f"Error getting competitor data: {str(e)}")
            raise
    
    def get_market_analysis(self, item_name: str, current_price: float) -> Dict[str, Any]:
        """
        Get market analysis comparing current price to competitors.
        """
        try:
            competitors = self.get_competitor_data(item_name)
            
            if not competitors:
                return {
                    'competitors_found': 0,
                    'market_position': 'unknown',
                    'price_comparison': None,
                    'recommendations': ['No competitor data available']
                }
            
            prices = [comp['price'] for comp in competitors if comp['price'] > 0]
            
            if not prices:
                return {
                    'competitors_found': len(competitors),
                    'market_position': 'unknown',
                    'price_comparison': None,
                    'recommendations': ['Competitor prices not available']
                }
            
            avg_competitor_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            
            # Determine market position
            if current_price < min_price:
                position = 'below_market'
                recommendation = 'Consider increasing price - you are below all competitors'
            elif current_price > max_price:
                position = 'above_market'
                recommendation = 'Consider decreasing price - you are above all competitors'
            elif current_price < avg_competitor_price:
                position = 'below_average'
                recommendation = 'Room for price increase - you are below market average'
            elif current_price > avg_competitor_price:
                position = 'above_average'
                recommendation = 'Monitor sales - you are above market average'
            else:
                position = 'market_average'
                recommendation = 'Well positioned at market average'
            
            price_difference = current_price - avg_competitor_price
            price_difference_percent = (price_difference / avg_competitor_price) * 100
            
            return {
                'competitors_found': len(competitors),
                'market_position': position,
                'price_comparison': {
                    'current_price': current_price,
                    'market_average': round(avg_competitor_price, 2),
                    'market_range': {'min': min_price, 'max': max_price},
                    'difference_amount': round(price_difference, 2),
                    'difference_percent': round(price_difference_percent, 2)
                },
                'recommendations': [recommendation],
                'competitors': competitors
            }
            
        except Exception as e:
            logger.error(f"Error getting market analysis: {str(e)}")
            raise
    
    def update_competitor_prices(self, user_id: int) -> Dict[str, Any]:
        """
        Update competitor prices for all user items.
        """
        try:
            # Get all user items
            items = self.db.query(models.Item).filter(models.Item.user_id == user_id).all()
            
            updated_items = 0
            total_competitors = 0
            
            for item in items:
                try:
                    # Search for competitors for this item
                    competitor_data = self.search_competitors(item.name, user_id)
                    competitors_found = len(competitor_data.get('competitors', []))
                    
                    if competitors_found > 0:
                        updated_items += 1
                        total_competitors += competitors_found
                        
                except Exception as e:
                    logger.error(f"Error updating competitors for item {item.name}: {str(e)}")
                    continue
            
            return {
                'items_processed': len(items),
                'items_updated': updated_items,
                'total_competitors_found': total_competitors
            }
            
        except Exception as e:
            logger.error(f"Error updating competitor prices: {str(e)}")
            raise
    
    def get_competitor_trends(self, item_name: str, days: int = 90) -> Dict[str, Any]:
        """
        Get competitor price trends over time.
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get historical competitor data
            competitors = self.db.query(models.CompetitorItem).filter(
                and_(
                    models.CompetitorItem.item_name.ilike(f"%{item_name}%"),
                    models.CompetitorItem.last_updated >= start_date
                )
            ).order_by(models.CompetitorItem.last_updated).all()
            
            # Group by source and track price changes
            trends_by_source = {}
            for comp in competitors:
                source = comp.source
                if source not in trends_by_source:
                    trends_by_source[source] = []
                
                trends_by_source[source].append({
                    'date': comp.last_updated.isoformat(),
                    'price': float(comp.price or 0)
                })
            
            # Calculate trend statistics
            trend_analysis = {}
            for source, price_history in trends_by_source.items():
                if len(price_history) >= 2:
                    first_price = price_history[0]['price']
                    last_price = price_history[-1]['price']
                    
                    if first_price > 0:
                        change_percent = ((last_price - first_price) / first_price) * 100
                        trend = 'increasing' if change_percent > 5 else 'decreasing' if change_percent < -5 else 'stable'
                    else:
                        change_percent = 0
                        trend = 'stable'
                    
                    trend_analysis[source] = {
                        'trend': trend,
                        'change_percent': round(change_percent, 2),
                        'first_price': first_price,
                        'last_price': last_price,
                        'data_points': len(price_history)
                    }
            
            return {
                'period_days': days,
                'sources_tracked': list(trends_by_source.keys()),
                'price_history': trends_by_source,
                'trend_analysis': trend_analysis
            }
            
        except Exception as e:
            logger.error(f"Error getting competitor trends: {str(e)}")
            raise
