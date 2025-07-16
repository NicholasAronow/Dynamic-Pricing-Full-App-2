#!/usr/bin/env python3
"""
Test script to verify the background Square sync task is working properly.
"""

import sys
import os
import time

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tasks import sync_square_data_task
from database import get_db
import models

def test_background_sync():
    """Test the background sync task"""
    print("🧪 Testing Background Square Sync Task")
    print("=" * 50)
    
    # Get a test user (you can modify this user ID)
    test_user_id = 1  # Change this to a valid user ID in your system
    
    try:
        # Start the background task
        print(f"🚀 Starting background sync for user {test_user_id}...")
        task = sync_square_data_task.delay(test_user_id, False)
        print(f"📋 Task ID: {task.id}")
        print(f"⏳ Task State: {task.state}")
        
        # Monitor progress for a short time
        max_checks = 12  # 1 minute with 5-second intervals
        checks = 0
        
        while checks < max_checks:
            task_result = task.AsyncResult(task.id)
            print(f"📊 Check {checks + 1}: State = {task_result.state}")
            
            if task_result.state == 'PENDING':
                print("   ⏳ Task is waiting to be processed...")
            elif task_result.state == 'PROGRESS':
                progress = task_result.info.get('progress', 0)
                status = task_result.info.get('status', 'Processing...')
                print(f"   📈 Progress: {progress}% - {status}")
            elif task_result.state == 'SUCCESS':
                result = task_result.result
                print("   ✅ Task completed successfully!")
                print(f"   📦 Items created: {result.get('items_created', 0)}")
                print(f"   🔄 Items updated: {result.get('items_updated', 0)}")
                print(f"   📋 Orders created: {result.get('orders_created', 0)}")
                print(f"   🔄 Orders updated: {result.get('orders_updated', 0)}")
                if result.get('orders_failed', 0) > 0:
                    print(f"   ❌ Orders failed: {result.get('orders_failed', 0)}")
                break
            elif task_result.state == 'FAILURE':
                print(f"   ❌ Task failed: {str(task_result.info)}")
                break
            
            time.sleep(5)
            checks += 1
        
        if checks >= max_checks:
            print(f"⏰ Stopped monitoring after {max_checks * 5} seconds")
            print(f"   Task {task.id} may still be running in the background")
            
    except Exception as e:
        print(f"❌ Error testing background sync: {str(e)}")
        return False
    
    print("\n✅ Background sync test completed!")
    return True

if __name__ == "__main__":
    test_background_sync()
