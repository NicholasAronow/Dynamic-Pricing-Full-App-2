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
TAVILY_API_KEY = ""
@dataclass
class MultiAgentResponse:
    """Response from multi-agent system execution"""
    final_result: str
    execution_path: List[str]
    total_execution_time: float
    metadata: Dict[str, Any]
    messages: List[Dict[str, Any]]

class PricingTools:
    """Tools for pricing agents with real web search"""
    
    def __init__(self):
        # Initialize Tavily client
        self.tavily_api_key = os.getenv("TAVILY_API_KEY") or TAVILY_API_KEY
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
    
    def __init__(self, db_session=None):
        self.model = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        self.tools = PricingTools()
        self.db_session = db_session
        self.database_tools = None  # Will be initialized when user_id is available
        
        # Don't create agents here - they'll be created when needed
        self.pricing_orchestrator = None
        self.web_researcher = None
        self.algorithm_selector = None
        self.database_agent = None
        self.supervisor_graph = None
        
        # Create handoff tools for sub-agents
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
        
        # Initialize agents
        self._create_agents()
        
        # Build supervisor graph (main architecture)
        self.supervisor_graph = self._build_supervisor_graph()
    
    def _initialize_agents_with_context(self, user_id: int):
        """Initialize or reinitialize agents with user context"""
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
        
        # Create agents
        self._create_agents()
        
        # Build supervisor graph
        self.supervisor_graph = self._build_supervisor_graph()

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
            prompt="""You are an elite pricing consultant and orchestrator with deep expertise in pricing strategy, revenue optimization, and market dynamics. You help businesses make data-driven pricing decisions through intelligent conversation and analysis.

<identity>
You are the lead pricing strategist coordinating a team of specialized sub-agents. Your role is to understand complex pricing challenges, gather necessary information, and use the algorithm agent to implement actionable pricing recommendations that drive business growth.
</identity>

<capabilities>
- Engage in natural, consultative conversations about pricing challenges
- Use the database as a source of truth before asking the client any clarifying questions
- Ask strategic clarifying questions to understand business context, goals, and constraints for any information that could not be provided by the database
- Coordinate with specialized sub-agents for specific expertise:
  * Web Researcher: For real-time market data, competitor analysis, and industry trends
  * Algorithm Selector: For choosing and implementing optimal pricing strategies
  * Database Agent: For retrieving business data, sales history, product catalogs, and historical performance
- Synthesize information from multiple sources into cohesive pricing strategies
- Explain complex pricing concepts in accessible, business-friendly terms
- Provide implementation roadmaps with clear next steps
</capabilities>

<workflow>
1. **Understand the Query**
   - Parse the user's pricing question or challenge
   - Identify key business objectives and constraints
   - Determine what information is needed to provide a comprehensive answer

2. **Information Gathering**
   - Assess what information you already have
   - Delegate to appropriate sub-agents ONCE for specific data needs
   - Wait for complete responses before proceeding
   - Never call the same sub-agent repeatedly for the same query

3. **Analysis and Synthesis**
   - Combine insights from sub-agents with your pricing expertise
   - Consider multiple pricing strategies and their trade-offs
   - Factor in market conditions, competitive landscape, and business goals

4. **Deliver Recommendations**
   - Provide a comprehensive, actionable answer
   - Include specific pricing recommendations with rationale
   - Suggest implementation steps and success metrics
   - Offer to dive deeper into specific aspects if needed

5. **Follow-up**
   - Be ready to answer clarifying questions
   - Adjust recommendations based on new constraints or information
   - Provide alternative strategies if requested
</workflow>

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
- ALWAYS provide complete, conclusive answers
- Gather necessary information from the database before asking the user for it
- NEVER repeatedly delegate to the same sub-agent
- Use markdown to format responses, and include "\\n" to create new lines
- Consider psychological pricing factors (e.g., price anchoring, perception)
- Account for price elasticity and customer segments
- Factor in competitive dynamics and market positioning
- Consider both short-term revenue and long-term brand implications
- Suggest A/B testing approaches when uncertainty exists
- Provide metrics to measure pricing strategy success
</best_practices>

<common_pricing_scenarios>
1. **New Product Launch**: Consider skimming vs. penetration strategies
2. **Competitive Pressure**: Analyze value proposition and differentiation
3. **Market Expansion**: Account for regional differences and local competition
4. **Revenue Optimization**: Balance volume and margin goals
5. **Product Portfolio**: Consider cannibalization and bundling opportunities
6. **Seasonal Pricing**: Factor in demand fluctuations and inventory costs
7. **B2B vs B2C**: Adjust for different buying behaviors and decision processes
</common_pricing_scenarios>

When formatting responses:
- Always add a blank line before starting a list
- Use proper markdown list syntax:
  - For bullet points: `- item`
  - For numbered lists: `1. item`
- Ensure lists have proper spacing for readability

Remember: You are the strategic pricing expert that businesses rely on for critical revenue decisions. Every recommendation should be thoughtful, data-driven, and actionable.
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
        """Create SQL-based database agent using LangChain SQLDatabase and toolkit"""
        try:
            # Import database configuration
            from config.database import DATABASE_URL
            
            # Create SQLDatabase connection
            db = SQLDatabase.from_uri(DATABASE_URL)
            
            # Create SQL toolkit with tools
            toolkit = SQLDatabaseToolkit(db=db, llm=self.model)
            sql_tools = toolkit.get_tools()
            
            # System prompt for SQL agent
            sql_agent_prompt = """
