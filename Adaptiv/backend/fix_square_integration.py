"""
Fix Square Integration Script

This script will repair or create a Square integration record with the provided credentials.
Run this script when you need to manually fix a broken integration.
"""

import os
import sys
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our modules
from database import SessionLocal
import models

def fix_integration(user_id: int, access_token: str = None, refresh_token: str = None):
    """
    Fix or create a Square integration for the specified user.
    
    Args:
        user_id: The ID of the user to fix the integration for
        access_token: Square access token (if None, will use the one from .env)
        refresh_token: Square refresh token (optional)
    """
    # If no access token provided, use the one from .env
    if not access_token:
        from dotenv import load_dotenv
        load_dotenv()
        access_token = os.getenv("SQUARE_ACCESS_TOKEN")
        if not access_token:
            logger.error("No access token provided and SQUARE_ACCESS_TOKEN not found in .env")
            return False

    # Create a database session
    db = SessionLocal()
    try:
        # Check if user exists
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            logger.error(f"User with ID {user_id} not found")
            return False
            
        # Check if integration already exists
        integration = db.query(models.POSIntegration).filter(
            models.POSIntegration.user_id == user_id,
            models.POSIntegration.provider == "square"
        ).first()
        
        if integration:
            logger.info(f"Fixing existing Square integration for user {user_id}")
            # Update the integration with the new token
            integration.access_token = access_token
            integration.refresh_token = refresh_token
            integration.updated_at = datetime.now()
            
            # Set expires_at to 30 days in the future if using sandbox token
            if os.getenv("SQUARE_ENV") == "sandbox":
                integration.expires_at = datetime.now() + timedelta(days=30)
                
            # Flush to see if changes will be saved
            db.flush()
            logger.info(f"Updated integration - access_token present: {bool(integration.access_token)}")
            
            # Commit changes
            db.commit()
            
            # Double check after commit
            db.refresh(integration)
            logger.info(f"After commit - Integration ID: {integration.id}, access_token present: {bool(integration.access_token)}")
            return True
        else:
            logger.info(f"Creating new Square integration for user {user_id}")
            # Create a new integration
            new_integration = models.POSIntegration(
                user_id=user_id,
                provider="square",
                access_token=access_token,
                refresh_token=refresh_token,
                merchant_id="sandbox",  # Placeholder for sandbox
                token_type="bearer"
            )
            
            # Set expires_at to 30 days in the future if using sandbox token
            if os.getenv("SQUARE_ENV") == "sandbox":
                new_integration.expires_at = datetime.now() + timedelta(days=30)
                
            # Add to database
            db.add(new_integration)
            
            # Flush to see if changes will be saved
            db.flush()
            logger.info(f"New integration created - ID: {new_integration.id}, access_token present: {bool(new_integration.access_token)}")
            
            # Commit changes
            db.commit()
            
            # Double check after commit
            db.refresh(new_integration)
            logger.info(f"After commit - Integration ID: {new_integration.id}, access_token present: {bool(new_integration.access_token)}")
            return True
    except Exception as e:
        logger.exception(f"Error fixing Square integration: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    # Check if user_id is provided as command line argument
    if len(sys.argv) < 2:
        print("Usage: python fix_square_integration.py USER_ID [ACCESS_TOKEN] [REFRESH_TOKEN]")
        sys.exit(1)
        
    # Get user_id from command line argument
    try:
        user_id = int(sys.argv[1])
    except ValueError:
        print(f"Invalid user ID: {sys.argv[1]}")
        sys.exit(1)
        
    # Get access_token and refresh_token if provided
    access_token = sys.argv[2] if len(sys.argv) > 2 else None
    refresh_token = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Fix integration
    success = fix_integration(user_id, access_token, refresh_token)
    
    if success:
        print(f"✅ Square integration for user {user_id} has been fixed")
    else:
        print(f"❌ Failed to fix Square integration for user {user_id}")
        sys.exit(1)
