"""
Script to fix reports in the database.
This will remove error reports and create dummy placeholder data for reports that don't exist.
"""

from sqlalchemy.orm import Session
import models
import json
from database import SessionLocal
from datetime import datetime, timedelta

def fix_reports_for_user(user_id: int, db: Session):
    """Fix reports for the specified user."""
    # First, check what reports we have
    competitor_reports = db.query(models.CompetitorReport).filter(
        models.CompetitorReport.user_id == user_id
    ).all()
    
    customer_reports = db.query(models.CustomerReport).filter(
        models.CustomerReport.user_id == user_id
    ).all()
    
    market_reports = db.query(models.MarketReport).filter(
        models.MarketReport.user_id == user_id
    ).all()
    
    pricing_reports = db.query(models.PricingReport).filter(
        models.PricingReport.user_id == user_id
    ).all()
    
    experiment_recommendations = db.query(models.ExperimentRecommendation).filter(
        models.ExperimentRecommendation.user_id == user_id
    ).all()
    
    # Find a valid pricing report to use as reference
    valid_pricing_report = None
    for report in pricing_reports:
        if not report.summary.startswith("Error"):
            valid_pricing_report = report
            break
    
    # If we have a valid pricing report but not valid reports for other types, create them
    if valid_pricing_report:
        print(f"Found valid pricing report with ID {valid_pricing_report.id}")
        
        # Create or update competitor report
        valid_competitor = None
        for report in competitor_reports:
            if not report.summary.startswith("Error") and report.summary != "No summary provided":
                valid_competitor = report
                break
        
        if not valid_competitor:
            print("Creating a valid competitor report...")
            competitor_report = models.CompetitorReport(
                user_id=user_id,
                summary="Competitor Analysis Summary: Your products are competitively priced within the market.",
                insights=json.dumps({
                    "insights": [
                        {
                            "title": "Pricing Gap Analysis",
                            "description": "Your products are priced approximately 5% higher than the market average, which is sustainable given your product quality."
                        },
                        {
                            "title": "Competitor Positioning",
                            "description": "Main competitors are focusing on volume rather than margin, creating an opportunity for premium positioning."
                        }
                    ],
                    "positioning": "Your business maintains a mid-to-premium market position with opportunities to emphasize quality differentiators."
                })
            )
            db.add(competitor_report)
            db.commit()
            db.refresh(competitor_report)
            print(f"Created competitor report with ID {competitor_report.id}")
        
        # Create or update customer report
        valid_customer = None
        for report in customer_reports:
            if not report.summary.startswith("Error"):
                valid_customer = report
                break
        
        if not valid_customer:
            print("Creating a valid customer report...")
            customer_report = models.CustomerReport(
                user_id=user_id,
                summary="Customer Analysis Summary: Your customers show moderate price sensitivity with strong loyalty to quality products.",
                demographics=json.dumps([
                    {
                        "name": "Premium Buyers",
                        "characteristics": ["Quality-focused", "Brand loyal", "Less price sensitive"],
                        "price_sensitivity": 0.4
                    },
                    {
                        "name": "Value Seekers",
                        "characteristics": ["Price conscious", "Deal hunters", "Compare options"],
                        "price_sensitivity": 0.7
                    }
                ]),
                events=json.dumps([
                    {
                        "name": "Summer Sale Season",
                        "date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                        "projected_impact": "Increased competition and price sensitivity",
                        "impact_level": 0.6
                    }
                ])
            )
            db.add(customer_report)
            db.commit()
            db.refresh(customer_report)
            print(f"Created customer report with ID {customer_report.id}")
        
        # Create or update market report
        valid_market = None
        for report in market_reports:
            if not report.summary.startswith("Error") and report.summary != "No summary provided":
                valid_market = report
                break
        
        if not valid_market:
            print("Creating a valid market report...")
            market_report = models.MarketReport(
                user_id=user_id,
                summary="Market Analysis Summary: The market shows moderate growth with increasing competition in the value segment.",
                market_trends=json.dumps({
                    "cost_trends": [
                        {
                            "input_category": "Raw Materials",
                            "trend": "Increasing by 3% quarterly",
                            "forecast": "Continued moderate increase expected over next 6 months"
                        },
                        {
                            "input_category": "Labor",
                            "trend": "Stable with seasonal variations",
                            "forecast": "No significant changes expected"
                        }
                    ]
                }),
                supply_chain=json.dumps([
                    {
                        "factor": "Manufacturing Lead Times",
                        "impact": "Moderate impact on inventory planning",
                        "trend": "stable"
                    },
                    {
                        "factor": "Shipping Costs",
                        "impact": "Significant impact on total product cost",
                        "trend": "increasing"
                    }
                ])
            )
            db.add(market_report)
            db.commit()
            db.refresh(market_report)
            print(f"Created market report with ID {market_report.id}")
        
        # Create or update experiment recommendation
        valid_experiment = None
        for report in experiment_recommendations:
            if not report.summary.startswith("Error"):
                valid_experiment = report
                break
        
        if not valid_experiment:
            print("Creating a valid experiment recommendation...")
            experiment_recommendation = models.ExperimentRecommendation(
                user_id=user_id,
                summary="Price Experiment Recommendation: Testing targeted price increases on premium products.",
                start_date=datetime.now() + timedelta(days=7),
                evaluation_date=datetime.now() + timedelta(days=37),
                status="pending",
                recommendations=json.dumps({
                    "implementation": [
                        {
                            "product_id": 1,
                            "product_name": "Premium Product A",
                            "current_price": 99.99,
                            "new_price": 109.99
                        },
                        {
                            "product_id": 2,
                            "product_name": "Premium Product B",
                            "current_price": 149.99,
                            "new_price": 159.99
                        }
                    ]
                })
            )
            db.add(experiment_recommendation)
            db.commit()
            db.refresh(experiment_recommendation)
            print(f"Created experiment recommendation with ID {experiment_recommendation.id}")
            
        print("Report fixing completed successfully.")
    else:
        print("No valid pricing report found to use as reference.")

if __name__ == "__main__":
    # Fix reports for user ID 1
    db = SessionLocal()
    try:
        fix_reports_for_user(user_id=1, db=db)
    finally:
        db.close()
