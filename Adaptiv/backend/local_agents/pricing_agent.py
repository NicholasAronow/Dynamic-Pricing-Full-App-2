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

async def generate_pricing_report(
    db: Session, 
    user_id: int, 
    competitor_report_id: Optional[int] = None,
    customer_report_id: Optional[int] = None,
    market_report_id: Optional[int] = None
) -> models.PricingReport:
    """
    Generate a pricing report using the OpenAI API.
    This agent uses data from the competitor, customer, and market agents
    to recommend optimal pricing strategies.
    """
    try:
        # Get business data
        business = db.query(models.BusinessProfile).filter(models.BusinessProfile.user_id == user_id).first()
        
        if not business:
            raise ValueError(f"No business profile found for user ID: {user_id}")
        
        # Get our items for pricing recommendations
        items = db.query(models.Item).filter(models.Item.user_id == user_id).all()
        
        # Get recent COGS data
        recent_cogs = db.query(models.COGS).filter(
            models.COGS.user_id == user_id
        ).order_by(models.COGS.week_end_date.desc()).first()
        
        # Get sales data
        orders = db.query(models.Order).filter(
            models.Order.user_id == user_id,
            models.Order.order_date >= datetime.now() - timedelta(days=30)  # Last 30 days
        ).all()
        
        # Get order items to understand product sales
        order_ids = [order.id for order in orders]
        order_items = db.query(models.OrderItem).filter(
            models.OrderItem.order_id.in_(order_ids)
        ).all()
        
        # Get the reports from the other agents
        competitor_report = None
        customer_report = None
        market_report = None
        
        if competitor_report_id:
            competitor_report = db.query(models.CompetitorReport).filter(
                models.CompetitorReport.id == competitor_report_id,
                models.CompetitorReport.user_id == user_id
            ).first()
        else:
            # Get the most recent report
            competitor_report = db.query(models.CompetitorReport).filter(
                models.CompetitorReport.user_id == user_id
            ).order_by(models.CompetitorReport.created_at.desc()).first()
        
        if customer_report_id:
            customer_report = db.query(models.CustomerReport).filter(
                models.CustomerReport.id == customer_report_id,
                models.CustomerReport.user_id == user_id
            ).first()
        else:
            # Get the most recent report
            customer_report = db.query(models.CustomerReport).filter(
                models.CustomerReport.user_id == user_id
            ).order_by(models.CustomerReport.created_at.desc()).first()
        
        if market_report_id:
            market_report = db.query(models.MarketReport).filter(
                models.MarketReport.id == market_report_id,
                models.MarketReport.user_id == user_id
            ).first()
        else:
            # Get the most recent report
            market_report = db.query(models.MarketReport).filter(
                models.MarketReport.user_id == user_id
            ).order_by(models.MarketReport.created_at.desc()).first()
        
        # Create a map of item sales
        item_sales = {}
        for order_item in order_items:
            if order_item.item_id not in item_sales:
                item_sales[order_item.item_id] = {
                    "quantity": 0,
                    "revenue": 0
                }
            item_sales[order_item.item_id]["quantity"] += order_item.quantity
            item_sales[order_item.item_id]["revenue"] += order_item.quantity * order_item.unit_price
        
        # Prepare data for OpenAI
        business_data = {
            "name": business.business_name,
            "industry": business.industry,
            "description": business.description
        }
        
        items_data = [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "current_price": item.current_price,
                "cost": item.cost,
                "sales_quantity": item_sales.get(item.id, {}).get("quantity", 0),
                "sales_revenue": item_sales.get(item.id, {}).get("revenue", 0)
            }
            for item in items
        ]
        
        # Prepare COGS data
        cogs_data = None
        if recent_cogs:
            cogs_data = {
                "week_start": recent_cogs.week_start_date.isoformat(),
                "week_end": recent_cogs.week_end_date.isoformat(),
                "amount": recent_cogs.amount
            }
        
        # Prepare report data
        competitor_report_data = None
        if competitor_report and competitor_report.insights:
            try:
                competitor_report_data = {
                    "summary": competitor_report.summary,
                    "insights": json.loads(competitor_report.insights) if competitor_report.insights else None,
                    "competitor_data": json.loads(competitor_report.competitor_data) if competitor_report.competitor_data else None
                }
            except:
                competitor_report_data = {
                    "summary": competitor_report.summary,
                    "error": "Failed to parse competitor report data"
                }
        
        customer_report_data = None
        if customer_report:
            try:
                customer_report_data = {
                    "summary": customer_report.summary,
                    "demographics": json.loads(customer_report.demographics) if customer_report.demographics else None,
                    "events": json.loads(customer_report.events) if customer_report.events else None,
                    "trends": json.loads(customer_report.trends) if customer_report.trends else None
                }
            except:
                customer_report_data = {
                    "summary": customer_report.summary,
                    "error": "Failed to parse customer report data"
                }
        
        market_report_data = None
        if market_report:
            try:
                market_report_data = {
                    "summary": market_report.summary,
                    "market_trends": json.loads(market_report.market_trends) if market_report.market_trends else None,
                    "supply_chain": json.loads(market_report.supply_chain) if market_report.supply_chain else None,
                    "industry_insights": json.loads(market_report.industry_insights) if market_report.industry_insights else None
                }
            except:
                market_report_data = {
                    "summary": market_report.summary,
                    "error": "Failed to parse market report data"
                }
        
        # Create prompt for OpenAI
        prompt = f"""
        You are a Pricing Strategy Agent for {business_data['name']}, a {business_data['industry']} business.
        
        Your task is to analyze all available data and recommend optimal pricing strategies for the business's products.
        You should:
        1. Identify products that would benefit from price changes
        2. Recommend specific price changes (increase, decrease, or maintain)
        3. Provide rationale for each recommendation based on the data
        4. Consider competitor pricing, customer behavior, and market trends
        
        Return your analysis in JSON format with these EXACT sections to match the frontend requirements:
        {{
          "summary": "A comprehensive summary of your pricing recommendations (text)",
          "recommended_changes": [
            /* IMPORTANT: You MUST include at least 3-5 specific product recommendations here. DO NOT return an empty array. */
            /* For each product mentioned in your summary that would benefit from a price change, include a specific recommendation. */
            {{
              "product_id": 123,  /* Must be a number from the items_data provided */
              "product_name": "Product Name",  /* Must match the name from items_data */
              "current_price": 10.99,  /* Must be the actual current price from items_data */
              "recommended_price": 12.99,  /* Must be a specific number representing your recommended price */
              "change_percentage": 18.2,  /* Must be a number, calculated as (recommended_price - current_price) / current_price * 100 */
              "rationale": "Detailed explanation for this specific recommendation"
            }},
            /* YOU MUST INCLUDE MULTIPLE PRODUCT RECOMMENDATIONS - DO NOT LEAVE THIS ARRAY EMPTY */
          ],
          "rationale": {{
            "implementation": {{
              "timing": "Specific timeline for when these changes should be implemented",
              "sequencing": "The specific order in which product price changes should be made",
              "monitoring": "Specific key metrics to track after implementation to measure success"
            }}
          }}
        }}
        
        IMPORTANT: Follow this format EXACTLY - the frontend expects these specific keys and structure.
        
        Here's the business information:
        {json.dumps(business_data)}
        
        Here are the products with their current prices and recent sales:
        {json.dumps(items_data)}
        """
        
        if cogs_data:
            prompt += f"\n\nRecent Cost of Goods Sold (COGS) data:\n{json.dumps(cogs_data)}"
        
        if competitor_report_data:
            prompt += f"\n\nCompetitor Report:\n{json.dumps(competitor_report_data)}"
        
        if customer_report_data:
            prompt += f"\n\nCustomer Report:\n{json.dumps(customer_report_data)}"
        
        if market_report_data:
            prompt += f"\n\nMarket Report:\n{json.dumps(market_report_data)}"
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a Pricing Strategy Agent specializing in optimizing prices for maximizing profitability while maintaining competitiveness."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=3000
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
            recommended_changes = analysis_json.get("recommended_changes", [])
            
            # If no recommended_changes were provided but there's a good summary,
            # create placeholder recommendations based on the summary
            if not recommended_changes and len(summary) > 100 and "price" in summary.lower():
                # Extract product mentions from summary to create placeholder recommendations
                for item in items_data:
                    item_name = item.get("name", "")
                    if item_name.lower() in summary.lower():
                        # Determine if this item was recommended for price increase or decrease
                        if "increase" in summary.lower() and item_name.lower() in summary.lower().split("increase")[0][-50:]:
                            direction = 1.05  # 5% increase
                        elif "decrease" in summary.lower() and item_name.lower() in summary.lower().split("decrease")[0][-50:]:
                            direction = 0.95  # 5% decrease
                        else:
                            continue  # Skip if no clear direction
                            
                        current_price = item.get("price", 10)
                        recommended_price = round(current_price * direction, 2)
                        recommended_changes.append({
                            "product_id": item.get("id", 0),
                            "product_name": item_name,
                            "current_price": current_price,
                            "recommended_price": recommended_price,
                            "change_percentage": round((recommended_price - current_price) / current_price * 100, 2),
                            "rationale": f"Based on analysis of market trends and competitor pricing"
                        })
                        
                        # Limit to 3 recommendations
                        if len(recommended_changes) >= 3:
                            break
            
            # Extract rationale components
            rationale = analysis_json.get("rationale", {})
            implementation = rationale.get("implementation", {})
            pricing_insights = rationale.get("pricing_insights", {})
            
            # Store in the database
            pricing_report = models.PricingReport(
                user_id=user_id,
                summary=summary,
                recommended_changes=json.dumps(recommended_changes),
                rationale=json.dumps({
                    "pricing_insights": pricing_insights,
                    "implementation": implementation
                }),
                competitor_report_id=competitor_report.id if competitor_report else None,
                customer_report_id=customer_report.id if customer_report else None,
                market_report_id=market_report.id if market_report else None
            )
            
            db.add(pricing_report)
            db.commit()
            db.refresh(pricing_report)
            
            return pricing_report
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, store the raw text
            pricing_report = models.PricingReport(
                user_id=user_id,
                summary=analysis_text[:500],  # Use the first 500 chars as summary
                recommended_changes=json.dumps({"raw_response": analysis_text}),
                competitor_report_id=competitor_report.id if competitor_report else None,
                customer_report_id=customer_report.id if customer_report else None,
                market_report_id=market_report.id if market_report else None
            )
            
            db.add(pricing_report)
            db.commit()
            db.refresh(pricing_report)
            
            return pricing_report
        
    except Exception as e:
        # Log the error
        print(f"Error in pricing agent: {str(e)}")
        
        # Create a report with the error
        error_report = models.PricingReport(
            user_id=user_id,
            summary=f"Error generating pricing report: {str(e)}",
            recommended_changes=json.dumps({"error": str(e)})
        )
        
        db.add(error_report)
        db.commit()
        db.refresh(error_report)
        
        return error_report
