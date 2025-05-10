#!/usr/bin/env python3
import requests

url = "http://localhost:8000/api/dashboard/sales-data"
response = requests.get(url)
print(f"Status code: {response.status_code}")
try:
    print(response.json())
except:
    print("Could not parse JSON response")
    print(response.text)
