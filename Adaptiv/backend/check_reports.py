"""
Script to check if reports exist in the database for user ID 1.
"""

from sqlalchemy.orm import Session
import models
from database import SessionLocal

def check_reports_for_user(user_id: int, db: Session):
    """Check what reports exist for the specified user."""
    # Check competitor reports
    competitor_reports = db.query(models.CompetitorReport).filter(
        models.CompetitorReport.user_id == user_id
    ).all()
    print(f"Found {len(competitor_reports)} competitor reports for user {user_id}")
    for i, report in enumerate(competitor_reports):
        print(f"  Report {i+1}: ID={report.id}, Summary: {report.summary[:50]}...")
    
    # Check customer reports
    customer_reports = db.query(models.CustomerReport).filter(
        models.CustomerReport.user_id == user_id
    ).all()
    print(f"Found {len(customer_reports)} customer reports for user {user_id}")
    for i, report in enumerate(customer_reports):
        print(f"  Report {i+1}: ID={report.id}, Summary: {report.summary[:50]}...")
    
    # Check market reports
    market_reports = db.query(models.MarketReport).filter(
        models.MarketReport.user_id == user_id
    ).all()
    print(f"Found {len(market_reports)} market reports for user {user_id}")
    for i, report in enumerate(market_reports):
        print(f"  Report {i+1}: ID={report.id}, Summary: {report.summary[:50]}...")
    
    # Check pricing reports
    pricing_reports = db.query(models.PricingReport).filter(
        models.PricingReport.user_id == user_id
    ).all()
    print(f"Found {len(pricing_reports)} pricing reports for user {user_id}")
    for i, report in enumerate(pricing_reports):
        print(f"  Report {i+1}: ID={report.id}, Summary: {report.summary[:50]}...")
    
    # Check experiment recommendations
    experiment_recommendations = db.query(models.ExperimentRecommendation).filter(
        models.ExperimentRecommendation.user_id == user_id
    ).all()
    print(f"Found {len(experiment_recommendations)} experiment recommendations for user {user_id}")
    for i, report in enumerate(experiment_recommendations):
        print(f"  Recommendation {i+1}: ID={report.id}, Summary: {report.summary[:50]}...")

if __name__ == "__main__":
    # Check reports for user ID 1
    db = SessionLocal()
    try:
        check_reports_for_user(user_id=1, db=db)
    finally:
        db.close()
