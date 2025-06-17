"""
Aggregate Pricing Agent - Runs multiple pricing agents and aggregates their results by item ID.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
import json

from ..base_agent import BaseAgent
from .data_collection import DataCollectionAgent
from .test_db_agent import TestDBAgentWrapper
from .test_web_agent import TestWebAgentWrapper

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
            # Step 1: Run DataCollectionAgent
            logger.info("Running DataCollectionAgent")
            data_collection_results = self.data_collection_agent.process(context)
            logger.info("DataCollectionAgent completed successfully")
            
            # Create updated context with data collection results for other agents
            updated_context = context.copy()
            updated_context["data_collection_results"] = data_collection_results
            
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
                market_research_results.get("research_results", [])
            )
            
            logger.info(f"Successfully aggregated results for {len(aggregated_results)} items")
            
            # Step 5: Generate pricing recommendations based on aggregated results
            logger.info("Generating pricing recommendations using LLM")
            pricing_recommendations = await self._generate_price_recommendations(aggregated_results)
            logger.info(f"Generated pricing recommendations for {len(pricing_recommendations)} items")
            
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
    
    def _aggregate_results(self, data_collection_results: Dict[str, Any], 
                           competitor_results: List[Dict[str, Any]], 
                           market_research_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
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
                                aggregated_data[item_id] = {
                                    "name": item.get("item_name"),
                                    "basic_info": item
                                }
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse data collection JSON: {str(e)}")
            # Fallback to old approach
            elif isinstance(data_collection_results, dict) and 'items' in data_collection_results:
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
            
            # Call the LLM
            messages = [{"role": "system", "content": prompt}]
            response = self.call_llm(messages)
            
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
