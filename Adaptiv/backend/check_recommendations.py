from database import SessionLocal
from models import PricingRecommendation, Item
from sqlalchemy import desc

db = SessionLocal()

# Get recent recommendations
recommendations = db.query(PricingRecommendation).order_by(desc(PricingRecommendation.recommendation_date)).limit(5).all()

print("Recent pricing recommendations:")
print("-" * 80)
for rec in recommendations:
    item = db.query(Item).filter(Item.id == rec.item_id).first()
    item_name = item.name if item else "Unknown Item"
    print(f"ID: {rec.id}, Item: {item_name} (ID: {rec.item_id})")
    print(f"Current Price: ${rec.current_price:.2f}, Recommended Price: ${rec.recommended_price:.2f}")
    print(f"Change: ${rec.price_change_amount:.2f} ({rec.price_change_percent:.1f}%)")
    print(f"Status: {rec.implementation_status}")
    print(f"Date: {rec.recommendation_date}")
    print("-" * 80)

db.close()
