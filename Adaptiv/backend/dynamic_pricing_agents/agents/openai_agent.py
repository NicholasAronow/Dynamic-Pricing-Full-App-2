"""
Market Analysis Agent implementation using the OpenAI Agent SDK

This agent analyzes data collection output to identify items that would benefit from 
further market research, then uses tools to conduct that research.
"""

import json
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

# Import OpenAI client
from openai import OpenAI

# These imports may need adjustment based on your specific OpenAI SDK version
# We'll create compatible versions of necessary functionality
import logging
logger = logging.getLogger(__name__)

# Define placeholder for WebSearchTool for compatibility
WebSearchTool = None

# Create simple class structures to maintain code compatibility
class Runner:
    @staticmethod
    def run(agent, prompt):
        # This is a placeholder that will be replaced with actual functionality
        # when we have determined the correct SDK structure
        logger.warning("Runner.run() called but SDK functionality not available")
        
        class Result:
            def __init__(self):
                self.final_output = f"SDK compatibility issue: Unable to run agent with prompt: {prompt[:50]}..."
        
        return Result()

class Agent:
    def __init__(self, name, instructions, output_type, tools=None):
        self.name = name
        self.instructions = instructions
        self.output_type = output_type
        self.tools = tools or []
        
    def clone(self, **kwargs):
        # Create a new agent with updated parameters
        return Agent(
            name=kwargs.get("name", self.name),
            instructions=kwargs.get("instructions", self.instructions),
            output_type=kwargs.get("output_type", self.output_type),
            tools=kwargs.get("tools", self.tools),
        )

# Import our custom database tool
from ..tools.database_tool import DatabaseTool

# Define output models for the agent
class ResearchItem(BaseModel):
    """Model for an item that requires further research"""
    item_id: str = Field(description="The unique identifier for the item")
    item_name: str = Field(description="The name of the item")
    research_reason: str = Field(description="Why this item was selected for research")
    research_focus: List[str] = Field(description="Specific areas to focus research on")

class ResearchResults(BaseModel):
    """Model for research results for a specific item"""
    item_id: str = Field(description="The unique identifier for the item")
    item_name: str = Field(description="The name of the item")
    upcoming_events: List[Dict[str, str]] = Field(description="Events that might impact sales", default=[])
    confidence: float = Field(description="Confidence in the research (0.0-1.0)")
    sources: List[str] = Field(description="Sources used for this research", default=[])
    research_summary: str = Field(description="Item-specific detailed research summary", default="")

class OpenAIResponse(BaseModel):
    """Comprehensive response model for the OpenAI Agent"""
    items_to_research: List[ResearchItem] = Field(description="Items identified for further research")
    research_results: List[ResearchResults] = Field(description="Results of research conducted", default=[])
    summary: str = Field(description="Overall summary of findings and recommendations")

# Define criteria for identifying items that need research
RESEARCH_CRITERIA = {
    "price_elasticity": {
        "description": "Items with high elasticity might need research on market conditions",
        "threshold": 3.0,  # Items with elasticity > 3.0 are considered highly elastic
    },
    "competitive_position": {
        "description": "Items with significant price difference from competitors",
        "threshold_percent": 10.0,  # >10% difference may warrant research
    },
    "optimization_signals": {
        "description": "Items with specific optimization signals mentioned",
        "keywords": ["test", "consider", "potential", "monitor", "review"],
    },
    "cost_dynamics": {
        "description": "Items with changing cost structures",
        "keywords": ["up", "rising", "volatile", "seasonal"],
    }
}

