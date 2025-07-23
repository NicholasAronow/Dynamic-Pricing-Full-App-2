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

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent, InjectedState

from services.database_service import DatabaseService
from config.database import get_db

logger = logging.getLogger(__name__)

@dataclass
class MultiAgentResponse:
    """Response from multi-agent system execution"""
    final_result: str
    execution_path: List[str]
    total_execution_time: float
    metadata: Dict[str, Any]
    messages: List[Dict[str, Any]]

class PricingTools:
    """Tools for pricing agents"""
    
    @staticmethod
    @tool
    def search_web_for_pricing(query: str) -> str:
        """Search the web for pricing information and market data"""
        # Simulate web search results for pricing information
        return f"Web search results for '{query}': Found 15 relevant sources. Key findings: Market average price is $45-65 range, trending upward 8% this quarter. Top competitors: CompanyA ($52), CompanyB ($48), CompanyC ($61). Consumer sentiment shows price sensitivity at $60+ threshold."
    
    @staticmethod
    @tool
    def search_competitor_analysis(product_name: str, category: str) -> str:
        """Search for competitor pricing and positioning analysis"""
        return f"Competitor analysis for {product_name} in {category}: 12 direct competitors identified. Price range: $35-$75. Market leader pricing at $58 with premium positioning. Opportunity gap identified in $42-$48 range for value positioning."
    
    @staticmethod
    @tool
    def get_market_trends(category: str) -> str:
        """Get current market trends and consumer behavior"""
        return f"Market trends for {category}: Demand increasing 12% YoY, seasonal peak in Q4, price elasticity -1.3, consumer preference shifting toward value-oriented options, online sales growing 25% faster than retail."
    
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
    
    def _get_db_service(self):
        """Get database service with current session"""
        if not self.db_session:
            # Get a fresh database session using the generator
            db_gen = get_db()
            self.db_session = next(db_gen)
        return DatabaseService(self.db_session)
    
    def create_get_user_items_data(self):
        """Create the tool with proper context"""
        @tool
        def get_user_items_data() -> str:
            """Get all menu items for the current user from the database"""
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                
                db_service = self._get_db_service()
                items = db_service.get_user_items(self.user_id)
                
                if not items:
                    return f"No menu items found for user {self.user_id}"
                
                items_info = []
                for item in items:
                    item_info = f"- {item.name}: ${item.current_price:.2f}"
                    if hasattr(item, 'category') and item.category:
                        item_info += f" (Category: {item.category})"
                    if hasattr(item, 'description') and item.description:
                        item_info += f" - {item.description[:100]}..."
                    items_info.append(item_info)
                
                return f"Found {len(items)} menu items:\n" + "\n".join(items_info)
            except Exception as e:
                return f"Error retrieving items: {str(e)}"
        
        return get_user_items_data
    
    def create_get_user_sales_data(self):
        """Create the sales data tool"""
        @tool
        def get_user_sales_data(limit: int = 10) -> str:
            """Get recent sales/orders data for the current user from the database"""
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                    
                db_service = self._get_db_service()
                orders = db_service.get_user_orders(self.user_id, limit=limit)
                
                if not orders:
                    return f"No recent orders found for user {self.user_id}"
                
                total_revenue = sum(order.total_amount for order in orders if order.total_amount)
                order_count = len(orders)
                avg_order_value = total_revenue / order_count if order_count > 0 else 0
                
                recent_orders = []
                for order in orders[:5]:  # Show top 5 recent orders
                    order_info = f"- Order #{order.id}: ${order.total_amount:.2f} on {order.order_date.strftime('%Y-%m-%d')}"
                    recent_orders.append(order_info)
                
                return f"Sales Summary (last {limit} orders):\n" + \
                       f"Total Revenue: ${total_revenue:.2f}\n" + \
                       f"Order Count: {order_count}\n" + \
                       f"Average Order Value: ${avg_order_value:.2f}\n\n" + \
                       f"Recent Orders:\n" + "\n".join(recent_orders)
            except Exception as e:
                return f"Error retrieving sales data: {str(e)}"
        
        return get_user_sales_data
    
    def create_get_competitor_data(self):
        """Create the competitor data tool"""
        @tool
        def get_competitor_data() -> str:
            """Get competitor analysis data for the current user from the database"""
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                    
                db_service = self._get_db_service()
                competitor_report = db_service.get_latest_competitor_report(self.user_id)
                
                result = []
                
                if competitor_report:
                    result.append(f"Latest Competitor Report (from {competitor_report.created_at.strftime('%Y-%m-%d')}):")
                    if hasattr(competitor_report, 'summary') and competitor_report.summary:
                        result.append(competitor_report.summary[:500] + "...")
                    if hasattr(competitor_report, 'insights') and competitor_report.insights:
                        result.append("\nKey Insights:")
                        for insight in competitor_report.insights[:3]:
                            result.append(f"- {insight}")
                
                return "\n".join(result) if result else f"No competitor data found for user {self.user_id}"
            except Exception as e:
                return f"Error retrieving competitor data: {str(e)}"
        
        return get_competitor_data
    
    def create_get_price_history_data(self):
        """Create the price history tool"""
        @tool
        def get_price_history_data(item_name: str = None) -> str:
            """Get price history data for the current user's items"""
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                    
                db_service = self._get_db_service()
                items = db_service.get_user_items(self.user_id)
                
                if not items:
                    return f"No items found for user {self.user_id}"
                
                # Filter by item name if provided
                if item_name:
                    items = [item for item in items if item_name.lower() in item.name.lower()]
                    if not items:
                        return f"No items found matching '{item_name}' for user {self.user_id}"
                
                price_histories = []
                for item in items[:5]:  # Limit to 5 items
                    history = db_service.get_price_history(item.id)
                    if history:
                        price_histories.append(f"\n{item.name} price history:")
                        for price_change in history[:3]:  # Show last 3 changes
                            price_histories.append(f"  - ${price_change.previous_price:.2f} → ${price_change.new_price:.2f} on {price_change.changed_at.strftime('%Y-%m-%d')}")
                
                return "\n".join(price_histories) if price_histories else "No price history found"
            except Exception as e:
                return f"Error retrieving price history: {str(e)}"
        
        return get_price_history_data
    
    def create_get_business_profile_data(self):
        """Create the business profile tool"""
        @tool
        def get_business_profile_data() -> str:
            """Get business profile information for the current user"""
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                    
                db_service = self._get_db_service()
                profile = db_service.get_business_profile(self.user_id)
                
                if not profile:
                    return f"No business profile found for user {self.user_id}"
                
                profile_info = []
                if hasattr(profile, 'business_name') and profile.business_name:
                    profile_info.append(f"Business: {profile.business_name}")
                if hasattr(profile, 'industry') and profile.industry:
                    profile_info.append(f"Industry: {profile.industry}")
                if hasattr(profile, 'company_size') and profile.company_size:
                    profile_info.append(f"Company Size: {profile.company_size}")
                if hasattr(profile, 'description') and profile.description:
                    profile_info.append(f"Description: {profile.description[:200]}...")
                
                return "\n".join(profile_info) if profile_info else "Business profile found but no details available"
            except Exception as e:
                return f"Error retrieving business profile: {str(e)}"
        
        return get_business_profile_data

