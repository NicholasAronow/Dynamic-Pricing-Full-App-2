#!/usr/bin/env python3
from sqlalchemy.orm import sessionmaker
import models
from database import engine

# Create a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def update_intuit_priority():
    """Update priority of all 'Connect Intuit' action items to high"""
    try:
        # Find all action items with title "Connect Intuit"
        intuit_items = db.query(models.ActionItem).filter(models.ActionItem.title == "Connect Intuit").all()
        
        count = 0
        for item in intuit_items:
            if item.priority != "high":
                item.priority = "high"
                count += 1
                print(f"Updated action item ID {item.id} for user {item.user_id}")
        
        if count > 0:
            db.commit()
            print(f"Successfully updated {count} 'Connect Intuit' action items to high priority")
        else:
            print("No items needed updating")
            
    except Exception as e:
        print(f"Error updating action items: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_intuit_priority()