# Define the instructions/prompt for the agent
OPENAI_AGENT_PROMPT = """
You are an advanced market research agent for dynamic pricing optimization. Your responsibilities are:

1. ANALYZE DATA COLLECTION OUTPUT:
   - Review detailed item data from the data collection agent
   - Apply specific criteria to identify items that would benefit from further research
   - Focus on items with high price elasticity, changing costs, competitive disparities, or clear optimization signals
   - Do not conduct research on all items - only those that would most benefit from further examination

2. CONDUCT MARKET RESEARCH:
   - For identified items, conduct targeted market research using web search
   - Research supply chain trends that impact costs and availability
   - Identify competitor information and strategies
   - Look for upcoming events in the user's area that might impact sales
   - Research overall market trends for the product category and industry

3. PROVIDE ACTIONABLE INSIGHTS:
   - Synthesize research findings into clear, data-driven insights
   - Make specific pricing recommendations based on market intelligence
   - Explain the rationale behind each recommendation
   - Provide confidence levels and sources for your recommendations

When analyzing data, pay special attention to:
- Items with high elasticity (>3.0) as they are sensitive to price changes
- Items with prices significantly different from competitors (>10%)
- Items with changing cost dynamics (ingredients with rising costs)
- Items where the optimization signals suggest specific actions

Your output should be structured, evidence-based, and directly actionable by the pricing strategy team.
"""

# Initialize tools
tools = []

# Add WebSearchTool if available
if WebSearchTool is not None:
    tools.append(WebSearchTool())

# Add DatabaseTool for competitor information
db_tool = DatabaseTool()  # In production, pass a real db_session
tools.append(db_tool)

# Create the OpenAI Agent instance with tools
openai_agent = Agent(
    name="MarketResearchAgent",
    instructions=OPENAI_AGENT_PROMPT,
    output_type=OpenAIResponse,
    tools=tools,
)

class OpenAIAgentWrapper:
    """Wrapper class to provide compatibility with the agent testing framework"""
    
    def __init__(self, agent):
        self.agent = agent
        self.name = "openai_agent"
        self.display_name = "OpenAI Market Research Agent"
        self.description = "Analyzes data collection output to identify items that need market research and conducts that research."
        self.capabilities = [
            "Analyze product data to identify research candidates",
            "Research market trends for specific products",
            "Gather competitor pricing information",
            "Identify supply chain issues and events impacting pricing",
            "Provide research-based pricing recommendations"
        ]
    
    def process(self, context):
        """Process method compatible with the agent testing framework
        
        Args:
            context: Dictionary containing execution context including user_id, db, test_mode, etc.
            
        Returns:
            Results from the OpenAI agent analysis
        """
        import os
        from ..sample_outputs.data_collection_output import output as sample_output
        import logging
        
        logger = logging.getLogger(__name__)
        
        # In a production environment, we would get data from the database
        # For testing, use the sample data collection output
        try:
            # Check for OpenAI API key
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                return {
                    "status": "error",
                    "error": "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.",
                    "research_candidates": [],
                    "message": "Unable to perform market research without API key."
                }
                
            # Process the sample data to identify research candidates
            logger.info("Processing data collection output to identify research candidates")
            data = sample_output  # Use sample data for testing
            
            # Parse data and get all original items
            all_items = parse_data_collection_output(data)
            
            # Identify research candidates
            research_candidates = identify_research_candidates(all_items)
            
            if not research_candidates:
                return {
                    "status": "success",
                    "message": "No items identified that need further market research.",
                    "research_candidates": [],
                    "research_results": None
                }
            
            # Always proceed with research (test mode restriction removed)
            logger.info(f"Identified {len(research_candidates)} research candidates for further analysis")
            
            # For real execution, conduct research on the candidates
            logger.info(f"Conducting market research on selected candidates")
            
            # Use all identified research candidates
            limited_candidates = research_candidates
            
            # Call the OpenAI agent to conduct research, passing both research candidates and all items
            try:
                research_results = conduct_research(limited_candidates, all_items)
                return {
                    "status": "success",
                    "message": f"Completed market research for {len(limited_candidates)} items. Output includes all {len(all_items)} menu items.",
                    "research_results": research_results.dict() if hasattr(research_results, "dict") else research_results,
                }
            except Exception as e:
                logger.exception(f"Error during research: {str(e)}")
                return {
                    "status": "partial_success",
                    "message": f"Successfully identified research candidates but encountered error during research: {str(e)}",
                    "research_candidates": [item.dict() for item in research_candidates],
                    "error": str(e)
                }
                
        except Exception as e:
            logger.exception(f"Error processing data: {str(e)}")
            return {
                "status": "error",
                "message": f"Error processing data collection output: {str(e)}",
                "error": str(e)
            }


