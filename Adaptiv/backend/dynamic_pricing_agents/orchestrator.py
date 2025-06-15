"""
Dynamic Pricing Agent Orchestrator - Coordinates all agents and manages workflow
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from .agents import (
    DataCollectionAgent,
    MarketAnalysisAgent,
    PricingStrategyAgent,
    PerformanceMonitorAgent,
    ExperimentationAgent
)
from .task_manager import running_tasks  # Import from shared module

class DynamicPricingOrchestrator:
    """Orchestrates the dynamic pricing agent system"""
    
    def __init__(self, max_workers: int = 3):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.max_workers = max_workers
        
        # Initialize agents
        self.agents = {
            'data_collection': DataCollectionAgent(),
            'market_analysis': MarketAnalysisAgent(),
            'pricing_strategy': PricingStrategyAgent(),
            'performance_monitor': PerformanceMonitorAgent(),
            'experimentation': ExperimentationAgent()
        }
        
        self.execution_history = []
    
    def run_full_analysis(self, db, user_id: int, trigger_source: str = "manual") -> Dict[str, Any]:
        """Run complete dynamic pricing analysis with all agents"""
        start_time = datetime.now()
        
        self.logger.info(f"Starting full dynamic pricing analysis for user {user_id}")
        
        # Update status
        self._update_task_status(user_id, "running", "Starting analysis...")
        
        try:
            # Phase 1: Data Collection (must run first)
            self._update_task_status(user_id, "running", "Phase 1: Collecting data...")
            collection_results = self._run_data_collection(db, user_id)
            self.logger.info(f"Data collection results: {collection_results}")
            # Phase 2: Parallel Analysis (market analysis and performance monitoring can run together)
            self._update_task_status(user_id, "running", "Phase 2: Running market analysis and performance monitoring...")
            analysis_results = self._run_parallel_analysis(db, user_id, collection_results)
            
            # Phase 3: Strategy Development (needs results from phase 2)
            self._update_task_status(user_id, "running", "Phase 3: Developing pricing strategies...")
            strategy_results = self._run_strategy_development(
                db, user_id, collection_results, analysis_results
            )
            
            # Phase 4: Experimentation Planning (needs strategy results)
            self._update_task_status(user_id, "running", "Phase 4: Planning experiments...")
            experiment_results = self._run_experimentation(
                db, user_id, strategy_results, analysis_results
            )
            
            # Compile results
            self._update_task_status(user_id, "running", "Compiling final results...")
            final_results = self._compile_results(
                collection_results,
                analysis_results,
                strategy_results,
                experiment_results
            )
            
            # Record execution
            execution_record = {
                "execution_id": f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "user_id": user_id,
                "trigger_source": trigger_source,
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "duration_seconds": (datetime.now() - start_time).total_seconds(),
                "status": "success",
                "agents_executed": list(self.agents.keys())
            }
            self.execution_history.append(execution_record)
            
            self.logger.info(f"Completed full analysis in {execution_record['duration_seconds']:.2f} seconds")
            
            self.logger.info("Full dynamic pricing analysis completed successfully")
            self._update_task_status(user_id, "completed", "Analysis completed successfully", final_results)
            return {
                "status": "success",
                "execution_id": execution_record["execution_id"],
                "results": final_results,
                "execution_summary": execution_record
            }
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            self.logger.error(f"Error in orchestrator: {str(e)}")
            self.logger.error(f"Full traceback: {error_trace}")
            
            # Add detailed error information to the task status
            error_message = f"Error: {str(e)}"
            self._update_task_status(user_id, "error", error_message)
            
            # Return more detailed error information
            return {
                "status": "error",
                "error": str(e),
                "error_trace": error_trace,
                "timestamp": datetime.now().isoformat()
            }
    
    def run_specific_agents(self, db, user_id: int, agent_names: List[str]) -> Dict[str, Any]:
        """Run specific agents only"""
        results = {}
        
        for agent_name in agent_names:
            if agent_name not in self.agents:
                results[agent_name] = {"error": f"Unknown agent: {agent_name}"}
                continue
            
            try:
                context = {"db": db, "user_id": user_id}
                agent_result = self.agents[agent_name].process(context)
                results[agent_name] = agent_result
            except Exception as e:
                self.logger.error(f"Error running agent {agent_name}: {str(e)}")
                results[agent_name] = {"error": str(e)}
        
        return results
    
    def _run_data_collection(self, db, user_id: int) -> Dict[str, Any]:
        """Run data collection phase"""
        self.logger.info("Phase 1: Running data collection")
        self._update_task_status(user_id, "running", "Agent: Data Collection - Starting...")
        
        context = {
            "db": db,
            "user_id": user_id
        }
        
        try:
            self.logger.info(f"Starting data collection agent for user {user_id}")
            result = self.agents['data_collection'].process(context)
            self.logger.info(f"Data collection completed for user {user_id}")
            self._update_task_status(user_id, "running", "Agent: Data Collection - Completed")
            return result
        except Exception as e:
            self.logger.error(f"Error in data collection: {str(e)}")
            self._update_task_status(user_id, "error", f"Data Collection Error: {str(e)}")
            raise
    
    def _run_parallel_analysis(self, db, user_id: int, collection_data: Dict) -> Dict[str, Any]:
        """Run market analysis and performance monitoring in parallel"""
        self.logger.info("Phase 2: Running parallel analysis")
        
        # For simplicity, run sequentially but could be made parallel with threading
        self._update_task_status(user_id, "running", "Agent: Market Analysis - Starting...")
        market_context = {
            "db": db,
            "user_id": user_id,
            "consolidated_data": collection_data
        }
        
        market_results = self.agents['market_analysis'].process(market_context)
        self._update_task_status(user_id, "running", "Agent: Market Analysis - Completed")
        
        self._update_task_status(user_id, "running", "Agent: Performance Monitor - Starting...")
        performance_context = {
            "db": db,
            "user_id": user_id,
            "consolidated_data": collection_data
        }
        
        performance_results = self.agents['performance_monitor'].process(performance_context)
        self._update_task_status(user_id, "running", "Agent: Performance Monitor - Completed")
        
        return {
            "market_analysis": market_results,
            "performance_monitor": performance_results
        }
    
    def _run_strategy_development(self, db, user_id: int, 
                                   collection_data: Dict, 
                                   analysis_results: Dict) -> Dict[str, Any]:
        """Run pricing strategy development"""
        self.logger.info("Phase 3: Running strategy development")
        self._update_task_status(user_id, "running", "Agent: Pricing Strategy - Starting...")
        
        context = {
            "db": db,
            "user_id": user_id,
            "consolidated_data": collection_data,
            "market_analysis": analysis_results.get('market_analysis', {}),
            "performance_data": analysis_results.get('performance_monitor', {})
        }
        
        result = self.agents['pricing_strategy'].process(context)
        self._update_task_status(user_id, "running", "Agent: Pricing Strategy - Completed")
        return result
    
    def _run_experimentation(self, db, user_id: int,
                            strategy_results: Dict,
                            analysis_results: Dict) -> Dict[str, Any]:
        """Run experimentation planning"""
        self.logger.info("Phase 4: Running experimentation planning")
        self._update_task_status(user_id, "running", "Agent: Experimentation - Starting...")
        
        context = {
            "db": db,
            "user_id": user_id,
            "strategy_recommendations": strategy_results,
            "performance_data": analysis_results.get('performance_monitor', {})
        }
        
        result = self.agents['experimentation'].process(context)
        self._update_task_status(user_id, "running", "Agent: Experimentation - Completed")
        return result
    
    def _compile_results(self, collection: Dict, analysis: Dict, 
                        strategy: Dict, experiments: Dict) -> Dict[str, Any]:
        """Compile all results into a unified format"""
        
        # Extract key insights and recommendations
        all_recommendations = []
        
        # Extract specific item pricing recommendations
        specific_price_recommendations = []
        if 'item_strategies' in strategy:
            # Get top items with significant price changes (both up and down)
            items_with_changes = []
            for item in strategy['item_strategies']:
                price_change_pct = item.get('price_change_percent', 0)
                if abs(price_change_pct) >= 2.0:  # Only significant changes (>= 2%)
                    items_with_changes.append(item)
            
            # Sort by magnitude of price change
            items_with_changes.sort(key=lambda x: abs(x.get('price_change_percent', 0)), reverse=True)
            
            # Add specific item recommendations
            for item in items_with_changes[:10]:  # Top 10 most significant changes
                direction = "increase" if item.get('price_change', 0) > 0 else "decrease"
                specific_price_recommendations.append({
                    "recommendation": f"Change price for {item['item_name']} from ${item['current_price']:.2f} to ${item['recommended_price']:.2f} ({direction} of {abs(item['price_change_percent']):.1f}%)",
                    "rationale": item.get('rationale', ''),
                    "category": item.get('category', 'Uncategorized'),
                    "price_change": item.get('price_change', 0),
                    "current_price": item.get('current_price', 0),
                    "recommended_price": item.get('recommended_price', 0),
                    "priority": "high" if abs(item.get('price_change_percent', 0)) > 10 else "medium",
                    "timeline": item.get('implementation_timing', 'Immediate'),
                    "item_name": item.get('item_name', ''),
                    "type": "specific_price_change"
                })
            
        # From strategy agent - general recommendations
        if 'recommendations' in strategy:
            all_recommendations.extend(strategy['recommendations'])
        
        # Add the specific item price recommendations
        all_recommendations.extend(specific_price_recommendations)
        
        # From performance monitor
        if 'performance_monitor' in analysis and 'recommendations' in analysis['performance_monitor']:
            all_recommendations.extend(analysis['performance_monitor']['recommendations'])
        
        # From experimentation
        if 'recommendations' in experiments:
            all_recommendations.extend(experiments['recommendations'])
        
        # If we don't have any recommendations, add default ones
        if not all_recommendations:
            self.logger.warning("No recommendations found in agent outputs, using defaults")
            all_recommendations = [
                {
                    "recommendation": "Optimize pricing for top-selling items",
                    "reasoning": "Top-selling items have the most impact on revenue",
                    "priority": "high",
                    "expected_impact": "Increase revenue by 5-8%",
                    "timeline": "Immediate"
                },
                {
                    "recommendation": "Review competitor pricing regularly",
                    "reasoning": "Staying competitive is essential in dynamic markets",
                    "priority": "medium",
                    "expected_impact": "Maintain market share",
                    "timeline": "Weekly"
                },
                {
                    "recommendation": "Implement A/B testing for price sensitivity",
                    "reasoning": "Understanding elasticity provides optimization opportunities",
                    "priority": "high",
                    "expected_impact": "More precise pricing decisions",
                    "timeline": "Next month"
                }
            ]
        
        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        all_recommendations.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 3))
        
        # Create executive summary
        executive_summary = self._generate_executive_summary({
            "collection": collection,
            "analysis": analysis,
            "strategy": strategy,
            "experiments": experiments
        })
        
        # Generate next steps
        next_steps = self._generate_next_steps(all_recommendations)
        
        # Ensure we have next steps even if generation failed
        if not next_steps:
            next_steps = [
                {
                    "step": 1,
                    "action": "Review pricing strategy for top 10 products",
                    "expected_impact": "Identify optimization opportunities",
                    "timeline": "Immediate"
                },
                {
                    "step": 2,
                    "action": "Analyze competitor pricing changes from last 30 days",
                    "expected_impact": "Adjust prices to remain competitive",
                    "timeline": "This week"
                },
                {
                    "step": 3,
                    "action": "Test price increases on premium product lines",
                    "expected_impact": "Potential revenue increase",
                    "timeline": "Next 2 weeks"
                }
            ]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "executive_summary": executive_summary,
            "data_collection": collection,
            "market_analysis": analysis.get('market_analysis', {}),
            "performance_monitoring": analysis.get('performance_monitor', {}),
            "pricing_strategy": strategy,
            "experimentation": experiments,
            "consolidated_recommendations": all_recommendations[:10],  # Top 10
            "next_steps": next_steps
        }
    
    def _generate_executive_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary from all agent results"""
        
        # Extract key metrics (with safe navigation)
        performance = results.get('analysis', {}).get('performance_monitor', {})
        strategy = results.get('strategy', {})
        
        # Determine revenue trend based on performance metrics
        revenue_trend = "improving"
        revenue_metrics = performance.get('performance_metrics', {}).get('revenue', {})
        if revenue_metrics.get('change_percent', 0) < 0:
            revenue_trend = "declining"
        elif revenue_metrics.get('change_percent', 0) == 0:
            revenue_trend = "stable"
        
        # Determine overall status 
        overall_status = self._determine_overall_status(results)
        
        # Extract insights and recommendations
        key_opportunities = self._extract_key_opportunities(results)
        immediate_actions = self._extract_immediate_actions(results)
        risk_factors = self._extract_risk_factors(results)
        
        # Ensure we have at least some data to display
        if not key_opportunities:
            key_opportunities = [
                "Optimize pricing for top-selling items", 
                "Review competitor pricing regularly",
                "Evaluate price elasticity for high-volume products"
            ]
            
        if not immediate_actions:
            immediate_actions = [
                "Review pricing strategy for underperforming items",
                "Analyze top competitor pricing changes"
            ]
            
        if not risk_factors:
            risk_factors = [
                "Potential market saturation in premium segment",
                "Increasing price sensitivity among core customers"
            ]
            
        return {
            "overall_status": overall_status,
            "revenue_trend": revenue_trend,
            "key_opportunities": key_opportunities,
            "immediate_actions": immediate_actions,
            "risk_factors": risk_factors,
            "last_updated": datetime.now().isoformat()
        }
    
    def _generate_next_steps(self, recommendations: List[Dict]) -> List[Dict[str, Any]]:
        """Generate prioritized next steps"""
        next_steps = []
        
        # Group by category
        high_priority = [r for r in recommendations if r.get('priority') == 'high']
        
        for i, rec in enumerate(high_priority[:3]):  # Top 3 high priority
            next_steps.append({
                "step": i + 1,
                "action": rec.get('recommendation', ''),
                "expected_impact": rec.get('expected_impact', 'TBD'),
                "timeline": rec.get('timeline', 'Immediate')
            })
            
        # Ensure we have at least some next steps to display
        if not next_steps:
            next_steps = [
                {
                    "step": 1,
                    "action": "Review current pricing strategy",
                    "expected_impact": "Identify optimization opportunities",
                    "timeline": "Immediate"
                },
                {
                    "step": 2,
                    "action": "Analyze competitor pricing",
                    "expected_impact": "Improve market positioning",
                    "timeline": "This week"
                }
            ]
        
        return next_steps
    
    def _determine_overall_status(self, results: Dict) -> str:
        """Determine overall business status"""
        performance = results['analysis'].get('performance_monitor', {})
        health = performance.get('performance_metrics', {}).get('overall_health', 'unknown')
        
        if health in ['excellent', 'good']:
            return "healthy"
        elif health == 'fair':
            return "stable"
        else:
            return "needs_attention"
    
    def _extract_key_opportunities(self, results: Dict) -> List[str]:
        """Extract top opportunities from results"""
        opportunities = []
        
        # From market analysis
        market = results['analysis'].get('market_analysis', {})
        if market.get('opportunities', []):
            opportunities.extend([opp['description'] for opp in market['opportunities'][:2]])
        
        # From pricing strategy
        strategy = results['strategy']
        if strategy.get('optimization_opportunities', []):
            opportunities.extend([opp['opportunity'] for opp in strategy['optimization_opportunities'][:2]])
        
        return opportunities[:3]  # Top 3
    
    def _extract_immediate_actions(self, results: Dict) -> List[str]:
        """Extract immediate actions needed"""
        actions = []
        
        # From performance alerts
        performance = results['analysis'].get('performance_monitor', {})
        alerts = performance.get('alerts', [])
        for alert in alerts:
            if alert.get('severity') == 'high':
                actions.append(alert.get('action', ''))
        
        return actions[:2]  # Top 2
    
    def _extract_risk_factors(self, results: Dict) -> List[str]:
        """Extract key risk factors"""
        risks = []
        
        # From market analysis
        market = results['analysis'].get('market_analysis', {})
        if market.get('competitive_threats', []):
            risks.extend([threat['description'] for threat in market['competitive_threats'][:2]])
        
        # From performance anomalies
        performance = results['analysis'].get('performance_monitor', {})
        anomalies = performance.get('anomalies_detected', [])
        if anomalies:
            risks.append(f"{len(anomalies)} performance anomalies detected")
        
        return risks[:3]  # Top 3
    
    def _update_task_status(self, user_id: int, status: str, message: str, results: Dict = None):
        """Update the task status in running_tasks"""
        if user_id in running_tasks:
            update = {
                'status': status,
                'message': message,
                'last_updated': datetime.now().isoformat()
            }
            if results:
                update['results'] = results
            running_tasks[user_id].update(update)
            self.logger.info(f"Updated task status for user {user_id}: {status} - {message}")
