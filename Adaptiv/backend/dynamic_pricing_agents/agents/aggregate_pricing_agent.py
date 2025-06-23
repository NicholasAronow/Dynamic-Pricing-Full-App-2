"""
Aggregate Pricing Agent - Runs multiple pricing agents and aggregates their results by item ID.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
import json
from datetime import datetime, timedelta, timezone, date
import models
import os
from anthropic import Anthropic
from ..base_agent import BaseAgent
from .data_collection import DataCollectionAgent
from .test_db_agent import TestDBAgentWrapper
from .test_web_agent import TestWebAgentWrapper
# Use absolute import instead of relative
from knock_integration import KnockClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AggregatePricingAgent(BaseAgent):
    """Agent that runs multiple agents and aggregates their results by item ID"""
    
    def __init__(self):
        super().__init__("AggregatePricingAgent", model="gpt-4o")
        self.data_collection_agent = DataCollectionAgent()
        self.competitor_agent = TestDBAgentWrapper()
        self.market_research_agent = TestWebAgentWrapper()
        
    def get_system_prompt(self) -> str:
        return """You are an Aggregate Pricing Agent that runs multiple agents for data collection, 
        competitor analysis, and market research, then aggregates their outputs by item ID."""
    
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process all agents and aggregate their results by item ID"""
        
        logger.info("Starting aggregate pricing process")
        
        try:
            # Ensure context has required fields with reasonable defaults
            safe_context = context.copy()
            
            # If username isn't provided but email is, use email
            if "username" not in safe_context and "user_id" in safe_context:
                # Just use user_id as a placeholder if needed
                safe_context["username"] = f"user_{safe_context['user_id']}"
                logger.info(f"Using user_id as username substitute: {safe_context['username']}")
                
            # Ensure we have business_context
            if "business_context" not in safe_context:
                safe_context["business_context"] = {}
                
            # Make sure db is passed in safe_context if available
            if "db" in context and "db" not in safe_context:
                safe_context["db"] = context["db"]
                
            # Step 1: Run DataCollectionAgent
            logger.info("Running DataCollectionAgent")
            data_collection_results = self.data_collection_agent.process(safe_context)
            logger.info("DataCollectionAgent completed successfully")
            
            # Filter out items with active price recommendations
            filtered_data_collection_results = self._filter_active_recommendations(data_collection_results, safe_context)
            logger.info("Filtered out items with active price recommendations")
            logger.info(filtered_data_collection_results)
            
            # Create updated context with data collection results for other agents
            logger.info("Creating updated context with data collection results")
            updated_context = safe_context.copy()
            updated_context["data_collection_results"] = filtered_data_collection_results
            
            # Step 2: Run TestDBAgent (competitor analysis)
            logger.info("Running TestDBAgent for competitor analysis")
            competitor_results = await self.competitor_agent.process(updated_context)
            logger.info("TestDBAgent completed successfully")
            
            # Step 3: Run TestWebAgent (market research)
            logger.info("Running TestWebAgent for market research")
            market_research_results = await self.market_research_agent.process(updated_context)
            logger.info("TestWebAgent completed successfully")
            
            # Step 4: Aggregate all results by item ID
            aggregated_results = self._aggregate_results(
                data_collection_results, 
                competitor_results.get("competitor_results", []), 
                market_research_results.get("research_results", []),
                context
            )
            
            logger.info(f"Successfully aggregated results for {len(aggregated_results)} items")
            
            # Step 5: Generate pricing recommendations based on aggregated results
            logger.info("Generating pricing recommendations using LLM")
            pricing_recommendations = await self._generate_price_recommendations(aggregated_results)
            logger.info(f"Generated pricing recommendations for {len(pricing_recommendations)} items")
            
            # Step 6: Send notification email with pricing recommendations
            await self._send_notification(pricing_recommendations, safe_context)
            
            return {
                "success": True,
                "pricing_recommendations": pricing_recommendations,
            }
            
        except Exception as e:
            logger.error(f"Error in aggregate pricing process: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def _send_notification(self, pricing_recommendations: List[Dict[str, Any]], context: Dict[str, Any]):
        """
        Send a notification with pricing recommendations
        """
        try:
            # Skip if there are no recommendations
            if not pricing_recommendations or len(pricing_recommendations) == 0:
                logger.info("No pricing recommendations to send notification for")
                return
                
            # Get user information for notification
            user_id = context.get('user_id')
            if not user_id:
                logger.warning("Cannot send notification: no user_id in context")
                return
                
            # Try to get recipient email from context - multiple fallback mechanisms
            recipient_email = None
            
            # Option 1: Direct user_email or email in context
            if 'user_email' in context:
                recipient_email = context['user_email']
            elif 'email' in context:
                recipient_email = context['email']
            
            # Option 2: Try to get from user in database if we have user_id
            if not recipient_email and user_id:
                try:
                    # Get db from context (same as data_collection.py)
                    db = context.get("db")
                    
                    if db:
                        # Import User model only
                        import models
                        
                        # Use the existing session from context
                        db_user = db.query(models.User).filter(models.User.id == user_id).first()
                        if db_user and db_user.email:
                            recipient_email = db_user.email
                            logger.info(f"Found user email from database: {recipient_email}")
                    else:
                        logger.warning("No database session available in context")
                except Exception as db_err:
                    logger.error(f"Error getting user email from database: {str(db_err)}")
                    logger.exception(db_err)  # More detailed error logging
            
            # Option 3: Try username if it looks like an email
            if not recipient_email and 'username' in context and '@' in context['username']:
                potential_email = context['username']
                if '.' in potential_email.split('@')[1]:  # Basic email format validation
                    recipient_email = potential_email
                    logger.info(f"Using username as email: {recipient_email}")
                    
            if not recipient_email:
                logger.warning("Cannot send notification: no recipient email found in context")
                return
                
            # Create a correctly structured report data object for the notification
            report_data = {
                "task_id": context.get('task_id', f"task_{datetime.now().timestamp()}"),
                "completed_at": datetime.now().isoformat(),
                "status": "completed",
                "results": {
                    "pricing_recommendations": pricing_recommendations
                }
            }
            
            # Initialize Knock client
            knock_client = KnockClient()
            
            # Send notification
            logger.info(f"Sending pricing report notification to {recipient_email}")
            notification_sent = await knock_client.send_pricing_report_notification(
                report_data=report_data,
                recipients=[recipient_email],
                user_id=user_id
            )
            
            if notification_sent:
                logger.info(f"Pricing report notification sent successfully to {recipient_email}")
            else:
                logger.warning(f"Failed to send pricing report notification to {recipient_email}")
                
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            # Don't re-raise the exception since this is a non-critical feature
    
    def _filter_active_recommendations(self, data_collection_results: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter out items that have active price recommendations (implementation status = 'implemented'
        and current date is before reevaluation_date)
        
        Args:
            data_collection_results: Results from DataCollectionAgent
            context: Processing context with db session
            
        Returns:
            Filtered data collection results with excluded items removed
        """
        # Make a copy of the results to modify
        filtered_results = data_collection_results.copy()
        
        # Check if we have a database session
        db = context.get("db")
        user_id = context.get("user_id")
        
        if not db or not user_id:
            logger.warning("No database session or user_id available. Cannot filter active recommendations.")
            return data_collection_results
            
        try:
            # Import the PricingRecommendation model
            from models import PricingRecommendation
            
            # Get all active pricing recommendations for this user where today < reevaluation_date
            today = datetime.now().date()
            
            active_recommendations = db.query(PricingRecommendation).filter(
                PricingRecommendation.user_id == user_id,
                PricingRecommendation.implementation_status == 'approved',  # Match status used when user accepts a recommendation
                PricingRecommendation.reevaluation_date > today
            ).all()
            
            # If no active recommendations, return original results
            if not active_recommendations:
                logger.info("No active pricing recommendations found to exclude")
                return data_collection_results
                
            # Create a set of item IDs to exclude
            exclude_item_ids = {str(rec.item_id) for rec in active_recommendations}
            logger.info(f"Found {len(exclude_item_ids)} items with active pricing recommendations")
            
            # Process the data collection results to remove excluded items
            if isinstance(filtered_results, dict) and 'content' in filtered_results:
                content = filtered_results['content']
                
                # Extract JSON content if wrapped in markdown code blocks
                if '```json' in content and '```' in content:
                    json_start = content.find('```json') + 7
                    json_end = content.rfind('```')
                    
                    if json_start > 6 and json_end > json_start:
                        json_content = content[json_start:json_end].strip()
                        
                        # Parse the JSON string into a list of items
                        try:
                            items = json.loads(json_content)
                            # Filter out items with active recommendations
                            filtered_items = [item for item in items if str(item.get("item_id")) not in exclude_item_ids]
                            
                            # Update the content with filtered items
                            filtered_json = json.dumps(filtered_items, indent=2)
                            filtered_results['content'] = content[:json_start] + filtered_json + content[json_end:]
                            
                            logger.info(f"Filtered out {len(items) - len(filtered_items)} items with active recommendations")
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse data collection JSON: {str(e)}")
            # Fallback to old approach
            elif isinstance(filtered_results, dict) and 'items' in filtered_results:
                items = filtered_results.get('items', [])
                filtered_results['items'] = [item for item in items if str(item.get("item_id")) not in exclude_item_ids]
                logger.info(f"Filtered out {len(items) - len(filtered_results['items'])} items with active recommendations")
                
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error filtering active recommendations: {str(e)}")
            logger.exception(e)  # More detailed error logging
            # Return original results in case of error
            return data_collection_results
    
    def _aggregate_results(self, data_collection_results: Dict[str, Any], 
                           competitor_results: List[Dict[str, Any]], 
                           market_research_results: List[Dict[str, Any]],
                           context: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate all results by item ID
        
        Args:
            data_collection_results: Results from DataCollectionAgent
            competitor_results: Results from TestDBAgent
            market_research_results: Results from TestWebAgent
            
        Returns:
            Dict where keys are item_ids and values are consolidated data for each item
        """
        aggregated_data = {}
        
        # Step 1: Process data collection results
        try:
            db = context.get("db")
            # Data collection results come as a dict with 'status' and 'content' keys
            # The content is a JSON string wrapped in markdown code blocks
            if isinstance(data_collection_results, dict) and 'content' in data_collection_results:
                content = data_collection_results['content']
                
                # Extract JSON content if wrapped in markdown code blocks
                if '```json' in content and '```' in content:
                    json_start = content.find('```json') + 7
                    json_end = content.rfind('```')
                    if json_start > 6 and json_end > json_start:
                        json_content = content[json_start:json_end].strip()
                        
                        # Parse the JSON string into a list of items
                        try:
                            import json
                            items = json.loads(json_content)
                            logger.info(f"Successfully parsed {len(items)} items from data collection JSON")
                            
                            # Initialize aggregated data with items from data collection
                            for item in items:
                                item_id = str(item.get("item_id"))
                
                                # Get the most recent pricing recommendation for this item
                                latest_recommendation = db.query(models.PricingRecommendation).filter(
                                    (models.PricingRecommendation.item_id == item_id) & 
                                    (models.PricingRecommendation.implementation_status == "approved")
                                ).order_by(models.PricingRecommendation.created_at.desc()).first()
                                if latest_recommendation:
                                    self.logger.info(f"Latest recommendation for item {item_id}: {latest_recommendation.reevaluation_date}")
                                # Check if reevaluation date is approaching
                                if latest_recommendation and latest_recommendation.reevaluation_date and isinstance(latest_recommendation.reevaluation_date, datetime):
                                    # Use naive datetime objects for both sides of comparison
                                    if latest_recommendation.reevaluation_date < datetime.utcnow():
                                        self.logger.info("Adding item to aggregated data")
                                        self.logger.warning(item.get("item_name"))
                                        self.logger.info(latest_recommendation.reevaluation_date)
                                        self.logger.info(datetime.utcnow())
                                        aggregated_data[item_id] = {
                                            "name": item.get("item_name"),
                                            "basic_info": item
                                        }
                                else:
                                    self.logger.info("Adding item to aggregated data")
                                    aggregated_data[item_id] = {
                                        "name": item.get("item_name"),
                                        "basic_info": item
                                    }
                            self.logger.info(f"Aggregated {len(aggregated_data)} items")
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse data collection JSON: {str(e)}")
            # Fallback to old approach
            elif isinstance(data_collection_results, dict) and 'items' in data_collection_results:
                self.logger.info("Fallback to old approach")
                for item in data_collection_results.get('items', []):
                    item_id = str(item.get("item_id"))
                    aggregated_data[item_id] = {
                        "name": item.get("item_name"),
                        "basic_info": item
                    }
                    
            # Try to extract LLM analysis if it exists
            try:
                if isinstance(data_collection_results, dict) and 'llm_analysis' in data_collection_results and isinstance(data_collection_results['llm_analysis'], list):
                    for item in data_collection_results['llm_analysis']:
                        item_id = str(item.get("item_id"))
                        if item_id in aggregated_data:
                            aggregated_data[item_id]["llm_analysis"] = item
            except Exception as e:
                logger.error(f"Error parsing LLM analysis: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing data collection results: {str(e)}")
            logger.error(f"Data collection results type: {type(data_collection_results)}")
            logger.error(f"Data collection results keys: {data_collection_results.keys() if isinstance(data_collection_results, dict) else 'Not a dict'}") 
        # Step 2: Process competitor results
        self.logger.warning(aggregated_data)
        try:
            for comp_item in competitor_results:
                item_id = str(comp_item.get("item_id"))
                if item_id in aggregated_data:
                    aggregated_data[item_id]["competitor_analysis"] = {
                        "competitive_position": comp_item.get("competitive_position"),
                        "price_gap": comp_item.get("price_gap"),
                        "competitor_prices": comp_item.get("competitor_prices", {}),
                        "recommendation": comp_item.get("recommendation"),
                        "sources": comp_item.get("sources", [])
                    }
        except Exception as e:
            logger.error(f"Error processing competitor results: {str(e)}")
        
        # Step 3: Process market research results
        try:
            for research_item in market_research_results:
                item_id = str(research_item.get("item_id"))
                if item_id in aggregated_data:
                    aggregated_data[item_id]["market_research"] = {
                        "research_summary": research_item.get("research_summary"),
                        "sources": research_item.get("sources", [])
                    }
        except Exception as e:
            logger.error(f"Error processing market research results: {str(e)}")

        # Log summary information instead of entire data structures
        if isinstance(data_collection_results, dict) and 'content' in data_collection_results:
            logger.info(f"Data Collection Results: JSON content found")
        else:
            logger.info(f"Data Collection Results: {len(data_collection_results.get('items', []) if isinstance(data_collection_results, dict) else [])} items processed")
        logger.info(f"Competitor Results: {len(competitor_results) if competitor_results else 0} items analyzed")
        logger.info(f"Market Research Results: {len(market_research_results) if market_research_results else 0} items researched")
        # Log summary of aggregated results
        logger.info(f"Aggregated {len(aggregated_data)} items with combined pricing data")
        
        # Sample the first item for debugging purposes
        if aggregated_data:
            sample_item_id = next(iter(aggregated_data))
            sample_item = aggregated_data[sample_item_id]
            logger.info(f"Sample aggregated item (ID: {sample_item_id}): {sample_item.get('name', 'Unknown')}")
            logger.info(f"Data sources for sample item: {', '.join([k for k in sample_item.keys() if k != 'name'])}")
        
        return aggregated_data


    async def _generate_price_recommendations(self, aggregated_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate pricing recommendations using LLM based on aggregated data
        
        Args:
            aggregated_data: Dictionary with aggregated results from all agents
            
        Returns:
            List of pricing recommendations with item_id, item_name, old_price, suggested_price, and rationale
        """
        try:
            # Prepare the data for LLM consumption
            items_for_analysis = []
            for item_id, item_data in aggregated_data.items():
                # Extract current price from basic info if available
                current_price = None
                if "basic_info" in item_data:
                    basic_info = item_data["basic_info"]
                    if "item_basics" in basic_info:
                        # Try to extract price from item_basics string
                        basics_parts = basic_info["item_basics"].split("|") if isinstance(basic_info["item_basics"], str) else []
                        if len(basics_parts) >= 4:
                            try:
                                current_price = basics_parts[3].strip()
                            except (IndexError, ValueError):
                                pass
                
                item_summary = {
                    "item_id": item_id,
                    "item_name": item_data.get("name", "Unknown"),
                    "current_price": current_price
                }
                
                # Add data from each agent if available
                if "basic_info" in item_data:
                    for key, value in item_data["basic_info"].items():
                        if key not in ["item_id", "item_name"]:
                            item_summary[key] = value
                            
                if "competitor_analysis" in item_data:
                    item_summary["competitor_analysis"] = item_data["competitor_analysis"]
                    
                if "market_research" in item_data:
                    item_summary["market_research"] = item_data["market_research"]
                
                items_for_analysis.append(item_summary)
            
            # Create prompt for the LLM
            prompt = f"""
You are a pricing optimization expert analyzing data for {len(items_for_analysis)} items in a business.

For each item, review the consolidated data and recommend whether to change the price and by how much.
Your analysis should consider:
1. Sales metrics and elasticity indicators
2. Competitive position and pricing gaps
3. Cost dynamics and margins
4. Market research insights
5. Customer segments and price sensitivity

Here is the data for analysis:
{json.dumps(items_for_analysis, indent=2)}

For each item, provide a structured pricing recommendation with:
1. item_id: The item's ID
2. item_name: The name of the item
3. current_price: The current price (if available)
4. suggested_price: Your recommended price (with $ symbol)
5. change_percentage: The percentage change from current price (e.g., +5% or -3%)
6. re_evaluation_days: Number of days to keep this price before re-evaluating (14-90 days)
7. rationale: A brief explanation of your recommendation based on the data

Provide your response as a JSON array of recommendation objects. Be precise with your price suggestions.
"""
            
            # Call Claude's API directly instead of using self.call_llm
            # Claude API requires system message to be separate from the messages array
            messages = [{"role": "system", "content": prompt}]
            # response = self.call_llm(messages)
            # GPT costs practically nothing per call - claude is close to $0.20 for the analysis. Noticeably better results with claude
            try:
                # Initialize the Anthropic client
                anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
                
                # Call Claude's API - note the system parameter is separate from messages
                claude_response = anthropic_client.messages.create(
                    model="claude-opus-4-20250514",  # Use appropriate Claude model version
                    max_tokens=8192,
                    system=prompt,
                    messages=[{"role": "user", "content": "{}".format(messages)}]
                )
                
                # Format response to match the expected structure
                response = {
                    "content": claude_response.content[0].text,
                    "usage": {
                        "prompt_tokens": claude_response.usage.input_tokens,
                        "completion_tokens": claude_response.usage.output_tokens,
                        "total_tokens": claude_response.usage.input_tokens + claude_response.usage.output_tokens
                    }
                }
                
                logger.info(f"Successfully called Claude API for pricing recommendations")
                logger.info(response)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error calling Claude API: {error_msg}")
                response = {
                    "content": f"ERROR: Failed to call Claude API - {error_msg}",
                    "usage": None,
                    "error": "api_error"
                }
            
            # Extract recommendations from the response
            recommendations = []
            if response and "content" in response:
                content = response["content"]
                logger.info("Received LLM response for pricing recommendations")
                
                # Handle the case where the content is wrapped in code blocks
                try:
                    # First try to extract JSON from code blocks
                    if "```json" in content and "```" in content:
                        json_start = content.find("```json") + 7
                        json_end = content.rfind("```")
                        if json_start > 6 and json_end > json_start:
                            json_content = content[json_start:json_end].strip()
                            recommendations = json.loads(json_content)
                            logger.info(f"Successfully parsed {len(recommendations)} pricing recommendations from JSON code block")
                    # Try regular code block if no JSON block found
                    elif "```" in content:
                        json_start = content.find("```") + 3
                        json_end = content.rfind("```")
                        if json_start > 3 and json_end > json_start:
                            json_content = content[json_start:json_end].strip()
                            recommendations = json.loads(json_content)
                            logger.info(f"Successfully parsed {len(recommendations)} pricing recommendations from code block")
                    # Try parsing the whole content as JSON
                    else:
                        recommendations = json.loads(content)
                        logger.info(f"Successfully parsed {len(recommendations)} pricing recommendations from raw content")
                except json.JSONDecodeError as e:
                    # If the above parsing methods fail, extract JSON using regex as a fallback
                    logger.warning(f"Standard JSON parsing failed: {str(e)}. Attempting alternative parsing.")
                    try:
                        # Check if we can use the raw response directly
                        if "raw_response" in content:
                            # The user provided a sample of previously failed output containing valid JSON
                            import re
                            json_pattern = r'\[\s*\{.*?\}\s*\]'
                            json_match = re.search(json_pattern, content, re.DOTALL)
                            if json_match:
                                potential_json = json_match.group(0)
                                recommendations = json.loads(potential_json)
                                logger.info(f"Successfully parsed {len(recommendations)} pricing recommendations using regex")
                            else:
                                logger.error("Could not find JSON array pattern in content")
                                recommendations = [{"error": "Failed to parse recommendations", "raw_response": content[:500] + "..."}]
                        else:
                            # Just return the raw content for debugging
                            logger.error(f"All JSON parsing methods failed")
                            recommendations = [{"error": "Failed to parse recommendations", "raw_response": content[:500] + "..."}]
                    except Exception as inner_e:
                        logger.error(f"Alternative parsing also failed: {str(inner_e)}")
                        # Include a portion of the raw response for debugging
                        recommendations = [{"error": "Failed to parse recommendations", "raw_response": content[:500] + "..."}]
                except Exception as e:
                    logger.error(f"Unexpected error parsing recommendations: {str(e)}")
                    recommendations = [{"error": f"Unexpected error: {str(e)}", "raw_response": content[:500] + "..."}]
            else:
                logger.error("No response content from LLM")
                
            return recommendations
        except Exception as e:
            logger.error(f"Error generating price recommendations: {str(e)}")
            return [{"error": str(e)}]


# For direct testing
async def test_aggregate_agent():
    """Test the aggregate agent with sample data"""
    agent = AggregatePricingAgent()
    context = {
        "user_id": 1,
        "db": None,  # This would be a real DB session in production
        "test_mode": True,
        "business_name": "Test Business",
        "industry": "Coffee Shop",
        "location": "Austin, Texas",
        "company_size": "Small Business"
    }
    
    result = await agent.process(context)
    print("Aggregate Agent Result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(test_aggregate_agent())

