from database import SessionLocal
from models import PricingRecommendation, Item, User
from sqlalchemy import desc
from datetime import datetime, timedelta
import random

db = SessionLocal()

# Get first user
user = db.query(User).first()
if not user:
    print("No users found in database!")
    exit(1)

user_id = user.id
print(f"Generating recommendations for user ID: {user_id}")

# Get items
items = db.query(Item).filter(Item.user_id == user_id).all()
if not items:
    print("No items found for this user!")
    exit(1)

print(f"Found {len(items)} items")

# Generate new recommendations
for item in items:
    # Check if we already have a pending recommendation for this item
    existing = db.query(PricingRecommendation).filter(
        PricingRecommendation.item_id == item.id,
        PricingRecommendation.implementation_status == 'pending'
    ).first()
    
    if existing:
        # Update existing recommendation with a new price
        current_price = item.current_price
        
        # Generate a 3-10% price change
        change_percent = random.uniform(3, 10) * (-1 if random.random() < 0.4 else 1) / 100
        new_price = round(current_price * (1 + change_percent), 2)
        
        existing.recommended_price = new_price
        existing.price_change_amount = new_price - current_price
        existing.price_change_percent = change_percent
        
        print(f"Updated recommendation for {item.name}: ${current_price:.2f} -> ${new_price:.2f} ({change_percent*100:.1f}%)")
    else:
        # Create a new recommendation
        current_price = item.current_price
        
        # Generate a 3-10% price change
        change_percent = random.uniform(3, 10) * (-1 if random.random() < 0.4 else 1) / 100
        new_price = round(current_price * (1 + change_percent), 2)
        
        # Create random confidences between 0.7 and 0.95
        confidence = random.uniform(0.7, 0.95)
        
        # Generate recommendations from past 7 days
        days_ago = random.randint(0, 6)
        rec_date = datetime.utcnow() - timedelta(days=days_ago)
        
        new_rec = PricingRecommendation(
            user_id=user_id,
            item_id=item.id,
            recommendation_date=rec_date,
            current_price=current_price,
            recommended_price=new_price,
            price_change_amount=new_price - current_price,
            price_change_percent=change_percent,
            strategy_type="competitive_pricing",
            confidence_score=confidence,
            rationale="Test recommendation with price variation to demonstrate the accept/reject functionality.",
            expected_revenue_change=change_percent * 2 if change_percent < 0 else change_percent * 0.5,
            expected_quantity_change=change_percent * -3 if change_percent > 0 else change_percent * -2,
            expected_margin_change=change_percent,
            implementation_status="pending",
            reevaluation_date=datetime.utcnow() + timedelta(days=30)
        )
        
        db.add(new_rec)
        print(f"Created recommendation for {item.name}: ${current_price:.2f} -> ${new_price:.2f} ({change_percent*100:.1f}%)")

# Commit changes
db.commit()
db.close()

print("Done! New recommendations created with price variations.")
