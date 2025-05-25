import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models
from openai import OpenAI
import os
from typing import Optional, Dict, List, Any
import asyncio

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

async def generate_customer_report(db: Session, user_id: int) -> models.CustomerReport:
    """
    Generate a customer report using the OpenAI API.
    This agent analyzes demographic trends, socioeconomic patterns, customer behavior,
    and upcoming events that could impact foot traffic.
    """
    try:
        # Get business data
        business = db.query(models.BusinessProfile).filter(models.BusinessProfile.user_id == user_id).first()
        
        if not business:
            raise ValueError(f"No business profile found for user ID: {user_id}")
        
        # Get orders data to understand customer behavior
        orders = db.query(models.Order).filter(
            models.Order.user_id == user_id,
            models.Order.order_date >= datetime.now() - timedelta(days=90)  # Last 90 days
        ).all()
        
        # Get order items to understand product preferences
        order_ids = [order.id for order in orders]
        order_items = db.query(models.OrderItem).filter(
            models.OrderItem.order_id.in_(order_ids)
        ).all()
        
        # Map order items to orders
        order_item_map = {}
        for order_item in order_items:
            if order_item.order_id not in order_item_map:
                order_item_map[order_item.order_id] = []
            order_item_map[order_item.order_id].append(order_item)
        
        # Prepare data for OpenAI
        business_data = {
            "name": business.business_name,
            "industry": business.industry,
            "description": business.description
        }
        
        # Aggregate order data to reduce token usage
        # 1. Aggregate by day
        orders_by_day = {}
        for order in orders:
            day = order.order_date.strftime('%Y-%m-%d')
            if day not in orders_by_day:
                orders_by_day[day] = {
                    "count": 0,
                    "total_amount": 0,
                    "items": {}
                }
            
            orders_by_day[day]["count"] += 1
            orders_by_day[day]["total_amount"] += order.total_amount
            
            # Add items data (aggregated by item_id)
            if order.id in order_item_map:
                for item in order_item_map[order.id]:
                    if item.item_id not in orders_by_day[day]["items"]:
                        orders_by_day[day]["items"][item.item_id] = {
                            "quantity": 0,
                            "total_spent": 0
                        }
                    
                    orders_by_day[day]["items"][item.item_id]["quantity"] += item.quantity
                    orders_by_day[day]["items"][item.item_id]["total_spent"] += (item.quantity * item.unit_price)
        
        # 2. Convert to a list and limit to most recent 30 days if needed
        days = sorted(orders_by_day.keys())
        if len(days) > 30:
            days = days[-30:]
        
        # 3. Create final aggregated data structure
        orders_data = []
        for day in days:
            # Convert items dict to a simpler list format
            items_list = []
            for item_id, item_data in orders_by_day[day]["items"].items():
                items_list.append({
                    "item_id": item_id,
                    "quantity": item_data["quantity"],
                    "total_spent": item_data["total_spent"]
                })
            
            # Only include top 5 items by quantity to further reduce data
            items_list.sort(key=lambda x: x["quantity"], reverse=True)
            top_items = items_list[:5] if len(items_list) > 5 else items_list
            
            orders_data.append({
                "date": day,
                "order_count": orders_by_day[day]["count"],
                "total_amount": orders_by_day[day]["total_amount"],
                "top_items": top_items
            })
        
        # Create prompt for OpenAI
        prompt = f"""
        You are a Customer Analysis Agent for {business_data['name']}, a {business_data['industry']} business.
        
        Your task is to:
        1. Analyze customer demographics and socioeconomic patterns based on sales data
        2. Identify return customer trends and new customer acquisition
        3. Estimate how customers would respond to price changes
        4. Research upcoming local events (weather patterns, college reunions, concerts, etc.) that could impact foot traffic
        
        Return your analysis in JSON format with these EXACT sections to match the frontend requirements:
        {{
          "summary": "A comprehensive summary of customer behavior and trends (text)",
          "demographics": [
            {{
              "name": "Segment name (e.g., 'Premium Buyers')",
              "characteristics": ["Trait 1", "Trait 2", "Trait 3"],
              "price_sensitivity": 0.7  
            }},
            /* Add more demographic segments as needed */
          ],
          "events": [
            {{
              "name": "Event name (e.g., 'Summer Festival')", 
              "date": "2025-06-15",
              "projected_impact": "Description of how this will affect business",
              "impact_level": 0.8
            }},
            /* Add more events as needed */
          ],
          "trends": {{
            "price_sensitivity": {{"details": "Include price sensitivity details here"}},
            "recommendations": [{{
              "detail": "Include targeting recommendations here"
            }}]
          }}
        }}
        
        IMPORTANT: Follow this format EXACTLY - the frontend expects these specific keys and structure.
        
        Here's the business information:
        {json.dumps(business_data)}
        
        And here's the recent order data (last 90 days):
        {json.dumps(orders_data)}
        
        For the upcoming events, today's date is {datetime.now().strftime('%Y-%m-%d')}. Include weather forecasts, local events, holidays, etc. in the next 30 days that could affect customer behavior.
        """
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are a Customer Analysis Agent specializing in consumer behavior, demographics, and event forecasting."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Extract the analysis from the response
        analysis_text = response.choices[0].message.content
        
        # Parse the JSON response
        try:
            # Try to extract JSON if it's embedded in markdown or text
            if "```json" in analysis_text:
                json_start = analysis_text.find("```json") + 7
                json_end = analysis_text.find("```", json_start)
                analysis_json = json.loads(analysis_text[json_start:json_end].strip())
            elif "```" in analysis_text:
                json_start = analysis_text.find("```") + 3
                json_end = analysis_text.find("```", json_start)
                analysis_json = json.loads(analysis_text[json_start:json_end].strip())
            else:
                analysis_json = json.loads(analysis_text)
            
            # Extract components
            summary = analysis_json.get("summary", "No summary provided")
            demographics = analysis_json.get("demographics", {})
            price_sensitivity = analysis_json.get("price_sensitivity", {})
            upcoming_events = analysis_json.get("upcoming_events", [])
            recommendations = analysis_json.get("recommendations", [])
            
            # Store in the database
            customer_report = models.CustomerReport(
                user_id=user_id,
                summary=summary,
                demographics=json.dumps(demographics),
                events=json.dumps(upcoming_events),
                trends=json.dumps({
                    "price_sensitivity": price_sensitivity,
                    "recommendations": recommendations
                })
            )
            
            db.add(customer_report)
            db.commit()
            db.refresh(customer_report)
            
            return customer_report
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, store the raw text
            customer_report = models.CustomerReport(
                user_id=user_id,
                summary=analysis_text[:500],  # Use the first 500 chars as summary
                demographics=json.dumps({"raw_response": analysis_text})
            )
            
            db.add(customer_report)
            db.commit()
            db.refresh(customer_report)
            
            return customer_report
        
    except Exception as e:
        # Log the error
        print(f"Error in customer agent: {str(e)}")
        
        # Create a report with the error
        error_report = models.CustomerReport(
            user_id=user_id,
            summary=f"Error generating customer report: {str(e)}",
            demographics=json.dumps({"error": str(e)})
        )
        
        db.add(error_report)
        db.commit()
        db.refresh(error_report)
        
        return error_report
