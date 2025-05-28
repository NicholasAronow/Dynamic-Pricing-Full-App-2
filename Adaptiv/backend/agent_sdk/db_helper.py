"""
Database helper for agents that wraps SQLAlchemy Session in a way that's compatible with the Agents SDK.
This prevents Pydantic serialization issues with SQLAlchemy Session objects.
"""
from sqlalchemy.orm import Session
import models as db_models
import json
from typing import List, Dict, Any, Optional, ClassVar, Type
from datetime import datetime, timedelta
import pydantic_core
from pydantic import GetCoreSchemaHandler

class DBHelper:
    """A helper class that wraps database operations for agents."""
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, __source_type: Type[Any], __handler: GetCoreSchemaHandler
    ) -> pydantic_core.CoreSchema:
        """Generate a CoreSchema for DBHelper class.
        
        This allows Pydantic to work with DBHelper objects without serialization issues.
        
        Args:
            __source_type: The source type
            __handler: The core schema handler
            
        Returns:
            A CoreSchema for DBHelper class
        """
        # Use any_schema to allow DBHelper to be used without serialization issues
        schema = pydantic_core.core_schema.any_schema()
        schema["metadata"] = {
            "title": "DBHelper", 
            "description": "Database helper for agent operations (non-serializable)"
        }
        return schema
    
    def __init__(self, session: Session):
        self._session = session
    
    def get_business_info(self, user_id: int) -> Dict[str, Any]:
        """Get the business information for the specified user."""
        business = self._session.query(db_models.BusinessProfile).filter(db_models.BusinessProfile.user_id == user_id).first()
        if not business:
            return {"error": "Business not found"}
        
        # Format address as a string if any address components exist
        location = ""
        if any([business.city, business.state, business.postal_code]):
            address_parts = []
            if business.city:
                address_parts.append(business.city)
            if business.state:
                address_parts.append(business.state)
            if business.postal_code:
                address_parts.append(business.postal_code)
            if business.country and business.country.lower() != "usa":
                address_parts.append(business.country)
            location = ", ".join(address_parts)
        
        return {
            "name": business.business_name,
            "industry": business.industry,
            "description": business.description,
            "location": location,
            "street_address": business.street_address or "",
            "city": business.city or "",
            "state": business.state or "",
            "postal_code": business.postal_code or "",
            "country": business.country or "USA"
        }
    
    def get_competitor_items(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all competitor items from the database."""
        competitor_items = self._session.query(db_models.CompetitorItem).all()
        
        competitor_data = {}
        for item in competitor_items:
            if item.competitor_name not in competitor_data:
                competitor_data[item.competitor_name] = []
            
            competitor_data[item.competitor_name].append({
                "name": item.item_name,
                "category": item.category,
                "price": item.price,
                "description": item.description,
                "similarity_score": item.similarity_score
            })
        
        return competitor_data
    
    def get_our_items(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all items for the specified user."""
        items = self._session.query(db_models.Item).filter(db_models.Item.user_id == user_id).all()
        
        items_data = []
        for item in items:
            items_data.append({
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "price": item.price,
                "description": item.description
            })
        
        return items_data
    
    def get_price_history(self, user_id: int) -> Dict[int, List[Dict[str, Any]]]:
        """Get price history for the specified user's items."""
        price_history = self._session.query(db_models.PriceHistory).filter(
            db_models.PriceHistory.user_id == user_id
        ).all()
        
        history_data = {}
        for record in price_history:
            if record.item_id not in history_data:
                history_data[record.item_id] = []
            
            history_data[record.item_id].append({
                "price": record.price,
                "date": record.date.isoformat(),
                "reason": record.reason
            })
        
        return history_data
    
    def save_competitor_items(self, competitors_data: List[Dict[str, Any]]) -> List[db_models.CompetitorItem]:
        """Save new competitor items to the database.
        
        Args:
            competitors_data: List of competitor items with name, price, etc.
            
        Returns:
            List of saved CompetitorItem objects
        """
        saved_items = []
        
        for item_data in competitors_data:
            # Check if this competitor item already exists
            existing_item = self._session.query(db_models.CompetitorItem).filter(
                db_models.CompetitorItem.competitor_name == item_data.get('competitor_name'),
                db_models.CompetitorItem.item_name == item_data.get('item_name')
            ).first()
            
            if existing_item:
                # Update the existing item with new information
                existing_item.price = item_data.get('price', existing_item.price)
                existing_item.category = item_data.get('category', existing_item.category)
                existing_item.description = item_data.get('description', existing_item.description)
                existing_item.similarity_score = item_data.get('similarity_score', existing_item.similarity_score)
                existing_item.updated_at = func.now()
                saved_items.append(existing_item)
            else:
                # Create a new competitor item
                new_item = db_models.CompetitorItem(
                    competitor_name=item_data.get('competitor_name'),
                    item_name=item_data.get('item_name'),
                    price=item_data.get('price'),
                    category=item_data.get('category', ''),
                    description=item_data.get('description', ''),
                    similarity_score=item_data.get('similarity_score'),
                    url=item_data.get('url', '')
                )
                self._session.add(new_item)
                saved_items.append(new_item)
        
        # Commit all changes
        self._session.commit()
        
        # Refresh all items to get their IDs
        for item in saved_items:
            self._session.refresh(item)
            
        return saved_items
    
    def save_competitor_report(self, user_id: int, report_data: Dict[str, Any]) -> db_models.CompetitorReport:
        """Save a competitor report to the database."""
        # First save any new competitor items discovered by the agent
        new_competitors = report_data.get("discovered_competitors", [])
        if new_competitors:
            self.save_competitor_items(new_competitors)
        
        competitor_report = db_models.CompetitorReport(
            user_id=user_id,
            summary=report_data.get("summary", ""),
            insights=json.dumps(report_data.get("insights", {})),
            competitor_data=json.dumps(report_data.get("competitor_data", {}))
        )
        
        self._session.add(competitor_report)
        self._session.commit()
        self._session.refresh(competitor_report)
        
        return competitor_report
    
    def save_customer_report(self, user_id: int, report_data: Dict[str, Any]) -> db_models.CustomerReport:
        """Save a customer report to the database."""
        customer_report = db_models.CustomerReport(
            user_id=user_id,
            summary=report_data.get("summary", ""),
            demographics=json.dumps(report_data.get("demographics", {})),
            price_sensitivity=json.dumps(report_data.get("price_sensitivity", {})),
            upcoming_events=json.dumps(report_data.get("upcoming_events", []))
        )
        
        self._session.add(customer_report)
        self._session.commit()
        self._session.refresh(customer_report)
        
        return customer_report
    
    def save_market_report(self, user_id: int, report_data: Dict[str, Any]) -> db_models.MarketReport:
        """Save a market report to the database."""
        market_report = db_models.MarketReport(
            user_id=user_id,
            summary=report_data.get("summary", ""),
            supply_chain=json.dumps(report_data.get("supply_chain", [])),
            cost_trends=json.dumps(report_data.get("cost_trends", [])),
            competitive_landscape=json.dumps(report_data.get("competitive_landscape", {}))
        )
        
        self._session.add(market_report)
        self._session.commit()
        self._session.refresh(market_report)
        
        return market_report
    
    def save_pricing_report(self, user_id: int, report_data: Dict[str, Any]) -> db_models.PricingReport:
        """Save a pricing report to the database."""
        pricing_report = db_models.PricingReport(
            user_id=user_id,
            summary=report_data.get("summary", ""),
            product_recommendations=json.dumps(report_data.get("product_recommendations", [])),
            pricing_insights=json.dumps(report_data.get("pricing_insights", [])),
            implementation_advice=json.dumps(report_data.get("implementation", {})),
            competitor_report_id=report_data.get("competitor_report_id"),
            customer_report_id=report_data.get("customer_report_id"),
            market_report_id=report_data.get("market_report_id")
        )
        
        self._session.add(pricing_report)
        self._session.commit()
        self._session.refresh(pricing_report)
        
        return pricing_report
    
    def save_experiment_plan(self, user_id: int, plan_data: Dict[str, Any]) -> db_models.ExperimentRecommendation:
        """Save an experiment plan to the database."""
        experiment_recommendation = db_models.ExperimentRecommendation(
            user_id=user_id,
            summary=plan_data.get("summary", ""),
            implementation=json.dumps(plan_data.get("implementation", [])),
            evaluation_criteria=json.dumps(plan_data.get("evaluation_criteria", [])),
            risks=json.dumps(plan_data.get("risks", [])),
            pricing_report_id=plan_data.get("pricing_report_id")
        )
        
        self._session.add(experiment_recommendation)
        self._session.commit()
        self._session.refresh(experiment_recommendation)
        
        return experiment_recommendation
