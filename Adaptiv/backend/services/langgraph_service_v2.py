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
    
    def __init__(self):
        self.model = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)  # Slightly higher temp for conversational responses
        self.tools = PricingTools()
        
        # Create handoff tools for sub-agents
        self.transfer_to_web_researcher = create_handoff_tool(
            agent_name="web_researcher",
            description="Transfer to web research agent for market data and competitor analysis"
        )
        self.transfer_to_algorithm_selector = create_handoff_tool(
            agent_name="algorithm_selector",
            description="Transfer to algorithm selection agent for pricing strategy recommendations"
        )
        
        # Initialize agents
        self._create_agents()
        
        # Build supervisor graph (main architecture)
        self.supervisor_graph = self._build_supervisor_graph()
    
    def _create_agents(self):
        """Create the pricing orchestrator and specialized sub-agents"""
        
        # Main Pricing Expert Orchestrator
        self.pricing_orchestrator = create_react_agent(
            model=self.model,
            tools=[
                self.transfer_to_web_researcher,
                self.transfer_to_algorithm_selector
            ],
            prompt="""You are an expert pricing consultant and orchestrator. You help businesses make informed pricing decisions through conversational interaction.
            
            Your capabilities:
            - Engage in natural conversation about pricing challenges
            - Ask clarifying questions to understand the business context
            - Coordinate with specialized sub-agents when needed:
              * Web Researcher: For market data and competitor analysis
              * Algorithm Selector: For choosing optimal pricing strategies
            - Provide expert pricing advice and recommendations
            - Explain pricing concepts in accessible terms
            
            Workflow:
            1. Understand the user's pricing question or challenge
            2. Ask follow-up questions if needed for context
            3. Use sub-agents to gather market data or select algorithms when appropriate
            4. Synthesize information into actionable pricing recommendations
            5. Engage conversationally and be ready to answer follow-up questions
            
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
    
    def _build_supervisor_graph(self):
        """Build the pricing expert orchestrator graph"""
        graph = (
            StateGraph(MessagesState)
            .add_node("pricing_orchestrator", self.pricing_orchestrator)
            .add_node("web_researcher", self.web_researcher)
            .add_node("algorithm_selector", self.algorithm_selector)
            .add_edge(START, "pricing_orchestrator")  # Always start with the main orchestrator
            .compile()
        )
        return graph
    
    async def execute_supervisor_workflow(self, task: str, context: str = "") -> MultiAgentResponse:
        """Execute pricing consultation using the orchestrator"""
        start_time = datetime.now()
        
        try:
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
    
    async def stream_supervisor_workflow(self, task: str, context: str = "", previous_messages: List[Dict] = None) -> AsyncGenerator[str, None]:
        """Stream the pricing orchestrator workflow with real-time updates"""
        try:
            start_time = datetime.now()
            execution_path = []
            
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
            
            async for chunk in self.supervisor_graph.astream(initial_state):
                for node_name, node_output in chunk.items():
                    if node_name not in execution_path:
                        execution_path.append(node_name)
                        current_agent = node_name
                        
                        # Yield agent activation
                        agent_display_name = {
                            "pricing_orchestrator": "💼 Pricing Expert",
                            "web_researcher": "🔍 Market Researcher", 
                            "algorithm_selector": "⚙️ Algorithm Specialist"
                        }.get(node_name, f"🤖 {node_name}")
                        
                        yield json.dumps({
                            "type": "agent_start",
                            "agent": node_name,
                            "agent_name": agent_display_name,
                            "message": f"{agent_display_name} is thinking...",
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    result = node_output
                    
                    # Extract and stream any new messages
                    if "messages" in node_output and node_output["messages"]:
                        # Get the last message that's an AI message
                        for msg in node_output["messages"]:
                            if isinstance(msg, AIMessage) and msg.content:
                                # Only stream if this is a new message from the current agent
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
