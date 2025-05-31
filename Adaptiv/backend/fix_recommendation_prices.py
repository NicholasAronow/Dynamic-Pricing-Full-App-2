from database import SessionLocal
from models import PricingRecommendation, Item
import re

db = SessionLocal()

# Get all pending recommendations
recommendations = db.query(PricingRecommendation).filter(
    PricingRecommendation.implementation_status == 'pending'
).all()

print(f"Found {len(recommendations)} pending recommendations to check")

# Count of fixes made
fixes_count = 0

for rec in recommendations:
    # Get the item name
    item = db.query(Item).filter(Item.id == rec.item_id).first()
    item_name = item.name if item else "Unknown Item"
    
    # Check if current price equals recommended price
    if abs(rec.current_price - rec.recommended_price) < 0.01:
        print(f"\nChecking {item_name} with identical prices: ${rec.current_price:.2f}")
        
        # Extract the recommended price from the rationale using regex
        rationale = rec.rationale or ""
        
        # Pattern to find price mentions like "$4.25 to $4.30" or "from $4.25 to $4.30"
        price_pattern = r'(?:from\s+)?\$([0-9.]+)\s+to\s+\$([0-9.]+)'
        matches = re.findall(price_pattern, rationale)
        
        if matches:
            # Get the last match (most likely to be relevant)
            from_price_str, to_price_str = matches[-1]
            try:
                from_price = float(from_price_str)
                to_price = float(to_price_str)
                
                print(f"  Found price change in rationale: ${from_price:.2f} to ${to_price:.2f}")
                
                # Only update if the current price matches the "from" price
                if abs(from_price - rec.current_price) < 0.10:  # Allow for small rounding differences
                    # Update the recommendation
                    rec.recommended_price = to_price
                    rec.price_change_amount = to_price - rec.current_price
                    rec.price_change_percent = (to_price - rec.current_price) / rec.current_price if rec.current_price > 0 else 0
                    
                    print(f"  ✅ Updated {item_name}: ${rec.current_price:.2f} → ${rec.recommended_price:.2f} ({rec.price_change_percent*100:.1f}%)")
                    fixes_count += 1
                else:
                    print(f"  ⚠️ From price in rationale (${from_price:.2f}) doesn't match current price (${rec.current_price:.2f})")
            except ValueError:
                print(f"  ⚠️ Could not convert prices: {from_price_str}, {to_price_str}")
        else:
            # Try another pattern for percentage mentions
            percent_pattern = r'([0-9.]+)%\s+(?:price\s+)?increase'
            percent_matches = re.findall(percent_pattern, rationale)
            
            if percent_matches:
                try:
                    percentage = float(percent_matches[0])
                    new_price = round(rec.current_price * (1 + percentage/100), 2)
                    
                    print(f"  Found {percentage}% increase in rationale")
                    # Update the recommendation
                    rec.recommended_price = new_price
                    rec.price_change_amount = new_price - rec.current_price
                    rec.price_change_percent = percentage / 100
                    
                    print(f"  ✅ Updated {item_name} using percentage: ${rec.current_price:.2f} → ${rec.recommended_price:.2f} ({percentage}%)")
                    fixes_count += 1
                except ValueError:
                    print(f"  ⚠️ Could not convert percentage: {percent_matches[0]}")
            else:
                print(f"  ⚠️ No price change found in rationale for {item_name}")

# Commit changes to database
if fixes_count > 0:
    db.commit()
    print(f"\nSuccessfully updated {fixes_count} recommendations")
else:
    print("\nNo changes were made")

db.close()
