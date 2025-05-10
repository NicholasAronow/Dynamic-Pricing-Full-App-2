#!/usr/bin/env python3
"""
Script to test the dashboard endpoint directly.
"""
import requests
import json

def main():
    # Test the dashboard endpoint
    url = "http://localhost:8000/api/dashboard/sales-data"
    print(f"Testing endpoint: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nDashboard Data Summary:")
            print(f"Total Sales: ${data.get('totalSales', 0):.2f}")
            print(f"Total Orders: {data.get('totalOrders', 0)}")
            print(f"Average Order Value: ${data.get('averageOrderValue', 0):.2f}")
            
            # Check top selling items
            top_items = data.get('topSellingItems', [])
            print(f"\nTop Selling Items (count: {len(top_items)}):")
            for item in top_items:
                print(f"ID: {item.get('id')}, Name: {item.get('name')}, Quantity: {item.get('total_quantity')}")
            
            # Print full response for debugging
            print("\nFull response:")
            print(json.dumps(data, indent=2))
        else:
            print(f"Error response: {response.text}")
    except Exception as e:
        print(f"Exception occurred: {str(e)}")

if __name__ == "__main__":
    main()
