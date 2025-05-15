import os
import sys
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
import models
from auth import get_password_hash

# Create a database connection
SQLALCHEMY_DATABASE_URL = "sqlite:///./adaptiv.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_recent_cogs_data():
    db = next(get_db())
    
    # Find all users
    users = db.query(models.User).all()
    print(f"Found {len(users)} users in the database")
    
    cogs_updated = 0
    
    # Focus on the last 26 weeks (approximately 6 months)
    for user in users:
        # Only update data for test accounts
        if not "test" in user.email.lower():
            print(f"Skipping non-test user: {user.email}")
            continue
            
        print(f"Updating recent COGS data for user: {user.email}")
        
        # Current date (end point)
        end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # Go back to the previous Sunday
        while end_date.weekday() != 6:  # Sunday is 6
            end_date -= timedelta(days=1)
            
        # Start date (26 weeks ago)
        start_date = end_date - timedelta(weeks=26)
        
        # Query existing entries in date range to update
        existing_entries = db.query(models.COGS).filter(
            models.COGS.user_id == user.id,
            models.COGS.week_start_date >= start_date,
            models.COGS.week_end_date <= end_date
        ).all()
        
        # Map entries by week start date for easy lookup
        existing_by_week = {entry.week_start_date.strftime('%Y-%m-%d'): entry for entry in existing_entries}
        
        updated_count = 0
        created_count = 0
        
        # Process each week
        current_week = start_date
        while current_week <= end_date:
            week_start = current_week
            week_end = week_start + timedelta(days=6)
            
            # Generate realistic COGS amount with seasonal variation
            base_amount = 15000 + random.uniform(-500, 500)
            
            # Add seasonal variation
            month = week_end.month
            
            # Higher costs during holiday season (November, December)
            if month == 11 or month == 12:
                base_amount *= 1.4  # 40% increase
            # Higher costs during summer (June, July, August)
            elif month >= 6 and month <= 8:
                base_amount *= 1.2  # 20% increase
            # Slightly lower in slow months (January, February)
            elif month == 1 or month == 2:
                base_amount *= 0.9  # 10% decrease
                
            # Add weekly trend (slight increase over time - business growth)
            # Calculate weeks from start date
            weeks_from_start = (current_week - start_date).days // 7
            growth_factor = 1.0 + (weeks_from_start * 0.005)  # 0.5% growth per week
            
            # Apply growth factor
            base_amount *= growth_factor
            
            # Add random variation
            amount = base_amount * (0.95 + random.uniform(0, 0.1))
            
            # Format date for lookup
            week_start_str = week_start.strftime('%Y-%m-%d')
            
            # Update existing entry or create new one
            if week_start_str in existing_by_week:
                entry = existing_by_week[week_start_str]
                entry.amount = round(amount, 2)
                updated_count += 1
            else:
                entry = models.COGS(
                    user_id=user.id,
                    week_start_date=week_start,
                    week_end_date=week_end,
                    amount=round(amount, 2)
                )
                db.add(entry)
                created_count += 1
                
            # Move to next week
            current_week += timedelta(weeks=1)
        
        # Commit changes
        db.commit()
        
        print(f"User {user.email}: Updated {updated_count} entries, created {created_count} entries")
        cogs_updated += (updated_count + created_count)
    
    print(f"Total COGS entries updated/created: {cogs_updated}")

if __name__ == "__main__":
    seed_recent_cogs_data()
