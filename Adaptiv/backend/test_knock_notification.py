import asyncio
import json
import os
from datetime import datetime, timedelta
from knock_integration import knock_client

async def test_notification():
    # Sample report data mimicking what would come from the dynamic pricing analysis task
    # Batch ID for this set of recommendations
    batch_id = f"batch-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Item-level pricing recommendations that match the PricingRecommendation model structure
    pricing_recommendations = [
        {
            "id": 1001,
            "item_id": 101,
            "item_name": "Premium Widget",
            "batch_id": batch_id,
            "recommendation_date": datetime.now().isoformat(),
            "current_price": 29.99,
            "recommended_price": 34.99,
            "price_change_amount": 5.00,
            "price_change_percent": 16.67,
            "strategy_type": "premium_pricing",
            "confidence_score": 0.85,
            "rationale": "Competitors have higher prices for similar quality products. Market research shows customers value this product higher than current pricing.",
            "expected_revenue_change": 5000.00,
            "expected_quantity_change": -3.0,
            "expected_margin_change": 8.5,
            "implementation_status": "pending",
            "reevaluation_date": (datetime.now() + timedelta(days=30)).isoformat(),
        },
        {
            "id": 1002,
            "item_id": 102,
            "item_name": "Basic Package",
            "batch_id": batch_id,
            "recommendation_date": datetime.now().isoformat(),
            "current_price": 9.99,
            "recommended_price": 8.99,
            "price_change_amount": -1.00,
            "price_change_percent": -10.01,
            "strategy_type": "penetration_pricing",
            "confidence_score": 0.72,
            "rationale": "Reducing price will increase sales volume. Analysis shows price elasticity is high for this item, with potential to boost customer acquisition.",
            "expected_revenue_change": 2500.00,
            "expected_quantity_change": 15.0,
            "expected_margin_change": -2.3,
            "implementation_status": "pending",
            "reevaluation_date": (datetime.now() + timedelta(days=45)).isoformat(),
        },
        {
            "id": 1003,
            "item_id": 103,
            "item_name": "Enterprise Solution",
            "batch_id": batch_id,
            "recommendation_date": datetime.now().isoformat(),
            "current_price": 199.99,
            "recommended_price": 249.99,
            "price_change_amount": 50.00,
            "price_change_percent": 25.0,
            "strategy_type": "value_based_pricing",
            "confidence_score": 0.91,
            "rationale": "Product delivers significant business value to enterprise customers, with ROI 5x higher than current pricing suggests. Limited price sensitivity at enterprise level.",
            "expected_revenue_change": 12000.00,
            "expected_quantity_change": -5.0,
            "expected_margin_change": 12.5,
            "implementation_status": "pending",
            "reevaluation_date": (datetime.now() + timedelta(days=60)).isoformat(),
        }
    ]
    
    # Simplified report data focusing only on pricing recommendations
    mock_report_data = {
        "task_id": "test-task-123",
        "completed_at": datetime.now().isoformat(),
        "status": "completed",
        "results": {
            # The pricing_recommendations is the most important part for the email
            "pricing_recommendations": pricing_recommendations
        }
    }
    
    # Test email recipients - use your own email for testing
    recipients = ["ncaronow@optonline.net"]  # Replace with your actual email
    
    print(f"Sending pricing report notification with {len(mock_report_data['results']['pricing_recommendations'])} recommendations...")
    result = await knock_client.send_pricing_report_notification(
        report_data=mock_report_data,
        recipients=recipients,
        user_id=1
    )
    
    if result:
        print("✅ Test notification sent successfully!")
        print(f"📧 Email sent to: {', '.join(recipients)}")
        print("📋 Notification contains:")
        print(f"   - Subject: {len(mock_report_data['results']['pricing_recommendations'])} New Price Recommendations Available")
        print("   - Detailed pricing changes with rationale")
        print("   - Links to view the full report")
    else:
        print("❌ Failed to send test notification. Check logs for details.")
    
    return result

if __name__ == "__main__":
    # Run the test notification function
    asyncio.run(test_notification())
