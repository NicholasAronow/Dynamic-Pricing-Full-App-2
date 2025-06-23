#!/usr/bin/env python3
"""
User Data Cleanup Script

This script removes all data associated with a specific user ID from the database.
It handles the deletion in the correct order to avoid foreign key constraint violations.

Usage:
    python cleanup_user_data.py <user_id>
    
    Optional flags:
    --dry-run: Show what would be deleted without actually deleting
    --all-test-users: Delete data for all users with test emails (@example.com, @test.com, etc.)
"""

import sys
import os
import logging
import argparse
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("cleanup_user_data")

# Add the current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import database models
from database import SessionLocal
import models
from sqlalchemy import inspect, text, MetaData
from sqlalchemy.orm import Session

def get_user_by_id(db: Session, user_id: int) -> Dict[str, Any]:
    """Get user details by ID"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    return {"id": user.id, "email": user.email}

def get_all_test_users(db: Session) -> List[Dict[str, Any]]:
    """Get all users with test email addresses"""
    test_domains = ['@example.com', '@test.com', '@testing.com', '@demo.com']
    users = []
    
    for domain in test_domains:
        domain_users = db.query(models.User).filter(models.User.email.like(f'%{domain}')).all()
        users.extend([{"id": user.id, "email": user.email} for user in domain_users])
    
    return users

def delete_user_data(db: Session, user_id: int, dry_run: bool = False) -> Dict[str, Any]:
    """Delete all data associated with a user ID"""
    
    user = get_user_by_id(db, user_id)
    if not user:
        logger.error(f"User with ID {user_id} not found")
        return {"success": False, "message": f"User with ID {user_id} not found"}
    
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Cleaning up data for user {user_id} ({user['email']})")
    
    deletion_stats = {}
    
    # Define the tables and their foreign key relationships to the user
    # The order matters to avoid foreign key constraint violations
    # This assumes knowledge of your schema - adjust as needed
    tables_to_clean = [
        # Start with the most dependent tables first
        {"table": models.PricingRecommendation, "user_field": "user_id"},
        {"table": models.AgentMemory, "user_field": "user_id"},
        {"table": models.CompetitorPriceHistory, "user_field": "user_id"},
        # Add OrderItem before Order
        {"table": models.OrderItem, "user_field": None, "custom_filter": lambda q, user_id: q.filter(models.OrderItem.order_id.in_(db.query(models.Order.id).filter(models.Order.user_id == user_id)))},
        {"table": models.Order, "user_field": "user_id"},
        {"table": models.Item, "user_field": "user_id"},
        {"table": models.PriceHistory, "user_field": "user_id"},
        {"table": models.BusinessProfile, "user_field": "user_id"},
        {"table": models.Recipe, "user_field": "user_id"},
        {"table": models.Ingredient, "user_field": "user_id"},
        {"table": models.COGS, "user_field": "user_id"},
        {"table": models.Employee, "user_field": "user_id"},
        {"table": models.FixedCost, "user_field": "user_id"},
        # We are using Competitor Report in Competitors
        {"table": models.CompetitorReport, "user_field": "user_id"},
        # Handle data collection snapshots before deleting the user
        {"table": models.DataCollectionSnapshot, "user_field": "user_id"},
        # Add POS integration
        {"table": models.POSIntegration, "user_field": "user_id"},
        {"table": models.User, "user_field": "id"},
        # Add other tables that have user references
    ]
    
    # Delete data from each table
    for table_info in tables_to_clean:
        table = table_info["table"]
        user_field = table_info["user_field"]
        custom_filter = table_info.get("custom_filter")
        
        table_name = table.__tablename__
        try:
            if user_field:
                query = db.query(table).filter(getattr(table, user_field) == user_id)
            else:
                # Use custom filter for tables without direct user_id relationship
                query = custom_filter(db.query(table), user_id)
            
            count = query.count()
            
            if count > 0:
                logger.info(f"{'[DRY RUN] ' if dry_run else ''}Deleting {count} records from {table_name}")
                deletion_stats[table_name] = count
                
                if not dry_run:
                    query.delete(synchronize_session=False)
                    db.commit()  # Commit after each successful deletion
            
        except Exception as e:
            if not dry_run:
                db.rollback()  # Rollback transaction on error
            logger.error(f"Error deleting from {table_name}: {str(e)}")
    
    # Optionally delete the user itself
    try:
        if not dry_run:
            # Uncomment this if you want to delete the user record as well
            # db.query(models.User).filter(models.User.id == user_id).delete(synchronize_session=False)
            # deletion_stats["users"] = 1
            
            # Commit all changes
            db.commit()
            logger.info(f"Successfully cleaned up data for user {user_id}")
        else:
            logger.info(f"[DRY RUN] Would delete user {user_id} and related data")
            db.rollback()  # Roll back any changes in dry run mode
    except Exception as e:
        db.rollback()
        logger.error(f"Error committing changes: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}", "stats": deletion_stats}
    
    return {
        "success": True, 
        "message": f"Successfully cleaned up data for user {user_id}" if not dry_run else f"Dry run completed for user {user_id}",
        "stats": deletion_stats,
        "user": user
    }

def main():
    """Main function to run the cleanup script"""
    
    parser = argparse.ArgumentParser(description="Delete all data for a specific user ID")
    parser.add_argument("user_id", type=int, nargs="?", help="User ID to delete data for")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    parser.add_argument("--all-test-users", action="store_true", help="Delete data for all test users")
    
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        if args.all_test_users:
            # Delete data for all test users
            test_users = get_all_test_users(db)
            logger.info(f"Found {len(test_users)} test users")
            
            for user in test_users:
                result = delete_user_data(db, user["id"], args.dry_run)
                if not result["success"]:
                    logger.error(f"Failed to clean up user {user['id']}: {result['message']}")
        elif args.user_id:
            # Delete data for a specific user
            result = delete_user_data(db, args.user_id, args.dry_run)
            if not result["success"]:
                logger.error(f"Failed to clean up user {args.user_id}: {result['message']}")
        else:
            logger.error("No user ID provided. Use --help for usage information.")
            sys.exit(1)
            
    finally:
        db.close()

if __name__ == "__main__":
    main()