def get_openai_agent():
    """Returns the OpenAI Agent instance wrapped for compatibility"""
    return OpenAIAgentWrapper(openai_agent)

def parse_data_collection_output(data_collection_json: str) -> List[Dict[str, Any]]:
    """
    Parse the output from the data collection agent into a structured format
    
    Args:
        data_collection_json: JSON string output from data collection agent
        
    Returns:
        List of dictionaries containing item data
    """
    try:
        # First try direct JSON parsing
        data = json.loads(data_collection_json)
        return data.get('items', data) if isinstance(data, dict) else data
    except json.JSONDecodeError:
        # If the input is not valid JSON, try to extract it from the string
        # (in case it's wrapped in python assignment syntax)
        if 'output = """' in data_collection_json:
            json_str = data_collection_json.split('output = """')[1].split('"""')[0].strip()
            try:
                parsed_data = json.loads(json_str)
                return parsed_data.get('items', parsed_data) if isinstance(parsed_data, dict) else parsed_data
            except json.JSONDecodeError:
                raise ValueError(f"Unable to parse data collection output: {data_collection_json[:100]}...")
        raise ValueError(f"Unable to parse data collection output: {data_collection_json[:100]}...")
    
    # If we have a valid object but need to unwrap an items array
    if isinstance(data, dict) and 'items' in data:
        return data['items']

def identify_research_candidates(items: List[Dict[str, Any]]) -> List[ResearchItem]:
    """
    Identify items that would benefit from further research using LLM-based qualitative assessment
    
    Args:
        items: List of item data dictionaries
        
    Returns:
        List of ResearchItem objects
    """
    import os
    import logging
    from openai import OpenAI
    import json
    
    logger = logging.getLogger(__name__)
    
    # Check for OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.warning("No OpenAI API key found. Falling back to rule-based identification.")
        # Fallback to simplified rule-based identification - minimal version
        research_candidates = []
        for idx, item in enumerate(items):
            if idx < 3:  # Just take first 3 items in fallback mode
                research_candidates.append(
                    ResearchItem(
                        item_id=item.get("item_id", str(idx)),
                        item_name=item.get("item_name", f"Item {idx}"),
                        research_reason="Selected for basic market research",
                        research_focus=["General market conditions"]
                    )
                )
        return research_candidates
    
    # The data is already structured, so we'll pass it directly without creating a summary
    # Just limit to max 20 items to avoid exceeding token limits
    items_to_analyze = items
    
    # Craft a prompt that asks the model to identify research candidates
    prompt = """
    You are an AI assistant helping with dynamic pricing optimization. Based on the data collection output for 
    multiple items, identify which specific items would benefit most from further market research.
    
    Follow these guidelines to select items:
    1. Focus on items with high price elasticity (price sensitive items)
    2. Prioritize items with significant differences from competitor pricing
    3. Consider items with changing cost structures or supply chain issues
    4. Look for items where optimization signals suggest specific actions needed
    5. Select only items that truly need research - don't select everything
    6. Look for upcoming events (concerts, festivals, reunions, etc.) that may impact demand for certain items
    
    For each item you select, provide:
    - A specific reason why this item needs further research (be analytical and specific)
    - 1-3 focused areas for the research to investigate

    For those you do not select, leave research reason and focus blank
    
    The data collection output is structured as follows:
    {item_data}
    
    Respond in this JSON format only (no additional text):
    [
      {{
        "item_id": "id",
        "item_name": "name",
        "research_reason": "detailed reason for selecting this item",
        "research_focus": ["area1", "area2"]
      }}
    ]
    
    Important: Select only items that would benefit most from research. Quality over quantity.
    """
    
    # Use OpenAI API for analysis
    try:
        client = OpenAI(api_key=api_key)
        
        # Make the API call with the raw data (limited to avoid token limits)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a pricing analyst identifying items that need market research."},
                {"role": "user", "content": prompt.format(item_data=json.dumps(items_to_analyze, indent=2))}
            ],
            temperature=0.3,  # Lower temperature for more consistent results
            max_tokens=2000
        )
        
        # Extract and parse the response
        if response and response.choices and len(response.choices) > 0:
            result_text = response.choices[0].message.content
            
            # Try to parse the JSON response
            try:
                # Clean the response in case there's markdown code block formatting
                cleaned_result = result_text
                if "```json" in result_text:
                    cleaned_result = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    cleaned_result = result_text.split("```")[1].strip()
                
                # Parse the cleaned JSON
                candidate_data = json.loads(cleaned_result)
                
                # Convert to ResearchItem objects
                research_candidates = []
                for item in candidate_data:
                    research_candidates.append(
                        ResearchItem(
                            item_id=item.get("item_id", ""),
                            item_name=item.get("item_name", ""),
                            research_reason=item.get("research_reason", "Identified by qualitative analysis"),
                            research_focus=item.get("research_focus", ["Market trends"])
                        )
                    )
                    
                logger.info(f"LLM identified {len(research_candidates)} research candidates")
                return research_candidates
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing LLM response: {e}\nResponse: {result_text[:200]}...")
                # Fall back to basic selection
        
        # Fallback case if parsing fails
        logger.warning("Falling back to basic selection due to parsing error")
        
    except Exception as e:
        logger.error(f"Error during LLM-based candidate identification: {str(e)}")
    
    # Fallback to very simple selection (first 2 items) if all else fails
    research_candidates = []
    for idx, item in enumerate(items[:2]):  # Just take first 2 items in emergency fallback
        research_candidates.append(
            ResearchItem(
                item_id=item.get("item_id", str(idx)),
                item_name=item.get("item_name", f"Item {idx}"),
                research_reason="Selected for basic market research (fallback)",
                research_focus=["General market conditions"]
            )
        )
    
    return research_candidates