def create_handoff_tool(*, agent_name: str, description: str | None = None):
    """Create a handoff tool for agent-to-agent communication"""
    name = f"transfer_to_{agent_name}"
    description = description or f"Transfer control to {agent_name}"

    @tool(name, description=description)
    def handoff_tool(
        state: Annotated[MessagesState, InjectedState], 
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        tool_message = {
            "role": "tool",
            "content": f"Successfully transferred to {agent_name}",
            "name": name,
            "tool_call_id": tool_call_id,
        }
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
            prompt="""You are an expert pricing consultant and orchestrator. You help businesses make informed pricing decisions through conversational interaction.
            
            Your capabilities:
            - Engage in natural conversation about pricing challenges
            - Ask clarifying questions to understand the business context
            - Coordinate with specialized sub-agents when needed:
            * Web Researcher: For market data and competitor analysis
            * Algorithm Selector: For choosing optimal pricing strategies
            * Database Agent: For retrieving business data, sales history, menu items, and competitor information
            - Provide expert pricing advice and recommendations
            - Explain pricing concepts in accessible terms
            
            Workflow:
            1. Understand the user's pricing question or challenge
            2. If you need specific data, delegate to the appropriate sub-agent ONCE
            3. Once you have sufficient information, provide a comprehensive final answer
            4. Do NOT repeatedly call the same sub-agent or transfer control unnecessarily
            5. Always aim to provide a complete, helpful response based on available information
            
            IMPORTANT: After gathering information from sub-agents, provide your final answer directly. Do not keep transferring control back and forth. Be decisive and conclusive in your responses.
            
            Always be helpful, professional, and focus on practical pricing solutions.""",
            name="pricing_orchestrator"
        )
        
        # Web Research Agent
        self.web_researcher = create_react_agent(
            model=self.model,
            tools=[
                self.tools.search_web_for_pricing,
                self.tools.search_competitor_analysis,
                self.tools.get_market_trends
            ],
            prompt="""You are a web research specialist focused on pricing and market intelligence.
            
            Your role is to:
            - Search for current market pricing data and trends
            - Analyze competitor pricing strategies and positioning
            - Gather market intelligence that informs pricing decisions
            - Provide comprehensive market context for pricing strategies
            
            Always provide specific, actionable market insights that directly support pricing decisions.""",
            name="web_researcher"
        )
        
        # Algorithm Selection Agent
        self.algorithm_selector = create_react_agent(
            model=self.model,
            tools=[
                self.tools.select_pricing_algorithm
            ],
            prompt="""You are a pricing algorithm specialist who recommends optimal pricing strategies.
            
            Your role is to:
            - Analyze business context, market conditions, and goals
            - Select the most appropriate pricing algorithm for the situation
            - Explain the rationale behind algorithm selection
            - Provide clear next steps for implementation
            
            Available algorithms include competitive pricing, value-based pricing, dynamic pricing, 
            market penetration, price skimming, and psychological pricing.
            
            Always explain your selection clearly and provide implementation guidance.""",
            name="algorithm_selector"
        )
        
        # Database Agent - use factory methods if database_tools exists
        if self.database_tools:
            self.database_agent = create_react_agent(
                model=self.model,
                tools=[
                    self.database_tools.create_get_user_items_data(),
                    self.database_tools.create_get_user_sales_data(),
                    self.database_tools.create_get_competitor_data(),
                    self.database_tools.create_get_price_history_data(),
                    self.database_tools.create_get_business_profile_data()
                ],
                prompt="""You are a database specialist who retrieves and analyzes business data to support pricing decisions.
                
                Your role is to:
                - Access and retrieve business data from the database
                - Analyze sales history, menu items, and pricing trends
                - Provide competitor data and market positioning insights
                - Extract relevant business profile information
                - Present data in a clear, actionable format for pricing decisions
                
                Available data includes:
                - Menu items and current pricing
                - Sales history and revenue trends
                - Competitor pricing data
                - Price change history
                - Business profile and market information
                
                IMPORTANT: Retrieve the requested data efficiently and provide a comprehensive summary. Do not make multiple redundant tool calls. Provide your analysis and return control to the orchestrator promptly.
                
                Always provide specific, data-driven insights that directly support pricing strategy decisions.""",
                name="database_agent"
            )
        else:
            # Create a dummy database agent that returns error messages
            self.database_agent = create_react_agent(
                model=self.model,
                tools=[],
                prompt="You are a database specialist but no database connection is available. Inform the user that database access is not configured.",
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
            
            # Add previous messages if provided
            if previous_messages:
                for msg in previous_messages:
                    if msg.get('role') == 'user':
                        messages.append(HumanMessage(content=msg.get('content', '')))
                    elif msg.get('role') == 'assistant':
                        messages.append(AIMessage(content=msg.get('content', '')))
            
            # Add the new user message
            messages.append(HumanMessage(content=task))
            
            initial_state = {"messages": messages}
            
            # Rest of the method remains the same...
            
            # Yield initial status
            yield json.dumps({
                "type": "status",
                "message": "🤖 Initializing pricing expert system...",
                "timestamp": datetime.now().isoformat()
            })
            
            # Stream the graph execution
            result = None
            current_agent = None
            previous_message_count = len(initial_state["messages"])  # Track initial message count
            
            async for chunk in self.supervisor_graph.astream(
                initial_state,
                config={"recursion_limit": 50}
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
                        
                        yield json.dumps({
                            "type": "agent_start",
                            "agent": node_name,
                            "agent_name": agent_display_name,
                            "message": f"{agent_display_name} is thinking...",
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    result = node_output
                    
                    # Extract and stream only NEW messages (beyond the initial conversation)
                    if "messages" in node_output and node_output["messages"]:
                        current_messages = node_output["messages"]
                        
                        # Only process messages that are new (beyond the initial count)
                        if len(current_messages) > previous_message_count:
                            # Get only the new messages
                            new_messages = current_messages[previous_message_count:]
                            
                            for msg in new_messages:
                                if isinstance(msg, AIMessage) and msg.content:
                                    content = msg.content
                                    
                                    # Yield message start
                                    yield json.dumps({
                                        "type": "message_start",
                                        "agent": current_agent,
                                        "timestamp": datetime.now().isoformat()
                                    })
                                    
                                    # Stream words with small delays
                                    words = content.split()
                                    for i, word in enumerate(words):
                                        yield json.dumps({
                                            "type": "message_chunk",
                                            "agent": current_agent,
                                            "content": word + (" " if i < len(words) - 1 else ""),
                                            "timestamp": datetime.now().isoformat()
                                        })
                                        await asyncio.sleep(0.02)  # Reduced delay for better UX
                                    
                                    # Yield message complete
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
        
        # Get the last AI message as the final result
        # LangGraph messages are AIMessage/HumanMessage objects, not dicts
        from langchain_core.messages import AIMessage
        
        ai_messages = [msg for msg in messages if isinstance(msg, AIMessage)]
        if ai_messages:
            return ai_messages[-1].content or "No content in final message"
        
        return "No AI response generated"
    
    def _convert_messages_to_dict(self, messages: List[Any]) -> List[Dict[str, Any]]:
        """Convert LangGraph message objects to dictionaries for JSON serialization"""
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        
        converted_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                converted_messages.append({
                    "role": "user",
                    "content": msg.content,
                    "type": "human"
                })
            elif isinstance(msg, AIMessage):
                converted_messages.append({
                    "role": "assistant", 
                    "content": msg.content,
                    "type": "ai"
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
