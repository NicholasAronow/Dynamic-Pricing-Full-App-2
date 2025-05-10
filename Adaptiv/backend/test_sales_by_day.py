#!/usr/bin/env python3
"""
Script to test the sales-by-day data in the dashboard endpoint.
"""
import requests
import json
from datetime import datetime, timedelta

def main():
    # Test the dashboard endpoint
    url = "http://localhost:8000/api/dashboard/sales-data"
    print(f"Testing endpoint: {url}")
    
    # Create date parameters for the last 30 days
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    params = {
        'start_date': start_date,
        'end_date': end_date
    }
    
    try:
        response = requests.get(url, params=params)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if salesByDay data exists
            sales_by_day = data.get('salesByDay', [])
            print(f"\nSales By Day data ({len(sales_by_day)} days):")
            if sales_by_day:
                print("First 5 days:")
                for day in sales_by_day[:5]:
                    print(f"Date: {day.get('date')}, Orders: {day.get('orders')}, Revenue: ${day.get('revenue', 0):.2f}")
                
                # Print the total days and revenue
                total_revenue = sum(day.get('revenue', 0) for day in sales_by_day)
                total_orders = sum(day.get('orders', 0) for day in sales_by_day)
                print(f"\nTotal days: {len(sales_by_day)}")
                print(f"Total revenue from daily data: ${total_revenue:.2f}")
                print(f"Total orders from daily data: {total_orders}")
                
                # Check if it matches the summary data
                dashboard_total = data.get('totalSales', 0)
                dashboard_orders = data.get('totalOrders', 0)
                print(f"\nDashboard summary says: ${dashboard_total:.2f} revenue, {dashboard_orders} orders")
                
                # Check for category data too
                sales_by_category = data.get('salesByCategory', [])
                print(f"\nSales By Category data ({len(sales_by_category)} categories):")
                for cat in sales_by_category:
                    print(f"Category: {cat.get('category')}, Orders: {cat.get('orders')}, Revenue: ${cat.get('revenue', 0):.2f}")
            else:
                print("No daily sales data found!")
                
        else:
            print(f"Error response: {response.text}")
    except Exception as e:
        print(f"Exception occurred: {str(e)}")

if __name__ == "__main__":
    main()
