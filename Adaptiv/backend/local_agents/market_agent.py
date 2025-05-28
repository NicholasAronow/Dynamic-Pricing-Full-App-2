import json
from datetime import datetime
from sqlalchemy.orm import Session
import models
from openai import OpenAI
import os
from typing import Optional, Dict, List, Any
import asyncio

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

async def generate_market_report(db: Session, user_id: int) -> models.MarketReport:
    """
    Generate a market report using the OpenAI API.
    This agent analyzes market trends, supply chain issues, and other factors
    affecting the business's vertical market.
    """
    try:
        # Get business data
        business = db.query(models.BusinessProfile).filter(models.BusinessProfile.user_id == user_id).first()
        
        if not business:
            raise ValueError(f"No business profile found for user ID: {user_id}")
        
        # Get COGS data to understand supply chain costs
        cogs_data = db.query(models.COGS).filter(
            models.COGS.user_id == user_id
        ).order_by(models.COGS.week_start_date.desc()).limit(12).all()  # Last 12 weeks
        
        # Prepare data for OpenAI
        business_data = {
            "name": business.business_name,
            "industry": business.industry,
            "description": business.description
        }
        
        # Prepare COGS data
        cogs_trend = [
            {
                "week_start": cogs.week_start_date.isoformat(),
                "week_end": cogs.week_end_date.isoformat(),
                "amount": cogs.amount
            }
            for cogs in cogs_data
        ]
        
        # Create prompt for OpenAI
        prompt = f"""
        You are a Market Analysis Agent for {business_data['name']}, a {business_data['industry']} business.
        
        Your task is to:
        1. Analyze current market trends in the {business_data['industry']} industry
        2. Identify supply chain issues or opportunities
        3. Research cost trends for key inputs
        4. Evaluate market competition and industry dynamics
        
        Return your analysis in JSON format with these EXACT sections to match the frontend requirements:
        {{
          "summary": "A comprehensive summary of the market landscape and key trends (text)",
          "supply_chain": [
            {{
              "factor": "Supply chain factor name",
              "impact": "Description of the impact",
              "trend": "increasing"  /* Must be exactly one of: 'increasing', 'decreasing', or 'stable' */
            }},
            /* Add more supply chain factors as needed */
          ],
          "market_trends": {{
            "cost_trends": [
              {{
                "input_category": "Category name (e.g., 'Raw Materials')",
                "trend": "Description of the trend",
                "forecast": "Future forecast description"
              }},
              /* Add more cost trend categories as needed */
            ]
          }},
          "competitive_landscape": {{
            "assessment": "Overall assessment of competition",
            "recommendations": [
              {{
                "recommendation": "Strategic recommendation",
                "rationale": "Reasoning behind this recommendation"
              }}
            ]
          }}
        }}
        
        IMPORTANT: Follow this format EXACTLY - the frontend expects these specific keys and structure.
        
        Here's the business information:
        {json.dumps(business_data)}
        
        And here's the recent cost of goods sold (COGS) data:
        {json.dumps(cogs_trend)}
        
        Today's date is {datetime.now().strftime('%Y-%m-%d')}. Focus on current market conditions and trends in the {business_data['industry']} industry.
        """
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are a Market Analysis Agent specializing in industry trends, supply chain dynamics, and competitive landscape analysis."},
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
            supply_chain = analysis_json.get("supply_chain", [])
            market_trends = analysis_json.get("market_trends", {})
            cost_trends = market_trends.get("cost_trends", [])  # Properly extract cost_trends from market_trends
            competitive_landscape = analysis_json.get("competitive_landscape", {})
            recommendations = analysis_json.get("recommendations", [])
            
            # Store in the database
            market_report = models.MarketReport(
                user_id=user_id,
                summary=summary,
                market_trends=json.dumps({
                    "cost_trends": cost_trends,  # This is now properly extracted from market_trends
                    "competitive_landscape": competitive_landscape
                }),
                supply_chain=json.dumps(supply_chain),
                industry_insights=json.dumps({
                    "recommendations": recommendations,
                    "industry": business.industry
                })
            )
            
            db.add(market_report)
            db.commit()
            db.refresh(market_report)
            
            return market_report
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, store the raw text
            market_report = models.MarketReport(
                user_id=user_id,
                summary=analysis_text[:500],  # Use the first 500 chars as summary
                market_trends=json.dumps({"raw_response": analysis_text})
            )
            
            db.add(market_report)
            db.commit()
            db.refresh(market_report)
            
            return market_report
        
    except Exception as e:
        # Log the error
        print(f"Error in market agent: {str(e)}")
        
        # Create a report with the error
        error_report = models.MarketReport(
            user_id=user_id,
            summary=f"Error generating market report: {str(e)}",
            market_trends=json.dumps({"error": str(e)})
        )
        
        db.add(error_report)
        db.commit()
        db.refresh(error_report)
        
        return error_report
