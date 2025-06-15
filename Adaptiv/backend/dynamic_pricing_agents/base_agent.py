"""
Base agent class with memory functionality for all dynamic pricing agents
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import logging
from openai import OpenAI
import os
from sqlalchemy.orm import Session
from sqlalchemy import desc

# Import memory models
from models import (
    AgentMemory, 
    PricingDecision, 
    PricingRecommendation,
    MarketAnalysisSnapshot,
    DataCollectionSnapshot,
    CompetitorPriceHistory,
    BundleRecommendation,
    PerformanceBaseline,
    PerformanceAnomaly,
    PricingExperiment,
    ExperimentLearning,
    StrategyEvolution
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all dynamic pricing agents with memory capabilities"""
    
    def __init__(self, agent_name: str, model: str = "gpt-4o-mini"):
        self.agent_name = agent_name
        self.model = model
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.conversation_history: List[Dict[str, str]] = []
        self.logger = logging.getLogger(f"{__name__}.{agent_name}")
        
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent"""
        pass
    
    @abstractmethod
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing method for the agent"""
        pass
    
    def call_llm(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Call the OpenAI API with the given messages and optional tools"""
        try:
            if tools:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                )
            
            # Extract the response
            message = response.choices[0].message
            
            return {
                "content": message.content,
                "tool_calls": message.tool_calls if hasattr(message, 'tool_calls') else None,
                "usage": response.usage.dict() if hasattr(response, 'usage') else None
            }
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error calling OpenAI API: {error_msg}")
            
            # Check for specific error types
            if "insufficient_quota" in error_msg or "exceeded your current quota" in error_msg:
                self.logger.error("OpenAI API quota exceeded. Please check your billing.")
                return {
                    "content": f"ERROR: OpenAI API quota exceeded. The {self.agent_name} cannot process this request. Please check your OpenAI billing settings.",
                    "tool_calls": None,
                    "usage": None,
                    "error": "quota_exceeded"
                }
            elif "rate_limit_exceeded" in error_msg:
                self.logger.error("OpenAI API rate limit exceeded.")
                return {
                    "content": f"ERROR: OpenAI API rate limit exceeded. The {self.agent_name} is temporarily unable to process requests. Please try again in a few moments.",
                    "tool_calls": None,
                    "usage": None,
                    "error": "rate_limit"
                }
            else:
                return {
                    "content": f"ERROR: Failed to call OpenAI API - {error_msg}",
                    "tool_calls": None,
                    "usage": None,
                    "error": "api_error"
                }
    
    def log_action(self, action: str, details: Dict[str, Any]):
        """Log an action taken by the agent"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_name,
            "action": action,
            "details": details
        }
        self.logger.info(json.dumps(log_entry))
        
    def save_state(self, state: Dict[str, Any], filepath: str):
        """Save agent state to a file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            self.logger.info(f"State saved to {filepath}")
        except Exception as e:
            self.logger.error(f"Error saving state: {str(e)}")
    
    def load_state(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Load agent state from a file"""
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
            self.logger.info(f"State loaded from {filepath}")
            return state
        except Exception as e:
            self.logger.error(f"Error loading state: {str(e)}")
            return None
    
    def get_memory_context(self, db: Session, user_id: int, memory_types: List[str] = None, 
                         days_back: int = 30, limit: int = 10) -> Dict[str, Any]:
        """Retrieve relevant memory context for the agent"""
        memory_context = {}
        
        # Default memory types if not specified
        if memory_types is None:
            memory_types = ['recommendation', 'insight', 'learning', 'outcome']
        
        # Retrieve agent-specific memories
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        for memory_type in memory_types:
            memories = db.query(AgentMemory).filter(
                AgentMemory.agent_name == self.agent_name,
                AgentMemory.user_id == user_id,
                AgentMemory.memory_type == memory_type,
                AgentMemory.created_at >= cutoff_date
            ).order_by(desc(AgentMemory.created_at)).limit(limit).all()
            
            memory_context[memory_type] = [
                {
                    'content': mem.content,
                    'metadata': mem.memory_metadata,  # Note: using memory_metadata instead of metadata (reserved name)
                    'created_at': mem.created_at.isoformat()
                }
                for mem in memories
            ]
        
        # Get recent pricing decisions
        recent_decisions = db.query(PricingDecision).filter(
            PricingDecision.user_id == user_id,
            PricingDecision.decision_date >= cutoff_date
        ).order_by(desc(PricingDecision.decision_date)).limit(5).all()
        
        memory_context['recent_decisions'] = [
            {
                'decision_type': dec.decision_type,
                'affected_items': dec.affected_items,
                'primary_rationale': dec.primary_rationale,
                'confidence_score': dec.confidence_score,
                'outcome_metrics': dec.outcome_metrics,
                'success_rating': dec.success_rating,
                'decision_date': dec.decision_date.isoformat()
            }
            for dec in recent_decisions
        ]
        
        return memory_context
    
    def save_memory(self, db: Session, user_id: int, memory_type: str, 
                   content: Any, metadata: Dict[str, Any] = None):
        """Save a memory to the database"""
        memory = AgentMemory(
            agent_name=self.agent_name,
            user_id=user_id,
            memory_type=memory_type,
            content=content if isinstance(content, dict) else {'data': content},
            memory_metadata=metadata or {}
        )
        db.add(memory)
        db.commit()
        self.logger.info(f"Saved {memory_type} memory for user {user_id}")
    
    def save_conversation(self, db: Session, user_id: int, messages: List[Dict[str, str]], 
                         response: str, context: Dict[str, Any] = None):
        """Save conversation history with the LLM"""
        conversation_data = {
            'messages': messages,
            'response': response,
            'model': self.model,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.save_memory(
            db, user_id, 'conversation', 
            conversation_data, 
            metadata={'context': context} if context else None
        )
    
    def get_relevant_memories(self, db: Session, user_id: int, query_context: Dict[str, Any], 
                            limit: int = 5) -> List[Dict[str, Any]]:
        """Get memories most relevant to the current query context"""
        # This is a simple implementation - could be enhanced with vector similarity search
        memories = []
        
        # Get memories based on context keywords
        if 'items' in query_context:
            item_ids = query_context['items']
            # Get all recent memories for this agent/user and filter in Python
            # This approach is more database-agnostic than using JSON operators
            recent_memories = db.query(AgentMemory).filter(
                AgentMemory.agent_name == self.agent_name,
                AgentMemory.user_id == user_id
            ).order_by(desc(AgentMemory.created_at)).limit(50).all()
            
            # Filter memories that mention the relevant items
            # Note: This is not as efficient as using database JSON operators, but is more portable
            relevant_memories = []
            for mem in recent_memories:
                content = mem.content
                if isinstance(content, dict) and 'affected_items' in content:
                    affected_items = content['affected_items']
                    if any(item_id in affected_items for item_id in item_ids):
                        relevant_memories.append(mem)
                if len(relevant_memories) >= limit:
                    break
            
            memories.extend([{
                'type': mem.memory_type,
                'content': mem.content,
                'created_at': mem.created_at.isoformat()
            } for mem in relevant_memories])
        
        return memories
    
    def track_decision(self, db: Session, user_id: int, decision_type: str, 
                      affected_items: List[int], rationale: str, 
                      supporting_data: Dict[str, Any], confidence: float,
                      related_recommendations: List[int] = None,
                      related_experiments: List[str] = None):
        """Track a pricing decision made by the agent"""
        decision = PricingDecision(
            user_id=user_id,
            decision_type=decision_type,
            affected_items=affected_items,
            primary_rationale=rationale,
            supporting_data=supporting_data,
            confidence_score=confidence,
            recommendation_ids=related_recommendations or [],
            experiment_ids=related_experiments or []
        )
        
        # Add current context
        decision.market_conditions = supporting_data.get('market_conditions', {})
        decision.performance_metrics = supporting_data.get('performance_metrics', {})
        decision.competitive_landscape = supporting_data.get('competitive_landscape', {})
        
        db.add(decision)
        db.commit()
        
        self.logger.info(f"Tracked {decision_type} decision for user {user_id}")
        return decision.id
    
    def call_llm_with_memory(self, messages: List[Dict[str, str]], db: Session, 
                           user_id: int, context: Dict[str, Any] = None, 
                           tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Call the OpenAI API with memory context"""
        # Get relevant memory context
        memory_context = self.get_memory_context(db, user_id)
        
        # Enhance system prompt with memory context
        memory_summary = self._summarize_memory_context(memory_context)
        
        # Add memory context to the first user message or create a new one
        enhanced_messages = messages.copy()
        if memory_summary:
            memory_message = {
                "role": "user",
                "content": f"""
                Based on our previous interactions and learnings:
                {memory_summary}
                
                Now, addressing the current request:
                {messages[-1]['content'] if messages and messages[-1]['role'] == 'user' else ''}
                """
            }
            # Replace the last user message with the enhanced one
            if messages and messages[-1]['role'] == 'user':
                enhanced_messages[-1] = memory_message
            else:
                enhanced_messages.append(memory_message)
        
        # Call the LLM
        response = self.call_llm(enhanced_messages, tools)
        
        # Save the conversation
        if response.get('content') and not response.get('error'):
            self.save_conversation(db, user_id, messages, response['content'], context)
        
        return response
    
    def _summarize_memory_context(self, memory_context: Dict[str, Any]) -> str:
        """Summarize memory context for inclusion in prompts"""
        summary_parts = []
        
        # Summarize recent recommendations
        if memory_context.get('recommendation'):
            recent_recs = memory_context['recommendation'][:3]
            if recent_recs:
                summary_parts.append("Recent recommendations:")
                for rec in recent_recs:
                    content = rec['content']
                    summary_parts.append(f"- {content.get('summary', 'Recommendation made on')} ({rec['created_at'][:10]})")
        
        # Summarize recent insights
        if memory_context.get('insight'):
            recent_insights = memory_context['insight'][:3]
            if recent_insights:
                summary_parts.append("\nKey insights:")
                for insight in recent_insights:
                    content = insight['content']
                    summary_parts.append(f"- {content.get('insight', 'Insight gained on')} ({insight['created_at'][:10]})")
        
        # Summarize recent decisions and outcomes
        if memory_context.get('recent_decisions'):
            summary_parts.append("\nRecent pricing decisions and outcomes:")
            for decision in memory_context['recent_decisions'][:3]:
                success_rating = decision.get('success_rating')
                # Safely handle the case when success_rating is None
                outcome = "Successful" if success_rating is not None and success_rating >= 4 else "Mixed results"
                summary_parts.append(
                    f"- {decision['decision_type']} on {len(decision.get('affected_items', []))} items: {outcome}"
                )
        
        return "\n".join(summary_parts) if summary_parts else ""
    
    def learn_from_outcome(self, db: Session, user_id: int, decision_id: int, 
                          outcome_metrics: Dict[str, Any], success_rating: int, 
                          lessons: str):
        """Update a decision with its outcomes and learnings"""
        decision = db.query(PricingDecision).filter(
            PricingDecision.id == decision_id,
            PricingDecision.user_id == user_id
        ).first()
        
        if decision:
            decision.outcome_metrics = outcome_metrics
            decision.success_rating = success_rating
            decision.lessons_learned = lessons
            decision.updated_at = datetime.utcnow()
            db.commit()
            
            # Save the learning as a memory
            self.save_memory(
                db, user_id, 'learning',
                {
                    'decision_id': decision_id,
                    'decision_type': decision.decision_type,
                    'success_rating': success_rating,
                    'lessons': lessons,
                    'metrics': outcome_metrics
                },
                metadata={'decision_date': decision.decision_date.isoformat()}
            )
