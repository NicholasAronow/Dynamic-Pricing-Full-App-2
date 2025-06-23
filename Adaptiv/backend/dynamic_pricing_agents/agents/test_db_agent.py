"""
WORKING VERSION
Competitor tracking agent that analyzes menu items vs competitors and performs competitive analysis.
"""
import asyncio
import logging
import time
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from agents import Agent, WebSearchTool, Runner, trace, gen_trace_id
from agents.model_settings import ModelSettings
from agents.agent_output import AgentOutputSchema
import models
from models import CompetitorPriceHistory

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_data_collection_output(file_path=None, file_content=None):
    """
    Parse the data collection output file or content string.
    Returns a list of menu item dictionaries.
    """
    if file_path and not file_content:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading data collection file: {e}")
            return []
    else:
        content = file_content
    
    try:
        if 'output = """' in content:
            json_str = content.split('output = """')[1].split('""";')[0].strip()
        else:
            json_str = content.strip()
            
        if json_str.endswith(',]'):
            json_str = json_str[:-2] + ']'
        
        data = json.loads(json_str)
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"Error parsing data collection output: {e}", exc_info=True)
        return []

# Instructions for the competitor analysis workflow
COMPETITOR_INSTRUCTIONS = """
You are a competitor analysis agent determining which menu items need competitive analysis. Follow this exact workflow:

PHASE 1: ANALYZE MENU DATA
Review all menu items and identify which items have competitor data or should be tracked against competitors:
- Items with explicit competitor pricing information
- Items in competitive categories
- Items where market position is important

PHASE 2: COMPETITIVE POSITIONING ANALYSIS
For each relevant menu item:
1. Analyze price differential vs competitors
2. Determine if we're positioned as value, parity, or premium
3. Evaluate if current pricing aligns with desired market position
4. Consider elasticity in relation to competitive positioning

PHASE 3: COMPETITOR RESEARCH
For items needing additional research:
1. Search the web for competitor information
2. Look up historical pricing data from our database
3. Analyze trends in competitor pricing strategies

PHASE 4: GENERATE RECOMMENDATIONS
For each analyzed item, provide:
- Current competitive position
- Pricing gap analysis
- Market share implications
- Suggested competitive strategy (match, premium, discount)

PHASE 5: GENERATE OUTPUT
Return a JSON array with ONLY items that have relevant competitive insights:
[
  {
    "item_id": "id",
    "item_name": "name",
    "current_price": "our price",
    "competitor_prices": {"competitor1": "price", "competitor2": "price"},
    "competitive_position": "value/parity/premium",
    "price_gap": "percentage difference",
    "recommendation": "specific pricing recommendation based on competitive analysis",
    "sources": ["url1", "url2"]
  }
]

Leave out items with no applicable competitive findings.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class CompetitorAnalysisItem(BaseModel):
    """A menu item with competitive analysis data"""
    item_id: str
    item_name: str
    current_price: str
    competitor_prices: Dict[str, str]
    competitive_position: str
    price_gap: str
    recommendation: str
    sources: List[str]

class CompetitorAnalysisResults(BaseModel):
    """A list of menu items with competitive analysis data"""
    insights: List[CompetitorAnalysisItem]

# Create the competitor tracking agent with strict mode disabled
competitor_tracking_agent = Agent(
    name="CompetitorTrackingAgent",
    instructions=COMPETITOR_INSTRUCTIONS,
    tools=[WebSearchTool()],
    model="gpt-4o",
    output_type=AgentOutputSchema(CompetitorAnalysisResults, strict_json_schema=False),
    model_settings=ModelSettings(max_tokens=5000)
)

class TestDBAgentWrapper:
    """Wrapper for running the competitor tracking agent."""
    
    def __init__(self):
        """Initialize the agent wrapper."""
        self.agent = competitor_tracking_agent
        self.display_name = "Competitor Tracking Agent"
        self.description = "Analyzes menu items vs competitors and performs competitive analysis"
        self.logger = logger
        
    def _safe_get_competitor_data(self, report):
        """Safely extract competitor data from a report with comprehensive error handling"""
        try:
            # Handle None values
            if not report or not hasattr(report, 'competitor_data'):
                self.logger.warning(f"Report missing competitor_data attribute")
                return None
                
            competitor_data = report.competitor_data
            
            # Handle None competitor_data
            if competitor_data is None:
                self.logger.warning(f"Found null competitor_data for report ID {getattr(report, 'id', 'unknown')}")
                return None
            
            # If it's already a dictionary, validate and return
            if isinstance(competitor_data, dict):
                if 'name' in competitor_data:
                    return competitor_data
                else:
                    self.logger.warning(f"Dict competitor_data missing 'name' key for report ID {getattr(report, 'id', 'unknown')}")
                    return None
            
            # If it's a string, try to parse as JSON
            elif isinstance(competitor_data, str):
                if not competitor_data.strip():  # Empty string
                    self.logger.warning(f"Empty competitor_data string for report ID {getattr(report, 'id', 'unknown')}")
                    return None
                    
                try:
                    parsed_data = json.loads(competitor_data)
                    if isinstance(parsed_data, dict) and 'name' in parsed_data:
                        return parsed_data
                    else:
                        self.logger.warning(f"Parsed JSON is not a dict with 'name' key for report ID {getattr(report, 'id', 'unknown')}")
                        return None
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse competitor_data as JSON for report ID {getattr(report, 'id', 'unknown')}: {e}")
                    return None
            
            # Handle other types
            else:
                self.logger.warning(f"Unexpected competitor_data type: {type(competitor_data)} for report ID {getattr(report, 'id', 'unknown')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Unexpected error processing competitor_data for report ID {getattr(report, 'id', 'unknown')}: {e}")
            return None
        
    def _collect_competitor_data(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Collect competitor pricing data from database for analysis"""
        self.logger.info(f"Collecting competitor data for user {user_id}")
        
        try:
            # Validate user_id
            if not user_id or not isinstance(user_id, (int, str)):
                self.logger.error(f"Invalid user_id: {user_id}")
                return {"competitors": []}
            
            # Convert to int if string
            user_id = int(user_id)
            
            # Get selected competitor reports from the database
            competitor_reports = db.query(models.CompetitorReport).filter(
                models.CompetitorReport.user_id == user_id,    
                models.CompetitorReport.is_selected == True  # Only get selected competitors
            ).order_by(desc(models.CompetitorReport.created_at)).all()
            
            self.logger.info(f"Found {len(competitor_reports)} selected competitor reports")
            
            # Extract competitors data from reports
            competitors = []
            for report in competitor_reports:
                competitor_data = self._safe_get_competitor_data(report)
                
                if competitor_data:
                    competitors.append({
                        "name": str(competitor_data.get('name', '')),
                        "address": str(competitor_data.get('address', '')),
                        "category": str(competitor_data.get('category', '')),
                        "report_id": getattr(report, 'id', 0)
                    })
            
            self.logger.info(f"Successfully processed {len(competitors)} competitors")
            
            # Get our menu items for matching
            our_menu_items = db.query(models.Item).filter(models.Item.user_id == user_id).all()
            our_item_names = [item.name.lower() for item in our_menu_items if item and hasattr(item, 'name') and item.name]
            self.logger.info(f"Found {len(our_menu_items)} menu items for matching")
            
            # Get historical competitor prices for comparison (past 30 days)
            historical_prices = self._get_historical_competitor_prices(db, user_id, days_back=30)
            
            # Track matched competitor items
            competitors_dict = {}
            
            # Process each competitor
            for competitor in competitors:
                if not competitor or not isinstance(competitor, dict):
                    continue
                    
                competitor_name = competitor.get("name", "")
                if not competitor_name:
                    continue
                
                try:
                    # Get the latest batch of menu items for this competitor
                    latest_batch = db.query(models.CompetitorItem.batch_id, 
                                            func.max(models.CompetitorItem.sync_timestamp).label('latest'))\
                        .filter(models.CompetitorItem.competitor_name == competitor_name)\
                        .group_by(models.CompetitorItem.batch_id)\
                        .order_by(desc('latest')).first()
                    
                    if not latest_batch:
                        self.logger.info(f"No menu items found for competitor: {competitor_name}")
                        continue
                        
                    latest_batch_id = latest_batch[0]
                    
                    # Get all menu items in the latest batch for this competitor
                    menu_items = db.query(models.CompetitorItem).filter(
                        models.CompetitorItem.competitor_name == competitor_name,
                        models.CompetitorItem.batch_id == latest_batch_id
                    ).all()
                    
                    self.logger.info(f"Found {len(menu_items)} menu items for {competitor_name}")
                    
                    # Add competitor info to the dictionary
                    if competitor_name not in competitors_dict:
                        competitors_dict[competitor_name] = {
                            "name": competitor_name,
                            "address": competitor.get("address", ""),
                            "category": competitor.get("category", ""),
                            "items": []
                        }
                    
                    # Process each menu item - only include items that match with our menu
                    for item in menu_items:
                        if not item or not hasattr(item, 'item_name') or not item.item_name:
                            continue
                        
                        # Check if item matches any of our menu items
                        if self._is_item_match(item.item_name, our_item_names):
                            # Find price trend - convert to tuple and ensure strings
                            key = (str(competitor_name), str(item.item_name))
                            trend = "stable"
                            if key in historical_prices:
                                trend = self._get_price_trend(historical_prices[key])
                            
                            # Convert any numeric values to float safely
                            try:
                                price = float(item.price) if item.price is not None else 0.0
                            except (ValueError, TypeError):
                                price = 0.0
                            
                            # Add item to competitor dictionary with safe accessors
                            competitors_dict[competitor_name]["items"].append({
                                "name": str(item.item_name),
                                "price": price,
                                "category": str(getattr(item, 'category', '')),
                                "price_trend": trend
                            })
                            
                except Exception as e:
                    self.logger.error(f"Error processing competitor {competitor_name}: {e}")
                    continue
            
            # Return only competitors with matched items
            result_competitors = [comp for comp in competitors_dict.values() if comp.get("items")]
            
            self.logger.info(f"Returning {len(result_competitors)} competitors with matched items")
            
            return {
                "competitors": result_competitors
            }
            
        except Exception as e:
            self.logger.error(f"Error in _collect_competitor_data: {e}", exc_info=True)
            return {"competitors": []}
    
    def _is_item_match(self, comp_item_name, our_items):
        """Check if competitor item matches any of our items using fuzzy matching"""
        if not comp_item_name or not our_items:
            return False
            
        try:
            comp_words = str(comp_item_name).lower().split()
            
            for our_item_name in our_items:
                if not our_item_name:
                    continue
                    
                our_words = str(our_item_name).split()
                
                matched_words = 0
                for our_word in our_words:
                    if any(comp_word.find(our_word) >= 0 or our_word.find(comp_word) >= 0 
                          for comp_word in comp_words):
                        matched_words += 1
                
                # Consider similar if 70% of words match (same threshold as frontend)
                if len(our_words) > 0 and len(comp_words) > 0:
                    match_ratio = matched_words / max(len(our_words), len(comp_words))
                    if match_ratio >= 0.7:
                        return True
                        
            return False
        except Exception as e:
            self.logger.error(f"Error in fuzzy matching: {e}")
            return False
    
    def _get_historical_competitor_prices(self, db: Session, user_id: int, 
                                        days_back: int = 30) -> Dict[tuple, Dict]:
        """Get historical competitor prices for comparison"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            historical = db.query(CompetitorPriceHistory).filter(
                CompetitorPriceHistory.user_id == user_id,
                CompetitorPriceHistory.captured_at >= cutoff_date
            ).all()
            
            # Group by competitor-item combination
            price_history = {}
            for entry in historical:
                if not entry or not hasattr(entry, 'competitor_name') or not hasattr(entry, 'item_name'):
                    continue
                    
                key = (str(entry.competitor_name), str(entry.item_name))
                if key not in price_history:
                    price_history[key] = {
                        'prices': [],
                        'dates': []
                    }
                
                if hasattr(entry, 'price') and entry.price is not None:
                    price_history[key]['prices'].append(entry.price)
                if hasattr(entry, 'captured_at') and entry.captured_at:
                    price_history[key]['dates'].append(entry.captured_at)
                if hasattr(entry, 'price') and entry.price is not None:
                    price_history[key]['price'] = entry.price  # Latest price
            
            return price_history
            
        except Exception as e:
            self.logger.error(f"Error getting historical prices: {e}")
            return {}
    
    def _get_price_trend(self, history: Dict) -> str:
        """Determine price trend from historical data"""
        try:
            if not history or not isinstance(history, dict):
                return "stable"
                
            prices = history.get('prices', [])
            if not prices or len(prices) < 2:
                return "stable"
            
            # Simple trend: compare first and last
            first_price = float(prices[0]) if prices[0] is not None else 0
            last_price = float(prices[-1]) if prices[-1] is not None else 0
            
            if first_price == 0:
                return "stable"
                
            if last_price > first_price * 1.05:
                return "increasing"
            elif last_price < first_price * 0.95:
                return "decreasing"
            else:
                return "stable"
                
        except Exception as e:
            self.logger.error(f"Error calculating price trend: {e}")
            return "stable"
        
    def _safe_parse_menu_items(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Safely parse menu items from context with fallback"""
        try:
            # First try to get data from data_collection_results in context
            data_collection_results = context.get("data_collection_results", {})
            if data_collection_results:
                # Try to get menu items from data collection results
                menu_items = data_collection_results.get("menu_items", [])
                if menu_items and isinstance(menu_items, list):
                    self.logger.info(f"Using menu items from data_collection_results: {len(menu_items)} items")
                    return menu_items
            
            # Then try to get menu items directly from context
            menu_items = context.get("menu_items")
            if menu_items and isinstance(menu_items, list):
                # Validate each item is a dictionary
                valid_items = []
                for idx, item in enumerate(menu_items):
                    if isinstance(item, dict):
                        valid_items.append(item)
                    else:
                        self.logger.warning(f"Skipping non-dictionary item at index {idx}: {type(item)}")
                
                if valid_items:
                    return valid_items
            
            # Fallback to sample data
            try:
                from ..sample_outputs.data_collection_output import output
                if isinstance(output, list):
                    self.logger.warning("Using fallback sample data")
                    return output
            except ImportError:
                self.logger.warning("Could not import sample data")
            
            # Final fallback - create basic menu structure
            return [
                {
                    "item_id": "SAMPLE001",
                    "item_name": "Sample Item",
                    "current_price": "10.00",
                    "category": "General",
                    "item_basics": "Sample item for testing",
                    "competitive_position": "Unknown",
                    "elasticity_indicators": "Unknown",
                    "optimization_signals": "None"
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Error parsing menu items: {e}")
            return []
        
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # First try to parse menu items from data collection results if it contains a content field with JSON
        data_collection_results = context.get("data_collection_results", {})
        menu_items = []
        
        # Check if the data_collection_results contains a content field with JSON
        if data_collection_results and 'content' in data_collection_results:
            content = data_collection_results.get('content', '')
            self.logger.info(f"Found content field in data_collection_results")
            
            # Check if content is a string containing markdown JSON block
            if isinstance(content, str) and '```json' in content:
                # Extract the JSON from markdown code block
                self.logger.info(f"CONTENT: {content}")
                try:
                    # More robust JSON extraction handling various markdown formats
                    import re
                    json_match = re.search(r'```json\s*([\s\S]*?)```', content)
                    if json_match:
                        json_str = json_match.group(1).strip()
                        menu_items_from_json = json.loads(json_str)
                        if isinstance(menu_items_from_json, list) and len(menu_items_from_json) > 0:
                            self.logger.info(f"Successfully parsed {len(menu_items_from_json)} items from data collection JSON")
                            # Store the parsed menu items in the context for later use
                            context["menu_items"] = menu_items_from_json
                    else:
                        self.logger.error("No JSON content found between markdown code blocks")
                except Exception as e:
                    self.logger.error(f"Failed to parse JSON from content: {str(e)}")
        """
        Process menu items with competitor analysis.
        
        Args:
            context: Context dictionary containing menu data
            
        Returns:
            Dict with competitor analysis results mapped to items
        """
        try:
            # Safely parse menu items
            db = context.get("db")
            user_id = context.get("user_id")
            menu_items = self._get_menu_items(db, user_id)
            
            if not menu_items:
                return {
                    "success": False,
                    "error": "No valid menu items found in context",
                    "competitor_results": []
                }
            
            # Build the query with menu data
            query = """
            Analyze these menu items and conduct competitor analysis. Focus on items with competitive positioning data.
            Identify which of our menu items are relevant for competitor analysis, and perform a detailed competitor analysis.
            
            Menu Items:
            """
            
            # Add menu items to query
            for idx, item in enumerate(menu_items):
                # Use get() method for all keys to avoid KeyError
                item_name = item.get('item_name', item.get('name', f"Item {idx+1}"))
                item_price = item.get('current_price', item.get('price', '?'))
                
                query += f"\n{idx + 1}. {item_name} - ${item_price}\n"
                query += f"   Category: {item.get('category', 'General')}\n"
                
                # Add sales data if available
                if item.get('sales_30_days'):
                    query += f"   Sales (30 days): {item.get('sales_30_days')}\n"
                    
                # Add elasticity if available
                if item.get('elasticity'):
                    query += f"   Price Elasticity: {item.get('elasticity')}\n"
                    
                # Add competitor data if available
                if item.get('competitive_position'):
                    query += f"   Current Competitive Position: {item.get('competitive_position')}\n"
                    
                query += "\n"
                    
            # Add competitor data from database if available
            db = context.get("db")
            user_id = context.get("user_id")
            competitors_info = None
            
            if db and user_id:
                try:
                    # Retrieve competitor data from database
                    competitors_info = self._collect_competitor_data(db, user_id)
                    if competitors_info and competitors_info.get("competitors"):
                        query += "\n\nCurrent Competitor Data from Database:\n"
                        
                        for competitor in competitors_info["competitors"]:
                            if not isinstance(competitor, dict):
                                continue
                                
                            query += f"\nCompetitor: {competitor.get('name', 'Unknown')}\n"
                            query += f"Category: {competitor.get('category', 'Unknown')}\n"
                            query += "Items:\n"
                            
                            for item in competitor.get("items", []):
                                if isinstance(item, dict):
                                    item_name = item.get('name', 'Unknown')
                                    item_price = item.get('price', 0)
                                    price_trend = item.get('price_trend', 'stable')
                                    
                                    query += f"  - {item_name}: ${item_price:.2f}"
                                    if price_trend:
                                        query += f" (Price trend: {price_trend})"
                                    query += "\n"
                        
                        self.logger.info(f"Added data for {len(competitors_info['competitors'])} competitors")
                    else:
                        self.logger.info("No competitor data found in database")
                except Exception as e:
                    self.logger.error(f"Error retrieving competitor data: {e}")
                    # Continue without competitor data

            # Get business context from API context
            business_name = context.get('business_name', 'Your Business')
            industry = context.get('industry', 'Food Service')
            location = context.get('location', 'New York')
            company_size = context.get('company_size', 'Small Business')
            
            # Add business context for more targeted research
            business_context = f"""
            BUSINESS CONTEXT:
            - Business Name: {business_name}
            - Industry: {industry}
            - Size: {company_size}
            - Location: {location}
            """
            
            logger.info(f"Using business context: {business_name} ({industry}) in {location}")
            
            # Build comprehensive query
            comprehensive_query = query + "\n" + business_context + "\n\nMENU ITEMS:\n"
            
            for item in menu_items:
                if not isinstance(item, dict):
                    item = dict(item)
                    
                item_name = item.get('item_name', item.get('name', 'Unknown'))
                item_id = item.get('item_id', item.get('id', 'unknown'))
                
                comprehensive_query += f"\n{item_name} ({item_id}):"
                comprehensive_query += f"\n- {item.get('item_basics', 'No basics')}"
                comprehensive_query += f"\n- {item.get('competitive_position', 'No position')}"
                comprehensive_query += f"\n- {item.get('elasticity_indicators', 'No elasticity')}"
                comprehensive_query += f"\n- {item.get('optimization_signals', 'No signals')}\n"
            
            comprehensive_query += f"\nLocation: {location}"
            comprehensive_query += "\n\nNow conduct comprehensive competitor analysis and identify items with competitive positioning data."
            comprehensive_query += "\n\nAnalyze these items in the context of our competitive positioning. "
            comprehensive_query += "Compare our prices to competitor prices. Identify gaps and opportunities. "
            comprehensive_query += "Return specific recommendations based on competitive analysis that apply directly to our menu items."
            
            logger.info(f"Starting competitor analysis for {len(menu_items)} items")
            start_time = time.time()
            
            # Generate trace ID
            trace_id = gen_trace_id()
            trace_url = f"https://platform.openai.com/traces/trace?trace_id={trace_id}"
            logger.info(f"Trace URL: {trace_url}")
            
            # Run the agent
            try:
                agent_response = None
                with trace("Competitor Analysis", trace_id=trace_id):
                    try:
                        agent_response = await Runner.run(self.agent, comprehensive_query)
                    except Exception as e:
                        logger.error(f"Agent invoke error: {str(e)}")
                        # Extract output from any exception response
                        error_message = str(e)
                        if "trace_id" in error_message:
                            return {
                                "success": False,
                                "error": error_message,
                                "trace_id": trace_id,
                                "trace_url": trace_url,
                                "competitor_results": []
                            }
                        raise e
                
                # Parse the results safely
                competitor_results = self._safe_parse_agent_response(agent_response)
                
            except Exception as e:
                logger.error(f"Error running competitor analysis: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                    "trace_id": trace_id,
                    "trace_url": trace_url,
                    "competitor_results": []
                }
                
            execution_time = time.time() - start_time
            logger.info(f"Competitor analysis completed in {execution_time:.2f} seconds")
            
            # Create detailed summary info
            items_with_analysis = len([r for r in competitor_results if r.get("recommendation")])
            logger.info(f"Found competitive insights for {items_with_analysis} items out of {len(menu_items)} total items")
            
            # Log each competitor analysis item for debugging
            for item in competitor_results:
                if isinstance(item, dict):
                    item_id = item.get("item_id", "unknown")
                    item_name = item.get("item_name", "unknown")
                    rec_len = len(str(item.get("recommendation", "")))
                    sources = item.get("sources", [])
                    logger.info(f"Item {item_id} ({item_name}): {rec_len} chars recommendation, {len(sources)} sources")
            
            summary = f"Analyzed {len(menu_items)} items, found competitive insights for {items_with_analysis} items"
            
            return {
                "success": True,
                "summary": summary,
                "competitor_results": competitor_results,
                "execution_time": f"{execution_time:.2f}s",
                "trace_id": trace_id,
                "trace_url": trace_url,
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in process method: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "competitor_results": []
            }

    def _get_menu_items(self, db: Session, user_id: int) -> List[Dict[str, Any]]:
        """Retrieve menu items for a user"""
        self.logger.info(f"Retrieving menu items for user {user_id}")
        
        menu_items = db.query(models.Item).filter(
            models.Item.user_id == user_id
        ).all()
        
        result = []
        for item in menu_items:

            # Extract item details including the most recent reevaluation date
            item_dict = {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "current_price": item.current_price,
                "cost": item.cost,
                "description": item.description
            }
            
            # Get the most recent pricing recommendation for this item
            latest_recommendation = db.query(models.PricingRecommendation).filter(
                (models.PricingRecommendation.item_id == item.id) & 
                (models.PricingRecommendation.implementation_status == "approved")
            ).order_by(models.PricingRecommendation.created_at.desc()).first()

            if latest_recommendation:
                item_dict["reevaluation_date"] = latest_recommendation.reevaluation_date
            
            # Check if reevaluation date is approaching
            if item_dict.get("reevaluation_date") and isinstance(item_dict["reevaluation_date"], datetime):
                if item_dict["reevaluation_date"] < datetime.utcnow():
                    result.append({
                        "id": item.id,
                        "name": item.name,
                        "category": item.category,
                        "current_price": item.current_price,
                        "cost": item.cost,
                        "description": item.description
                    })
            else:
                result.append({
                        "id": item.id,
                        "name": item.name,
                        "category": item.category,
                        "current_price": item.current_price,
                        "cost": item.cost,
                        "description": item.description
                    })

            
            
            
        
        self.logger.info(f"Retrieved {len(result)} menu items")
        return result
    
    def _safe_parse_agent_response(self, agent_response) -> List[Dict[str, Any]]:
        """Safely parse agent response with comprehensive error handling"""
        competitor_results = []
        
        try:
            # Check if we got a response
            if not agent_response:
                logger.warning("No agent response found")
                return competitor_results
            
            # Log what type of response we got
            logger.info(f"Agent response type: {type(agent_response)}")
            
            # Try to access final_output first
            if hasattr(agent_response, 'final_output') and agent_response.final_output:
                response_data = agent_response.final_output
                logger.info(f"Final output type: {type(response_data)}")
                
                # Check if it's our CompetitorAnalysisResults model
                if hasattr(response_data, 'insights'):
                    insights = response_data.insights
                    if isinstance(insights, (list, tuple)):
                        for insight in insights:
                            insight_dict = self._safe_extract_insight(insight)
                            if insight_dict:
                                competitor_results.append(insight_dict)
                        logger.info(f"Parsed {len(competitor_results)} insights from final_output.insights")
                    else:
                        logger.warning(f"Insights is not a list/tuple: {type(insights)}")
                        
                # Try to parse as dictionary if no insights attribute
                elif isinstance(response_data, dict):
                    insights = response_data.get('insights', [])
                    if isinstance(insights, (list, tuple)):
                        for item in insights:
                            if isinstance(item, dict):
                                insight_dict = self._safe_extract_insight_from_dict(item)
                                if insight_dict:
                                    competitor_results.append(insight_dict)
                            else:
                                logger.warning(f"Skipping non-dict insight: {type(item)}")
                    else:
                        logger.warning("No insights list found in response_data dictionary")
                        
                # Try JSON parsing as last resort
                else:
                    try:
                        json_str = str(response_data)
                        parsed_data = json.loads(json_str)
                        if isinstance(parsed_data, dict) and 'insights' in parsed_data:
                            for item in parsed_data['insights']:
                                if isinstance(item, dict):
                                    insight_dict = self._safe_extract_insight_from_dict(item)
                                    if insight_dict:
                                        competitor_results.append(insight_dict)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.error(f"JSON parsing failed: {e}")
            else:
                logger.warning("No final_output found in agent response")
                
        except Exception as e:
            logger.error(f"Error processing agent response: {str(e)}", exc_info=True)
        
        return competitor_results
    
    def _safe_extract_insight(self, insight) -> Optional[Dict[str, Any]]:
        """Safely extract insight data from Pydantic model or dict"""
        try:
            return {
                "item_id": str(getattr(insight, 'item_id', '')),
                "item_name": str(getattr(insight, 'item_name', '')),
                "current_price": str(getattr(insight, 'current_price', '')),
                "competitor_prices": dict(getattr(insight, 'competitor_prices', {})),
                "competitive_position": str(getattr(insight, 'competitive_position', '')),
                "price_gap": str(getattr(insight, 'price_gap', '')),
                "recommendation": str(getattr(insight, 'recommendation', '')),
                "sources": list(getattr(insight, 'sources', []))
            }
        except Exception as e:
            logger.error(f"Error extracting insight: {e}")
            return None
    
    def _safe_extract_insight_from_dict(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Safely extract insight data from dictionary"""
        try:
            return {
                "item_id": str(item.get('item_id', '')),
                "item_name": str(item.get('item_name', '')),
                "current_price": str(item.get('current_price', '')),
                "competitor_prices": dict(item.get('competitor_prices', {})) if isinstance(item.get('competitor_prices'), dict) else {},
                "competitive_position": str(item.get('competitive_position', '')),
                "price_gap": str(item.get('price_gap', '')),
                "recommendation": str(item.get('recommendation', '')),
                "sources": list(item.get('sources', [])) if isinstance(item.get('sources'), (list, tuple)) else []
            }
        except Exception as e:
            logger.error(f"Error extracting insight from dict: {e}")
            return None
    
    def _safe_convert_to_dict(self, agent_response) -> Optional[Dict[str, Any]]:
        """Safely convert agent response to dictionary"""
        try:
            # Handle various response formats
            if isinstance(agent_response, dict):
                return agent_response
            elif hasattr(agent_response, '__dict__'):
                return agent_response.__dict__
            elif hasattr(agent_response, 'model_dump'):
                # Handle Pydantic v2 models
                return agent_response.model_dump()
            elif hasattr(agent_response, 'dict'):
                # Handle Pydantic v1 models
                return agent_response.dict()
            else:
                # Last resort - try JSON parsing
                try:
                    return json.loads(str(agent_response))
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Couldn't convert response to dict: {str(agent_response)[:100]}")
                    return None
        except Exception as e:
            logger.error(f"Error converting to dict: {e}")
            return None

# Standalone test function
async def test_competitor_workflow():
    """Test the complete competitor analysis workflow."""
    wrapper = TestDBAgentWrapper()
    
    # Test with sample context
    context = {
        "location": "Austin, Texas",  # Can customize location
        "menu_items": [
            {
                "item_id": "LATTE001",
                "item_name": "Latte",
                "current_price": "5.95",
                "category": "Beverages",
                "item_basics": "Price: $5.95 | Cost: $1.20 | Margin: 79.8%",
                "competitive_position": "Market Avg: $5.25 | Premium: +11.8%",
                "elasticity_indicators": "High elasticity (E = 3.63)",
                "optimization_signals": "Consider price reduction due to high elasticity"
            },
            {
                "item_id": "BURG001", 
                "item_name": "Classic Burger",
                "current_price": "14.95",
                "category": "Entrees",
                "item_basics": "Price: $14.95 | Cost: $4.50 | Margin: 69.9%",
                "competitive_position": "Market Avg: $13.50 | Premium: +10.7%",
                "elasticity_indicators": "Moderate elasticity (E = 2.1)",
                "optimization_signals": "Room for slight price increase"
            }
        ]
    }
    
    print("=== Starting Competitor Analysis Workflow ===")
    result = await wrapper.process(context)
    
    if result.get("success"):
        print(f"\nSummary: {result['summary']}")
        print(f"Execution Time: {result['execution_time']}")
        print(f"Trace URL: {result['trace_url']}")
        
        print("\n=== Competitor Analysis Results ===")
        for item in result['competitor_results']:
            if isinstance(item, dict):
                print(f"\n{item.get('item_name', 'Unknown')} ({item.get('item_id', 'Unknown')}):")
                print(f"Current Price: {item.get('current_price', 'Unknown')}")
                print(f"Competitor Prices: {item.get('competitor_prices', {})}")
                print(f"Competitive Position: {item.get('competitive_position', 'Unknown')}")
                print(f"Price Gap: {item.get('price_gap', 'Unknown')}")
                print(f"Recommendation: {item.get('recommendation', 'None')}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
        if result.get('trace_url'):
            print(f"Trace URL: {result['trace_url']}")

# Direct agent test
async def test_agent_directly():
    """Test the agent with a simple query."""
    query = """
    Analyze these items and conduct competitor tracking:
    
    Latte (LATTE001):
    - Price: $5.95 | Cost: $1.20 | Margin: 79.8%
    - Market Avg: $5.25 | Premium: +11.8%
    - High elasticity (E = 3.63)
    
    Classic Burger (BURG001):
    - Price: $14.95 | Cost: $4.50 | Margin: 69.9%
    - Market Avg: $13.50 | Premium: +10.7%
    - Moderate elasticity (E = 2.1)
    
    Location: Austin, Texas
    
    Analyze competitive positioning of these items, compare to competitor prices, and provide price recommendations.
    """
    
    trace_id = gen_trace_id()
    print(f"Trace: https://platform.openai.com/traces/trace?trace_id={trace_id}")
    
    try:
        with trace("Direct Agent Test", trace_id=trace_id):
            result = await Runner.run(competitor_tracking_agent, query)
            print("\nAgent Output:")
            print(result.final_output)
    except Exception as e:
        print(f"Error in direct agent test: {e}")

# Main execution
if __name__ == "__main__":
    import sys
    
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "direct":
            # Run direct agent test
            asyncio.run(test_agent_directly())
        else:
            # Run full workflow test
            asyncio.run(test_competitor_workflow())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Error running test: {e}")
        import traceback
        traceback.print_exc()