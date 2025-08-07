"""
LangGraph Multi-Agent Service - Modern Implementation

This service uses LangGraph's prebuilt components and official patterns
to create robust multi-agent systems for dynamic pricing applications.
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from typing import Annotated
import os

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent, InjectedState
from langchain_core.messages import ToolMessage
from tavily import TavilyClient

# SQL Database imports
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool

from services.database_service import DatabaseService
from config.database import get_db
from config.external_apis import get_langsmith_client, LANGSMITH_TRACING, LANGSMITH_PROJECT

logger = logging.getLogger(__name__)

# Initialize LangSmith tracing if enabled
if LANGSMITH_TRACING:
    langsmith_client = get_langsmith_client()
    if langsmith_client:
        logger.info(f"LangSmith tracing enabled for project: {LANGSMITH_PROJECT}")
    else:
        logger.warning("LangSmith tracing requested but client initialization failed")
else:
    langsmith_client = None
    logger.info("LangSmith tracing disabled")
@dataclass
class MultiAgentResponse:
    """Response from multi-agent system execution"""
    final_result: str
    execution_path: List[str]
    total_execution_time: float
    metadata: Dict[str, Any]
    messages: List[Dict[str, Any]]

class DatabaseWriteTools:
    """Tools for safely modifying database information"""
    
    def __init__(self, user_id: int = None, db_session=None):
        self.db_session = db_session
        self.user_id = user_id
    
    @tool
    def add_competitor(self, name: str, location: str, category: str, notes: str = None) -> str:
        """Add a new competitor to the database
        
        Args:
            name: Competitor business name
            location: Business location/address
            category: Business category (e.g., 'coffee shop', 'restaurant')
            notes: Optional notes about the competitor
        """
        try:
            from models.competitor import CompetitorEntity
            
            # Check if competitor already exists
            existing = self.db_session.query(CompetitorEntity).filter_by(
                name=name,
                user_id=self.user_id
            ).first()
            
            if existing:
                return f"Competitor '{name}' already exists in your database."
            
            # Create new competitor
            new_competitor = CompetitorEntity(
                name=name,
                location=location,
                category=category,
                notes=notes,
                user_id=self.user_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.db_session.add(new_competitor)
            self.db_session.commit()
            
            return f"✅ Successfully added '{name}' as a competitor in {location}."
            
        except Exception as e:
            self.db_session.rollback()
            return f"❌ Error adding competitor: {str(e)}"
    
    @tool
    def update_item_price(self, item_name: str, new_price: float, notes: str = None) -> str:
        """Update the price of an existing menu item
        
        Args:
            item_name: Name of the menu item
            new_price: New price for the item
            notes: Optional notes about the price change
        """
        try:
            from models.item import Item
            from models.price_history import PriceHistory
            
            # Find the item
            item = self.db_session.query(Item).filter_by(
                name=item_name,
                user_id=self.user_id
            ).first()
            
            if not item:
                return f"❌ Item '{item_name}' not found in your menu."
            
            # Store old price in history
            price_history = PriceHistory(
                item_id=item.id,
                old_price=item.price,
                new_price=new_price,
                change_reason=notes or "Price updated via Ada",
                changed_by=self.user_id,
                created_at=datetime.now()
            )
            
            # Update the item price
            old_price = item.price
            item.price = new_price
            item.updated_at = datetime.now()
            
            self.db_session.add(price_history)
            self.db_session.commit()
            
            return f"✅ Updated '{item_name}' price from ${old_price:.2f} to ${new_price:.2f}"
            
        except Exception as e:
            self.db_session.rollback()
            return f"❌ Error updating price: {str(e)}"
    
    @tool
    def add_menu_item(self, name: str, price: float, category: str, 
                      description: str = None, cost: float = None) -> str:
        """Add a new item to your menu
        
        Args:
            name: Item name
            price: Selling price
            category: Item category
            description: Optional item description
            cost: Optional item cost (for margin calculations)
        """
        try:
            from models.item import Item
            
            # Check if item already exists
            existing = self.db_session.query(Item).filter_by(
                name=name,
                user_id=self.user_id
            ).first()
            
            if existing:
                return f"Item '{name}' already exists. Use update_item_price to modify it."
            
            # Create new item
            new_item = Item(
                name=name,
                price=price,
                category=category,
                description=description,
                cost=cost,
                user_id=self.user_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.db_session.add(new_item)
            self.db_session.commit()
            
            margin = ((price - cost) / price * 100) if cost else None
            margin_text = f" (Margin: {margin:.1f}%)" if margin else ""
            
            return f"✅ Added '{name}' to menu at ${price:.2f}{margin_text}"
            
        except Exception as e:
            self.db_session.rollback()
            return f"❌ Error adding item: {str(e)}"
    
    @tool
    def add_competitor_item(self, competitor_name: str, item_name: str, 
                           price: float, category: str = None) -> str:
        """Add a competitor's menu item for price comparison
        
        Args:
            competitor_name: Name of the competitor
            item_name: Name of their menu item
            price: Price of the item
            category: Optional category
        """
        try:
            from models.competitor import CompetitorEntity, CompetitorItem
            
            # Find competitor
            competitor = self.db_session.query(CompetitorEntity).filter_by(
                name=competitor_name,
                user_id=self.user_id
            ).first()
            
            if not competitor:
                return f"❌ Competitor '{competitor_name}' not found. Add them first using add_competitor."
            
            # Check if item already exists
            existing = self.db_session.query(CompetitorItem).filter_by(
                competitor_id=competitor.id,
                name=item_name
            ).first()
            
            if existing:
                # Update existing item
                existing.price = price
                existing.updated_at = datetime.now()
                self.db_session.commit()
                return f"✅ Updated '{item_name}' price for {competitor_name} to ${price:.2f}"
            
            # Create new competitor item
            new_item = CompetitorItem(
                competitor_id=competitor.id,
                name=item_name,
                price=price,
                category=category,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.db_session.add(new_item)
            self.db_session.commit()
            
            return f"✅ Added '{item_name}' at ${price:.2f} for competitor {competitor_name}"
            
        except Exception as e:
            self.db_session.rollback()
            return f"❌ Error adding competitor item: {str(e)}"

    @tool
    def bulk_import_data(self, data_type: str, csv_content: str) -> str:
        """Import multiple items from CSV data
        
        Args:
            data_type: Type of data ('menu_items', 'competitors', 'competitor_items')
            csv_content: CSV formatted string with headers
        """
        try:
            import csv
            from io import StringIO
            
            # Parse CSV
            reader = csv.DictReader(StringIO(csv_content))
            rows = list(reader)
            
            if not rows:
                return "❌ No data found in CSV"
            
            results = []
            errors = []
            
            if data_type == 'menu_items':
                for row in rows:
                    try:
                        result = self.add_menu_item(
                            name=row.get('name'),
                            price=float(row.get('price', 0)),
                            category=row.get('category', 'Uncategorized'),
                            description=row.get('description'),
                            cost=float(row.get('cost')) if row.get('cost') else None
                        )
                        results.append(result)
                    except Exception as e:
                        errors.append(f"Row {row}: {str(e)}")
            
            elif data_type == 'competitors':
                for row in rows:
                    try:
                        result = self.add_competitor(
                            name=row.get('name'),
                            location=row.get('location', ''),
                            category=row.get('category', ''),
                            notes=row.get('notes')
                        )
                        results.append(result)
                    except Exception as e:
                        errors.append(f"Row {row}: {str(e)}")
            
            summary = f"Imported {len(results)} items successfully."
            if errors:
                summary += f"\n{len(errors)} errors occurred:\n" + "\n".join(errors[:5])
            
            return summary
            
        except Exception as e:
            return f"❌ Error importing data: {str(e)}"

class PricingTools:
    """Tools for pricing agents with real web search"""
    
    def __init__(self):
        # Initialize Tavily client
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        if self.tavily_api_key:
            self.tavily = TavilyClient(api_key=self.tavily_api_key)
        else:
            self.tavily = None
            logger.warning("TAVILY_API_KEY not set - web search will use simulated results")
    
    def _search_web_impl(self, query: str, search_type: str = "general") -> str:
        """Internal implementation of web search"""
        if not self.tavily:
            return f"[Simulated] Web search results for '{query}': Limited data available. Please set TAVILY_API_KEY for real results."
        
        try:
            # Optimize query based on search type
            optimized_query = self._optimize_query_for_search_type(query, search_type)
            
            # Configure search parameters based on type
            search_params = self._get_search_params_for_type(search_type)
            
            # Perform search with optimized parameters
            search_results = self.tavily.search(
                query=optimized_query,
                **search_params
            )
            
            # Format results based on search type
            return self._format_search_results(search_results, query, search_type)
            
        except Exception as e:
            logger.error(f"Tavily search error for query '{query}': {e}")
            return f"Search error: {str(e)}. Please try rephrasing your query or check if it's under 400 characters."
    
    def create_search_web_tool(self):
        """Create the search_web tool with proper binding"""
        @tool
        def search_web(query: str, search_type: str = "general") -> str:
            """Search the web for any information using Tavily's advanced search capabilities.
            
            Args:
                query: The search query (keep under 400 characters for best results)
                search_type: Type of search - 'general', 'news', 'pricing', 'competitor', 'market_trends', 'events'
            
            Returns:
                Formatted search results with summary and key findings
            """
            return self._search_web_impl(query, search_type)
        
        return search_web
    
    def _optimize_query_for_search_type(self, query: str, search_type: str) -> str:
        """Optimize query based on search type for better results"""
        # Ensure query is under 400 characters
        if len(query) > 350:  # Leave room for additional keywords
            query = query[:350].rsplit(' ', 1)[0]  # Truncate at word boundary
        
        # Add context keywords based on search type
        if search_type == "pricing":
            return f"{query} pricing cost price analysis market"
        elif search_type == "competitor":
            return f"{query} competitors comparison market analysis competitive landscape"
        elif search_type == "market_trends":
            return f"{query} market trends industry analysis consumer behavior"
        elif search_type == "news":
            return f"{query} latest news recent developments"
        elif search_type == "events":
            return f"{query} events calendar local events upcoming festivals conferences"
        else:
            return query
    
    def _get_search_params_for_type(self, search_type: str) -> dict:
        """Get optimized search parameters for different search types"""
        base_params = {
            "max_results": 5,
            "include_answer": True,
            "include_raw_content": False,
            "include_images": False
        }
        
        if search_type == "news":
            base_params.update({
                "topic": "news",
                "days": 7,  # Last 7 days for news
                "search_depth": "basic"  # Faster for news
            })
        elif search_type == "events":
            base_params.update({
                "search_depth": "basic",  # Fast search for events
                "time_range": "month",  # Look for events in the next month
                "include_raw_content": False  # Don't need full content for events
            })
        elif search_type in ["pricing", "competitor", "market_trends"]:
            base_params.update({
                "search_depth": "advanced",  # More thorough for business intelligence
                "include_raw_content": True  # Better for detailed analysis
            })
        else:
            base_params["search_depth"] = "basic"
        
        return base_params
    
    def _format_search_results(self, search_results: dict, original_query: str, search_type: str) -> str:
        """Format search results with type-specific formatting"""
        result_text = f"🔍 Web Search Results for '{original_query}' ({search_type}):\n\n"
        
        # Include AI-generated summary if available
        if search_results.get('answer'):
            result_text += f"📋 **Summary:** {search_results['answer']}\n\n"
        
        # Include individual results with relevance scoring
        if search_results.get('results'):
            result_text += "🔗 **Key Sources:**\n"
            for i, result in enumerate(search_results['results'][:5], 1):
                title = result.get('title', 'No title')
                url = result.get('url', 'No URL')
                content = result.get('content', 'No content available')
                score = result.get('score', 0)
                
                # Add relevance indicator
                relevance = "🟢 High" if score > 0.8 else "🟡 Medium" if score > 0.5 else "🔴 Low"
                
                result_text += f"\n{i}. **{title}** ({relevance} Relevance)\n"
                result_text += f"   🌐 Source: {url}\n"
                
                # Truncate content based on search type
                if search_type == "events":
                    content_length = 250  # Medium length for event descriptions
                elif search_type in ["pricing", "competitor"]:
                    content_length = 300  # Longer for detailed business analysis
                else:
                    content_length = 200  # Standard length
                
                result_text += f"   📄 {content[:content_length]}...\n"
                
                # Add published date for news
                if search_type == "news" and result.get('published_date'):
                    result_text += f"   📅 Published: {result['published_date']}\n"
                
                # Add event-specific formatting hints
                if search_type == "events":
                    # Look for date/time patterns in content for events
                    import re
                    date_patterns = re.findall(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:,?\s+\d{4})?|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}', content, re.IGNORECASE)
                    if date_patterns:
                        result_text += f"   🗓️ Event Date: {date_patterns[0]}\n"
        
        # Add search metadata
        result_text += f"\n🔍 Search completed with {len(search_results.get('results', []))} results"
        
        return result_text
    
    @tool
    def search_web_for_pricing(self, query: str) -> str:
        """Search the web for pricing information and market data"""
        return self.search_web(query, "pricing")
    
    @tool
    def search_competitor_analysis(self, product_name: str, category: str) -> str:
        """Search for competitor pricing and positioning analysis"""
        query = f"{product_name} {category} competitors"
        return self.search_web(query, "competitor")
    
    @tool
    def get_market_trends(self, category: str) -> str:
        """Get current market trends and consumer behavior"""
        query = f"{category} market trends 2024 2025 consumer behavior pricing elasticity demand"
        return self.search_web(query, "market_trends")

    @staticmethod
    @tool
    def select_pricing_algorithm(product_type: str, market_conditions: str, business_goals: str) -> str:
        """Select the most appropriate pricing algorithm based on conditions"""
        algorithms = {
            "competitive": "Competitive Pricing Algorithm - Matches competitor prices with small adjustments",
            "value_based": "Value-Based Pricing Algorithm - Prices based on perceived customer value", 
            "dynamic": "Dynamic Pricing Algorithm - Real-time price adjustments based on demand/supply",
            "penetration": "Market Penetration Algorithm - Low initial prices to gain market share",
            "skimming": "Price Skimming Algorithm - High initial prices for early adopters",
            "psychological": "Psychological Pricing Algorithm - Uses pricing psychology (e.g., $9.99)"
        }
        
        # Simple logic to recommend algorithm (in real implementation, this would be more sophisticated)
        if "competitive" in market_conditions.lower():
            selected = "competitive"
        elif "premium" in business_goals.lower() or "luxury" in product_type.lower():
            selected = "skimming"
        elif "market share" in business_goals.lower():
            selected = "penetration"
        elif "demand fluctuation" in market_conditions.lower():
            selected = "dynamic"
        else:
            selected = "value_based"
            
        return f"SELECTED ALGORITHM: {algorithms[selected]}. Rationale: Based on {product_type} product type, {market_conditions} market conditions, and {business_goals} business goals, this algorithm will optimize for your specific situation."
    @tool
    def process_uploaded_file(self, file_type: str, file_content: str, 
                            file_name: str = None) -> str:
        """Process uploaded files and extract structured data
        
        Args:
            file_type: Type of file (csv, json, excel, pdf)
            file_content: Base64 encoded file content or text content
            file_name: Optional filename for context
        """
        try:
            import base64
            import json
            import csv
            from io import StringIO
            
            if file_type == 'csv':
                # Process CSV content
                reader = csv.DictReader(StringIO(file_content))
                data = list(reader)
                
                # Analyze the data structure
                if not data:
                    return "Empty CSV file"
                
                # Detect data type based on columns
                columns = data[0].keys()
                
                if 'price' in columns or 'item' in columns:
                    return f"Menu data detected with {len(data)} items. Use 'bulk_import_data' tool to import."
                elif 'competitor' in columns or 'business' in columns:
                    return f"Competitor data detected with {len(data)} entries. Use 'bulk_import_data' tool to import."
                else:
                    return f"CSV processed: {len(data)} rows, columns: {', '.join(columns)}"
                    
            elif file_type == 'json':
                # Process JSON content
                data = json.loads(file_content)
                return f"JSON processed with {len(data)} items" if isinstance(data, list) else "JSON object processed"
                
            else:
                return f"File type '{file_type}' processing not yet implemented"
                
        except Exception as e:
            return f"Error processing file: {str(e)}"
class DatabaseTools:
    """Tools for accessing database information"""
    
    def __init__(self, user_id: int = None, db_session=None):
        self.db_session = db_session
        self.user_id = user_id
    

def create_handoff_tool(*, agent_name: str, description: str | None = None):
    """Create a handoff tool for agent-to-agent communication"""
    name = f"transfer_to_{agent_name}"
    description = description or f"Transfer control to {agent_name}"

    @tool(name, description=description)
    def handoff_tool(
        state: Annotated[MessagesState, InjectedState], 
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        
        tool_message = ToolMessage(
            content=f"Successfully transferred to {agent_name}",
            name=name,
            tool_call_id=tool_call_id,
        )
        return Command(  
            goto=agent_name,  
            update={"messages": state["messages"] + [tool_message]},  
            graph=Command.PARENT,  
        )
    return handoff_tool

class LangGraphService:
    """Pricing Expert Orchestrator with Sub-Agents"""
    
    def _safe_extract_content(self, content) -> str:
        """Safely extract text content from Claude message content that might be a list or other type"""
        if isinstance(content, list):
            # Claude sometimes returns content as a list of content blocks
            content_text = ""
            for block in content:
                if isinstance(block, dict) and 'text' in block:
                    content_text += block['text']
                elif isinstance(block, str):
                    content_text += block
            return content_text
        elif isinstance(content, str):
            return content
        else:
            # Convert any other type to string
            return str(content) if content else ""
    
    def __init__(self, db_session=None):
        self.model = ChatAnthropic(
            model="claude-sonnet-4-20250514", 
            temperature=0.3,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.tools = PricingTools()
        self.db_session = db_session  # Store the session
        self.database_tools = None
        self.user_id = None  # Initialize as None
        
        # Don't create agents here - they'll be created when needed
        self.pricing_orchestrator = None
        self.web_researcher = None
        self.algorithm_selector = None
        self.database_agent = None
        self.supervisor_graph = None
        
        # Log initialization
        logger.info(f"LangGraphService initialized with db_session: {bool(db_session)}")
    
    def _initialize_agents_with_context(self, user_id: int):
        """Initialize or reinitialize agents with user context"""
        logger.info(f"Initializing agents with user context for user_id: {user_id}")
        
        # Store user_id first
        self.user_id = user_id
        
        # Initialize database tools with user_id
        self.database_tools = DatabaseTools(user_id=user_id, db_session=self.db_session)
        
        # Create handoff tools
        self.transfer_to_web_researcher = create_handoff_tool(
            agent_name="web_researcher",
            description="Transfer to web research agent for market data and competitor analysis"
        )
        self.transfer_to_algorithm_selector = create_handoff_tool(
            agent_name="algorithm_selector",
            description="Transfer to algorithm selection agent for pricing strategy recommendations"
        )
        self.transfer_to_database_agent = create_handoff_tool(
            agent_name="database_agent",
            description="Transfer to database agent to retrieve business data, sales history, menu items, and competitor information from the database"
        )
        
        # Create agents (this will now have access to self.user_id)
        self._create_agents()
        
        # Build supervisor graph
        self.supervisor_graph = self._build_supervisor_graph()
        
        logger.info(f"✅ Agents initialized with context for user {user_id}")

    def _create_agents(self):
        """Create the pricing orchestrator and specialized sub-agents"""
        
        # Main Pricing Expert Orchestrator
        self.pricing_orchestrator = create_react_agent(
            model=self.model,
            tools=[
                self.transfer_to_web_researcher,
                self.transfer_to_algorithm_selector,
                self.transfer_to_database_agent
            ],
            prompt="""You are Ada, an elite pricing consultant and multi-agent orchestrator specializing in comprehensive pricing optimization.

