from database import get_db
from models import PricingRecommendation, Item
import re

# Get database session
db = next(get_db())

# Get most recent pending recommendations
recommendations = db.query(PricingRecommendation).filter(
    PricingRecommendation.implementation_status == 'pending'
).order_by(PricingRecommendation.recommendation_date.desc()).limit(10).all()

print("\n===== CHECKING PRICE RECOMMENDATIONS DATA CONSISTENCY =====\n")

# Check each recommendation for consistency issues
for rec in recommendations:
    # Get item name
    item = db.query(Item).filter(Item.id == rec.item_id).first()
    item_name = item.name if item else f"Item #{rec.item_id}"
    
    # Examine data integrity
    print(f"\n--- {item_name} ---")
    print(f"Current Price: ${rec.current_price:.2f}")
    print(f"Recommended Price: ${rec.recommended_price:.2f}")
    print(f"Stored Price Change: ${rec.price_change_amount:.2f} ({rec.price_change_percent*100:.2f}%)")
    
    # Calculate expected values
    expected_amount = rec.recommended_price - rec.current_price
    expected_percent = (expected_amount / rec.current_price) * 100 if rec.current_price > 0 else 0
    
    # Check for inconsistencies
    amount_match = abs(expected_amount - rec.price_change_amount) < 0.01
    percent_match = abs(expected_percent - rec.price_change_percent*100) < 0.1
    
    print(f"Expected Change: ${expected_amount:.2f} ({expected_percent:.2f}%)")
    print(f"Amount Match: {'✓' if amount_match else '✗'}")
    print(f"Percent Match: {'✓' if percent_match else '✗'}")
    
    # Check rationale for price mention
    print("\nRationale Excerpt:")
    print(rec.rationale[:150] + "..." if len(rec.rationale) > 150 else rec.rationale)
    
    # Look for price mentions in rationale
    price_pattern = r'from \$(\d+\.\d+) to \$(\d+\.\d+)'
    rationale_prices = re.search(price_pattern, rec.rationale)
    
    if rationale_prices:
        rationale_current = float(rationale_prices.group(1))
        rationale_recommended = float(rationale_prices.group(2))
        print(f"\nPrices mentioned in rationale: ${rationale_current:.2f} → ${rationale_recommended:.2f}")
        
        # Check for mismatch between rationale and stored data
        if abs(rationale_current - rec.current_price) > 0.01 or abs(rationale_recommended - rec.recommended_price) > 0.01:
            print("⚠️ MISMATCH: Prices in rationale don't match stored prices!")
    else:
        print("\nNo specific prices mentioned in rationale in the expected format.")

print("\n===== ANALYSIS COMPLETE =====\n")
