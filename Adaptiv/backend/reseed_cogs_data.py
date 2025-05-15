"""
Script to delete all existing COGS data and reseed with values more aligned with recent sales patterns.
This ensures that we have realistic profit margins, including negative values.
"""

import os
import sys
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from database import Base, get_db
import models

def reseed_cogs_data():
    db = next(get_db())
    
    # First, delete all existing COGS data
    deleted_count = db.query(models.COGS).delete()
    db.commit()
    print(f"Deleted {deleted_count} existing COGS entries")
    
    # Find test users
    test_user = db.query(models.User).filter(models.User.email == "testprofessional@test.com").first()
    
    if not test_user:
        print("Test user not found. Exiting.")
        return
    
    print(f"Found test user: {test_user.email} (ID: {test_user.id})")
    
    # Generate weekly COGS data
    cogs_data = []
    
    # Get current date
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # Go back to the previous Sunday
    while end_date.weekday() != 6:  # Sunday is 6
        end_date -= timedelta(days=1)
    
    # Look up recent sales data to calibrate COGS
    # Get the most recent full week of sales
    last_week_end = end_date
    last_week_start = last_week_end - timedelta(days=6)
    
    # Get sales for the last week
    last_week_sales = db.query(func.sum(models.Order.total_amount)).filter(
        models.Order.user_id == test_user.id,
        models.Order.order_date >= last_week_start,
        models.Order.order_date <= last_week_end
    ).scalar() or 0
    
    print(f"Last week sales: ${last_week_sales:.2f}")
    
    # Target ranges for profit margins
    # We want to have some weeks with negative margins
    profit_margin_ranges = [
        (-20, -5),  # Negative profit margin (for some weeks)
        (5, 15),    # Low profit margin
        (15, 25),   # Medium profit margin
        (25, 40)    # High profit margin
    ]
    
    # Generate 51 weeks of historical data
    for i in range(0, 52):  # Including current week
        week_end = end_date - timedelta(weeks=i)
        week_start = week_end - timedelta(days=6)
        
        # Get actual sales data if available, or estimate it
        week_sales = db.query(func.sum(models.Order.total_amount)).filter(
            models.Order.user_id == test_user.id,
            models.Order.order_date >= week_start,
            models.Order.order_date <= week_end
        ).scalar() or 0
        
        if week_sales == 0:
            # If no sales data, estimate based on last known week
            # Higher in holiday season (Nov-Dec), summer (Jun-Aug)
            month = week_end.month
            if month == 11 or month == 12:
                week_sales = last_week_sales * 1.4  # 40% higher in holidays
            elif month >= 6 and month <= 8:
                week_sales = last_week_sales * 1.2  # 20% higher in summer
            elif month == 1 or month == 2:
                week_sales = last_week_sales * 0.9  # 10% lower in slow months
            else:
                week_sales = last_week_sales
            
            # Add some randomness
            week_sales *= (0.9 + random.uniform(0, 0.2))
        
        # Select a profit margin range - vary it to create interesting patterns
        # Make the most recent few weeks more likely to have negative margins
        if i < 3 and random.random() < 0.6:  # 60% chance for recent weeks
            margin_range = profit_margin_ranges[0]  # Negative margin
        elif i < 10 and random.random() < 0.3:  # 30% chance for somewhat recent weeks
            margin_range = profit_margin_ranges[0]  # Negative margin
        else:
            # For other weeks, use a distribution of mostly positive margins
            margin_range = random.choices(
                profit_margin_ranges,
                weights=[0.15, 0.25, 0.35, 0.25],  # Weighted distribution
                k=1
            )[0]
        
        # Calculate COGS based on target profit margin
        target_margin_pct = random.uniform(margin_range[0], margin_range[1])
        if target_margin_pct == 0:  # Avoid division by zero
            target_margin_pct = 0.1
            
        # COGS formula: Revenue * (1 - Margin%)
        cogs_amount = week_sales * (1 - (target_margin_pct / 100))
        
        # Create the COGS entry
        cogs_entry = models.COGS(
            user_id=test_user.id,
            week_start_date=week_start,
            week_end_date=week_end,
            amount=round(cogs_amount, 2)
        )
        cogs_data.append(cogs_entry)
        
        print(f"Week {week_start.date()} to {week_end.date()}: Sales=${week_sales:.2f}, COGS=${cogs_amount:.2f}, Target Margin={target_margin_pct:.1f}%")
    
    # Add all entries to database
    db.add_all(cogs_data)
    db.commit()
    
    print(f"Added {len(cogs_data)} COGS entries for user {test_user.email}")

if __name__ == "__main__":
    reseed_cogs_data()