<identity>
You are a strategic pricing expert who coordinates multiple specialized agents to deliver thorough, data-driven pricing recommendations. You excel at breaking down complex pricing challenges into systematic analyses that leverage both internal data and external market intelligence.
</identity>

<capabilities>
- Orchestrate comprehensive pricing analyses using multiple specialized agents
- Coordinate iterative research workflows between database analysis and web research
- Synthesize complex data from multiple sources into actionable pricing strategies
- Manage multi-step optimization processes for entire product portfolios
- Execute sophisticated competitive intelligence gathering
- Perform deep-dive market research with multiple search iterations
- Generate algorithm-specific pricing recommendations with detailed parameters
</capabilities>

<specialized_agents>
**Database Agent**: Analyzes internal business data
- Sales performance, trends, and historical patterns
- Menu items, pricing history, and cost structures
- Competitor tracking and price comparisons
- Customer behavior and order analytics
- Financial metrics and profitability analysis

**Web Researcher**: Gathers external market intelligence
- Current market pricing and competitor analysis
- Industry trends and supply cost fluctuations
- Local events and seasonal demand factors
- Consumer sentiment and market positioning
- Regulatory changes and market disruptions

**Algorithm Selector**: Recommends optimal pricing strategies
- Selects appropriate algorithms based on market conditions
- Provides specific implementation parameters
- Considers business goals and constraints
- Balances risk and opportunity
</specialized_agents>

