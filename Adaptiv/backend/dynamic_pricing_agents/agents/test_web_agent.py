"""
WORKING VERSION
Market research agent that conducts web searches and maps insights to menu items.
"""
import asyncio
import logging
import time
import json
from typing import Dict, Any, List
from agents import Agent, WebSearchTool, Runner, trace, gen_trace_id
from agents.model_settings import ModelSettings

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
        
        import json
        data = json.loads(json_str)
        return data
    except Exception as e:
        logger.error(f"Error parsing data collection output: {e}", exc_info=True)
        return []

# Instructions for the research workflow
RESEARCH_INSTRUCTIONS = """
You are a market research agent analyzing menu items for pricing optimization. Follow this exact workflow:

PHASE 1: CONDUCT MARKET RESEARCH
Perform comprehensive web searches on:
1. Overall [our business industry] trends
2. Key ingredient supply chain issues for our industry
3. Local market conditions and upcoming events in our location
4. Competitor pricing strategies for our industry
5. Consumer behavior for our industry

PHASE 2: ANALYZE MENU DATA
Review all menu items and identify which items the research applies to and:
- Identify what part of the research is relevant
- Explain why the research applies to the item

Use web_search for queries like:
- "[our industry] trends 2025"
- "[our industry] ingredient supply chain issues 2025"
- "[our industry] local market conditions and upcoming events in [location]"
- "[our industry] competitor pricing strategies 2025"
- "[our industry] consumer behavior 2025"

PHASE 3: MAP INSIGHTS TO ITEMS
After gathering research, analyze which insights apply to specific menu items:
- [our industry] ingredient supply chain issues → affects all items with those ingredients
- [our industry] local market conditions and upcoming events → affects items based on event type
- [our industry] competitor pricing → affects directly competing items

PHASE 4: GENERATE OUTPUT
Return a JSON array with ONLY items that have relevant research insights:
[
  {
    "item_id": "id",
    "item_name": "name", 
    "research_summary": "Specific insights from research that apply to this item",
    "sources": ["url1", "url2"]
  }
]

Leave out items with no applicable research findings.
"""
from pydantic import BaseModel

class MarketSearchItem(BaseModel):
    """A JSON array for all items, research_summary and sources are blank if there is no data for that item"""
    item_id: str
    item_name: str
    research_summary: str
    sources: list[str]

class MarketSearchResults(BaseModel):
    insights: list[MarketSearchItem]
    """A list of all of our menu items, with research data for those identified as relevant."""

# Create the market research agent
market_research_agent = Agent(
    name="MarketResearchAgent",
    instructions=RESEARCH_INSTRUCTIONS,
    tools=[WebSearchTool()],
    model="gpt-4o",
    output_type=MarketSearchResults,
    model_settings=ModelSettings(max_tokens=5000)
)

