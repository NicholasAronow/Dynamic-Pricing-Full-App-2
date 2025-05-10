#!/usr/bin/env python3
"""
Script to test the product performance endpoint directly.
"""
import requests
import json

def main():
    # Test the product performance endpoint
    url = "http://localhost:8000/api/dashboard/product-performance"
    print(f"Testing endpoint: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nProduct Performance Summary:")
            print(f"Total products returned: {len(data)}")
            
            # Print first 5 items with their revenue data
            print("\nFirst 5 products:")
            for i, item in enumerate(data[:5]):
                print(f"{i+1}. {item.get('name')} - Revenue: ${item.get('revenue', 0):.2f}, Margin: {item.get('margin', 0):.2f}%, Quantity Sold: {item.get('quantitySold', 0)}")
            
            # Find the highest revenue item
            if data:
                highest_revenue_item = max(data, key=lambda x: x.get('revenue', 0))
                print(f"\nHighest revenue item: {highest_revenue_item.get('name')} - ${highest_revenue_item.get('revenue', 0):.2f}")
            
            # Print a few full items for debugging
            print("\nDetailed view of first 2 items:")
            for item in data[:2]:
                print(json.dumps(item, indent=2))
        else:
            print(f"Error response: {response.text}")
    except Exception as e:
        print(f"Exception occurred: {str(e)}")

if __name__ == "__main__":
    main()
