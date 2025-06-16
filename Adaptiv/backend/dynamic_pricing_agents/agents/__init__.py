"""
Dynamic Pricing Agents Module
"""

from .data_collection import DataCollectionAgent
from .market_analysis import MarketAnalysisAgent
from .pricing_strategy import PricingStrategyAgent
from .performance_monitor import PerformanceMonitorAgent
from .experimentation import ExperimentationAgent
from .openai_agent import openai_agent, get_openai_agent
from .competitor_agent import CompetitorAgentWrapper
from .test_web_agent import TestWebAgentWrapper

__all__ = [
    'DataCollectionAgent',
    'MarketAnalysisAgent',
    'PricingStrategyAgent',
    'PerformanceMonitorAgent',
    'ExperimentationAgent',
    'openai_agent',
    'get_openai_agent',
    'CompetitorAgentWrapper',
    'get_competitor_agent',
    'TestWebAgentWrapper',
    'get_test_web_agent'
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
