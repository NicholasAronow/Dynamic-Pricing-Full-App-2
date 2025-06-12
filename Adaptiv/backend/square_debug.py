"""
Square API Diagnostic Tool

This script helps diagnose issues with Square catalog and IDs.
"""
import os
import sys
import requests
import json
from datetime import datetime

# Import database and models from your project
from database import get_db_session
import models

# Square environment and credentials
SQUARE_ENV = os.getenv("SQUARE_ENV", "sandbox")

# Square API URLs
SQUARE_API_BASE = "https://connect.squareupsandbox.com" if SQUARE_ENV == "sandbox" else "https://connect.squareup.com"

# Get database session
db = get_db_session()

def get_square_token():
    """Get a Square access token from the database"""
    # Get the first integration record from the database
    integration = db.query(models.Integration).filter(models.Integration.provider == "square").first()
    
    if not integration:
        print("No Square integration found in the database")
        return None
    
    # Check if token is expired
    if integration.expires_at and integration.expires_at < datetime.now():
        print(f"Square token is expired. Expired at: {integration.expires_at}")
        return None
    
    print(f"Found Square integration for user ID: {integration.user_id}")
    return integration.access_token

def get_catalog():
    """Get the complete catalog from Square"""
    token = get_square_token()
    if not token:
        return None
        
    catalog_url = f"{SQUARE_API_BASE}/v2/catalog/list?types=ITEM"
    
    response = requests.get(
        catalog_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )
    
    if response.status_code != 200:
        print(f"Error getting catalog: {response.status_code}")
        print(response.text)
        return None
        
    return response.json()

def test_item_existence(item_id):
    """Test if a specific catalog item exists"""
    token = get_square_token()
    if not token:
        return False
        
    item_url = f"{SQUARE_API_BASE}/v2/catalog/object/{item_id}"
    
    response = requests.get(
        item_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )
    
    if response.status_code != 200:
        print(f"Item {item_id} not found: {response.status_code}")
        print(response.text)
        return False
        
    return True

def get_and_display_catalog():
    """Get catalog and display items with IDs"""
    catalog = get_catalog()
    if not catalog:
        return
        
    items = catalog.get("objects", [])
    print(f"Found {len(items)} items in catalog")
    
    for item in items:
        if item.get("type") != "ITEM":
            continue
            
        item_id = item.get("id")
        item_data = item.get("item_data", {})
        name = item_data.get("name", "Unknown")
        print(f"\nItem: {name}")
        print(f"  ID: {item_id}")
        
        # Get variations
        variations = item_data.get("variations", [])
        print(f"  Variations: {len(variations)}")
        
        for i, variation in enumerate(variations):
            variation_id = variation.get("id")
            variation_data = variation.get("item_variation_data", {})
            variation_name = variation_data.get("name", "Default")
            price_money = variation_data.get("price_money", {})
            price = price_money.get("amount", 0) / 100.0 if price_money else 0
            
            print(f"    {i+1}. {variation_name}")
            print(f"       Variation ID: {variation_id}")
            print(f"       Price: ${price:.2f}")
            
            # Verify this ID works
            exists = test_item_existence(variation_id)
            print(f"       ✅ ID valid in Square API: {exists}")

def test_specific_ids():
    """Test specific IDs that are failing"""
    problem_id = "GJEW7DFZZNSJ6VWLTGN22VAN"
    exists = test_item_existence(problem_id)
    print(f"\nTesting problematic ID: {problem_id}")
    print(f"Exists in Square? {exists}")

if __name__ == "__main__":
    print("Square Catalog Diagnostic")
    print("-----------------------")
    get_and_display_catalog()
    print("\n\nTesting Specific IDs")
    print("-----------------------")
    test_specific_ids()
