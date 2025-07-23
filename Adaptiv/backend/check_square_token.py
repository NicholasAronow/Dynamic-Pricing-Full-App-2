#!/usr/bin/env python3
"""
Script to check Square token status for a user
"""

from config.database import SessionLocal
import models
from datetime import datetime, timezone

def check_square_token(user_id: int):
    """Check Square integration token status for a user"""
    db = SessionLocal()
    try:
        integration = db.query(models.POSIntegration).filter(
            models.POSIntegration.user_id == user_id,
            models.POSIntegration.provider == 'square'
        ).first()
        
        if not integration:
            print(f"No Square integration found for user {user_id}")
            return
        
        print(f"Square Integration for User {user_id}:")
        print(f"  Access Token: {'Present' if integration.access_token else 'Missing'}")
        print(f"  Refresh Token: {'Present' if integration.refresh_token else 'Missing'}")
        print(f"  Merchant ID: {integration.merchant_id}")
        print(f"  Expires At: {integration.expires_at}")
        print(f"  Created At: {integration.created_at}")
        print(f"  Updated At: {integration.updated_at}")
        print(f"  Last Sync At: {integration.last_sync_at}")
        
        # Check if token is expired
        if integration.expires_at:
            now = datetime.now(timezone.utc)
            if integration.expires_at < now:
                print(f"  ❌ TOKEN EXPIRED: Expired {integration.expires_at}, Current time: {now}")
            else:
                print(f"  ✅ TOKEN VALID: Expires {integration.expires_at}, Current time: {now}")
        else:
            print(f"  ⚠️  NO EXPIRATION SET: Token may not expire or expiration not tracked")
        
        # Check active status
        is_active = (
            integration.access_token is not None and 
            integration.access_token.strip() != "" and
            (integration.expires_at is None or integration.expires_at > datetime.now(timezone.utc))
        )
        print(f"  Integration Active: {'✅ Yes' if is_active else '❌ No'}")
        
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python3 check_square_token.py <user_id>")
        sys.exit(1)
    
    user_id = int(sys.argv[1])
    check_square_token(user_id)
