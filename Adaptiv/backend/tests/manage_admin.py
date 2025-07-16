#!/usr/bin/env python3
"""
Admin Management Script for Dynamic Pricing App

Usage:
    python3 manage_admin.py --grant --user-id 123
    python3 manage_admin.py --grant --email user@example.com
    python3 manage_admin.py --revoke --user-id 123
    python3 manage_admin.py --revoke --email user@example.com
    python3 manage_admin.py --list
    python3 manage_admin.py --status --user-id 123
"""

import argparse
import sys
from sqlalchemy import text
from database import engine
from sqlalchemy.orm import sessionmaker

def create_session():
    """Create a database session"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def find_user(session, user_id=None, email=None):
    """Find a user by ID or email"""
    if user_id:
        result = session.execute(
            text('SELECT id, email, is_admin FROM users WHERE id = :user_id;'), 
            {'user_id': user_id}
        ).fetchone()
    elif email:
        result = session.execute(
            text('SELECT id, email, is_admin FROM users WHERE email = :email;'), 
            {'email': email}
        ).fetchone()
    else:
        return None
    
    return result

def grant_admin(session, user_id=None, email=None):
    """Grant admin permissions to a user"""
    user = find_user(session, user_id, email)
    
    if not user:
        print(f"❌ User not found: {user_id or email}")
        return False
    
    user_id, user_email, is_admin = user
    
    if is_admin:
        print(f"ℹ️  User {user_email} (ID: {user_id}) is already an admin")
        return True
    
    try:
        session.execute(
            text('UPDATE users SET is_admin = TRUE WHERE id = :user_id;'), 
            {'user_id': user_id}
        )
        session.commit()
        print(f"✅ Granted admin permissions to {user_email} (ID: {user_id})")
        return True
    except Exception as e:
        print(f"❌ Error granting admin permissions: {e}")
        session.rollback()
        return False

def revoke_admin(session, user_id=None, email=None):
    """Revoke admin permissions from a user"""
    user = find_user(session, user_id, email)
    
    if not user:
        print(f"❌ User not found: {user_id or email}")
        return False
    
    user_id, user_email, is_admin = user
    
    if not is_admin:
        print(f"ℹ️  User {user_email} (ID: {user_id}) is not an admin")
        return True
    
    # Check if this is the last admin
    admin_count = session.execute(
        text('SELECT COUNT(*) FROM users WHERE is_admin = TRUE;')
    ).scalar()
    
    if admin_count <= 1:
        print(f"⚠️  Cannot revoke admin permissions from {user_email} - they are the last admin!")
        print("   Please grant admin permissions to another user first.")
        return False
    
    try:
        session.execute(
            text('UPDATE users SET is_admin = FALSE WHERE id = :user_id;'), 
            {'user_id': user_id}
        )
        session.commit()
        print(f"✅ Revoked admin permissions from {user_email} (ID: {user_id})")
        return True
    except Exception as e:
        print(f"❌ Error revoking admin permissions: {e}")
        session.rollback()
        return False

def list_admins(session):
    """List all admin users"""
    try:
        results = session.execute(
            text('SELECT id, email, created_at FROM users WHERE is_admin = TRUE ORDER BY created_at;')
        ).fetchall()
        
        if not results:
            print("No admin users found")
            return
        
        print(f"\n📋 Admin Users ({len(results)} total):")
        print("-" * 60)
        for user_id, email, created_at in results:
            print(f"ID: {user_id:4} | Email: {email:30} | Created: {created_at}")
        print("-" * 60)
        
    except Exception as e:
        print(f"❌ Error listing admins: {e}")

def check_status(session, user_id=None, email=None):
    """Check admin status of a user"""
    user = find_user(session, user_id, email)
    
    if not user:
        print(f"❌ User not found: {user_id or email}")
        return
    
    user_id, user_email, is_admin = user
    status = "Admin" if is_admin else "Regular User"
    icon = "👑" if is_admin else "👤"
    
    print(f"{icon} {user_email} (ID: {user_id}) - Status: {status}")

def main():
    parser = argparse.ArgumentParser(
        description="Manage admin permissions for Dynamic Pricing App users",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Grant admin to user ID 123:
    python3 manage_admin.py --grant --user-id 123
    
  Grant admin to user by email:
    python3 manage_admin.py --grant --email user@example.com
    
  Revoke admin from user:
    python3 manage_admin.py --revoke --user-id 123
    
  List all admins:
    python3 manage_admin.py --list
    
  Check user status:
    python3 manage_admin.py --status --email user@example.com
        """
    )
    
    # Action arguments
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument('--grant', action='store_true', help='Grant admin permissions')
    action_group.add_argument('--revoke', action='store_true', help='Revoke admin permissions')
    action_group.add_argument('--list', action='store_true', help='List all admin users')
    action_group.add_argument('--status', action='store_true', help='Check admin status of a user')
    
    # User identification arguments
    user_group = parser.add_mutually_exclusive_group()
    user_group.add_argument('--user-id', type=int, help='User ID')
    user_group.add_argument('--email', type=str, help='User email address')
    
    args = parser.parse_args()
    
    # Validate arguments
    if (args.grant or args.revoke or args.status) and not (args.user_id or args.email):
        parser.error("--grant, --revoke, and --status require either --user-id or --email")
    
    # Create database session
    session = create_session()
    
    try:
        if args.grant:
            success = grant_admin(session, args.user_id, args.email)
            sys.exit(0 if success else 1)
            
        elif args.revoke:
            success = revoke_admin(session, args.user_id, args.email)
            sys.exit(0 if success else 1)
            
        elif args.list:
            list_admins(session)
            
        elif args.status:
            check_status(session, args.user_id, args.email)
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
        
    finally:
        session.close()

if __name__ == "__main__":
    main()
