#!/usr/bin/env python3
"""
Script to mark a user as a beta tester with an active subscription.
This script sets a special marker in the user's stripe_customer_id field
which will be recognized by the get_subscription_status function.
"""

import argparse
from sqlalchemy.orm import Session
from config.database import SessionLocal, engine
import models

# The special marker we'll use for beta testers
BETA_TESTER_MARKER = "BETA_TESTER_SUBSCRIPTION_ACTIVE"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def mark_user_as_beta_tester(email: str):
    """Mark a user as a beta tester with an active subscription."""
    db = next(get_db())
    
    # Find the user by email
    user = db.query(models.User).filter(models.User.email == email).first()
    
    if not user:
        print(f"User with email {email} not found.")
        return False
    
    # Update the user's stripe_customer_id to our special marker
    user.stripe_customer_id = BETA_TESTER_MARKER
    db.commit()
    
    print(f"User {user.email} has been successfully marked as a beta tester with an active subscription.")
    return True

def remove_beta_tester_status(email: str):
    """Remove beta tester status from a user."""
    db = next(get_db())
    
    # Find the user by email
    user = db.query(models.User).filter(models.User.email == email).first()
    
    if not user:
        print(f"User with email {email} not found.")
        return False
    
    # Check if the user has our special marker
    if user.stripe_customer_id == BETA_TESTER_MARKER:
        user.stripe_customer_id = None
        db.commit()
        print(f"Beta tester status removed from user {user.email}.")
        return True
    else:
        print(f"User {user.email} is not currently marked as a beta tester.")
        return False

def list_beta_testers():
    """List all users marked as beta testers."""
    db = next(get_db())
    
    # Find all users with our special marker
    beta_testers = db.query(models.User).filter(models.User.stripe_customer_id == BETA_TESTER_MARKER).all()
    
    if not beta_testers:
        print("No beta testers found.")
        return
    
    print(f"Found {len(beta_testers)} beta testers:")
    for user in beta_testers:
        print(f"- {user.email}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mark or unmark users as beta testers with active subscriptions.")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add beta tester status to a user")
    add_parser.add_argument("email", help="Email of the user to mark as a beta tester")
    
    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove beta tester status from a user")
    remove_parser.add_argument("email", help="Email of the user to remove beta tester status from")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all beta testers")
    
    args = parser.parse_args()
    
    if args.command == "add":
        mark_user_as_beta_tester(args.email)
    elif args.command == "remove":
        remove_beta_tester_status(args.email)
    elif args.command == "list":
        list_beta_testers()
    else:
        parser.print_help()
