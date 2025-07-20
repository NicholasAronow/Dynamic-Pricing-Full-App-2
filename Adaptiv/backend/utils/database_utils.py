"""
Simple database interface to work around Pydantic schema generation issues with SQLAlchemy Session objects.
"""
from sqlalchemy.orm import Session
import models

class DatabaseInterface:
    """A simple wrapper around SQLAlchemy Session to avoid Pydantic schema generation issues."""
    
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
