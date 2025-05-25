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

async def generate_experiment_recommendation(
    db: Session, 
    user_id: int, 
    pricing_report_id: Optional[int] = None
) -> models.ExperimentRecommendation:
    """
    Generate an experiment recommendation using the OpenAI API.
    This agent takes pricing recommendations and determines the best timing
    for implementation and evaluation.
    """
    try:
        # Get business data
        business = db.query(models.BusinessProfile).filter(models.BusinessProfile.user_id == user_id).first()
        
        if not business:
            raise ValueError(f"No business profile found for user ID: {user_id}")
        
        # Get the pricing report
        pricing_report = None
        if pricing_report_id:
            pricing_report = db.query(models.PricingReport).filter(
                models.PricingReport.id == pricing_report_id,
                models.PricingReport.user_id == user_id
            ).first()
        else:
            # Get the most recent report
            pricing_report = db.query(models.PricingReport).filter(
                models.PricingReport.user_id == user_id
            ).order_by(models.PricingReport.created_at.desc()).first()
        
        if not pricing_report:
            raise ValueError(f"No pricing report found for user ID: {user_id}")
        
        # Get order data to understand sales patterns
        orders = db.query(models.Order).filter(
            models.Order.user_id == user_id,
            models.Order.order_date >= datetime.now() - timedelta(days=90)  # Last 90 days
        ).all()
        
        # Prepare data for OpenAI
        business_data = {
            "name": business.business_name,
            "industry": business.industry,
            "description": business.description
        }
        
        # Extract pricing recommendations
        pricing_recommendations = []
        if pricing_report.recommended_changes:
            try:
                pricing_recommendations = json.loads(pricing_report.recommended_changes)
            except:
                pricing_recommendations = []
        
        # Extract pricing rationale
        pricing_rationale = {}
        if pricing_report.rationale:
            try:
                pricing_rationale = json.loads(pricing_report.rationale)
            except:
                pricing_rationale = {}
        
        # Aggregate orders by day to reduce token count
        order_by_day = {}
        for order in orders:
            day = order.order_date.strftime('%Y-%m-%d')
            if day not in order_by_day:
                order_by_day[day] = 0
            order_by_day[day] += order.total_amount
        
        # Convert to sorted lists for the prompt
        days = sorted(order_by_day.keys())
        daily_amounts = [order_by_day[day] for day in days]
        
        # For additional token reduction, limit to the most recent 30 days if there are many days
        if len(days) > 30:
            days = days[-30:]
            daily_amounts = daily_amounts[-30:]
        
        # Create prompt for OpenAI
        prompt = f"""
        You are an Experimental Pricing Agent for {business_data['name']}, a {business_data['industry']} business.
        
        Your task is to:
        1. Analyze the pricing recommendations from the Pricing Agent
        2. Determine the optimal timing for implementing price changes
        3. Set appropriate evaluation dates to assess the impact of price changes
        4. Prioritize which recommendations to implement first
        
        Return your analysis in JSON format with these EXACT sections to match the frontend requirements:
        {{
          "summary": "A comprehensive summary of your experimental approach (text)",
          "start_date": "2025-06-01",  /* Use YYYY-MM-DD format for implementation date */
          "evaluation_date": "2025-06-15",  /* Use YYYY-MM-DD format for evaluation date */
          "recommendations": {{
            "implementation": [
              {{
                "product_id": 123,  /* Must be a number */
                "product_name": "Product Name",
                "current_price": 10.99,  /* Must be a number */
                "new_price": 12.99  /* Must be a number */
              }},
              /* Add more product recommendations as needed */
            ]
          }},
          "evaluation": {{
            "metrics": ["Sales volume", "Revenue", "Customer retention"],
            "risks": ["Customer backlash", "Competitor response"],
            "mitigation": "Strategies to mitigate identified risks"
          }}
        }}
        
        IMPORTANT: Follow this format EXACTLY - the frontend expects these specific keys and structure.
        
        Here's the business information:
        {json.dumps(business_data)}
        
        Here are the pricing recommendations from the Pricing Agent:
        {json.dumps(pricing_recommendations)}
        
        Here is the rationale behind the pricing recommendations:
        {json.dumps(pricing_rationale)}
        
        Here is daily aggregated order data to help identify sales patterns:
        {json.dumps({"dates": days, "daily_totals": daily_amounts})}
        
        Today's date is {datetime.now().strftime('%Y-%m-%d')}. Please provide specific dates for implementation and evaluation.
        """
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are an Experimental Pricing Agent specializing in designing and evaluating pricing experiments to test price elasticity and customer responses."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
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
            implementation = analysis_json.get("implementation", [])
            evaluation_criteria = analysis_json.get("evaluation_criteria", {})
            risk_assessment = analysis_json.get("risk_assessment", {})
            
            # Determine earliest implementation date
            start_date = datetime.now()
            evaluation_date = datetime.now() + timedelta(days=14)  # Default to 2 weeks
            
            if implementation and len(implementation) > 0:
                # Parse the dates from the first implementation recommendation
                try:
                    implementation_date_str = implementation[0].get("implementation_date", None)
                    evaluation_date_str = implementation[0].get("evaluation_date", None)
                    
                    if implementation_date_str:
                        start_date = datetime.fromisoformat(implementation_date_str.replace("Z", "+00:00"))
                    
                    if evaluation_date_str:
                        evaluation_date = datetime.fromisoformat(evaluation_date_str.replace("Z", "+00:00"))
                except:
                    # Use default dates if parsing fails
                    pass
            
            # Store in the database
            experiment_recommendation = models.ExperimentRecommendation(
                user_id=user_id,
                pricing_report_id=pricing_report.id,
                summary=summary,
                start_date=start_date,
                evaluation_date=evaluation_date,
                recommendations=json.dumps({
                    "implementation": implementation,
                    "evaluation_criteria": evaluation_criteria,
                    "risk_assessment": risk_assessment
                }),
                status="pending"
            )
            
            db.add(experiment_recommendation)
            db.commit()
            db.refresh(experiment_recommendation)
            
            # Create experiment price changes
            for impl in implementation:
                item_id = impl.get("product_id", None)
                current_price = impl.get("current_price", None)
                new_price = impl.get("new_price", None)
                
                if item_id and current_price and new_price:
                    price_change = models.ExperimentPriceChange(
                        experiment_id=experiment_recommendation.id,
                        item_id=item_id,
                        original_price=current_price,
                        new_price=new_price,
                        implemented=False
                    )
                    
                    db.add(price_change)
            
            db.commit()
            
            return experiment_recommendation
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, store the raw text
            experiment_recommendation = models.ExperimentRecommendation(
                user_id=user_id,
                pricing_report_id=pricing_report.id if pricing_report else None,
                summary=analysis_text[:500],  # Use the first 500 chars as summary
                start_date=datetime.now(),
                evaluation_date=datetime.now() + timedelta(days=14),  # Default to 2 weeks
                recommendations=json.dumps({"raw_response": analysis_text}),
                status="pending"
            )
            
            db.add(experiment_recommendation)
            db.commit()
            db.refresh(experiment_recommendation)
            
            return experiment_recommendation
        
    except Exception as e:
        # Log the error
        print(f"Error in experiment agent: {str(e)}")
        
        # Create a report with the error
        error_recommendation = models.ExperimentRecommendation(
            user_id=user_id,
            pricing_report_id=pricing_report_id,
            summary=f"Error generating experiment recommendation: {str(e)}",
            start_date=datetime.now(),
            evaluation_date=datetime.now() + timedelta(days=14),  # Default to 2 weeks
            recommendations=json.dumps({"error": str(e)}),
            status="pending"
        )
        
        db.add(error_recommendation)
        db.commit()
        db.refresh(error_recommendation)
        
        return error_recommendation

