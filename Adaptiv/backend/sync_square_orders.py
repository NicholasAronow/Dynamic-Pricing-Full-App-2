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
from config.database import get_db
import models
from tasks import sync_square_data_task


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
        pos_connected = "Yes" if user.pos_connected else "No"
        print(f"{user.id:<5} {user.email:<30} {pos_connected:<12}")


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
        
        # Use background task for sync to prevent RAM issues
        print(f"🚀 Starting Square sync in background for user {user_id}...")
        
        # Start the background task
        task = sync_square_data_task.delay(user_id, force_sync)
        print(f"📋 Task ID: {task.id}")
        print(f"⏳ Monitoring progress...")
        
        # Poll for completion
        import time
        max_wait_time = 600  # 10 minutes
        start_time = time.time()
        last_progress = -1
        
        while time.time() - start_time < max_wait_time:
            # task is already an AsyncResult object, no need to call task.AsyncResult()
            if task.state == 'PENDING':
                print("⏳ Task is waiting to be processed...")
            elif task.state == 'PROGRESS':
                progress = task.info.get('progress', 0)
                status = task.info.get('status', 'Processing...')
                if progress != last_progress:
                    print(f"📊 Progress: {progress}% - {status}")
                    last_progress = progress
            elif task.state == 'SUCCESS':
                result = task.result
                print(f"✅ Sync completed successfully!")
                print(f"   Items created: {result.get('items_created', 0)}")
                print(f"   Items updated: {result.get('items_updated', 0)}")
                print(f"   Orders created: {result.get('orders_created', 0)}")
                print(f"   Orders updated: {result.get('orders_updated', 0)}")
                if result.get('orders_failed', 0) > 0:
                    print(f"   Orders failed: {result.get('orders_failed', 0)}")
                print(f"   Locations processed: {result.get('locations_processed', 0)}")
                return True
            elif task.state == 'FAILURE':
                print(f"❌ Sync failed: {str(task.info)}")
                return False
            
            time.sleep(5)  # Wait 5 seconds before checking again
        
        print(f"⏰ Sync task timed out after {max_wait_time} seconds")
        print(f"   Task ID {task.id} may still be running in the background")
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
