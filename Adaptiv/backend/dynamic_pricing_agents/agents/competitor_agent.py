"""
Competitor Analysis Agent implementation using the OpenAI API

This agent analyzes data collection output to identify items that would benefit from 
detailed competitor analysis, then uses OpenAI to conduct that research.
"""

import logging
import json
import re
import os
import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from pydantic import BaseModel, Field
from agents import Agent, WebSearchTool

# Import OpenAI client for direct API calls when needed
from openai import OpenAI

logger = logging.getLogger(__name__)

# Define output models for the agent
class CompetitorItem(BaseModel):
    """Model for an item that requires competitor analysis"""
    item_id: str = Field(description="The unique identifier for the item")
    item_name: str = Field(description="The name of the item")
    analysis_reason: str = Field(description="Why this item was selected for competitor analysis")
    analysis_focus: List[str] = Field(description="Specific areas to focus analysis on")

class CompetitorResults(BaseModel):
    """Model for competitor analysis results for a specific item"""
    item_id: str = Field(description="The unique identifier for the item")
    item_name: str = Field(description="The name of the item")
    confidence: float = Field(description="Confidence in the analysis (0.0-1.0)")
    sources: List[str] = Field(description="Sources used for this analysis", default=[])
    pricing_gap: Optional[float] = Field(description="Price gap vs competitors (percentage)", default=None)
    competitor_analysis: str = Field(description="Item-specific detailed competitor analysis", default="")

class CompetitorResponse(BaseModel):
    """Comprehensive response model for the Competitor Agent"""
    items_to_analyze: List[CompetitorItem] = Field(description="Items identified for competitor analysis")
    analysis_results: List[CompetitorResults] = Field(description="Results of analysis conducted", default=[])
    summary: str = Field(description="Overall summary of findings and recommendations", default="")
    

def parse_data_collection_output(data: str) -> List[Dict[str, Any]]:
    """
    Parse the data collection output to extract meaningful item data
    
    Args:
        data: Raw data collection output, either JSON string or already parsed JSON
        
    Returns:
        List of item dictionaries from the parsed data
    """
    if isinstance(data, str):
        try:
            # Try to parse the string as JSON
            parsed_data = json.loads(data)
            
            # Handle case where the JSON might be wrapped in another object
            if isinstance(parsed_data, dict) and "items" in parsed_data:
                return parsed_data["items"]
            elif isinstance(parsed_data, list):
                return parsed_data
            else:
                return [parsed_data]  # Return as a single-item list
                
        except json.JSONDecodeError:
            # If it's not valid JSON, return empty list
            logger.error("Failed to parse data collection output as JSON")
            return []
    else:
        # If it's already a Python object (dict or list)
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        elif isinstance(data, list):
            return data
        else:
            return [data]  # Return as a single-item list