async def evaluate_experiment(
    db: Session, 
    experiment_id: int
) -> models.ExperimentRecommendation:
    """
    Evaluate an existing pricing experiment to determine its success.
    """
    try:
        # Get the experiment recommendation
        experiment = db.query(models.ExperimentRecommendation).filter(
            models.ExperimentRecommendation.id == experiment_id
        ).first()
        
        if not experiment:
            raise ValueError(f"No experiment found with ID: {experiment_id}")
        
        # Get the user ID
        user_id = experiment.user_id
        
        # Get the price changes
        price_changes = db.query(models.ExperimentPriceChange).filter(
            models.ExperimentPriceChange.experiment_id == experiment_id
        ).all()
        
        # Check if any price changes were actually implemented
        implemented_changes = [pc for pc in price_changes if pc.implemented]
        
        if not implemented_changes:
            # No changes were implemented, update status and return
            experiment.status = "cancelled"
            experiment.evaluation_results = json.dumps({
                "status": "cancelled",
                "reason": "No price changes were implemented"
            })
            db.commit()
            db.refresh(experiment)
            return experiment
        
        # Get orders for the evaluation period
        orders = db.query(models.Order).filter(
            models.Order.user_id == user_id,
            models.Order.order_date >= experiment.start_date,
            models.Order.order_date <= experiment.evaluation_date
        ).all()
        
        # Get order items
        order_ids = [order.id for order in orders]
        order_items = db.query(models.OrderItem).filter(
            models.OrderItem.order_id.in_(order_ids)
        ).all()
        
        # Create a map of item sales during the experiment
        item_sales = {}
        for order_item in order_items:
            if order_item.item_id not in item_sales:
                item_sales[order_item.item_id] = {
                    "quantity": 0,
                    "revenue": 0
                }
            item_sales[order_item.item_id]["quantity"] += order_item.quantity
            item_sales[order_item.item_id]["revenue"] += order_item.quantity * order_item.unit_price
        
        # Get sales data for the same period before the experiment
        before_start = experiment.start_date - (experiment.evaluation_date - experiment.start_date)
        before_orders = db.query(models.Order).filter(
            models.Order.user_id == user_id,
            models.Order.order_date >= before_start,
            models.Order.order_date < experiment.start_date
        ).all()
        
        # Get order items for before period
        before_order_ids = [order.id for order in before_orders]
        before_order_items = db.query(models.OrderItem).filter(
            models.OrderItem.order_id.in_(before_order_ids)
        ).all()
        
        # Create a map of item sales before the experiment
        before_item_sales = {}
        for order_item in before_order_items:
            if order_item.item_id not in before_item_sales:
                before_item_sales[order_item.item_id] = {
                    "quantity": 0,
                    "revenue": 0
                }
            before_item_sales[order_item.item_id]["quantity"] += order_item.quantity
            before_item_sales[order_item.item_id]["revenue"] += order_item.quantity * order_item.unit_price
        
        # Prepare data for the evaluation
        experiment_data = json.loads(experiment.recommendations) if experiment.recommendations else {}
        
        evaluation_results = []
        for change in implemented_changes:
            item = db.query(models.Item).filter(models.Item.id == change.item_id).first()
            
            if not item:
                continue
            
            # Calculate sales change
            before_sales = before_item_sales.get(change.item_id, {"quantity": 0, "revenue": 0})
            current_sales = item_sales.get(change.item_id, {"quantity": 0, "revenue": 0})
            
            quantity_change = current_sales["quantity"] - before_sales["quantity"]
            revenue_change = current_sales["revenue"] - before_sales["revenue"]
            
            # Calculate percentage changes
            quantity_change_pct = 0
            if before_sales["quantity"] > 0:
                quantity_change_pct = (quantity_change / before_sales["quantity"]) * 100
            
            revenue_change_pct = 0
            if before_sales["revenue"] > 0:
                revenue_change_pct = (revenue_change / before_sales["revenue"]) * 100
            
            # Calculate price change percentage
            price_change_pct = 0
            if change.original_price > 0:
                price_change_pct = ((change.new_price - change.original_price) / change.original_price) * 100
            
            # Calculate elasticity
            elasticity = 0
            if price_change_pct != 0:
                elasticity = quantity_change_pct / price_change_pct
            
            # Add to results
            evaluation_results.append({
                "item_id": change.item_id,
                "item_name": item.name,
                "original_price": change.original_price,
                "new_price": change.new_price,
                "price_change_pct": price_change_pct,
                "before_quantity": before_sales["quantity"],
                "current_quantity": current_sales["quantity"],
                "quantity_change": quantity_change,
                "quantity_change_pct": quantity_change_pct,
                "before_revenue": before_sales["revenue"],
                "current_revenue": current_sales["revenue"],
                "revenue_change": revenue_change,
                "revenue_change_pct": revenue_change_pct,
                "elasticity": elasticity,
                "success": revenue_change > 0  # Simple success metric: increased revenue
            })
        
        # Update the experiment status and results
        experiment.status = "evaluated"
        experiment.evaluation_results = json.dumps({
            "evaluation_date": datetime.now().isoformat(),
            "results": evaluation_results,
            "overall_success": sum(1 for r in evaluation_results if r["success"]) / len(evaluation_results) if evaluation_results else 0
        })
        
        db.commit()
        db.refresh(experiment)
        
        return experiment
        
    except Exception as e:
        # Log the error
        print(f"Error in experiment evaluation: {str(e)}")
        
        # Create an error result
        if experiment:
            experiment.evaluation_results = json.dumps({
                "error": str(e),
                "status": "error"
            })
            db.commit()
            db.refresh(experiment)
            
            return experiment
        else:
            raise e