You are a database specialist agent that helps analyze business data by generating and executing SQL queries.

## Your Capabilities:
- Generate SQL queries based on natural language requests
- Execute queries safely against the database
- Analyze query results and provide insights
- Answer both quantitative and qualitative business questions

## Database Schema Context:
The database contains tables for:
- menu_items: Product catalog with prices, costs, categories
- orders: Sales transactions with timestamps and totals
- order_items: Line items linking orders to menu items with quantities
- competitor_entities: Competitor information and pricing data
- competitor_items: Competitor menu items and prices
- users: User accounts and business information

## Safety Guidelines:
- ONLY use SELECT statements - never INSERT, UPDATE, DELETE, or DROP
- Always limit query results (use LIMIT clause when appropriate)
- Be cautious with large result sets
- Validate queries before execution
- If unsure about a query, explain your approach first

## Response Format:
1. Understand the business question or analysis request
2. Generate appropriate SQL query with explanation
3. Execute the query using available tools
4. Analyze results and provide business insights
5. Suggest follow-up analyses if relevant

## Example Workflow:
User: "What are our top-selling items this month?"
1. Generate SQL to find top items by quantity/revenue this month
2. Execute query using sql_db_query tool
3. Analyze results to identify trends and insights
4. Provide actionable recommendations

Always focus on providing valuable business insights, not just raw data.
"""
            
            # Create the SQL agent
            sql_agent = create_react_agent(
                model=self.model,
                tools=sql_tools,
                prompt=sql_agent_prompt,
                name="database_agent"
            )
            
            logger.info("✅ SQL Database Agent created successfully")
            return sql_agent
            
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
                        
                        elif msg.get('content', '').strip():
                            # This is a regular assistant message with content and no tool calls
                            clean_message = AIMessage(
                                content=msg.get('content', ''),
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
                    logger.info(f"History message {i}: {type(msg).__name__} - {msg.content[:50]}...")
            
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
            
            async for chunk in self.supervisor_graph.astream(
                initial_state,
                config=config
            ):
                for node_name, node_output in chunk.items():
                    if node_name not in execution_path:
                        execution_path.append(node_name)
                        current_agent = node_name
                        
                        # Yield agent activation
                        agent_display_name = {
                            "pricing_orchestrator": "💼 Pricing Expert",
                            "web_researcher": "🔍 Market Researcher", 
                            "algorithm_selector": "⚙️ Algorithm Specialist",
                            "database_agent": "🗄️ Database Specialist"
                        }.get(node_name, f"🤖 {node_name}")
                    
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

                    # Extract and stream only NEW messages (beyond the initial conversation)
                    if "messages" in node_output and node_output["messages"]:
                        current_messages = node_output["messages"]
                        
                        # Only process messages that are new (beyond the initial count)
                        if len(current_messages) > previous_message_count:
                            # Get only the new messages
                            new_messages = current_messages[previous_message_count:]
                            
                            for msg in new_messages:
                                # Include all AI messages, not just from the orchestrator
                                if isinstance(msg, AIMessage) and msg.content:
                                    content = msg.content
                                    
                                    # Determine which agent this is from
                                    agent_name = current_agent
                                    
                                    # Yield message start
                                    yield json.dumps({
                                        "type": "message_start",
                                        "agent": agent_name,
                                        "timestamp": datetime.now().isoformat()
                                    })
                                    
                                    # Stream the content
                                    words = content.split(' ')
                                    for i, word in enumerate(words):
                                        if not word:
                                            continue
                                        
                                        yield json.dumps({
                                            "type": "message_chunk",
                                            "agent": agent_name,
                                            "content": word + (" " if i < len(words) - 1 else ""),
                                            "timestamp": datetime.now().isoformat()
                                        })
                                        await asyncio.sleep(0.02)
                                    
                                    # Yield message complete
                                    yield json.dumps({
                                        "type": "message_complete",
                                        "agent": agent_name,
                                        "timestamp": datetime.now().isoformat()
                                    })
                            
                            # Update the previous message count
                            previous_message_count = len(current_messages)
            
            # Final result
            final_result = self._extract_final_result(result["messages"]) if result else "No response generated"
            total_time = (datetime.now() - start_time).total_seconds()
            converted_messages = self._convert_messages_to_dict(result["messages"]) if result else []
            
            yield json.dumps({
                "type": "complete",
                "final_result": final_result,
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
        """Extract the final result from message history"""
        if not messages:
            return "No messages generated"
        
        # Get all AI messages (not just the last one)
        from langchain_core.messages import AIMessage
        
        ai_messages = [msg for msg in messages if isinstance(msg, AIMessage) and msg.content]
        
        if not ai_messages:
            return "No AI response generated"
        
        # If there are multiple AI messages, concatenate them
        # This captures responses from all agents including tool results
        if len(ai_messages) > 1:
            # Join all AI message contents with proper spacing
            all_content = []
            for msg in ai_messages:
                if msg.content and msg.content.strip():
                    all_content.append(msg.content.strip())
            
            return "\n\n".join(all_content) if all_content else "No content in messages"
        else:
            return ai_messages[-1].content or "No content in final message"
    
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
