"""
Provides tracking of agent process status.
"""
import time
from typing import Dict, Any, Optional
from datetime import datetime

# Global store for agent progress
agent_progress = {}

class AgentProgress:
    """Tracks the progress of agent processes."""
    
    @staticmethod
    def start_process(user_id: int) -> str:
        """
        Start tracking a new agent process.
        
        Args:
            user_id: The ID of the user who started the process
            
        Returns:
            A process ID that can be used to track this process
        """
        process_id = f"{user_id}-{int(time.time())}"
        
        agent_progress[process_id] = {
            "user_id": user_id,
            "process_id": process_id,
            "status": "started",
            "started_at": datetime.now(),
            "steps": {
                "competitor_agent": {"status": "pending"},
                "customer_agent": {"status": "pending"},
                "market_agent": {"status": "pending"},
                "pricing_agent": {"status": "pending"},
                "experiment_agent": {"status": "pending"}
            },
            "current_step": "initial",
            "progress_percent": 0,
            "message": "Process started",
            "error": None
        }
        
        return process_id
    
    @staticmethod
    def update_process(process_id: str, **kwargs) -> None:
        """
        Update the status of an agent process.
        
        Args:
            process_id: The ID of the process to update
            **kwargs: Key-value pairs to update in the process
        """
        if process_id not in agent_progress:
            return
            
        for key, value in kwargs.items():
            if key == "steps" and isinstance(value, dict):
                # Update specific step entries rather than replacing the entire steps dict
                for step_name, step_data in value.items():
                    if step_name in agent_progress[process_id]["steps"]:
                        agent_progress[process_id]["steps"][step_name].update(step_data)
            else:
                agent_progress[process_id][key] = value
    
    @staticmethod
    def get_process(process_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of an agent process.
        
        Args:
            process_id: The ID of the process to get
            
        Returns:
            The process status, or None if the process doesn't exist
        """
        return agent_progress.get(process_id)
    
    @staticmethod
    def get_latest_user_process(user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the latest process for a specific user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            The latest process status, or None if no process exists
        """
        user_processes = [p for p in agent_progress.values() if p["user_id"] == user_id]
        if not user_processes:
            return None
            
        # Sort by started_at and return the most recent
        return sorted(user_processes, key=lambda p: p["started_at"], reverse=True)[0]