<iterative_workflow_methodology>
**For Comprehensive Analyses:**

1. **Initial Assessment**
   - Start with database agent to understand current business state
   - Identify key products, performance metrics, and existing challenges
   - Establish baseline data for optimization

2. **Market Intelligence Gathering**
   - Use web researcher for broad market overview
   - Research competitor pricing and positioning
   - Investigate supply costs and industry trends
   - Look for local events or seasonal factors

3. **Deep Dive Analysis** (Iterate as needed)
   - Return to database agent for specific performance deep-dives
   - Use web researcher for targeted competitor research
   - Cross-reference internal data with external market signals
   - Identify gaps requiring additional research

4. **Strategic Synthesis**
   - Combine all gathered intelligence
   - Identify optimization opportunities
   - Consider constraints and business objectives

5. **Algorithm Selection & Implementation**
   - Use algorithm selector for each product category
   - Provide specific parameters and implementation timelines
   - Include monitoring and adjustment recommendations

**Key Principle**: Continue iterating between agents until you have comprehensive data to make informed recommendations. Each agent call should build upon previous findings.
</iterative_workflow_methodology>

<coordination_guidelines>
- **Multiple Agent Calls**: You SHOULD call agents multiple times as needed for thorough analysis
- **Build Upon Previous Results**: Each subsequent agent call should reference and build upon earlier findings
- **Cross-Reference Data**: Compare internal database insights with external web research
- **Iterative Refinement**: Use new information to ask more targeted questions
- **Comprehensive Coverage**: Don't stop until you have sufficient data for confident recommendations

