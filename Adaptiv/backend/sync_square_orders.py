#!/usr/bin/env python3
"""
Square Orders Sync Script

This script allows you to sync Square orders for a specific user ID from the command line.
It replicates the functionality of the "re-sync" button in the PriceRecommendations component.

Usage:
    python3 sync_square_orders.py --user-id <USER_ID> [--force]
    python3 sync_square_orders.py --email <EMAIL> [--force]
    python3 sync_square_orders.py --list-users
    python3 sync_square_orders.py --help

Examples:
    python3 sync_square_orders.py --user-id 123
    python3 sync_square_orders.py --email user@example.com --force
    python3 sync_square_orders.py --list-users
"""

import argparse
import asyncio
import sys
import os
from typing import Optional

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database import get_db
import models
from square_integration import sync_initial_data


def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    """Get user by ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Get user by email"""
    return db.query(models.User).filter(models.User.email == email).first()


def list_users_with_square_integration(db: Session):
    """List all users who have Square integration set up"""
    users_with_square = db.query(models.User).join(
        models.POSIntegration, models.User.id == models.POSIntegration.user_id
    ).filter(
        models.POSIntegration.provider == "square"
    ).all()
    
    if not users_with_square:
        print("No users found with active Square integration.")
        return
    
    print(f"Found {len(users_with_square)} users with Square integration:")
    print("-" * 80)
    print(f"{'ID':<5} {'Email':<30} {'Business Name':<25} {'POS Connected':<12}")
    print("-" * 80)
    
    for user in users_with_square:
        business_name = user.business_name or "N/A"
        pos_connected = "Yes" if user.pos_connected else "No"
        print(f"{user.id:<5} {user.email:<30} {business_name:<25} {pos_connected:<12}")


async def sync_user_orders(user_id: int, force_sync: bool = False):
    """Sync Square orders for a specific user"""
    db = next(get_db())
    
    try:
        # Verify user exists
        user = get_user_by_id(db, user_id)
        if not user:
            print(f"❌ Error: User with ID {user_id} not found.")
            return False
        
        # Check if user has Square integration
        integration = db.query(models.POSIntegration).filter(
            models.POSIntegration.user_id == user_id,
            models.POSIntegration.provider == "square"
        ).first()
        
        if not integration:
            print(f"❌ Error: User {user.email} (ID: {user_id}) does not have an active Square integration.")
            return False
        
        print(f"🔄 Starting Square sync for user: {user.email} (ID: {user_id})")
        if force_sync:
            print("   Force sync enabled - will re-sync all data")
        
        # Call the sync function
        result = await sync_initial_data(user_id, db, force_sync=force_sync)
        
        if result.get("success", False):
            print("✅ Square sync completed successfully!")
            
            # Display sync results
            if "items_created" in result:
                print(f"   📦 Items created: {result['items_created']}")
            if "items_updated" in result:
                print(f"   🔄 Items updated: {result['items_updated']}")
            if "orders_synced" in result:
                print(f"   📋 Orders synced: {result['orders_synced']}")
            if "total_orders" in result:
                print(f"   📊 Total orders: {result['total_orders']}")
            if "message" in result:
                print(f"   💬 Message: {result['message']}")
                
            return True
        else:
            error_msg = result.get("error", "Unknown error occurred")
            print(f"❌ Square sync failed: {error_msg}")
            return False
            
    except Exception as e:
        print(f"❌ Error during sync: {str(e)}")
        return False
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Sync Square orders for a specific user",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --user-id 123
  %(prog)s --email user@example.com --force
  %(prog)s --list-users
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--user-id", type=int, help="User ID to sync orders for")
    group.add_argument("--email", type=str, help="User email to sync orders for")
    group.add_argument("--list-users", action="store_true", help="List all users with Square integration")
    
    parser.add_argument("--force", action="store_true", help="Force re-sync all data (default: incremental sync)")
    
    args = parser.parse_args()
    
    if args.list_users:
        db = next(get_db())
        try:
            list_users_with_square_integration(db)
        finally:
            db.close()
        return
    
    # Determine user ID
    user_id = args.user_id
    if args.email:
        db = next(get_db())
        try:
            user = get_user_by_email(db, args.email)
            if not user:
                print(f"❌ Error: User with email '{args.email}' not found.")
                sys.exit(1)
            user_id = user.id
            print(f"📧 Found user: {user.email} (ID: {user_id})")
        finally:
            db.close()
    
    # Run the sync
    success = asyncio.run(sync_user_orders(user_id, force_sync=args.force))
    
    if not success:
        sys.exit(1)
    
    print("🎉 Sync completed!")


if __name__ == "__main__":
    main()