def identify_competitor_candidates(items: List[Dict[str, Any]]) -> List[CompetitorItem]:
    """
    Analyze items to identify those that would benefit from competitor analysis
    using LLM-based qualitative analysis.
    
    Args:
        items: List of item dictionaries from parsed data
        
    Returns:
        List of CompetitorItem objects with reasons and focus areas
    """
    from openai import OpenAI
    import os
    
    # Check for OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        return []
        
    # Format the items data for the LLM
    items_text = json.dumps(items, indent=2)
    
    # Create the prompt for the LLM
    prompt = f"""
    You are a competitor analysis expert for retail pricing. Below is JSON data about menu items 
    including their competitive position, pricing, and sales metrics.
    
    DATA:
    {items_text}
    
    Your task is to identify which items would benefit most from detailed competitor analysis.
    Focus on these criteria:
    1. Items with significant price gaps compared to competitors (either above or below)
    2. Items positioned differently from competitors (value vs premium)
    3. Items facing competitive pressure as indicated in the data
    4. Items with optimization signals related to competitive positioning
    5. Select only items that truly need competitor analysis - don't select everything
    
    For each item you select, provide:
    - A specific reason why this item needs competitor analysis (be analytical and specific)
    - 2-3 focus areas for the competitor analysis (what specifically should be analyzed)
    
    Format your response as a JSON array with this structure:
    [
      {{"item_id": "id", "item_name": "name", "analysis_reason": "reason", "analysis_focus": ["focus1", "focus2"]}},
      // Additional items...
    ]
    
    For items you don't select, don't include them in the output at all.
    """
    
    # Call the OpenAI API
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",  # Using GPT-4o for best analysis
            messages=[
                {"role": "system", "content": "You are a retail pricing expert that specializes in competitor analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent, analytical responses
            response_format={"type": "json_object"}
        )
        
        # Extract the JSON response
        if response and response.choices and len(response.choices) > 0:
            result_text = response.choices[0].message.content
            try:
                # Parse the JSON response
                result_json = json.loads(result_text)
                
                # The response should be a list of items
                if isinstance(result_json, dict) and "items" in result_json:
                    candidates_data = result_json["items"]
                elif isinstance(result_json, list):
                    candidates_data = result_json
                else:
                    candidates_data = []
                    
                # Convert to CompetitorItem objects
                competitor_items = []
                for item_data in candidates_data:
                    try:
                        competitor_item = CompetitorItem(
                            item_id=item_data["item_id"],
                            item_name=item_data["item_name"],
                            analysis_reason=item_data["analysis_reason"],
                            analysis_focus=item_data["analysis_focus"]
                        )
                        competitor_items.append(competitor_item)
                    except Exception as e:
                        logger.warning(f"Error creating CompetitorItem: {str(e)}")
                        continue
                
                return competitor_items
            except json.JSONDecodeError:
                logger.error("Failed to parse LLM response as JSON")
                return []
    except Exception as e:
        logger.exception(f"Error identifying competitor analysis candidates: {str(e)}")
        return []


def conduct_competitor_analysis(items_to_analyze: List[CompetitorItem], all_items: List[Dict[str, Any]]) -> CompetitorResponse:
    """
    Use the OpenAI API to conduct competitor analysis on the identified items
    
    Args:
        items_to_analyze: List of items to analyze
        all_items: List of all menu items (to include in final output)
        
    Returns:
        Competitor analysis results and recommendations
    """
    import os
    import re
    from openai import OpenAI
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Check for OpenAI API key
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
            return CompetitorResponse(
                items_to_analyze=items_to_analyze,
                analysis_results=[],
                summary="Error: OpenAI API key not found. Please set the OPENAI_API_KEY environment variable."
            )
            
        client = OpenAI(api_key=api_key)
        
        # Construct prompt with info from the items
        items_info = ""
        for idx, item in enumerate(items_to_analyze, 1):
            items_info += f"\nITEM {idx}: {item.item_name} (ID: {item.item_id})\n"
            items_info += f"Analysis reason: {item.analysis_reason}\n"
            items_info += f"Analysis focus: {', '.join(item.analysis_focus)}\n"
            
            # Add specific competitive data from the original item data
            for orig_item in all_items:
                if orig_item.get('item_id') == item.item_id:
                    items_info += f"Original competitive position: {orig_item.get('competitive_position', 'Unknown')}\n"
                    items_info += f"Original price metrics: {orig_item.get('item_basics', 'Unknown')}\n"
                    break
            
        prompt = f"""
        You are a competitor analysis expert analyzing pricing and positioning data for a retail business.
        Please conduct comprehensive competitor analysis for the following items based on their analysis focus areas:
        
        {items_info}
        
        For each item, provide structured analysis covering:
        1. Competitive landscape and major competitors for this item
        2. Specific price positioning analysis (how far above/below competitor pricing)
        3. Competitor product quality, features and differentiation
        4. Competitive threats and opportunities
        5. Recommendations for positioning relative to competitors
        
        Also calculate a specific pricing gap percentage (positive if item is priced higher than competitors, negative if lower).
        
        Format your response with clear headings for each item and section, structured so it's easy to extract analysis for each item separately.
        """
        
        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a competitor analysis expert specializing in retail pricing."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,  # Balanced between creativity and consistency
            max_tokens=3000
        )
        
        # Extract and structure the response
        if response and response.choices and len(response.choices) > 0:
            analysis_text = response.choices[0].message.content
            
            # Try to parse the response text into per-item analyses
            item_analyses = {}
            current_item_id = None
            current_text = ""
            
            # Simple parsing of the response text to extract per-item sections
            for line in analysis_text.split('\n'):
                # Check for item headers to identify new sections
                if 'ITEM' in line and '(ID:' in line:
                    # If we were already processing an item, save it first
                    if current_item_id:
                        item_analyses[current_item_id] = current_text
                    
                    # Extract the item ID from the header
                    try:
                        item_id_match = re.search(r'\(ID:\s*([\w\d]+)\)', line)
                        if item_id_match:
                            current_item_id = item_id_match.group(1)
                            current_text = line + '\n'  # Start with the header
                    except:
                        # If extraction fails, use a fallback approach
                        for item in items_to_analyze:
                            if item.item_name in line:
                                current_item_id = item.item_id
                                current_text = line + '\n'
                                break
                else:
                    # Continue adding text to the current item
                    if current_item_id:
                        current_text += line + '\n'
            
            # Don't forget to save the last item
            if current_item_id and current_item_id not in item_analyses:
                item_analyses[current_item_id] = current_text
                
            # If parsing failed, use a more resilient approach
            if not item_analyses:
                logger.warning("Could not parse response by headers, falling back to item mention detection")
                for item in items_to_analyze:
                    item_text = ""
                    lines_to_check = analysis_text.split('\n')
                    in_item_section = False
                    
                    for i, line in enumerate(lines_to_check):
                        if item.item_name in line and ("ITEM" in line or "#" in line):
                            in_item_section = True
                            item_text += line + '\n'
                        elif in_item_section:
                            # Check if we've reached the next item section
                            next_item = False
                            for other_item in items_to_analyze:
                                if other_item.item_id != item.item_id and other_item.item_name in line and ("ITEM" in line or "#" in line):
                                    next_item = True
                                    break
                            
                            if next_item:
                                in_item_section = False
                            else:
                                item_text += line + '\n'
                    
                    if item_text:
                        item_analyses[item.item_id] = item_text
            
            # Create a lookup of item IDs selected for analysis
            analysis_item_ids = {item.item_id for item in items_to_analyze}
            
            # Create comprehensive analysis results for ALL menu items
            all_analysis_results = []
            
            # Process all items from the original data collection output
            for item_data in all_items:
                item_id = item_data.get("item_id", "")
                item_name = item_data.get("item_name", "")
                
                # If this item was analyzed, add full analysis results
                if item_id in analysis_item_ids:
                    item_specific_analysis = item_analyses.get(item_id, "Analysis not available for this specific item.")
                    
                    # Try to extract pricing gap if mentioned
                    pricing_gap = None
                    try:
                        # Look for percentage mentions
                        gap_matches = re.findall(r'([+-]?\d+(?:\.\d+)?)\s*%', item_specific_analysis)
                        price_gap_matches = re.findall(r'pricing gap[\s:]*([+-]?\d+(?:\.\d+)?)\s*%', 
                                                item_specific_analysis.lower())
                        
                        if price_gap_matches:  # Prefer explicit pricing gap mentions
                            pricing_gap = float(price_gap_matches[0])
                        elif gap_matches:      # Fall back to any percentage
                            pricing_gap = float(gap_matches[0])
                    except:
                        pass
                    
                    analysis_result = CompetitorResults(
                        item_id=item_id,
                        item_name=item_name,
                        confidence=0.8,
                        sources=["Competitor Analysis"],
                        pricing_gap=pricing_gap,
                        competitor_analysis=item_specific_analysis
                    )
                # If not analyzed, add a placeholder with blank analysis fields
                else:
                    analysis_result = CompetitorResults(
                        item_id=item_id,
                        item_name=item_name,
                        confidence=0.0,  # Zero confidence since no analysis was done
                        sources=[],
                        pricing_gap=None,
                        competitor_analysis=""  # Empty analysis for non-analyzed items
                    )
                
                all_analysis_results.append(analysis_result)
            
            # Return structured response with ALL items included
            return CompetitorResponse(
                items_to_analyze=items_to_analyze,  # Only analyzed items
                analysis_results=all_analysis_results,  # ALL items with per-item analyses
                summary=""  # No global summary needed as we have per-item analyses
            )
        else:
            return CompetitorResponse(
                items_to_analyze=items_to_analyze,
                analysis_results=[],
                summary="Error: Unable to get a response from the OpenAI API."
            )
    
    except Exception as e:
        logger.exception(f"Error conducting competitor analysis: {str(e)}")
        # In case of any errors during the analysis process
        return CompetitorResponse(
            items_to_analyze=items_to_analyze,
            analysis_results=[],
            summary=f"Error conducting competitor analysis: {str(e)}"
        )