**Example Multi-Agent Sequence:**
1. Database Agent: "Analyze sales performance for all menu items"
2. Web Researcher: "Research competitor pricing for coffee shop items"
3. Database Agent: "Compare our pricing to competitor data for top-selling items"
4. Web Researcher: "Research supply cost trends for coffee and food ingredients"
5. Database Agent: "Analyze profit margins considering current costs"
6. Algorithm Selector: "Recommend pricing strategies for each product category"
</coordination_guidelines>

<communication_style>
- Professional yet approachable
- Use business terminology appropriately but explain complex concepts
- Structure responses with clear headers and bullet points for readability
- Lead with key insights and recommendations
- Support claims with data and market evidence
- Acknowledge uncertainty when appropriate
- Use markdown to format responses, and include "\\n" to create new lines
</communication_style>

<best_practices>
**Analysis Methodology:**
- ALWAYS provide complete, comprehensive analyses before making recommendations
- Use iterative agent coordination to build a complete picture
- Cross-reference internal data with external market intelligence
- Continue research until you have sufficient data for confident recommendations
- Each agent call should build upon and reference previous findings

**Decision Quality:**
- Support all recommendations with specific data points and evidence
- Consider psychological pricing factors (e.g., price anchoring, perception)
- Account for price elasticity and customer segments
- Factor in competitive dynamics and market positioning
- Consider both short-term revenue and long-term brand implications
- Balance risk and opportunity in all recommendations

**Implementation Guidance:**
- Provide specific algorithm parameters for each recommendation
- Include implementation timelines and monitoring metrics
- Suggest A/B testing approaches when uncertainty exists
- Offer contingency plans for different market responses
- Use markdown to format responses with proper spacing and structure
</best_practices>

<comprehensive_analysis_examples>
**Example: Menu Optimization Request**
1. Database Agent: "Analyze current menu performance and profitability"
2. Web Researcher: "Research competitor pricing for similar items"
3. Database Agent: "Compare our prices to competitor benchmarks"
4. Web Researcher: "Investigate supply cost trends and market conditions"
5. Database Agent: "Analyze customer purchase patterns and price sensitivity"
6. Web Researcher: "Research local events and seasonal demand factors"
7. Algorithm Selector: "Recommend specific pricing strategies for each item category"

**Example: Competitive Response Analysis**
1. Database Agent: "Identify our most vulnerable products to competition"
2. Web Researcher: "Research competitor pricing changes and market positioning"
3. Database Agent: "Analyze historical performance during competitive pressure"
4. Web Researcher: "Investigate competitor customer sentiment and reviews"
5. Algorithm Selector: "Recommend defensive and offensive pricing strategies"

**Key Principle**: Each analysis should be thorough enough to support confident, data-driven pricing decisions.
</comprehensive_analysis_examples>

**Response Structure:**
For comprehensive analyses, structure your final response as:

1. **Executive Summary**: Key findings and primary recommendations
2. **Current State Analysis**: What the data reveals about current performance
3. **Market Intelligence**: External factors and competitive landscape
4. **Optimization Opportunities**: Specific areas for improvement
5. **Implementation Plan**: Detailed algorithm recommendations with parameters
6. **Monitoring & Success Metrics**: How to measure and adjust strategies

**Formatting Guidelines:**
- Use clear headers and bullet points for readability
- Include specific data points and percentages
- Provide algorithm parameters in the format: `algorithm_name(parameter: value, item_id: id)`
- Add proper spacing between sections

Remember: You are orchestrating a comprehensive pricing intelligence system. Use all available agents iteratively to deliver thorough, actionable insights that drive revenue growth.
""",
            name="pricing_orchestrator"
        )
        
        # Web Research Agent
        self.web_researcher = create_react_agent(
            model=self.model,
            tools=[
                self.tools.create_search_web_tool()
            ],
            prompt="""You are a specialized web research analyst focused on pricing intelligence and market dynamics. Your expertise lies in gathering, analyzing, and synthesizing real-time market data to support pricing decisions.

<identity>
You are a meticulous researcher who uncovers critical market insights that drive pricing strategy. You combine data gathering skills with analytical capabilities to provide actionable market intelligence.
</identity>

<research_capabilities>
- Use flexible web search to find any information needed for pricing analysis
- Search for current market pricing data across industries and regions
- Analyze competitor pricing strategies, positioning, and value propositions
- Gather market trends, consumer behavior patterns, and demand signals
- Identify pricing innovations and emerging pricing models
- Research regulatory considerations and market constraints
- Find industry benchmarks and best practices
- Discover customer willingness-to-pay indicators
- Perform targeted searches for news, general information, or specific business intelligence
</research_capabilities>

<research_methodology>
1. **Query Analysis**
   - Understand the specific pricing context
   - Identify key competitors and market segments
   - Determine relevant geographic markets
   - Note any time-sensitive factors

2. **Comprehensive Search Strategy**
   - Start with broad market overview searches
   - Narrow to specific competitors and products
   - Look for recent pricing changes and announcements
   - Search for consumer sentiment and reviews
   - Find industry reports and analyst insights

3. **Data Synthesis**
   - Compile findings into coherent insights
   - Identify patterns and anomalies
   - Highlight opportunities and threats
   - Quantify findings where possible

4. **Actionable Reporting**
   - Present findings in a structured format
   - Lead with most relevant insights
   - Include specific price points and ranges
   - Note confidence levels and data recency
   - Suggest areas for deeper investigation
</research_methodology>

<available_tools>
**search_web(query, search_type)**: Your primary and only search tool for all research needs
   - search_type options: 'general', 'news', 'pricing', 'competitor', 'market_trends', 'events'
   - Automatically optimizes search parameters based on type
   - Provides relevance scoring and structured results
   - Handles one or more research scenarios most pertinent to the prompt:
     * 'pricing': For product pricing, cost analysis, market rates
     * 'competitor': For competitive positioning, competitor pricing strategies  
     * 'market_trends': For industry trends, consumer behavior, demand patterns
     * 'news': For recent developments, announcements, market changes
     * 'events': For local events, festivals, conferences, seasonal activities that might affect demand
     * 'general': For any other business intelligence or research needs

This single tool replaces all specialized search functions and provides maximum flexibility for any research query.
</available_tools>

