"""
LangGraph Multi-Agent System Service

This service demonstrates different multi-agent architectures:
1. Supervisor Architecture - A supervisor coordinates specialized agents
2. Network Architecture - Agents can communicate with each other directly
3. Tool-calling Architecture - Agents as tools for a supervisor
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Literal, Annotated
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent, InjectedState
from langgraph_supervisor import create_supervisor

logger = logging.getLogger(__name__)

@dataclass
class AgentResult:
    """Result from a single agent execution"""
    agent_name: str
    result: str
    confidence: float
    execution_time: float
    metadata: Dict[str, Any]

@dataclass
class MultiAgentResponse:
    """Response from multi-agent system execution"""
    final_result: str
    agent_results: List[AgentResult]
    execution_path: List[str]
    total_execution_time: float
    metadata: Dict[str, Any] = {}

# Individual Agent Implementations
class ResearchAgent:
    """Agent specialized in research and information gathering"""
    
    def __init__(self):
        self.name = "research_agent"
        self.model = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=get_openai_api_key(),
            temperature=0.1
        )
    
    def execute(self, state: MultiAgentState) -> Dict[str, Any]:
        """Execute research task"""
        start_time = datetime.now()
        
        messages = state.get("messages", [])
        current_task = state.get("current_task", "")
        
        system_prompt = """You are a research specialist. Your job is to:
        1. Analyze the given task or question
        2. Identify key information needed
        3. Provide structured research findings
        4. Suggest next steps for analysis
        
        Be thorough but concise. Focus on actionable insights."""
        
        research_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Research task: {current_task}\n\nContext: {messages[-1].content if messages else 'No prior context'}")
        ]
        
        try:
            response = self.model.invoke(research_messages)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "agent_name": self.name,
                "result": response.content,
                "confidence": 0.85,
                "execution_time": execution_time,
                "metadata": {"task_type": "research", "model_used": "gpt-4o-mini"}
            }
        except Exception as e:
            logger.error(f"Research agent error: {e}")
            return {
                "agent_name": self.name,
                "result": f"Research failed: {str(e)}",
                "confidence": 0.0,
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "metadata": {"error": str(e)}
            }

class AnalysisAgent:
    """Agent specialized in data analysis and insights"""
    
    def __init__(self):
        self.name = "analysis_agent"
        self.model = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=get_openai_api_key(),
            temperature=0.2
        )
    
    def execute(self, state: MultiAgentState) -> Dict[str, Any]:
        """Execute analysis task"""
        start_time = datetime.now()
        
        messages = state.get("messages", [])
        research_results = state.get("agent_results", {}).get("research_agent", {})
        
        system_prompt = """You are an analysis specialist. Your job is to:
        1. Take research findings and analyze them deeply
        2. Identify patterns, trends, and insights
        3. Provide quantitative analysis where possible
        4. Make data-driven recommendations
        
        Be analytical and precise. Support conclusions with reasoning."""
        
        context = f"Research findings: {research_results.get('result', 'No research available')}"
        analysis_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Analyze this information: {context}")
        ]
        
        try:
            response = self.model.invoke(analysis_messages)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "agent_name": self.name,
                "result": response.content,
                "confidence": 0.80,
                "execution_time": execution_time,
                "metadata": {"task_type": "analysis", "model_used": "gpt-4o-mini"}
            }
        except Exception as e:
            logger.error(f"Analysis agent error: {e}")
            return {
                "agent_name": self.name,
                "result": f"Analysis failed: {str(e)}",
                "confidence": 0.0,
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "metadata": {"error": str(e)}
            }

class RecommendationAgent:
    """Agent specialized in generating actionable recommendations"""
    
    def __init__(self):
        self.name = "recommendation_agent"
        self.model = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=get_openai_api_key(),
            temperature=0.3
        )
    
    def execute(self, state: MultiAgentState) -> Dict[str, Any]:
        """Execute recommendation task"""
        start_time = datetime.now()
        
        agent_results = state.get("agent_results", {})
        research_results = agent_results.get("research_agent", {})
        analysis_results = agent_results.get("analysis_agent", {})
        
        system_prompt = """You are a recommendation specialist. Your job is to:
        1. Synthesize research and analysis findings
        2. Generate specific, actionable recommendations
        3. Prioritize recommendations by impact and feasibility
        4. Provide implementation guidance
        
        Be practical and actionable. Focus on clear next steps."""
        
        context = f"""
        Research: {research_results.get('result', 'No research available')}
        Analysis: {analysis_results.get('result', 'No analysis available')}
        """
        
        recommendation_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Based on this information, provide recommendations: {context}")
        ]
        
        try:
            response = self.model.invoke(recommendation_messages)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "agent_name": self.name,
                "result": response.content,
                "confidence": 0.90,
                "execution_time": execution_time,
                "metadata": {"task_type": "recommendations", "model_used": "gpt-4o-mini"}
            }
        except Exception as e:
            logger.error(f"Recommendation agent error: {e}")
            return {
                "agent_name": self.name,
                "result": f"Recommendation failed: {str(e)}",
                "confidence": 0.0,
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "metadata": {"error": str(e)}
            }

# Multi-Agent Orchestrators
class SupervisorOrchestrator:
    """Supervisor architecture - supervisor coordinates specialized agents"""
    
    def __init__(self):
        self.research_agent = ResearchAgent()
        self.analysis_agent = AnalysisAgent()
        self.recommendation_agent = RecommendationAgent()
        self.supervisor_model = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=get_openai_api_key(),
            temperature=0.1
        )
    
    def supervisor_node(self, state: MultiAgentState) -> Command[Literal["research_agent", "analysis_agent", "recommendation_agent", END]]:
        """Supervisor decides which agent to call next"""
        messages = state.get("messages", [])
        agent_results = state.get("agent_results", {})
        execution_history = state.get("execution_history", [])
        
        # Determine next agent based on current state
        if not agent_results.get("research_agent"):
            return Command(goto="research_agent")
        elif not agent_results.get("analysis_agent"):
            return Command(goto="analysis_agent")
        elif not agent_results.get("recommendation_agent"):
            return Command(goto="recommendation_agent")
        else:
            return Command(goto=END)
    
    def research_node(self, state: MultiAgentState) -> Command[Literal["supervisor"]]:
        """Research agent node"""
        result = self.research_agent.execute(state)
        
        return Command(
            goto="supervisor",
            update={
                "agent_results": {**state.get("agent_results", {}), "research_agent": result},
                "execution_history": state.get("execution_history", []) + [{"agent": "research_agent", "timestamp": datetime.now().isoformat()}],
                "messages": state.get("messages", []) + [AIMessage(content=f"Research completed: {result['result'][:200]}...")]
            }
        )
    
    def analysis_node(self, state: MultiAgentState) -> Command[Literal["supervisor"]]:
        """Analysis agent node"""
        result = self.analysis_agent.execute(state)
        
        return Command(
            goto="supervisor",
            update={
                "agent_results": {**state.get("agent_results", {}), "analysis_agent": result},
                "execution_history": state.get("execution_history", []) + [{"agent": "analysis_agent", "timestamp": datetime.now().isoformat()}],
                "messages": state.get("messages", []) + [AIMessage(content=f"Analysis completed: {result['result'][:200]}...")]
            }
        )
    
    def recommendation_node(self, state: MultiAgentState) -> Command[Literal["supervisor"]]:
        """Recommendation agent node"""
        result = self.recommendation_agent.execute(state)
        
        return Command(
            goto="supervisor",
            update={
                "agent_results": {**state.get("agent_results", {}), "recommendation_agent": result},
                "execution_history": state.get("execution_history", []) + [{"agent": "recommendation_agent", "timestamp": datetime.now().isoformat()}],
                "messages": state.get("messages", []) + [AIMessage(content=f"Recommendations completed: {result['result'][:200]}...")]
            }
        )
    
    def build_graph(self) -> StateGraph:
        """Build the supervisor graph"""
        builder = StateGraph(MultiAgentState)
        
        # Add nodes
        builder.add_node("supervisor", self.supervisor_node)
        builder.add_node("research_agent", self.research_node)
        builder.add_node("analysis_agent", self.analysis_node)
        builder.add_node("recommendation_agent", self.recommendation_node)
        
        # Add edges
        builder.add_edge(START, "supervisor")
        
        return builder.compile()

class ToolCallingOrchestrator:
    """Tool-calling architecture - agents as tools for supervisor"""
    
    def __init__(self):
        self.model = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=get_openai_api_key(),
            temperature=0.1
        )
    
    @tool
    def research_tool(self, query: str, state: Annotated[dict, InjectedState]) -> str:
        """Research information on a given topic"""
        agent = ResearchAgent()
        # Create a temporary state for the agent
        temp_state = MultiAgentState(
            messages=[HumanMessage(content=query)],
            current_task=query
        )
        result = agent.execute(temp_state)
        return result["result"]
    
    @tool
    def analysis_tool(self, data: str, state: Annotated[dict, InjectedState]) -> str:
        """Analyze given data and provide insights"""
        agent = AnalysisAgent()
        temp_state = MultiAgentState(
            messages=[HumanMessage(content=data)],
            agent_results={"research_agent": {"result": data}}
        )
        result = agent.execute(temp_state)
        return result["result"]
    
    @tool
    def recommendation_tool(self, context: str, state: Annotated[dict, InjectedState]) -> str:
        """Generate recommendations based on context"""
        agent = RecommendationAgent()
        temp_state = MultiAgentState(
            messages=[HumanMessage(content=context)],
            agent_results={
                "research_agent": {"result": context},
                "analysis_agent": {"result": context}
            }
        )
        result = agent.execute(temp_state)
        return result["result"]
    
    def build_graph(self) -> StateGraph:
        """Build the tool-calling supervisor graph"""
        tools = [self.research_tool, self.analysis_tool, self.recommendation_tool]
        return create_react_agent(self.model, tools)

# Main Service Class
class LangGraphService:
    """Main service for LangGraph multi-agent operations"""
    
    def __init__(self):
        self.supervisor_orchestrator = SupervisorOrchestrator()
        self.tool_calling_orchestrator = ToolCallingOrchestrator()
    
    async def execute_supervisor_workflow(self, task: str, context: str = "") -> MultiAgentResponse:
        """Execute task using supervisor architecture"""
        start_time = datetime.now()
        
        try:
            # Build and execute graph
            graph = self.supervisor_orchestrator.build_graph()
            
            initial_state = MultiAgentState(
                messages=[HumanMessage(content=f"Task: {task}\nContext: {context}")],
                current_task=task,
                agent_results={},
                execution_history=[],
                metadata={"architecture": "supervisor", "start_time": start_time.isoformat()}
            )
            
            # Execute the graph
            final_state = graph.invoke(initial_state)
            
            # Extract results
            agent_results = []
            execution_path = []
            
            for agent_name, result_data in final_state.get("agent_results", {}).items():
                agent_results.append(AgentResult(**result_data))
                execution_path.append(agent_name)
            
            # Generate final result
            final_result = self._synthesize_results(agent_results)
            
            total_time = (datetime.now() - start_time).total_seconds()
            
            return MultiAgentResponse(
                final_result=final_result,
                agent_results=agent_results,
                execution_path=execution_path,
                total_execution_time=total_time,
                metadata={
                    "architecture": "supervisor",
                    "execution_history": final_state.get("execution_history", [])
                }
            )
            
        except Exception as e:
            logger.error(f"Supervisor workflow error: {e}")
            return MultiAgentResponse(
                final_result=f"Execution failed: {str(e)}",
                agent_results=[],
                execution_path=[],
                total_execution_time=(datetime.now() - start_time).total_seconds(),
                metadata={"error": str(e)}
            )
    
    async def execute_tool_calling_workflow(self, task: str, context: str = "") -> MultiAgentResponse:
        """Execute task using tool-calling architecture"""
        start_time = datetime.now()
        
        try:
            # Build and execute graph
            graph = self.tool_calling_orchestrator.build_graph()
            
            initial_state = {
                "messages": [HumanMessage(content=f"Task: {task}\nContext: {context}")]
            }
            
            # Execute the graph
            final_state = graph.invoke(initial_state)
            
            # Extract results from messages
            messages = final_state.get("messages", [])
            final_result = messages[-1].content if messages else "No result generated"
            
            total_time = (datetime.now() - start_time).total_seconds()
            
            return MultiAgentResponse(
                final_result=final_result,
                agent_results=[],  # Tool-calling doesn't expose individual agent results
                execution_path=["tool_calling_supervisor"],
                total_execution_time=total_time,
                metadata={
                    "architecture": "tool_calling",
                    "message_count": len(messages)
                }
            )
            
        except Exception as e:
            logger.error(f"Tool-calling workflow error: {e}")
            raise
    
    def _synthesize_results(self, agent_results: List[AgentResult]) -> str:
        """Synthesize results from multiple agents into final result"""
        if not agent_results:
            return "No results to synthesize"
        
        synthesis = "## Multi-Agent Analysis Results\n\n"
        
        for result in agent_results:
            synthesis += f"### {result.agent_name.replace('_', ' ').title()}\n"
            synthesis += f"**Confidence:** {result.confidence:.2f}\n"
            synthesis += f"**Execution Time:** {result.execution_time:.2f}s\n\n"
            synthesis += f"{result.result}\n\n"
            synthesis += "---\n\n"
        
        return synthesis
    
    async def get_available_architectures(self) -> List[Dict[str, Any]]:
        """Get list of available multi-agent architectures"""
        return [
            {
                "name": "supervisor",
                "title": "Supervisor Architecture",
                "description": "A supervisor agent coordinates specialized sub-agents in sequence",
                "agents": ["research_agent", "analysis_agent", "recommendation_agent"],
                "best_for": "Complex tasks requiring sequential processing"
            },
            {
                "name": "tool_calling",
                "title": "Tool-Calling Architecture", 
                "description": "Agents are exposed as tools to a supervisor that decides which to call",
                "agents": ["research_tool", "analysis_tool", "recommendation_tool"],
                "best_for": "Dynamic task routing based on LLM decisions"
            }
        ]