def process_data_collection_output(data: str) -> List[CompetitorItem]:
    """
    Process data collection output to identify items that need competitor analysis
    
    Args:
        data: Raw data collection output
        
    Returns:
        List of CompetitorItem objects for items needing competitor analysis
    """
    # Parse the data
    items = parse_data_collection_output(data)
    return identify_competitor_candidates(items)

# Import OpenAI Agent SDK classes if available, otherwise use mock implementations
try:
    from agents import Agent, Runner, Tool, FunctionTool, function_tool
    from agents import custom_span, gen_trace_id, trace
    from openai.types.beta.threads import Run
    from openai.types.beta.threads.runs import ToolCallsStepDetails
    
    # Flag to indicate we're using the actual SDK
    USING_OPENAI_SDK = True
    logger.info("Successfully imported OpenAI Agents SDK")
except ImportError as e:
    # Create minimal mock implementations for SDK classes
    logger.warning(f"OpenAI Agents SDK not found, using mock implementations: {e}")
    USING_OPENAI_SDK = False
    
    # Mock SDK classes
    class Agent:
        def __init__(self, name=None, instructions=None, model=None, tools=None, handoffs=None):
            self.name = name
            self.instructions = instructions
            self.model = model
            self.tools = tools or []
            self.handoffs = handoffs or []
    
    class Runner:
        def __init__(self, agent=None):
            self.agent = agent
            
        def run(self, prompt):
            from dataclasses import dataclass
            
            @dataclass
            class MockResult:
                final_output: any
                
                def dict(self):
                    return {"message": "Mock output - SDK not available"}
                
                def model_dump(self):
                    return {"message": "Mock output - SDK not available"}
                    
                def json(self):
                    import json
                    return json.dumps({"message": "Mock output - SDK not available"})
            
            return MockResult(final_output=MockResult(final_output="SDK not available"))
            
        # Add async support for consistency
        async def arun(self, prompt):
            return self.run(prompt)
    
    class ToolType:
        FUNCTION = "function"
        
        def __init__(self, name="function"):
            self.name = name
            
        def to_dict(self):
            return {"type": self.name}
            
    class Tool:
        def __init__(self, type=None, function=None):
            self.type = type or ToolType()
            self.function = function
        
        def type_dict(self):
            if hasattr(self.type, 'to_dict'):
                return self.type.to_dict()
            return {"type": "function"}
    
    def gen_trace_id():
        # Generate a random UUID for tracing
        import uuid
        return str(uuid.uuid4())
    
    # Context manager for traces
    class _MockTrace:
        def __init__(self, name=None, trace_id=None, **kwargs):
            self.name = name
            self.trace_id = trace_id
            self.kwargs = kwargs
            
        def __enter__(self):
            logger.debug(f"[MOCK] Starting trace: {self.name} with ID: {self.trace_id}")
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            logger.debug(f"[MOCK] Ending trace: {self.name}")
            return False  # Don't suppress exceptions
    
    def trace(name=None, trace_id=None, **kwargs):
        # Mock implementation for traceability that works as a context manager
        return _MockTrace(name=name, trace_id=trace_id, **kwargs)
        
    # Context manager for spans within traces
    class custom_span:
        def __init__(self, name):
            self.name = name
        
        def __enter__(self):
            return self
        
        def __exit__(self, exc_type, exc_value, traceback):
            pass
            
    # Mock Tool classes
    class Tool:
        def __init__(self, type, function=None):
            self.type = type
            self.function = function
    
    class ToolType:
        FUNCTION = "function"
        
    class ToolCall:
        def __init__(self, id, type, function):
            self.id = id
            self.type = type
            self.function = function
    
    class Runner:
        @staticmethod
        def run(agent, prompt):
            logger.warning("Runner.run() called but SDK functionality not available")
            
            # Use direct OpenAI API calls instead
            try:
                from openai import OpenAI
                client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                
                # Ensure we mention JSON in the prompt if using json_object response format
                modified_prompt = f"{prompt}\n\nProvide your response as JSON."
                
                response = client.chat.completions.create(
                    model="gpt-4o",  # Using GPT-4o for best analysis
                    messages=[
                        {"role": "system", "content": agent.instructions},
                        {"role": "user", "content": modified_prompt}
                    ],
                    temperature=0.4,
                    response_format={"type": "json_object"}
                )
                
                result_text = response.choices[0].message.content
                
                # Attempt to parse the JSON response
                try:
                    result_data = json.loads(result_text)
                except json.JSONDecodeError as json_err:
                    logger.error(f"Failed to parse LLM response as JSON: {str(json_err)}")
                    logger.debug(f"Raw response: {result_text[:500]}...")
                    
                    # Try to extract JSON from markdown code blocks
                    json_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', result_text)
                    if json_match:
                        try:
                            result_data = json.loads(json_match.group(1))
                            logger.info("Successfully extracted JSON from code block")
                        except json.JSONDecodeError:
                            raise ValueError(f"Could not parse response as JSON: {result_text[:100]}...")
                    else:
                        raise ValueError(f"Response is not valid JSON and no code block found: {result_text[:100]}...")
                
                class Result:
                    def __init__(self, data):
                        # Use Pydantic v2 compatible parsing
                        try:
                            if hasattr(agent.output_type, 'parse_obj'):
                                # Pydantic v1
                                self.final_output = agent.output_type.parse_obj(data)
                            else:
                                # Pydantic v2
                                self.final_output = agent.output_type.model_validate(data)
                        except Exception as parse_err:
                            logger.exception(f"Error parsing response into {agent.output_type.__name__}: {str(parse_err)}")
                            logger.debug(f"Data that failed parsing: {data}")
                            raise
                
                return Result(result_data)
                
            except Exception as e:
                logger.exception(f"Error using fallback implementation: {str(e)}")
                raise
    
        @staticmethod
        async def arun(agent, prompt):
            """Async version of run for compatibility"""
            return Runner.run(agent, prompt)
    
    class Agent:
        def __init__(self, name, instructions, output_type, tools=None, model="gpt-4o"):
            self.name = name
            self.instructions = instructions
            self.output_type = output_type
            self.tools = tools or []
            self.model = model
            
        def clone(self, **kwargs):
            return Agent(
                name=kwargs.get("name", self.name),
                instructions=kwargs.get("instructions", self.instructions),
                output_type=kwargs.get("output_type", self.output_type),
                tools=kwargs.get("tools", self.tools),
                model=kwargs.get("model", self.model),
            )