<information_priorities>
1. **Competitor Pricing**: Exact prices, tiers, and recent changes
2. **Market Positioning**: How competitors justify their prices
3. **Customer Perception**: Reviews mentioning price/value
4. **Market Trends**: Growth rates, demand shifts, seasonal patterns
5. **Price Elasticity Indicators**: How customers respond to price changes
6. **Innovation Signals**: New pricing models or strategies emerging
</information_priorities>

<output_format>
Structure your research findings as:
- **Executive Summary**: Key findings in 2-3 sentences
- **Competitive Landscape**: Competitor prices and positioning
- **Market Dynamics**: Trends, growth, and demand patterns
- **Customer Insights**: Perception of value and price sensitivity
- **Opportunities**: Gaps or advantages to exploit
- **Risks**: Threats or constraints to consider
- **Data Quality Note**: Recency and reliability of sources
</output_format>

<quality_standards>
- Prioritize recent data (last 3-6 months preferred)
- Distinguish between list prices and actual selling prices
- Note promotional pricing vs. regular pricing
- Identify premium vs. budget market segments
- Consider total cost of ownership, not just initial price
- Look for hidden fees or bundled value
- Verify findings across multiple sources when possible
</quality_standards>

Remember: Your research directly impacts revenue decisions worth potentially millions. Be thorough, accurate, and focused on actionable insights that drive pricing strategy.
""",
            name="web_researcher"
        )
        
        # Algorithm Selection Agent
        self.algorithm_selector = create_react_agent(
            model=self.model,
            tools=[
                self.tools.select_pricing_algorithm
            ],
            prompt="""You are a pricing algorithm specialist with deep expertise in quantitative pricing strategies and implementation. You recommend optimal pricing approaches based on business context, market dynamics, and strategic objectives.

<identity>
You are a strategic advisor who bridges pricing theory with practical implementation. Your recommendations are grounded in economic principles, behavioral psychology, and real-world business constraints.
</identity>

<algorithm_expertise>
Available Pricing Algorithms:

1. **Competitive Pricing Algorithm**
   - Matches or undercuts competitor prices strategically
   - Best for: Commoditized products, price-sensitive markets
   - Implementation: Price monitoring, adjustment rules, positioning strategy

2. **Value-Based Pricing Algorithm**
   - Prices based on perceived customer value and willingness to pay
   - Best for: Differentiated products, strong brand, unique features
   - Implementation: Customer research, value mapping, segment analysis

3. **Dynamic Pricing Algorithm**
   - Real-time price adjustments based on demand, supply, and market conditions
   - Best for: Perishable inventory, high demand variability, digital products
   - Implementation: Demand forecasting, inventory tracking, price optimization

4. **Market Penetration Algorithm**
   - Low initial prices to rapidly gain market share
   - Best for: New market entry, network effects, growth focus
   - Implementation: Loss leader strategy, growth metrics, timeline planning

5. **Price Skimming Algorithm**
   - High initial prices for early adopters, gradual reduction
   - Best for: Innovative products, limited competition, premium positioning
   - Implementation: Launch pricing, reduction schedule, segment targeting

6. **Psychological Pricing Algorithm**
   - Leverages cognitive biases (charm pricing, anchoring, bundling)
   - Best for: Consumer products, retail, emotional purchases
   - Implementation: Price point testing, bundle design, framing strategies
</algorithm_expertise>

<selection_methodology>
1. **Context Analysis**
   - Evaluate product characteristics and differentiation
   - Assess market maturity and competitive intensity
   - Understand customer segments and buying behavior
   - Consider business goals (revenue, market share, profit)
   - Account for operational constraints

2. **Algorithm Matching**
   - Map context factors to algorithm strengths
   - Consider hybrid approaches when appropriate
   - Evaluate implementation complexity vs. benefit
   - Assess data and system requirements
   - Factor in organizational readiness

3. **Recommendation Framework**
   - Primary recommendation with clear rationale
   - Alternative approaches with trade-offs
   - Implementation roadmap with phases
   - Success metrics and KPIs
   - Risk factors and mitigation strategies
</selection_methodology>

<implementation_guidance>
For each selected algorithm, provide:

1. **Quick Start Guide**
   - Initial price point recommendations
   - Key parameters to set
   - Minimum data requirements
   - First 30-day action plan

2. **Technical Requirements**
   - Data collection needs
   - System integration points
   - Calculation methodology
   - Update frequency recommendations

3. **Optimization Parameters**
   - Variables to monitor
   - Adjustment triggers
   - Performance benchmarks
   - A/B testing approach

4. **Common Pitfalls**
   - What to avoid
   - Early warning signs
   - Course correction strategies
</implementation_guidance>

<decision_factors>
Consider these factors when selecting algorithms:
- Market factors: Competition, growth rate, customer sophistication
- Product factors: Lifecycle stage, differentiation, cost structure
- Business factors: Strategic goals, risk tolerance, capabilities
- Customer factors: Price sensitivity, segment diversity, purchase frequency
- Operational factors: Data availability, technical infrastructure, team expertise
</decision_factors>

<output_structure>
Your recommendations should include:
1. **Selected Algorithm**: Name and one-line description
2. **Rationale**: Why this algorithm fits the specific situation
3. **Implementation Steps**: Concrete actions to get started
4. **Expected Outcomes**: Realistic projections and timeline
5. **Success Metrics**: How to measure effectiveness
6. **Alternative Options**: Other viable approaches with trade-offs
7. **Evolution Path**: How to adapt as the business grows
</output_structure>

