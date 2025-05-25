"""
Script to display all reports for a user, regardless of their content or status.
This is a debugging tool to view reports that might not show in the dashboard.
"""

import json
from sqlalchemy.orm import Session
import models
from database import SessionLocal
from datetime import datetime

def display_all_reports_for_user(user_id: int, db: Session):
    """Display all reports for the specified user."""
    print(f"\n{'='*50}")
    print(f"REPORT VIEWER FOR USER ID: {user_id}")
    print(f"{'='*50}")
    
    # Get all reports
    competitor_reports = db.query(models.CompetitorReport).filter(
        models.CompetitorReport.user_id == user_id
    ).order_by(models.CompetitorReport.created_at.desc()).all()
    
    customer_reports = db.query(models.CustomerReport).filter(
        models.CustomerReport.user_id == user_id
    ).order_by(models.CustomerReport.created_at.desc()).all()
    
    market_reports = db.query(models.MarketReport).filter(
        models.MarketReport.user_id == user_id
    ).order_by(models.MarketReport.created_at.desc()).all()
    
    pricing_reports = db.query(models.PricingReport).filter(
        models.PricingReport.user_id == user_id
    ).order_by(models.PricingReport.created_at.desc()).all()
    
    experiment_recommendations = db.query(models.ExperimentRecommendation).filter(
        models.ExperimentRecommendation.user_id == user_id
    ).order_by(models.ExperimentRecommendation.created_at.desc()).all()
    
    # Display competitor reports
    print(f"\n\n{'-'*20} COMPETITOR REPORTS {'-'*20}")
    for i, report in enumerate(competitor_reports):
        print(f"\nReport #{i+1}: ID={report.id}")
        print(f"Created: {report.created_at}")
        print(f"Summary: {report.summary[:150]}...")
        if report.insights:
            print(f"Has insights data: Yes")
            insights = json.loads(report.insights)
            if 'insights' in insights and isinstance(insights['insights'], list):
                print(f"Number of insights: {len(insights['insights'])}")
        else:
            print(f"Has insights data: No")
    
    # Display customer reports
    print(f"\n\n{'-'*20} CUSTOMER REPORTS {'-'*20}")
    for i, report in enumerate(customer_reports):
        print(f"\nReport #{i+1}: ID={report.id}")
        print(f"Created: {report.created_at}")
        print(f"Summary: {report.summary[:150]}...")
        if report.demographics:
            print(f"Has demographics data: Yes")
            demographics = json.loads(report.demographics)
            if isinstance(demographics, list):
                print(f"Number of demographic segments: {len(demographics)}")
        else:
            print(f"Has demographics data: No")
        
        if report.events:
            print(f"Has events data: Yes")
            events = json.loads(report.events)
            if isinstance(events, list):
                print(f"Number of events: {len(events)}")
        else:
            print(f"Has events data: No")
    
    # Display market reports
    print(f"\n\n{'-'*20} MARKET REPORTS {'-'*20}")
    for i, report in enumerate(market_reports):
        print(f"\nReport #{i+1}: ID={report.id}")
        print(f"Created: {report.created_at}")
        print(f"Summary: {report.summary[:150]}...")
        if report.supply_chain:
            print(f"Has supply chain data: Yes")
            supply_chain = json.loads(report.supply_chain)
            if isinstance(supply_chain, list):
                print(f"Number of supply chain factors: {len(supply_chain)}")
        else:
            print(f"Has supply chain data: No")
            
        if report.market_trends:
            print(f"Has market trends data: Yes")
            market_trends = json.loads(report.market_trends)
            if isinstance(market_trends, dict) and 'cost_trends' in market_trends:
                print(f"Has cost trends: Yes")
            else:
                print(f"Has cost trends: No")
        else:
            print(f"Has market trends data: No")
    
    # Display pricing reports
    print(f"\n\n{'-'*20} PRICING REPORTS {'-'*20}")
    for i, report in enumerate(pricing_reports):
        print(f"\nReport #{i+1}: ID={report.id}")
        print(f"Created: {report.created_at}")
        print(f"Summary: {report.summary[:150]}...")
        if report.recommended_changes:
            print(f"Has recommended changes: Yes")
            changes = json.loads(report.recommended_changes)
            if isinstance(changes, list):
                print(f"Number of recommendations: {len(changes)}")
        else:
            print(f"Has recommended changes: No")
    
    # Display experiment recommendations
    print(f"\n\n{'-'*20} EXPERIMENT RECOMMENDATIONS {'-'*20}")
    for i, report in enumerate(experiment_recommendations):
        print(f"\nRecommendation #{i+1}: ID={report.id}")
        print(f"Created: {report.created_at}")
        print(f"Summary: {report.summary[:150]}...")
        print(f"Status: {report.status}")
        if report.recommendations:
            print(f"Has implementation data: Yes")
            recs = json.loads(report.recommendations)
            if isinstance(recs, dict) and 'implementation' in recs:
                print(f"Has implementation details: Yes")
                if isinstance(recs['implementation'], list):
                    print(f"Number of implementations: {len(recs['implementation'])}")
            else:
                print(f"Has implementation details: No")
        else:
            print(f"Has implementation data: No")
    
    print(f"\n{'='*50}")
    print("END OF REPORT VIEWER")
    print(f"{'='*50}")
    
    # Check latest for dashboard
    print("\nMost recent reports that should appear in dashboard:")
    latest_competitor = competitor_reports[0] if competitor_reports else None
    latest_customer = customer_reports[0] if customer_reports else None
    latest_market = market_reports[0] if market_reports else None
    latest_pricing = pricing_reports[0] if pricing_reports else None
    latest_experiment = experiment_recommendations[0] if experiment_recommendations else None
    
    print(f"Latest Competitor Report: ID={latest_competitor.id if latest_competitor else 'None'}, Has Error: {'Yes' if latest_competitor and 'Error' in latest_competitor.summary else 'No'}")
    print(f"Latest Customer Report: ID={latest_customer.id if latest_customer else 'None'}, Has Error: {'Yes' if latest_customer and 'Error' in latest_customer.summary else 'No'}")
    print(f"Latest Market Report: ID={latest_market.id if latest_market else 'None'}, Has Error: {'Yes' if latest_market and 'Error' in latest_market.summary else 'No'}")
    print(f"Latest Pricing Report: ID={latest_pricing.id if latest_pricing else 'None'}, Has Error: {'Yes' if latest_pricing and 'Error' in latest_pricing.summary else 'No'}")
    print(f"Latest Experiment Recommendation: ID={latest_experiment.id if latest_experiment else 'None'}, Has Error: {'Yes' if latest_experiment and 'Error' in latest_experiment.summary else 'No'}")

if __name__ == "__main__":
    # Display reports for user ID 1
    db = SessionLocal()
    try:
        display_all_reports_for_user(user_id=1, db=db)
    finally:
        db.close()