# Define tools for the competitor agent
# Define tool functions using the @function_tool decorator if SDK is available
if USING_OPENAI_SDK:
    @function_tool
    def search_competitor_prices(query: str) -> dict:
        """Search for competitor prices for a specific menu item
        
        Args:
            query: The menu item to search for, can include name and price information
        """
        # This would normally call an external API or database
        # For now, we'll return mock data
        import random
        
        # Generate random prices in a reasonable range based on the query
        search_results = []
        competitors = ["Local Bistro", "Cafe Roma", "Main Street Grill", "Urban Kitchen", "Flavor House"]
        
        # Extract any price mentions from the query to set a base price
        import re
        price_match = re.search(r'\$?(\d+\.?\d*)', query)
        base_price = float(price_match.group(1)) if price_match else random.uniform(10, 25)
        
        # Generate 3-5 competitor results
        for i in range(random.randint(3, 5)):
            competitor = random.choice(competitors)
            price_variation = random.uniform(0.8, 1.2)  # +/- 20%
            price = base_price * price_variation
            search_results.append({
                "competitor": competitor,
                "item_name": query.split("price")[0].strip() if "price" in query else query,
                "price": round(price, 2),
                "source": f"https://example.com/competitor/{competitor.lower().replace(' ', '-')}"
            })
        
        return {"results": search_results}

    @function_tool
    def get_market_trends(category: str) -> dict:
        """Get market trends for a specific food category
        
        Args:
            category: Food category like 'pizza', 'burger', 'pasta', etc.
        """
        # Mock implementation
        trends = {
            "pizza": {"trend": "rising", "avg_price_change": "+5%", "popular_variants": ["Wood-fired", "Neapolitan", "Detroit-style"]},
            "burger": {"trend": "stable", "avg_price_change": "+2%", "popular_variants": ["Smash burger", "Plant-based", "Gourmet toppings"]},
            "pasta": {"trend": "rising", "avg_price_change": "+4%", "popular_variants": ["House-made", "Gluten-free options", "Regional specialties"]},
            "salad": {"trend": "rising", "avg_price_change": "+7%", "popular_variants": ["Grain bowls", "Protein-focused", "Farm-to-table"]},
            "dessert": {"trend": "stable", "avg_price_change": "+1%", "popular_variants": ["Mini desserts", "Gluten-free", "Artisanal ice cream"]},
        }
        
        # Return the trend for the requested category or a generic response
        return trends.get(category.lower(), {"trend": "stable", "avg_price_change": "+3%", "popular_variants": ["Artisanal", "Local sourcing", "House-made"]})