class TestWebAgentWrapper:
    """Wrapper for running the market research agent."""
    
    def __init__(self):
        """Initialize the agent wrapper."""
        self.agent = market_research_agent
        self.display_name = "Market Research Agent"
        self.description = "Conducts market research and maps insights to menu items"
        
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process menu items with market research.
        
        Args:
            context: Context dictionary containing menu data
            
        Returns:
            Dict with research results mapped to items
        """
        # Build the query with menu data
        base_query = """
        Analyze these menu items and conduct relevant market research.
        """
        
        # Load menu data from context or fall back to sample data
        menu_items = []
        
        # First try to get data collection results from context
        data_collection_results = context.get("data_collection_results", {})
        if data_collection_results:
            menu_items_from_data = data_collection_results.get("menu_items", [])
            if menu_items_from_data and isinstance(menu_items_from_data, list):
                logger.info(f"Using menu items from data_collection_results: {len(menu_items_from_data)} items")
                menu_items = menu_items_from_data
                
        # If no menu items found, try getting them directly from context
        if not menu_items:
            direct_menu_items = context.get("menu_items")
            if direct_menu_items and isinstance(direct_menu_items, list):
                menu_items = direct_menu_items
                logger.info(f"Using menu items directly from context: {len(menu_items)} items")
        
        # If still no menu items, fall back to sample data
        if not menu_items:
            try:
                from ..sample_outputs.data_collection_output import output as sample_output
                menu_items = parse_data_collection_output(file_content=sample_output)
                logger.warning("Using sample data from data_collection_output")
            except Exception as e:
                logger.warning(f"Could not import sample data: {e}")
                # Final fallback sample data
                menu_items = [
                {
                    "item_id": "LATTE001",
                    "item_name": "Latte", 
                    "item_basics": "Price: $5.95 | Cost: $1.20 | Margin: 79.8%",
                    "competitive_position": "Market Avg: $5.25 | Premium: +11.8% | Starbucks: $5.45",
                    "elasticity_indicators": "Historical Response: High (E = 3.63)",
                    "optimization_signals": "Consider price reduction"
                },
                {
                    "item_id": "BURG001",
                    "item_name": "Classic Burger",
                    "item_basics": "Price: $14.95 | Cost: $4.50 | Margin: 69.9%", 
                    "competitive_position": "Market Avg: $13.50 | Premium: +10.7%",
                    "elasticity_indicators": "Historical Response: Moderate (E = 2.1)",
                    "optimization_signals": "Monitor beef costs"
                },
                {
                    "item_id": "CAES001",
                    "item_name": "Caesar Salad",
                    "item_basics": "Price: $12.95 | Cost: $3.20 | Margin: 75.3%",
                    "competitive_position": "Market Avg: $11.50 | Premium: +12.6%",
                    "elasticity_indicators": "Historical Response: Low (E = 1.5)",
                    "optimization_signals": "Stable performer"
                }
            ]
        
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
        
        # Build query with all items and business context
        query = base_query + "\n" + business_context + "\n\nMENU ITEMS:\n"
        for item in menu_items:
            query += f"\n{item['item_name']} ({item['item_id']}):"
            query += f"\n- {item.get('item_basics', 'No basics')}"
            query += f"\n- {item.get('competitive_position', 'No position')}"
            query += f"\n- {item.get('elasticity_indicators', 'No elasticity')}"
            query += f"\n- {item.get('optimization_signals', 'No signals')}\n"
        
        query += f"\nLocation: {location}"
        query += "\n\nNow conduct comprehensive market research and map findings to relevant items."
        query += "\n\nAnalyze these items in the context of our business and location. "
        query += "Find relevant industry trends, local market conditions, and competitor strategies. "
        query += "Return only insights that apply directly to our menu items and business context."
        
        logger.info(f"Starting market research for {len(menu_items)} items")
        start_time = time.time()
        
        # Generate trace ID
        trace_id = gen_trace_id()
        trace_url = f"https://platform.openai.com/traces/trace?trace_id={trace_id}"
        logger.info(f"Trace URL: {trace_url}")
        
            # Run the agent
        try:
            # Run the agent
            with trace("Market Research Analysis", trace_id=trace_id):
                result = await Runner.run(self.agent, query)
            
            # Parse the results
            research_results = []
            
            if result.final_output:
                # Check if final_output is already a MarketSearchResults object
                if isinstance(result.final_output, MarketSearchResults):
                    # Direct access to the Pydantic model
                    for insight in result.final_output.insights:
                        research_results.append({
                            "item_id": insight.item_id,
                            "item_name": insight.item_name,
                            "research_summary": insight.research_summary,
                            "sources": insight.sources
                        })
                    logger.info(f"Parsed {len(research_results)} insights from MarketSearchResults")
                else:
                    # Try to parse as string if it's not the Pydantic model
                    try:
                        output_data = json.loads(str(result.final_output))
                        if isinstance(output_data, dict) and 'insights' in output_data:
                            insights = output_data['insights']
                            for item in insights:
                                if item.get('research_summary'):
                                    research_results.append({
                                        "item_id": item.get('item_id', ''),
                                        "item_name": item.get('item_name', ''),
                                        "research_summary": item.get('research_summary', ''),
                                        "sources": item.get('sources', [])
                                    })
                    except:
                        logger.error(f"Could not parse final_output: {type(result.final_output)}")
            else:
                logger.warning("No final_output found")
                
        except Exception as e:
            logger.error(f"Error running market research: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "trace_id": trace_id,
                "trace_url": trace_url
            }
            
        execution_time = time.time() - start_time
        logger.info(f"Research completed in {execution_time:.2f} seconds")
        
        # Create detailed summary info
        items_with_research = len([r for r in research_results if r.get("research_summary")])
        logger.info(f"Found insights for {items_with_research} items out of {len(menu_items)} total items")
        
        # Log each research item for debugging
        # Log each research item for debugging
        for item in research_results:
            item_id = item["item_id"]
            item_name = item["item_name"]
            summary_len = len(item["research_summary"])
            sources = item["sources"]
            logger.info(f"Item {item_id} ({item_name}): {summary_len} chars, {len(sources)} sources")
        
        summary = f"Analyzed {len(menu_items)} items, found relevant insights for {items_with_research} items"
        
        return {
            "success": True,
            "summary": summary,
            "research_results": research_results,
            "execution_time": f"{execution_time:.2f}s",
            "trace_id": trace_id,
            "trace_url": trace_url,
        }

# Standalone test function
async def test_research_workflow():
    """Test the complete research workflow."""
    wrapper = TestWebAgentWrapper()
    
    # Test with sample context
    context = {
        "location": "Austin, Texas"  # Can customize location
    }
    
    print("=== Starting Market Research Workflow ===")
    result = await wrapper.process(context)
    
    if result["success"]:
        print(f"\nSummary: {result['summary']}")
        print(f"Execution Time: {result['execution_time']}")
        print(f"Trace URL: {result['trace_url']}")
        
        print("\n=== Research Results ===")
        for item in result['research_results']:
            print(f"\n{item['item_name']} ({item['item_id']}):")
            print(f"Research Summary: {item['research_summary']}")
    else:
        print(f"Error: {result['error']}")
        print(f"Trace URL: {result['trace_url']}")

# Direct agent test
async def test_agent_directly():
    """Test the agent with a simple query."""
    query = """
    Analyze these items and conduct market research:
    
    Latte (LATTE001):
    - Price: $5.95 | Cost: $1.20 | Margin: 79.8%
    - Market Avg: $5.25 | Premium: +11.8%
    - High elasticity (E = 3.63)
    
    Classic Burger (BURG001):
    - Price: $14.95 | Cost: $4.50 | Margin: 69.9%
    - Market Avg: $13.50 | Premium: +10.7%
    - Moderate elasticity (E = 2.1)
    
    Location: Austin, Texas
    
    Conduct web searches on industry trends, supply chains, local events, and competitors.
    Then return which insights apply to which items.
    """
    
    trace_id = gen_trace_id()
    print(f"Trace: https://platform.openai.com/traces/trace?trace_id={trace_id}")
    
    with trace("Direct Agent Test", trace_id=trace_id):
        result = await Runner.run(market_research_agent, query)
        print("\nAgent Output:")
        print(result.final_output)

# Main execution
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "direct":
        # Run direct agent test
        asyncio.run(test_agent_directly())
    else:
        # Run full workflow test
        asyncio.run(test_research_workflow())