from agents import Runner, trace, gen_trace_id
import asyncio
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import os
import models as db_models
import json
import logging
from .db_helper import DBHelper
from agent_progress import AgentProgress

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from .competitor_agent import competitor_agent, save_competitor_report
from .customer_agent import customer_agent, save_customer_report
from .market_agent import market_agent, save_market_report
from .pricing_agent import pricing_agent, save_pricing_report
from .experiment_agent import experiment_agent, save_experiment_plan

class AgentManager:
    """
    Manager class that orchestrates the execution of all agents in the proper sequence.
    Implements the agent workflow as described:
    1. Competitor, Customer, and Market agents run independently
    2. Pricing agent uses their reports to generate recommendations
    3. Experiment agent uses pricing recommendations to create an experiment plan
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.db_helper = DBHelper(db)
    
    async def run_full_process(self, user_id: int) -> Dict[str, Any]:
        """
        Run the full agent process.
        """
        # Generate a trace ID for the entire process
        trace_id = gen_trace_id()
        
        # Create a process ID for tracking progress
        process_id = AgentProgress.start_process(user_id)
        
        logger.info(f"Starting full agent process for user_id: {user_id}, process_id: {process_id}")
        
        # Import local agent implementations directly to avoid schema validation issues
        from local_agents.competitor_agent import generate_competitor_report
        from local_agents.customer_agent import generate_customer_report
        from local_agents.market_agent import generate_market_report
        from local_agents.pricing_agent import generate_pricing_report
        from local_agents.experiment_agent import generate_experiment_recommendation
        
        try:
            with trace("Dynamic Pricing Agent Process", trace_id=trace_id):
                # Update progress: Starting initial phase
                AgentProgress.update_process(
                    process_id,
                    status="running",
                    current_step="initial_analysis",
                    progress_percent=10,
                    message="Starting initial analysis with competitor, customer, and market agents"
                )
                
                logger.info("Step 1: Starting parallel execution of competitor, customer, and market agents")
                # Update individual agent statuses
                AgentProgress.update_process(
                    process_id,
                    steps={
                        "competitor_agent": {"status": "running"},
                        "customer_agent": {"status": "running"},
                        "market_agent": {"status": "running"}
                    }
                )
                
                # Step 1: Run the independent agents in parallel using local implementations
                competitor_result, customer_result, market_result = await asyncio.gather(
                    generate_competitor_report(self.db, user_id),
                    generate_customer_report(self.db, user_id),
                    generate_market_report(self.db, user_id)
                )
                
                # Update progress after agents complete
                AgentProgress.update_process(
                    process_id,
                    steps={
                        "competitor_agent": {"status": "completed", "report_id": competitor_result.id},
                        "customer_agent": {"status": "completed", "report_id": customer_result.id},
                        "market_agent": {"status": "completed", "report_id": market_result.id}
                    },
                    progress_percent=40,
                    message="Initial analysis complete, generating pricing recommendations"
                )
                
                logger.info(f"Step 1 complete: Generated competitor report #{competitor_result.id}, customer report #{customer_result.id}, and market report #{market_result.id}")
                
                logger.info("Step 2: Starting pricing agent")
                # Update pricing agent status
                AgentProgress.update_process(
                    process_id,
                    current_step="pricing_analysis",
                    steps={"pricing_agent": {"status": "running"}}
                )
                
                # Step 2: Run the pricing agent using the reports from the independent agents
                pricing_result = await generate_pricing_report(
                    self.db, 
                    user_id, 
                    competitor_report_id=competitor_result.id,
                    customer_report_id=customer_result.id,
                    market_report_id=market_result.id
                )
                
                # Update progress after pricing agent completes
                AgentProgress.update_process(
                    process_id,
                    steps={"pricing_agent": {"status": "completed", "report_id": pricing_result.id}},
                    progress_percent=70,
                    message="Pricing recommendations generated, creating experiment plan"
                )
                
                logger.info(f"Step 2 complete: Generated pricing report #{pricing_result.id}")
                
                logger.info("Step 3: Starting experiment agent")
                # Update experiment agent status
                AgentProgress.update_process(
                    process_id,
                    current_step="experiment_planning",
                    steps={"experiment_agent": {"status": "running"}}
                )
                
                # Step 3: Run the experiment agent using the pricing report
                experiment_result = await generate_experiment_recommendation(
                    self.db, 
                    user_id, 
                    pricing_report_id=pricing_result.id
                )
                
                # Update progress after experiment agent completes
                AgentProgress.update_process(
                    process_id,
                    status="completed",
                    steps={"experiment_agent": {"status": "completed", "report_id": experiment_result.id}},
                    progress_percent=100,
                    message="Full analysis complete with experiment plan"
                )
                
                logger.info(f"Step 3 complete: Generated experiment plan #{experiment_result.id}")
                logger.info(f"Full agent process completed successfully for user_id: {user_id}")
                
                return {
                    "trace_id": trace_id,
                    "process_id": process_id,
                    "competitor_report_id": competitor_result.id,
                    "customer_report_id": customer_result.id,
                    "market_report_id": market_result.id,
                    "pricing_report_id": pricing_result.id,
                    "experiment_recommendation_id": experiment_result.id
                }
        except Exception as e:
            logger.error(f"Error in full agent process for user_id {user_id}: {str(e)}")
            # Update progress to indicate error
            AgentProgress.update_process(
                process_id,
                status="error",
                message=f"Error during agent process: {str(e)}",
                error=str(e)
            )
            raise
    
    async def run_competitor_agent(self, user_id: int) -> db_models.CompetitorReport:
        """
        Run the competitor agent and save its report.
        """
        with trace("Competitor Agent"):
            # Create a context object that can be passed to the agent
            context = {"user_id": user_id, "db_helper": self.db_helper}
            
            # Run the competitor agent
            result = await Runner.run(competitor_agent, "", context=context)
            
            # Save the report to the database
            report_data = result.final_output.model_dump()
            competitor_report = self.db_helper.save_competitor_report(user_id, report_data)
            
            return competitor_report
    
    async def run_customer_agent(self, user_id: int) -> db_models.CustomerReport:
        """
        Run the customer agent and save its report.
        """
        with trace("Customer Agent"):
            # Create a context object that can be passed to the agent
            context = {"user_id": user_id, "db_helper": self.db_helper}
            
            # Run the customer agent
            result = await Runner.run(customer_agent, "", context=context)
            
            # Save the report to the database
            report_data = result.final_output.model_dump()
            customer_report = self.db_helper.save_customer_report(user_id, report_data)
            
            return customer_report
    
    async def run_market_agent(self, user_id: int) -> db_models.MarketReport:
        """
        Run the market agent and save its report.
        """
        with trace("Market Agent"):
            # Create a context object that can be passed to the agent
            context = {"user_id": user_id, "db_helper": self.db_helper}
            
            # Run the market agent
            result = await Runner.run(market_agent, "", context=context)
            
            # Save the report to the database
            report_data = result.final_output.model_dump()
            market_report = self.db_helper.save_market_report(user_id, report_data)
            
            return market_report
    
    async def run_pricing_agent(
        self, 
        user_id: int, 
        competitor_report_id: Optional[int] = None,
        customer_report_id: Optional[int] = None,
        market_report_id: Optional[int] = None
    ) -> db_models.PricingReport:
        """
        Run the pricing agent and save its report.
        """
        with trace("Pricing Agent"):
            # Create a context object that can be passed to the agent
            context = {"user_id": user_id, "db_helper": self.db_helper}
            
            # Run the pricing agent
            result = await Runner.run(pricing_agent, "", context=context)
            
            # Save the report to the database
            report_data = result.final_output.model_dump()
            report_data.update({
                "competitor_report_id": competitor_report_id,
                "customer_report_id": customer_report_id,
                "market_report_id": market_report_id
            })
            pricing_report = self.db_helper.save_pricing_report(user_id, report_data)
            
            return pricing_report
    
    async def run_experiment_agent(
        self, 
        user_id: int, 
        pricing_report_id: Optional[int] = None
    ) -> db_models.ExperimentRecommendation:
        """
        Run the experiment agent and save its recommendation.
        """
        with trace("Experiment Agent"):
            # Create a context object that can be passed to the agent
            context = {"user_id": user_id, "db_helper": self.db_helper, "pricing_report_id": pricing_report_id}
            
            # Run the experiment agent
            result = await Runner.run(experiment_agent, "", context=context)
            
            # Save the experiment plan to the database
            plan_data = result.final_output.model_dump()
            plan_data.update({
                "pricing_report_id": pricing_report_id
            })
            experiment_recommendation = self.db_helper.save_experiment_plan(user_id, plan_data)
            
            return experiment_recommendation