else:
    # Standard function implementations for when SDK is not available
    def search_competitor_prices(query: str) -> dict:
        """Search for competitor prices for a specific menu item"""
        # Log when this tool is called
        logger.info(f"*** TOOL CALLED: search_competitor_prices with query: '{query}' ***")
        
        # Mock implementation that returns simulated data
        import random
        search_results = []
        competitors = ["Local Bistro", "Cafe Roma", "Main Street Grill", "Urban Kitchen", "Flavor House"]
        
        # Extract any price mentions from the query to set a base price
        import re
        price_match = re.search(r'\$?(\d+\.?\d*)', query)
        base_price = float(price_match.group(1)) if price_match else random.uniform(10, 25)
        
        # Generate 3-5 competitor results
        for i in range(random.randint(3, 5)):
            competitor = random.choice(competitors)
            price_variation = random.uniform(0.8, 1.2)  # +/- 20%
            price = base_price * price_variation
            search_results.append({
                "competitor": competitor,
                "item_name": query.split("price")[0].strip() if "price" in query else query,
                "price": round(price, 2),
                "source": f"https://example.com/competitor/{competitor.lower().replace(' ', '-')}"
            })
        
        return {"results": search_results}

    def get_market_trends(category: str) -> dict:
        """Get market trends for a specific food category"""
        # Log when this tool is called
        logger.info(f"*** TOOL CALLED: get_market_trends with category: '{category}' ***")
        
        # Mock implementation
        trends = {
            "pizza": {"trend": "rising", "avg_price_change": "+5%", "popular_variants": ["Wood-fired", "Neapolitan", "Detroit-style"]},
            "burger": {"trend": "stable", "avg_price_change": "+2%", "popular_variants": ["Smash burger", "Plant-based", "Gourmet toppings"]},
            "pasta": {"trend": "rising", "avg_price_change": "+4%", "popular_variants": ["House-made", "Gluten-free options", "Regional specialties"]},
            "salad": {"trend": "rising", "avg_price_change": "+7%", "popular_variants": ["Grain bowls", "Protein-focused", "Farm-to-table"]},
            "dessert": {"trend": "stable", "avg_price_change": "+1%", "popular_variants": ["Mini desserts", "Gluten-free", "Artisanal ice cream"]},
        }
        
        # Return the trend for the requested category or a generic response
        return trends.get(category.lower(), {"trend": "stable", "avg_price_change": "+3%", "popular_variants": ["Artisanal", "Local sourcing", "House-made"]})

# Tool implementations based on SDK availability
if USING_OPENAI_SDK:
    # In the SDK mode, the tools are directly the decorated functions
    competitor_tools = [search_competitor_prices, get_market_trends, WebSearchTool()]
    
    # Tool implementations dictionary that maps function names to actual functions
    tool_implementations = {
        "search_competitor_prices": search_competitor_prices,
        "get_market_trends": get_market_trends,
        "web_search": WebSearchTool()
    }
else:
    # In non-SDK mode, we need to create mock tool definitions
    competitor_tools = []
    
    # Tool implementations dictionary that maps function names to actual functions
    tool_implementations = {
        "search_competitor_prices": search_competitor_prices,
        "get_market_trends": get_market_trends
    }

# Create the competitor analysis agent using the OpenAI SDK
competitor_agent = Agent(
    name="competitor_analysis",
    instructions="""You are a competitor analysis agent that helps restaurant owners analyze their competition.
    You will be given menu items with their prices, descriptions, and sales data.
    
    Your task is to:
    1. Identify which items need competitor analysis based on their performance, pricing, and market position
    2. For those items, conduct detailed competitor analysis including pricing gaps and competitive positioning
    3. Provide specific recommendations for each item to improve its market position
    
    You can use tools to search for competitor prices and market trends to make your analysis more accurate.
    Always use tools when specific data about competitors or market trends would help with your analysis.
    
    Focus on practical, actionable insights backed by data when possible.
    
    IMPORTANT: You must respond in JSON format.
    PROVIDE OUTPUT IN THE FOLLOWING JSON FORMAT:
    {
      "items_to_analyze": [
        {
          "item_id": "item123",
          "item_name": "Example Item",
          "analysis_reason": "Explanation of why this item was selected for analysis",
          "analysis_focus": ["pricing gap", "positioning", "quality comparison"]
        }
      ],
      "analysis_results": [
        {
          "item_id": "item123", 
          "item_name": "Example Item",
          "competitor_analysis": "Detailed analysis of competitor pricing and positioning",
          "pricing_gap": 15.5,
          "confidence": 0.85,
          "sources": ["competitor menu data", "market trends"]
        }
      ],
      "overall_summary": "Summary of key insights and recommendations across all items"
    }
    """,
    model="gpt-4o",
    output_type=CompetitorResponse,
    tools=competitor_tools if USING_OPENAI_SDK else None
)

# Core agent implementation