Remember: Your algorithm selection can make or break a pricing strategy. Be decisive but thoughtful, practical but innovative. Always connect your recommendation back to business outcomes.
""",
            name="algorithm_selector"
        )
        
        # Database Agent - SQL-based implementation
        self.database_agent = self._create_sql_database_agent()
    
    def _create_sql_database_agent(self):
        """Create SQL-based database agent with both read and write capabilities"""
        try:
            # Import database configuration
            from config.database import DATABASE_URL
            import sqlalchemy
            from sqlalchemy.orm import sessionmaker
            
            # Create SQLDatabase connection for read operations
            db = SQLDatabase.from_uri(DATABASE_URL)
            
            # Create SQL toolkit with tools
            toolkit = SQLDatabaseToolkit(db=db, llm=self.model)
            sql_tools = toolkit.get_tools()
            
            # Initialize write tools
            write_tools = []
            
            # Create a session for write operations if we have user context
            if self.db_session and self.user_id:
                # Create DatabaseWriteTools instance
                db_write_tools = DatabaseWriteTools(
                    user_id=self.user_id, 
                    db_session=self.db_session
                )
                
                # Add write capability tools
                write_tools = [
                    db_write_tools.add_competitor,
                    db_write_tools.update_item_price,
                    db_write_tools.add_menu_item,
                    db_write_tools.add_competitor_item,
                    db_write_tools.bulk_import_data,
                ]
                
                logger.info(f"✅ Database write tools initialized for user {self.user_id}")
            else:
                logger.warning(f"⚠️ Database write tools not initialized - user_id: {self.user_id}, db_session: {bool(self.db_session)}")
            
            # For business info updates, create a special tool
            @tool
            def update_business_info(field: str, value: str) -> str:
                """Update business information fields like address, name, phone, etc.
                
                Args:
                    field: The field to update (name, address, city, state, etc.)
                    value: The new value for the field
                """
                if not self.db_session or not self.user_id:
                    return "❌ Cannot update business info without user context"
                
                try:
                    import models
                    
                    # Get the user record
                    user = self.db_session.query(models.User).filter_by(id=self.user_id).first()
                    if not user:
                        return f"❌ User record not found"
                    
                    # Get or create business profile
                    business_profile = user.business
                    if not business_profile:
                        business_profile = models.BusinessProfile(user_id=self.user_id)
                        self.db_session.add(business_profile)
                        self.db_session.flush()  # Get the ID
                    
                    # Map common field names to database columns
                    field_mapping = {
                        'name': 'business_name',
                        'business_name': 'business_name',
                        'address': 'street_address',
                        'street_address': 'street_address',
                        'city': 'city',
                        'state': 'state',
                        'postal_code': 'postal_code',
                        'zip': 'postal_code',
                        'country': 'country',
                        'industry': 'industry',
                        'company_size': 'company_size',
                        'description': 'description',
                        'founded_year': 'founded_year',
                    }
                    
                    # Get the actual database field
                    db_field = field_mapping.get(field.lower(), field.lower())
                    
                    # Check if the field exists on the business profile model
                    if not hasattr(business_profile, db_field):
                        return f"❌ Field '{field}' is not a valid business information field. Available fields: {', '.join(field_mapping.keys())}"
                    
                    # Get old value for confirmation
                    old_value = getattr(business_profile, db_field)
                    
                    # Update the field
                    setattr(business_profile, db_field, value)
                    
                    # Handle special case for founded_year (convert to int if needed)
                    if db_field == 'founded_year' and value:
                        try:
                            setattr(business_profile, db_field, int(value))
                        except ValueError:
                            return f"❌ Founded year must be a valid number, got: {value}"
                    
                    self.db_session.commit()
                    
                    return f"✅ Successfully updated {field} from '{old_value}' to '{value}'"
                    
                except Exception as e:
                    self.db_session.rollback()
                    logger.error(f"Error updating business info: {e}")
                    return f"❌ Error updating {field}: {str(e)}"
            
            # Add the business info update tool if we have context
            if self.db_session and self.user_id:
                write_tools.append(update_business_info)
            
            # Combine all tools
            all_tools = sql_tools + write_tools
            
            # Enhanced prompt with write capabilities
            sql_agent_prompt = """
    You are a database specialist agent that helps analyze and manage business data.

    ## Your Capabilities:
    ### Read Operations:
    - Generate and execute SQL queries for analysis
    - Retrieve business metrics and insights
    - Analyze sales patterns and trends

    ### Write Operations:
    - Update business information (address, phone, email, name)
    - Add new competitors to track
    - Update menu item prices with history tracking
    - Add new menu items with cost/margin data
    - Import competitor pricing information
    - Bulk import data from CSV format

    ## CRITICAL QUERY GUIDELINES - AVOID RATE LIMITING:
    
    ### ❌ NEVER DO THESE QUERIES:
    - SELECT * FROM orders (returns massive datasets)
    - SELECT * FROM order_items (returns massive datasets)
    - Any query that returns more than 1000 rows
    - Bulk retrieval queries without aggregation
    - Raw data dumps without summarization
    
    ### ✅ ALWAYS DO THESE INSTEAD:
    - Use COUNT(), SUM(), AVG(), GROUP BY for aggregation
    - Add LIMIT clauses (typically LIMIT 50 or less)
    - Use date ranges to filter recent data (e.g., WHERE created_at >= DATE('now', '-30 days'))
    - Focus on summary statistics and insights, not raw data
    - Use analytical queries that provide business insights
    
    ### Examples of GOOD queries:
    ```sql
    -- Sales summary by month
    SELECT DATE(created_at, 'start of month') as month, 
           COUNT(*) as order_count, 
           SUM(total_amount) as revenue
    FROM orders 
    WHERE created_at >= DATE('now', '-6 months')
    GROUP BY month;
    
    -- Top selling items
    SELECT i.name, SUM(oi.quantity) as total_sold, 
           AVG(oi.price) as avg_price
    FROM items i
    JOIN order_items oi ON i.id = oi.item_id
    WHERE oi.created_at >= DATE('now', '-30 days')
    GROUP BY i.id, i.name
    ORDER BY total_sold DESC
    LIMIT 10;
    
    -- Performance metrics
    SELECT 
        COUNT(DISTINCT o.id) as total_orders,
        AVG(o.total_amount) as avg_order_value,
        SUM(o.total_amount) as total_revenue
    FROM orders o
    WHERE o.created_at >= DATE('now', '-30 days');
    ```

    ## Available Tools:
    - SQL query tools for reading data
    - update_business_info: Update business details like address, phone, etc.
    - add_competitor: Add new competitor businesses
    - update_item_price: Update menu item prices
    - add_menu_item: Add new items to menu
    - add_competitor_item: Add competitor pricing data
    - bulk_import_data: Import multiple items from CSV

    ## Database Schema:
    - users: Business account information (address, phone, email, etc.)
    - items: Your menu items (name, price, cost, category)
    - orders: Sales transactions (⚠️ LARGE TABLE - always use aggregation)
    - order_items: Order line items (⚠️ LARGE TABLE - always use aggregation)
    - competitor_entities: Competitor businesses
    - competitor_items: Competitor menu/pricing
    - price_history: Track price changes over time

    ## When updating business information:
    1. Use the update_business_info tool for address, phone, email changes
    2. Clearly confirm what was changed
    3. Provide the old and new values

    ## Example:
    User: "Change my business address to 17 Bank Street, Princeton NJ"
    Response: I'll update your business address now.
    [Use update_business_info("address", "17 Bank Street, Princeton NJ")]
    Then report: "✅ Successfully updated your business address to 17 Bank Street, Princeton NJ"

    Remember: 
    - Be helpful, precise, and always confirm successful changes
    - ALWAYS use aggregation and limits for orders/order_items queries
    - Focus on insights and analysis, not raw data retrieval
    - Prevent rate limiting by avoiding bulk data queries
    """
            
            # Create the enhanced SQL agent
            sql_agent = create_react_agent(
                model=self.model,
                tools=all_tools,
                prompt=sql_agent_prompt,
                name="database_agent"
            )
            
            logger.info(f"✅ SQL Database Agent created successfully with {len(all_tools)} tools")
            return sql_agent
            
        except Exception as e:
            logger.error(f"❌ Failed to create SQL Database Agent: {e}", exc_info=True)
            
            # Return a more helpful fallback agent
            fallback_prompt = f"""Database agent initialization failed. Error: {str(e)}
            
    This usually means:
    1. Database connection issues - check DATABASE_URL
    2. Missing database tables - run migrations
    3. Permission issues - check database user permissions

    I cannot perform database operations right now, but I can still help with:
    - General pricing advice
    - Market analysis (via web search)
    - Strategy recommendations

    Please contact support if this persists."""
            
            return create_react_agent(
                model=self.model,
                tools=[],
                prompt=fallback_prompt,
                name="database_agent"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to create SQL Database Agent: {e}")
            # Fallback to dummy agent if SQL setup fails
            return create_react_agent(
                model=self.model,
                tools=[],
                prompt="Database agent is temporarily unavailable due to connection issues. Please try again later.",
                name="database_agent"
            )
    
    def _build_supervisor_graph(self):
        """Build the pricing expert orchestrator graph"""
        graph = (
            StateGraph(MessagesState)
            .add_node("pricing_orchestrator", self.pricing_orchestrator)
            .add_node("web_researcher", self.web_researcher)
            .add_node("algorithm_selector", self.algorithm_selector)
            .add_node("database_agent", self.database_agent)
            .add_edge(START, "pricing_orchestrator")  # Always start with the main orchestrator
            .compile()
        )
        return graph
    
    async def execute_supervisor_workflow(self, task: str, context: str = "", user_id: int = None) -> MultiAgentResponse:
        """Execute pricing consultation using the orchestrator"""
        start_time = datetime.now()
    
        try:
            # Initialize agents with user context if provided
            if user_id:
                self._initialize_agents_with_context(user_id)
            elif not self.supervisor_graph:
                # Initialize without user context if not already initialized
                self._create_agents()
                self.supervisor_graph = self._build_supervisor_graph()
        
            # Prepare conversational message
            initial_message = task
            if context:
                initial_message += f"\n\nAdditional context: {context}"
            
            messages = [{"role": "user", "content": initial_message}]
            
            # Execute the graph and track agent interactions
            execution_path = []
            result = None
            
            # Stream the execution to track which agents are involved
            for chunk in self.supervisor_graph.stream({"messages": messages}):
                for node_name, node_output in chunk.items():
                    if node_name not in execution_path:
                        execution_path.append(node_name)
                    result = node_output
            
            final_result = self._extract_final_result(result["messages"]) if result else "No response generated"
            total_time = (datetime.now() - start_time).total_seconds()
            
            # Convert messages to dictionaries for JSON serialization
            converted_messages = self._convert_messages_to_dict(result["messages"]) if result else []
            
            return MultiAgentResponse(
                final_result=final_result,
                execution_path=execution_path,
                total_execution_time=total_time,
                metadata={
                    "architecture": "pricing_expert",
                    "task": task,
                    "context": context,
                    "message_count": len(converted_messages)
                },
                messages=converted_messages
            )
            
        except Exception as e:
            logger.error(f"Pricing orchestrator workflow error: {e}")
            raise
    
    async def stream_supervisor_workflow(self, task: str, context: str = "", previous_messages: List[Dict] = None, user_id: int = None) -> AsyncGenerator[str, None]:
        """Stream the pricing orchestrator workflow with real-time updates"""
        try:
            start_time = datetime.now()
            execution_path = []
            
            # Initialize agents with user context if provided
            if user_id:
                self._initialize_agents_with_context(user_id)
            elif not self.supervisor_graph:
                # Initialize without user context if not already initialized
                self._create_agents()
                self.supervisor_graph = self._build_supervisor_graph()
        
            # Build initial state with conversation history
            messages = []
            if previous_messages:
                logger.warning(previous_messages)
                logger.info(f"Processing {len(previous_messages)} previous messages")
                for i, msg in enumerate(previous_messages):
                    logger.info(f"Message {i}: role={msg.get('role')}, has_tool_calls={bool(msg.get('tool_calls') or msg.get('additional_kwargs', {}).get('tool_calls'))}, content_length={len(msg.get('content', ''))}")
                
                # Improved message processing to avoid orphaned tool calls
                # We'll build a clean conversation history by only including complete exchanges
                clean_messages = []
                i = len(previous_messages) - 1
                
                while i >= 0:  # Limit to 3 exchanges
                    msg = previous_messages[i]
                    
                    # Always include user messages
                    if msg.get('role') == 'user':
                        clean_messages.insert(0, HumanMessage(content=msg.get('content', '')))
                        i -= 1
                        continue
                    
                    # For assistant messages, check if they're part of a tool call chain
                    elif msg.get('role') == 'assistant':
                        tool_calls = msg.get('tool_calls') or msg.get('additional_kwargs', {}).get('tool_calls', [])
                        
                        if tool_calls:
                            # This is a tool-calling message, skip it and any related tool responses
                            # to avoid orphaned tool calls in the conversation history
                            logger.info(f"Skipping assistant message with tool calls to prevent orphaned messages")
                            
                            # Skip backwards through any tool messages that belong to this tool call
                            j = i - 1
                            while j >= 0:
                                prev_msg = previous_messages[j]
                                if (prev_msg.get('type') == 'tool' or 
                                    prev_msg.get('role') == 'tool' or
                                    'tool_call_id' in prev_msg):
                                    j -= 1  # Skip tool response messages
                                else:
                                    break
                            i = j  # Continue from before the tool chain
                            continue
                        
                        else:
                            # This is a regular assistant message, check if it has content
                            raw_content = msg.get('content', '')
                            safe_content = self._safe_extract_content(raw_content)
                            if safe_content.strip():
                                clean_message = AIMessage(
                                    content=safe_content,
                                    additional_kwargs={}  # Ensure clean message
                                )
                                clean_messages.insert(0, clean_message)
                    
                    # Skip tool messages entirely when building clean history
                    # They should only exist as part of complete tool call chains
                    elif (msg.get('type') == 'tool' or 
                          msg.get('role') == 'tool' or
                          'tool_call_id' in msg):
                        logger.info(f"Skipping orphaned tool message in history cleanup")
                    
                    i -= 1
                
                messages = clean_messages
                logger.info(f"Final conversation history has {len(messages)} clean messages")
                for i, msg in enumerate(messages):
                    # Handle different content types for logging
                    content_preview = str(msg.content)[:50] if msg.content else "No content"
                    logger.info(f"History message {i}: {type(msg).__name__} - {content_preview}...")
            
            # Add the new user message
            messages.append(HumanMessage(content=task))
            logger.info(f"Added new user message: {task}")
            
            initial_state = {"messages": messages}
            
            # Stream the graph execution
            result = None
            current_agent = None
            previous_message_count = len(initial_state["messages"])  # Track initial message count
            
            # Configure tracing for this run
            config = {"recursion_limit": 50}
            if langsmith_client and user_id:
                config["run_name"] = f"pricing_analysis_user_{user_id}"
                config["tags"] = ["dynamic_pricing", "multi_agent", f"user_{user_id}"]
                config["metadata"] = {
                    "user_id": user_id,
                    "task": task[:100],  # Truncate long tasks
                    "timestamp": start_time.isoformat(),
                    "context": context[:200] if context else None  # Truncate long context
                }
            
            # Add after line 735, before the main streaming loop:
# Track which agents have been activated
                        # After the activated_agents initialization (line ~750):
            activated_agents = set()
            agent_responses = {}  # Track responses from each agent

            async for chunk in self.supervisor_graph.astream(
                initial_state,
                config=config
            ):
                for node_name, node_output in chunk.items():
                    if node_name not in execution_path:
                        execution_path.append(node_name)
                        current_agent = node_name
                        
                        # Emit agent_start event
                        if node_name not in activated_agents:
                            activated_agents.add(node_name)
                            agent_display_name = {
                                "pricing_orchestrator": "Ada",
                                "web_researcher": "Market Researcher", 
                                "algorithm_selector": "Algorithm Specialist",
                                "database_agent": "Database Specialist"
                            }.get(node_name, node_name)
                            
                            yield json.dumps({
                                "type": "agent_start",
                                "agent": node_name,
                                "message": f"{agent_display_name} is analyzing...",
                                "timestamp": datetime.now().isoformat()
                            })
                            await asyncio.sleep(0.01)
                    
                    result = node_output
                    
                    # Monitor for tool calls in the messages
                    if "messages" in node_output and node_output["messages"]:
                        current_messages = node_output["messages"]
                        
                        # Check for tool calls in new messages
                        for msg in current_messages[previous_message_count:]:
                            # Check if this is an AIMessage with tool calls
                            if hasattr(msg, 'additional_kwargs') and 'tool_calls' in msg.additional_kwargs:
                                tool_calls = msg.additional_kwargs['tool_calls']
                                for tool_call in tool_calls:
                                    yield json.dumps({
                                        "type": "tool_call",
                                        "agent": current_agent,
                                        "tool_name": tool_call.get('function', {}).get('name', 'Unknown Tool'),
                                        "tool_id": tool_call.get('id', ''),
                                        "timestamp": datetime.now().isoformat()
                                    })
                                    await asyncio.sleep(0.01)
                            
                            # Check for ToolMessage (tool responses)
                            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'ToolMessage':
                                yield json.dumps({
                                    "type": "tool_response",
                                    "agent": current_agent,
                                    "tool_name": getattr(msg, 'name', 'Unknown Tool'),
                                    "tool_call_id": getattr(msg, 'tool_call_id', ''),
                                    "timestamp": datetime.now().isoformat()
                                })
                                await asyncio.sleep(0.01)

                    # Extract and stream messages from ALL agents
                    if "messages" in node_output and node_output["messages"]:
                        current_messages = node_output["messages"]
                        
                        if len(current_messages) > previous_message_count:
                            new_messages = current_messages[previous_message_count:]
                            
                            # In the message streaming section, make sure we stream ALL AI messages:
                            for msg in new_messages:
                                if isinstance(msg, AIMessage) and msg.content:
                                    content = self._safe_extract_content(msg.content)
                                    
                                    # Stream ALL content, not just from certain agents
                                    if content and content.strip():
                                        # Always stream the content
                                        yield json.dumps({
                                            "type": "message_start",
                                            "agent": current_agent,
                                            "timestamp": datetime.now().isoformat()
                                        })
                                        
                                        # Stream the content in chunks
                                        words = content.split(' ')
                                        for i, word in enumerate(words):
                                            if not word:
                                                continue
                                            
                                            yield json.dumps({
                                                "type": "message_chunk",
                                                "agent": current_agent,
                                                "content": word + (" " if i < len(words) - 1 else ""),
                                                "timestamp": datetime.now().isoformat()
                                            })
                                            await asyncio.sleep(0.02)
                                        
                                        yield json.dumps({
                                            "type": "message_complete",
                                            "agent": current_agent,
                                            "timestamp": datetime.now().isoformat()
                                        })
                            
                            # Update the previous message count
                            previous_message_count = len(current_messages)
            
            # Final result
            final_result = self._extract_final_result(result["messages"]) if result else "No response generated"
            total_time = (datetime.now() - start_time).total_seconds()
            converted_messages = self._convert_messages_to_dict(result["messages"]) if result else []
            
            # When sending the complete event, include all content:
            yield json.dumps({
                "type": "complete",
                "final_result": final_result,  # This is just for reference
                "preserve_content": True,  # Signal to frontend to keep accumulated content
                "execution_path": execution_path,
                "total_execution_time": total_time,
                "metadata": {
                    "architecture": "pricing_expert",
                    "task": task,
                    "context": context,
                    "message_count": len(converted_messages)
                },
                "messages": converted_messages,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Streaming pricing orchestrator workflow error: {e}")
            yield json.dumps({
                "type": "error",
                "message": f"Error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
    
    async def execute_swarm_workflow(self, task: str, context: str = "") -> MultiAgentResponse:
        """Alias for supervisor workflow - we only use one architecture now"""
        return await self.execute_supervisor_workflow(task, context)
    
    def _extract_final_result(self, messages: List[Any]) -> str:
        """Extract the final result from message history, prioritizing the orchestrator's final synthesis"""
        if not messages:
            return "No messages generated"
        
        from langchain_core.messages import AIMessage
        
        # Get all AI messages
        ai_messages = [msg for msg in messages if isinstance(msg, AIMessage) and msg.content]
        
        if not ai_messages:
            return "No AI response generated"
        
        # Look for the LAST message from the pricing_orchestrator specifically
        # This should be the synthesized response
        orchestrator_messages = []
        other_agent_messages = []
        
        for msg in ai_messages:
            content = self._safe_extract_content(msg.content)
            if content and content.strip():
                # Try to identify if this is from the orchestrator
                # (You might need to add metadata to messages to track their source)
                if "I'll help you" in content or "Based on" in content or "Let me" in content:
                    orchestrator_messages.append(content.strip())
                else:
                    other_agent_messages.append(content.strip())
        
        # Prefer the last orchestrator message as it should be the synthesis
        if orchestrator_messages:
            return orchestrator_messages[-1]
        
        # If no clear orchestrator message, combine all responses
        all_content = orchestrator_messages + other_agent_messages
        return "\n\n".join(all_content) if all_content else "No content in messages"
    
    def _convert_messages_to_dict(self, messages: List[Any]) -> List[Dict[str, Any]]:
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
        
        converted_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                converted_messages.append({
                    "role": "user",
                    "content": msg.content,
                    "type": "human"
                })
            elif isinstance(msg, AIMessage):
                msg_dict = {
                    "role": "assistant", 
                    "content": msg.content,
                    "type": "ai"
                }
                # Include tool calls if present
                if hasattr(msg, 'additional_kwargs') and 'tool_calls' in msg.additional_kwargs:
                    msg_dict['tool_calls'] = msg.additional_kwargs['tool_calls']
                converted_messages.append(msg_dict)
            elif isinstance(msg, ToolMessage):
                converted_messages.append({
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": msg.tool_call_id,
                    "name": msg.name,
                    "type": "tool"
                })
            elif isinstance(msg, SystemMessage):
                converted_messages.append({
                    "role": "system",
                    "content": msg.content,
                    "type": "system"
                })
            else:
                # Fallback for unknown message types
                converted_messages.append({
                    "role": "unknown",
                    "content": str(msg),
                    "type": "unknown"
                })
        
        return converted_messages
    
    async def get_available_architectures(self) -> List[Dict[str, Any]]:
        """Get information about available pricing consultation architectures"""
        return [
            {
                "name": "supervisor",
                "title": "Pricing Expert Consultation",
                "description": "Conversational pricing expert with specialized sub-agents for research and algorithm selection",
                "agents": ["pricing_orchestrator", "web_researcher", "algorithm_selector"],
                "best_for": "Interactive pricing consultation with market research and algorithm recommendations"
            },
            {
                "name": "swarm",
                "title": "Pricing Expert Consultation", 
                "description": "Same as supervisor - conversational pricing expert system",
                "agents": ["pricing_orchestrator", "web_researcher", "algorithm_selector"],
                "best_for": "Interactive pricing consultation with market research and algorithm recommendations"
            }
        ]
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the multi-agent system"""
        try:
            # Test basic model connectivity
            test_response = await asyncio.to_thread(
                self.model.invoke, 
                [HumanMessage(content="Health check")]
            )
            
            return {
                "status": "healthy",
                "model": "gpt-4o-mini",
                "agents": ["market_analyst", "pricing_strategist", "data_analyst"],
                "architectures": ["supervisor", "swarm"],
                "tools_available": 5
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
