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

def seed_cogs_data():
    db = next(get_db())
    
    # Find test users
    users = db.query(models.User).all()
    print(f"Found {len(users)} users in the database")
    
    seeded_count = 0
    
    for user in users:
        # Check if we already have COGS data for this user
        existing_count = db.query(models.COGS).filter(models.COGS.user_id == user.id).count()
        
        if existing_count > 0:
            print(f"User {user.email} already has {existing_count} COGS entries. Skipping.")
            continue
        
        # Generate 51 weeks of historical data
        cogs_data = []
        
        # Generate data with focus on test accounts
        is_test_account = "test" in user.email.lower()
        
        # Current week (don't seed this to allow the user to enter it themselves)
        end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # Go back to the previous Sunday
        while end_date.weekday() != 6:  # Sunday is 6
            end_date -= timedelta(days=1)
        
        # Generate 51 weeks of historical data
        for i in range(1, 52):  # Starting from previous week (i=1)
            week_end = end_date - timedelta(weeks=i)
            week_start = week_end - timedelta(days=6)
            
            # Base COGS amount differs by user type
            if is_test_account:
                base_amount = 15000 + random.uniform(-500, 500)
            else:
                # Regular accounts get random values
                base_amount = 5000 + random.uniform(-1000, 3000)
            
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
            
            # Add random variation
            amount = base_amount * (0.95 + random.uniform(0, 0.1))
            
            cogs_entry = models.COGS(
                user_id=user.id,
                week_start_date=week_start,
                week_end_date=week_end,
                amount=round(amount, 2)
            )
            cogs_data.append(cogs_entry)
        
        # Add all entries to database
        db.add_all(cogs_data)
        db.commit()
        
        seeded_count += 1
        print(f"Added {len(cogs_data)} COGS entries for user {user.email}")
    
    print(f"Seeded COGS data for {seeded_count} users")

if __name__ == "__main__":
    seed_cogs_data()
