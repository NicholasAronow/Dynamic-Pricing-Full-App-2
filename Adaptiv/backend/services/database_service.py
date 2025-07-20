"""
Database service to provide clean database operations and avoid Pydantic schema generation issues.
"""
from sqlalchemy.orm import Session
import models

class DatabaseService:
    """A service wrapper around SQLAlchemy Session to provide clean database operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_latest_competitor_report(self, user_id: int):
        """Get the most recent competitor report for a user."""
        return self.session.query(models.CompetitorReport).filter(
            models.CompetitorReport.user_id == user_id
        ).order_by(models.CompetitorReport.created_at.desc()).first()
    
    def get_latest_customer_report(self, user_id: int):
        """Get the most recent customer report for a user."""
        return self.session.query(models.CustomerReport).filter(
            models.CustomerReport.user_id == user_id
        ).order_by(models.CustomerReport.created_at.desc()).first()
    
    def get_latest_market_report(self, user_id: int):
        """Get the most recent market report for a user."""
        return self.session.query(models.MarketReport).filter(
            models.MarketReport.user_id == user_id
        ).order_by(models.MarketReport.created_at.desc()).first()
    
    def get_latest_pricing_report(self, user_id: int):
        """Get the most recent pricing report for a user."""
        return self.session.query(models.PricingReport).filter(
            models.PricingReport.user_id == user_id
        ).order_by(models.PricingReport.created_at.desc()).first()
    
    def get_latest_experiment_recommendation(self, user_id: int):
        """Get the most recent experiment recommendation for a user."""
        return self.session.query(models.ExperimentRecommendation).filter(
            models.ExperimentRecommendation.user_id == user_id
        ).order_by(models.ExperimentRecommendation.created_at.desc()).first()
    
    def get_pricing_report_by_id(self, report_id: int):
        """Get a pricing report by ID."""
        return self.session.query(models.PricingReport).filter(
            models.PricingReport.id == report_id
        ).first()
    
    def get_user_items(self, user_id: int):
        """Get all items for a user."""
        return self.session.query(models.Item).filter(
            models.Item.user_id == user_id
        ).all()
    
    def get_user_orders(self, user_id: int, limit: int = None):
        """Get orders for a user with optional limit."""
        query = self.session.query(models.Order).filter(
            models.Order.user_id == user_id
        ).order_by(models.Order.order_date.desc())
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    
    def get_competitor_items(self, user_id: int):
        """Get all competitor items for a user."""
        return self.session.query(models.CompetitorItem).filter(
            models.CompetitorItem.user_id == user_id
        ).all()
    
    def get_price_history(self, item_id: int):
        """Get price history for an item."""
        return self.session.query(models.PriceHistory).filter(
            models.PriceHistory.item_id == item_id
        ).order_by(models.PriceHistory.changed_at.desc()).all()
    
    def get_user_cogs(self, user_id: int):
        """Get COGS data for a user."""
        return self.session.query(models.COGS).filter(
            models.COGS.user_id == user_id
        ).order_by(models.COGS.week_start_date.desc()).all()
    
    def get_user_fixed_costs(self, user_id: int):
        """Get fixed costs for a user."""
        return self.session.query(models.FixedCost).filter(
            models.FixedCost.user_id == user_id
        ).order_by(models.FixedCost.date.desc()).all()
    
    def get_pos_integration(self, user_id: int):
        """Get POS integration for a user."""
        return self.session.query(models.POSIntegration).filter(
            models.POSIntegration.user_id == user_id
        ).first()
    
    def create_or_update_pos_integration(self, user_id: int, integration_data: dict):
        """Create or update POS integration for a user."""
        existing = self.get_pos_integration(user_id)
        
        if existing:
            for key, value in integration_data.items():
                setattr(existing, key, value)
            integration = existing
        else:
            integration = models.POSIntegration(user_id=user_id, **integration_data)
            self.session.add(integration)
        
        self.session.commit()
        return integration
    
    def get_business_profile(self, user_id: int):
        """Get business profile for a user."""
        return self.session.query(models.BusinessProfile).filter(
            models.BusinessProfile.user_id == user_id
        ).first()
    
    def get_action_items(self, user_id: int, completed: bool = None):
        """Get action items for a user, optionally filtered by completion status."""
        query = self.session.query(models.ActionItem).filter(
            models.ActionItem.user_id == user_id
        )
        
        if completed is not None:
            query = query.filter(models.ActionItem.completed == completed)
            
        return query.order_by(models.ActionItem.created_at.desc()).all()