# Core agent implementation
class CompetitorAgentWrapper:
    """
    Wrapper for the Competitor Analysis agent that integrates with the orchestration system.
    This agent identifies items needing competitor analysis and conducts detailed analysis.
    """
    
    def __init__(self):
        """Initialize the competitor analysis agent"""
        self.name = "competitor_analysis"
        self.display_name = "Competitor Analysis Agent"
        self.description = "Analyzes data collection output to identify items that would benefit from competitor analysis and generates detailed insights"
        self.capabilities = [
            "Analyze product data to identify competitor analysis candidates",
            "Analyze competitive landscape for specific products",
            "Calculate pricing gaps vs. competitors",
            "Identify competitive threats and opportunities",
            "Provide positioning recommendations relative to competitors"
        ]
        
        # Use the defined agent
        self.agent = competitor_agent
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data to identify items needing competitor analysis and conduct that analysis.
        
        Args:
            context: Context data including database connection and user info
            
        Returns:
            Dict with analysis results and status
        """
        logger.info("Starting competitor analysis process")
        start_time = time.time()
        
        # Generate a trace ID for OpenAI tracing if SDK is available
        trace_id = gen_trace_id()
        
        # Use trace as a context manager - this is the key to proper tracing
        # For real SDK: with trace("name", trace_id=id)
        # For mock SDK: our mock implementation needs to be enhanced to be a context manager
        trace_context = trace("Competitor Analysis", trace_id=trace_id) if USING_OPENAI_SDK else None
        
        # Log the trace URL for debugging
        trace_url = f"https://platform.openai.com/traces/trace?trace_id={trace_id}"
        logger.info(f"Trace URL: {trace_url}")
        
        # Use trace as context manager if available, otherwise just proceed
        with trace_context if USING_OPENAI_SDK else custom_span("run_competitor_agent"):
            try:
                # Get sample data (similar to the market analysis agent)
                from ..sample_outputs.data_collection_output import output as sample_output
                
                # Process the sample data to identify competitor analysis candidates
                logger.info("Processing data collection output to identify competitor analysis candidates")
                data = sample_output
                
                # Parse data and get all original items
                all_items = parse_data_collection_output(data)
                
                # Prepare the data for the agent
                items_json = json.dumps(all_items, indent=2)
                prompt = f"""Please analyze this menu item data to identify candidates for competitor analysis 
                and then conduct detailed competitor analysis on the selected items.
                
                DATA:
                {items_json}
                
                First identify which items would benefit most from competitor analysis based on price gaps, 
                competitive positioning, and other factors. Then conduct detailed analysis of those items.
                
                IMPORTANT: Use the search_competitor_prices tool to get actual competitor pricing data for each item you identify. 
                This is crucial for accurate analysis. For each item selected, you should use the tool to look up similar items 
                at competitor restaurants.
                
                IMPORTANT: Also use the get_market_trends tool to gather market trend information for each food category 
                you're analyzing. This will provide valuable context about pricing trends and popular variants.
                
                For your response, include detailed competitor analysis for each selected item, including pricing gaps, 
                competitive positioning, and specific recommendations backed by the data you gathered using the tools.
                """
                
                # Use OpenAI Agent SDK with proper tracing and spans
                with custom_span("run_competitor_agent"):
                    logger.info("Running competitor analysis agent with OpenAI Agent SDK")
                    
                    # Use the proper OpenAI Agent SDK approach with Runner to handle tools and traces
                    if USING_OPENAI_SDK:
                        logger.info("Using OpenAI Agent SDK Runner to execute agent with tool support")
                        
                        try:
                            # Handle async in a sync-compatible way to avoid event loop conflicts
                            import asyncio
                            
                            # Check if we're in an event loop
                            try:
                                loop = asyncio.get_running_loop()
                                in_event_loop = True
                            except RuntimeError:
                                in_event_loop = False
                            
                            # Run the appropriate method based on context
                            if in_event_loop:
                                logger.info("Running in event loop, using direct API approach")
                                # We're in an event loop but can't run async code, use direct API
                                from openai import OpenAI
                                client = OpenAI()
                                
                                # Direct implementation with tracing
                                # Handle FunctionTool objects which don't have a type attribute
                                tools_for_api = None
                                if self.agent.tools:
                                    tools_for_api = []
                                    for tool in self.agent.tools:
                                        # FunctionTool objects need special handling
                                        if tool.__class__.__name__ == "FunctionTool":
                                            # Extract function metadata from decorated tool
                                            tools_for_api.append({
                                                "type": "function",
                                                "function": {
                                                    "name": tool.name,
                                                    "description": tool.description,
                                                    "parameters": tool.params_json_schema
                                                }
                                            })
                                        elif hasattr(tool, 'type') and hasattr(tool.type, 'to_dict'):
                                            # Handle Tool objects with type
                                            tools_for_api.append(tool.type.to_dict())
                                        else:
                                            logger.warning(f"Unsupported tool type: {tool.__class__.__name__}")
                                
                                logger.info(f"Prepared {len(tools_for_api) if tools_for_api else 0} tools for API call")
                                
                                response = client.chat.completions.create(
                                    model=self.agent.model,
                                    messages=[{"role": "system", "content": self.agent.instructions}, 
                                              {"role": "user", "content": prompt}],
                                    temperature=0.5,
                                    max_tokens=2500,
                                    response_format={"type": "json_object"},
                                    tools=tools_for_api,
                                    extra_headers={"X-OpenAI-Trace-ID": trace_id},
                                )
                                result_text = response.choices[0].message.content
                            else:
                                logger.info("No event loop detected, running using Runner.run with asyncio.run()")
                                # Use the static Runner.run method directly but wrapped in asyncio.run()
                                # since the process method isn't async
                                async def run_with_sdk():
                                    return await Runner.run(
                                        self.agent,
                                        prompt
                                    )
                                
                                result = asyncio.run(run_with_sdk())
                                result_text = result.final_output.json()
                        except Exception as e:
                            logger.exception(f"Error running agent with SDK runner: {str(e)}")
                            # Fall back to synchronous Runner.run
                            logger.info("Falling back to direct API call")
                            from openai import OpenAI
                            client = OpenAI()
                            
                            # Ensure JSON output by modifying the prompt
                            modified_prompt = f"{prompt}\n\nProvide your response as JSON."
                            
                            # Handle FunctionTool objects which don't have a type attribute
                            tools_for_api = None
                            if self.agent.tools:
                                tools_for_api = []
                                for tool in self.agent.tools:
                                    # FunctionTool objects need special handling
                                    if tool.__class__.__name__ == "FunctionTool":
                                        # Extract function metadata from decorated tool
                                        tools_for_api.append({
                                            "type": "function",
                                            "function": {
                                                "name": tool.name,
                                                "description": tool.description,
                                                "parameters": tool.params_json_schema
                                            }
                                        })
                                    elif hasattr(tool, 'type') and hasattr(tool.type, 'to_dict'):
                                        # Handle Tool objects with type
                                        tools_for_api.append(tool.type.to_dict())
                                    else:
                                        logger.warning(f"Unsupported tool type: {tool.__class__.__name__}")
                            
                            logger.info(f"Prepared {len(tools_for_api) if tools_for_api else 0} tools for fallback API call")
                            
                            # Direct implementation without tracing
                            response = client.chat.completions.create(
                                model=self.agent.model,
                                messages=[{"role": "system", "content": self.agent.instructions}, 
                                          {"role": "user", "content": modified_prompt}],
                                temperature=0.5,
                                max_tokens=2500,
                                tools=tools_for_api,
                                response_format={"type": "json_object"}
                            )
                            result_text = response.choices[0].message.content
                            
                        # Log the result for debugging
                        logger.info(f"Received result of length {len(result_text) if isinstance(result_text, str) else 'unknown'} from OpenAI Agent SDK")
                        
                        # For direct API calls, we need to parse JSON; for SDK results it's already parsed
                        if in_event_loop or not USING_OPENAI_SDK:
                            # When using direct API, we need to parse the JSON
                            logger.info(f"Response preview from direct API: {result_text[:300] if isinstance(result_text, str) and len(result_text) > 0 else 'Empty'}...")
                            
                            # Parse JSON from the response
                            try:
                                # First try to parse the whole response as JSON (should work with response_format=json_object)
                                try:
                                    result_data = json.loads(result_text)
                                    logger.info("Successfully parsed raw JSON response")
                                except json.JSONDecodeError:
                                    # If that fails, try to find a JSON block in markdown
                                    logger.info("Raw JSON parse failed, looking for JSON in markdown code blocks...")
                                    json_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", result_text)
                                    if json_match:
                                        try:
                                            result_data = json.loads(json_match.group(1).strip())
                                            logger.info("Successfully parsed JSON from markdown code block")
                                        except json.JSONDecodeError:
                                            # One final attempt - try to find anything that looks like JSON
                                            logger.warning("Markdown JSON parse failed too. Last resort: try to extract any JSON-like substring")
                                            # Look for something that starts with { and ends with } with balanced braces
                                            json_like_match = re.search(r"(\{[\s\S]*\})", result_text)
                                            if json_like_match:
                                                result_data = json.loads(json_like_match.group(1))
                                                logger.info("Successfully extracted JSON-like substring")
                                            else:
                                                raise ValueError("Could not find any valid JSON in the response")
                                    else:
                                        raise ValueError("No JSON code block found in the response")
                            except Exception as json_e:
                                logger.exception(f"Error parsing JSON response: {str(json_e)}")
                                raise
                        else:
                            # When using SDK's Runner, we already have parsed data from the Pydantic model
                            result_data = json.loads(result_text) if isinstance(result_text, str) else result_text
                        
                        # Try to map the returned JSON to our expected format
                        def convert_to_expected_format(data):
                            """Convert various potential response formats to our expected CompetitorResponse format"""
                            processed_data = {}
                            
                            # Handle common key variations
                            if "items_to_analyze" in data:
                                processed_data["items_to_analyze"] = data["items_to_analyze"]
                            elif "selected_items_for_competitor_analysis" in data:
                                # Convert to expected format
                                items = []
                                for item in data["selected_items_for_competitor_analysis"]:
                                    new_item = {
                                        "item_id": item.get("item_id", ""),
                                        "item_name": item.get("item_name", ""),
                                        "analysis_reason": item.get("reason", ""),
                                        "analysis_focus": item.get("focus_areas", [])
                                    }
                                    items.append(new_item)
                                processed_data["items_to_analyze"] = items
                                
                            # Handle analysis results
                            if "analysis_results" in data:
                                processed_data["analysis_results"] = data["analysis_results"]
                            elif "competitor_analyses" in data:
                                # Convert to expected format
                                results = []
                                for analysis in data["competitor_analyses"]:
                                    new_result = {
                                        "item_id": analysis.get("item_id", ""),
                                        "item_name": analysis.get("item_name", ""),
                                        "competitor_analysis": analysis.get("analysis", ""),
                                        "pricing_gap": analysis.get("price_gap_percentage", 0.0),
                                        "confidence": 0.9,  # Default confidence if not specified
                                        "sources": analysis.get("data_sources", ["competitor analysis"])
                                    }
                                    results.append(new_result)
                                processed_data["analysis_results"] = results
                                    
                            # Handle overall summary
                            if "overall_summary" in data:
                                processed_data["overall_summary"] = data["overall_summary"]
                            elif "summary" in data:
                                processed_data["overall_summary"] = data["summary"]
                            
                            # Ensure we have the required fields even if the LLM didn't provide them
                            if "items_to_analyze" not in processed_data:
                                processed_data["items_to_analyze"] = []
                            if "analysis_results" not in processed_data:
                                processed_data["analysis_results"] = []
                            if "overall_summary" not in processed_data:
                                processed_data["overall_summary"] = "No summary provided"
                                
                            return processed_data
                        
                        # Convert the data to our expected format
                        try:
                            converted_data = convert_to_expected_format(result_data)
                            
                            # Create a result object with our model to validate
                            class Result:
                                def __init__(self, data, output_type):
                                    # Parse using Pydantic for consistency
                                    try:
                                        if hasattr(output_type, 'parse_obj'):
                                            # Pydantic v1
                                            self.final_output = output_type.parse_obj(data)
                                        else:
                                            # Pydantic v2
                                            self.final_output = output_type.model_validate(data)
                                    except Exception as parse_err:
                                        logger.exception(f"Error parsing response: {str(parse_err)}")
                                        # More detailed debugging
                                        logger.error(f"Failed data keys: {list(data.keys())}")
                                        logger.error(f"Expected model fields: {output_type.__annotations__ if hasattr(output_type, '__annotations__') else 'unknown'}")
                                        raise
                            
                            # Create a result object with our model
                            result = Result(converted_data, self.agent.output_type)
                            analysis_results = result.final_output
                            
                            # Log the trace URL for OpenAI
                            if trace_id:
                                trace_url = f"https://platform.openai.com/playground?trace={trace_id}"
                                logger.info(f"OpenAI Trace URL: {trace_url}")
                            
                            # Return success response with the results
                            duration = time.time() - start_time
                            return {
                                "status": "success",
                                "message": f"Successfully analyzed competitors in {duration:.2f} seconds",
                                "analysis": analysis_results.dict() if hasattr(analysis_results, 'dict') else analysis_results.model_dump()
                            }
                        except Exception as e:
                            logger.exception(f"Error creating and validating result: {str(e)}")
                            # Try to create a minimal valid structure as a last resort
                            # Create minimal valid data structure as fallback
                            minimal_valid_data = {
                                "items_to_analyze": [],
                                "analysis_results": [],
                                "overall_summary": "Analysis completed with data format issues."
                            }
                            try:
                                result = Result(minimal_valid_data, self.agent.output_type)
                                analysis_results = result.final_output
                                
                                # Return results with the minimal valid data
                                duration = time.time() - start_time
                                return {
                                    "status": "partial_success",
                                    "message": f"Completed with minimal valid data in {duration:.2f} seconds",
                                    "analysis": analysis_results.dict() if hasattr(analysis_results, 'dict') else analysis_results.model_dump(),
                                    "trace_id": trace_id
                                }
                            except Exception as final_e:
                                logger.exception(f"Final fallback attempt failed: {str(final_e)}")
                                # Absolute last resort - return empty dict with error message
                                return {
                                    "status": "error",
                                    "message": "All parsing attempts failed",
                                    "error": str(final_e),
                                    "trace_id": trace_id
                                }
                        except Exception as json_e:
                            logger.exception(f"Error parsing JSON from response: {str(json_e)}")
                            
                            # Return error response with debugging info
                            return {
                                "status": "error",
                                "message": f"Error processing competitor analysis: {str(json_e)}",
                                "error": str(json_e),
                                "trace_id": trace_id
                            }
                    
                    # Use our existing fallback implementation
                    try:
                        result = Runner.run(self.agent, prompt)
                        analysis_results = result.final_output
                    except Exception as e:
                        logger.exception(f"Error using fallback implementation: {str(e)}")
                        return {
                            "status": "error",
                            "message": f"Error in fallback implementation: {str(e)}",
                            "error": str(e)
                        }
                    
                    # For fallback implementation, if we reached here, return the result
                    # Calculate execution time
                    execution_time = time.time() - start_time
                    
                    # Create the final result structure
                    result = {
                        "status": "success",
                        "message": f"Completed competitor analysis in {execution_time:.2f} seconds",
                        "trace_id": trace_id,
                        "agent_name": "competitor_analysis",
                        "execution_details": {
                            "start_time": start_time,
                            "duration_seconds": execution_time,
                            "analysis_items_count": len(analysis_results.items_to_analyze) if hasattr(analysis_results, "items_to_analyze") else 0,
                            "total_items_count": len(all_items)
                        },
                        "analysis": analysis_results.dict() if hasattr(analysis_results, 'dict') else analysis_results.model_dump()
                    }
                    
                    # Add trace URL for OpenAI UI
                    if trace_id:
                        # Correct URL format for viewing traces in the OpenAI platform
                        result["trace_url"] = f"https://platform.openai.com/playground/traces/{trace_id}"
                    
                    return result
                
            except Exception as e:
                logger.exception(f"Error in competitor analysis process: {str(e)}")
                return {
                    "status": "error",
                    "message": f"Error processing competitor analysis: {str(e)}",
                    "error": str(e),
                    "agent_name": "competitor_analysis",
                    "trace_id": trace_id,
                    "analysis_candidates": [],
                    "analysis_results": None
                }