def process_data_collection_output(data_collection_output: str) -> List[ResearchItem]:
    """
    Process the data collection output and identify items for research
    
    Args:
        data_collection_output: Output from the data collection agent
        
    Returns:
        List of items that would benefit from further research
    """
    items = parse_data_collection_output(data_collection_output)
    return identify_research_candidates(items)

def conduct_research(items_to_research: List[ResearchItem], all_items: List[Dict[str, Any]]) -> OpenAIResponse:
    """
    Use the OpenAI API to conduct research on the identified items
    
    Args:
        items_to_research: List of items to research
        all_items: List of all menu items (to include in final output)
        
    Returns:
        Research results and recommendations
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
            return OpenAIResponse(
                items_to_research=items_to_research,
                research_results=[],
                summary="Error: OpenAI API key not found. Please set the OPENAI_API_KEY environment variable."
            )
            
        client = OpenAI(api_key=api_key)
        
        # Construct prompt with info from the items
        items_info = ""
        for idx, item in enumerate(items_to_research, 1):
            items_info += f"\nITEM {idx}: {item.item_name} (ID: {item.item_id})\n"
            items_info += f"Research reason: {item.research_reason}\n"
            items_info += f"Research focus: {', '.join(item.research_focus)}\n"
            
        prompt = f"""
        You are a dynamic pricing expert analyzing market research data for a retail business.
        Please conduct comprehensive market research for the following items based on their research focus areas:
        
        {items_info}
        
        For each item, provide structured analysis covering:
        1. Current market trends affecting pricing potential
        2. Supply chain insights/challenges
        3. Upcoming events in the user's area and seasonality impacts on demand
        4. Competitor analysis and strategies
        5. A specific pricing recommendation with reasoning and confidence level
        
        Format your response with clear headings for each item and section.
        """
        
        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a market research expert specializing in pricing analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,  # Balanced between creativity and consistency
            max_tokens=3000
        )
        
        # Extract and structure the response
        if response and response.choices and len(response.choices) > 0:
            research_text = response.choices[0].message.content
            
            # Try to parse the response text into per-item summaries
            item_summaries = {}
            current_item_id = None
            current_text = ""
            
            # Simple parsing of the response text to extract per-item sections
            # We look for item headers like "ITEM X: Name (ID: n)" or similar patterns
            for line in research_text.split('\n'):
                # Check for item headers to identify new sections
                if 'ITEM' in line and '(ID:' in line:
                    # If we were already processing an item, save it first
                    if current_item_id:
                        item_summaries[current_item_id] = current_text
                    
                    # Extract the item ID from the header
                    try:
                        item_id_match = re.search(r'\(ID:\s*([\w\d]+)\)', line)
                        if item_id_match:
                            current_item_id = item_id_match.group(1)
                            current_text = line + '\n'  # Start with the header
                    except:
                        # If extraction fails, use a fallback approach
                        for item in items_to_research:
                            if item.item_name in line:
                                current_item_id = item.item_id
                                current_text = line + '\n'
                                break
                else:
                    # Continue adding text to the current item
                    if current_item_id:
                        current_text += line + '\n'
            
            # Don't forget to save the last item
            if current_item_id and current_item_id not in item_summaries:
                item_summaries[current_item_id] = current_text
                
            # If parsing failed, use a more resilient approach with simple item mention detection
            if not item_summaries:
                logger.warning("Could not parse response by headers, falling back to item mention detection")
                for item in items_to_research:
                    item_text = ""
                    lines_to_check = research_text.split('\n')
                    in_item_section = False
                    
                    for i, line in enumerate(lines_to_check):
                        if item.item_name in line and ("ITEM" in line or "#" in line):
                            in_item_section = True
                            item_text += line + '\n'
                        elif in_item_section:
                            # Check if we've reached the next item section
                            next_item = False
                            for other_item in items_to_research:
                                if other_item.item_id != item.item_id and other_item.item_name in line and ("ITEM" in line or "#" in line):
                                    next_item = True
                                    break
                            
                            if next_item:
                                in_item_section = False
                            else:
                                item_text += line + '\n'
                    
                    if item_text:
                        item_summaries[item.item_id] = item_text
                    
            # Create a lookup of item IDs selected for research
            research_item_ids = {item.item_id for item in items_to_research}
            
            # Create comprehensive research results for ALL menu items
            all_research_results = []
            
            # Process all items from the original data collection output
            for item_data in all_items:
                item_id = item_data.get("item_id", "")
                item_name = item_data.get("item_name", "")
                                # If this item was researched, add full research results with its specific summary
                if item_id in research_item_ids:
                    item_specific_summary = item_summaries.get(item_id, "Analysis not available for this specific item.")
                    
                    # Extract any upcoming events if mentioned
                    upcoming_events = []
                    # Simple heuristic to find mentioned events
                    if "upcoming event" in item_specific_summary.lower() or "seasonal event" in item_specific_summary.lower():
                        try:
                            # Look for events mentioned
                            event_matches = re.findall(r'([A-Z][a-z]+ (?:festival|concert|holiday|season|event))', item_specific_summary)
                            if event_matches:
                                for event in event_matches[:3]:  # Limit to 3 events
                                    upcoming_events.append({"name": event, "date": ""})  # Date not extracted
                        except:
                            pass
                    
                    research_result = ResearchResults(
                        item_id=item_id,
                        item_name=item_name,
                        confidence=0.7,
                        sources=["OpenAI API Analysis"],
                        upcoming_events=upcoming_events,
                        research_summary=item_specific_summary  # Add the item-specific summary
                    )
                # If not researched, add a placeholder with blank research fields
                else:
                    research_result = ResearchResults(
                        item_id=item_id,
                        item_name=item_name,
                        confidence=0.0,  # Zero confidence since no research was done
                        sources=[],
                        upcoming_events=[],
                        research_summary=""  # Empty summary for non-researched items
                    )
                
                all_research_results.append(research_result)
            
            # Return structured response with ALL items included
            return OpenAIResponse(
                items_to_research=items_to_research,  # Only researched items 
                research_results=all_research_results,  # ALL items with per-item summaries
                summary=""  # No global summary needed as we have per-item summaries
            )
        else:
            return OpenAIResponse(
                items_to_research=items_to_research,
                research_results=[],
                summary="Error: Unable to get a response from the OpenAI API."
            )
    
    except Exception as e:
        logger.exception(f"Error conducting research: {str(e)}")
        # In case of any errors during the research process
        return OpenAIResponse(
            items_to_research=items_to_research,
            research_results=[],
            summary=f"Error conducting research: {str(e)}"
        )
