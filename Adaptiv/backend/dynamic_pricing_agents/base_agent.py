"""
Base agent class with common functionality for all dynamic pricing agents
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import logging
from openai import OpenAI
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all dynamic pricing agents"""
    
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
                    temperature=0.7,
                    max_tokens=2000,
                    timeout=30  # 30 second timeout
                )
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000,
                    timeout=30  # 30 second timeout
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
