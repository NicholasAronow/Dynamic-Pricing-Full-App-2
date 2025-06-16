"""
Dynamic Pricing Agents Module
"""

from .data_collection import DataCollectionAgent
from .pricing_strategy import PricingStrategyAgent
from .performance_monitor import PerformanceMonitorAgent
from .experimentation import ExperimentationAgent
from .competitor_agent import CompetitorAgentWrapper
from .test_web_agent import TestWebAgentWrapper
from .test_db_agent import TestDBAgentWrapper

__all__ = [
    'DataCollectionAgent',
    'PricingStrategyAgent',
    'PerformanceMonitorAgent',
    'ExperimentationAgent',
    'CompetitorAgentWrapper',
    'TestWebAgentWrapper',
    'get_test_web_agent',
    'TestDBAgentWrapper',
    'get_test_db_agent'
]

def get_competitor_agent():
    """
    Get an instance of the competitor analysis agent
    """
    return CompetitorAgentWrapper()

def get_test_web_agent():
    """
    Get an instance of the test web search agent
    """
    return TestWebAgentWrapper()

def get_test_db_agent():
    """
    Get an instance of the test database competitor tracking agent
    """
    return TestDBAgentWrapper()
