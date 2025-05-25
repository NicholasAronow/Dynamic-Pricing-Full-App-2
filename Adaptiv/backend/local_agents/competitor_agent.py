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

async def generate_competitor_report(db: Session, user_id: int) -> models.CompetitorReport:
    """
    Generate a competitor report using the OpenAI API.
    This agent monitors competitor information, menu items, and prices.
    """
    try:
        # Get business data
        business = db.query(models.BusinessProfile).filter(models.BusinessProfile.user_id == user_id).first()
        
        if not business:
            raise ValueError(f"No business profile found for user ID: {user_id}")
        
        # Get competitor data
        competitor_items = db.query(models.CompetitorItem).all()
        
        # Get our items for comparison
        our_items = db.query(models.Item).filter(models.Item.user_id == user_id).all()
        
        # Get price history for our items to identify trends
        price_history = db.query(models.PriceHistory).filter(
            models.PriceHistory.user_id == user_id
        ).order_by(models.PriceHistory.changed_at.desc()).all()
        
        # Prepare data for OpenAI
        business_data = {
            "name": business.business_name,
            "industry": business.industry,
            "description": business.description
        }
        
        competitor_data = {}
        for item in competitor_items:
            if item.competitor_name not in competitor_data:
                competitor_data[item.competitor_name] = []
            
            competitor_data[item.competitor_name].append({
                "name": item.item_name,
                "category": item.category,
                "price": item.price,
                "description": item.description,
                "similarity_score": item.similarity_score
            })
        
        our_items_data = [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "current_price": item.current_price,
                "cost": item.cost
            }
            for item in our_items
        ]
        
        price_history_data = [
            {
                "item_id": ph.item_id,
                "previous_price": ph.previous_price,
                "new_price": ph.new_price,
                "changed_at": ph.changed_at.isoformat(),
                "change_reason": ph.change_reason
            }
            for ph in price_history
        ]
        
        # Create prompt for OpenAI
        prompt = f"""
        You are a Competitor Analysis Agent for {business_data['name']}, a {business_data['industry']} business.
        
        Your task is to analyze competitor data, identify pricing trends, and provide insights on how the business's prices compare to competitors.
        Focus on:
        1. Price differences between our products and competitor products
        2. Recent price changes by competitors
        3. Categories where our prices are significantly higher or lower than competitors
        4. Recommendations for price adjustments based on competitor positioning
        
        Return your analysis in JSON format with these EXACT sections to match the frontend requirements:
        {{
          "summary": "A comprehensive summary of the competitive landscape (text)",
          "insights": {{
            "insights": [
              {{
                "title": "Key insight title",
                "description": "Detailed description of the insight"
              }},
              /* Add more insights as needed */
            ],
            "positioning": "Market positioning assessment (text)"
          }},
          "recommendations": [
            {{
              "product_id": 123,
              "recommendation": "Specific recommendation for this product",
              "rationale": "Reasoning behind this recommendation"
            }},
            /* Add more recommendations as needed */
          ]
        }}
        
        IMPORTANT: Follow this format EXACTLY - the frontend expects these specific keys and structure.
        
        Based on this data:
        """
        
        # Add the data to the prompt
        prompt += f"\nOur Business: {json.dumps(business_data)}"
        prompt += f"\nOur Products: {json.dumps(our_items_data)}"
        prompt += f"\nCompetitor Products: {json.dumps(competitor_data)}"
        prompt += f"\nRecent Price History: {json.dumps(price_history_data)}"
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are a Competitor Analysis Agent specializing in market research and competitive intelligence."},
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
            insights = analysis_json.get("insights", [])
            recommendations = analysis_json.get("recommendations", [])
            positioning = analysis_json.get("positioning", "No positioning assessment provided")
            
            # Store in the database
            competitor_report = models.CompetitorReport(
                user_id=user_id,
                summary=summary,
                insights=json.dumps({
                    "insights": insights,
                    "positioning": positioning
                }),
                competitor_data=json.dumps({
                    "recommendations": recommendations,
                    "competitors": list(competitor_data.keys())
                })
            )
            
            db.add(competitor_report)
            db.commit()
            db.refresh(competitor_report)
            
            return competitor_report
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, store the raw text
            competitor_report = models.CompetitorReport(
                user_id=user_id,
                summary=analysis_text[:500],  # Use the first 500 chars as summary
                insights=json.dumps({"raw_response": analysis_text})
            )
            
            db.add(competitor_report)
            db.commit()
            db.refresh(competitor_report)
            
            return competitor_report
        
    except Exception as e:
        # Log the error
        print(f"Error in competitor agent: {str(e)}")
        
        # Create a report with the error
        error_report = models.CompetitorReport(
            user_id=user_id,
            summary=f"Error generating competitor report: {str(e)}",
            insights=json.dumps({"error": str(e)})
        )
        
        db.add(error_report)
        db.commit()
        db.refresh(error_report)
        
        return error_report
