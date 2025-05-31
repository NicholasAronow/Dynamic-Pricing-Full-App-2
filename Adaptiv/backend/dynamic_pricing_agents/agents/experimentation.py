"""
Experimentation Agent - Manages pricing experiments and A/B tests
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import numpy as np
import random
from sqlalchemy import desc
from sqlalchemy.orm import Session
from models import AgentMemory, PricingExperiment, ExperimentLearning
from ..base_agent import BaseAgent


class ExperimentationAgent(BaseAgent):
    """Agent responsible for designing and managing pricing experiments"""
    
    def __init__(self):
        super().__init__("ExperimentationAgent", model="gpt-4o-mini")
        self.logger.info("Experimentation Agent initialized")
        
    def get_system_prompt(self) -> str:
        return """You are an Experimentation Agent specializing in pricing experiments and A/B testing. Your role is to:
        1. Design statistically rigorous pricing experiments
        2. Manage A/B tests and multi-armed bandit experiments
        3. Ensure proper sample sizes and statistical significance
        4. Minimize business risk while maximizing learning
        5. Analyze experiment results and draw conclusions
        
        Focus on scientific methodology and actionable results."""
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Design and manage pricing experiments with memory functionality"""
        db = context['db']
        user_id = context['user_id']
        strategy_recommendations = context.get('strategy_recommendations', {})
        performance_data = context.get('performance_data', {})
        
        self.log_action("experimentation_started", {"user_id": user_id})
        
        # Retrieve memory context
        memory_context = self.get_memory_context(db, user_id, 
                                             memory_types=['pricing_experiment', 'experiment_learning',
                                                          'market_insight', 'pricing_decision'])
        
        # Get experiment history from memory
        experiment_history = self._get_experiment_history(db, user_id)
        
        # Get current experiments
        active_experiments = self._get_active_experiments_with_memory(db, user_id, memory_context)
        completed_experiments = self._get_completed_experiments_with_memory(db, user_id, memory_context)
        
        # Analyze completed experiments with historical learnings
        experiment_results = self._analyze_experiment_results_with_memory(
            completed_experiments, experiment_history, db
        )
        
        # Design new experiments using memory context
        new_experiments = self._design_new_experiments_with_memory(
            strategy_recommendations,
            active_experiments,
            experiment_results,
            memory_context,
            db,
            user_id
        )
        
        # Update active experiments
        updated_experiments = self._update_active_experiments(active_experiments, db)
        
        # Save experiments and learnings to memory
        self._save_experiments_to_memory(db, user_id, updated_experiments, experiment_results)
        self._save_experiment_learnings(db, user_id, experiment_results)
        
        # Generate experiment insights with memory enhancement
        insights = self._generate_experiment_insights_with_memory({
            "active_experiments": updated_experiments,
            "completed_results": experiment_results,
            "new_experiments": new_experiments,
            "experiment_history": experiment_history,
            "memory_context": memory_context
        })
        
        experimentation_results = {
            "experimentation_timestamp": datetime.now().isoformat(),
            "active_experiments": updated_experiments,
            "completed_experiments": experiment_results,
            "new_experiment_proposals": new_experiments,
            "insights": insights,
            "recommendations": self._generate_experimentation_recommendations_with_memory(
                experiment_results, updated_experiments, new_experiments, memory_context
            ),
            "experiment_calendar": self._create_experiment_calendar(
                updated_experiments, new_experiments
            ),
            "historical_performance": self._analyze_historical_experiment_performance(experiment_history)
        }
        
        self.log_action("experimentation_completed", {
            "active_experiments": len(updated_experiments),
            "new_proposals": len(new_experiments),
            "completed_analyzed": len(experiment_results),
            "experiment_history_used": len(experiment_history)
        })
        
        return experimentation_results
    
    def _get_active_experiments(self, db, user_id: int) -> List[Dict[str, Any]]:
        """Get currently active pricing experiments"""
        # In a real implementation, this would query an experiments table
        # For now, we'll simulate active experiments
        return [
            {
                "experiment_id": "exp_001",
                "name": "Coffee Price Optimization",
                "type": "a_b_test",
                "status": "active",
                "started_at": (datetime.now() - timedelta(days=5)).isoformat(),
                "items": [1, 2, 3],  # Coffee items
                "control_group": {"size": 500, "price_multiplier": 1.0},
                "treatment_group": {"size": 480, "price_multiplier": 1.05},
                "metrics": {
                    "revenue": {"control": 5000, "treatment": 5200},
                    "units_sold": {"control": 1000, "treatment": 950}
                }
            }
        ]
    
    def _get_completed_experiments(self, db, user_id: int) -> List[Dict[str, Any]]:
        """Get recently completed experiments"""
        # Simulate completed experiments
        return [
            {
                "experiment_id": "exp_000",
                "name": "Pastry Bundle Test",
                "type": "a_b_test",
                "status": "completed",
                "started_at": (datetime.now() - timedelta(days=20)).isoformat(),
                "ended_at": (datetime.now() - timedelta(days=6)).isoformat(),
                "items": [4, 5],  # Pastry items
                "control_group": {"size": 1000, "price_multiplier": 1.0},
                "treatment_group": {"size": 1000, "price_multiplier": 0.9},
                "final_metrics": {
                    "revenue": {"control": 10000, "treatment": 10800},
                    "units_sold": {"control": 2000, "treatment": 2400}
                }
            }
        ]
    
    def _analyze_experiment_results(self, experiments: List[Dict], db) -> List[Dict[str, Any]]:
        """Analyze results from completed experiments"""
        results = []
        
        for exp in experiments:
            if exp["status"] == "completed":
                metrics = exp.get("final_metrics", {})
                
                # Calculate lift and statistical significance
                control_revenue = metrics.get("revenue", {}).get("control", 0)
                treatment_revenue = metrics.get("revenue", {}).get("treatment", 0)
                revenue_lift = (treatment_revenue - control_revenue) / control_revenue if control_revenue > 0 else 0
                
                control_units = metrics.get("units_sold", {}).get("control", 0)
                treatment_units = metrics.get("units_sold", {}).get("treatment", 0)
                units_lift = (treatment_units - control_units) / control_units if control_units > 0 else 0
                
                # Simulate statistical significance calculation
                p_value = self._calculate_p_value(
                    control_revenue, treatment_revenue,
                    exp["control_group"]["size"], exp["treatment_group"]["size"]
                )
                
                result = {
                    "experiment_id": exp["experiment_id"],
                    "name": exp["name"],
                    "duration_days": 14,  # Would calculate from dates
                    "revenue_lift": revenue_lift,
                    "units_lift": units_lift,
                    "p_value": p_value,
                    "statistically_significant": p_value < 0.05,
                    "recommendation": self._generate_experiment_recommendation(
                        revenue_lift, units_lift, p_value
                    ),
                    "learnings": self._extract_learnings(exp, revenue_lift, units_lift)
                }
                results.append(result)
        
        return results
    
    def _design_new_experiments(self, strategy: Dict, active: List[Dict], 
                                results: List[Dict], db, user_id: int) -> List[Dict[str, Any]]:
        """Design new experiments based on strategy and past results"""
        import models
        
        # Get items that haven't been tested recently
        all_items = db.query(models.Item).filter(models.Item.user_id == user_id).all()
        tested_items = set()
        for exp in active + results:
            tested_items.update(exp.get("items", []))
        
        untested_items = [item for item in all_items if item.id not in tested_items]
        
        new_experiments = []
        
        # Design A/B test for high-value untested items
        if untested_items:
            # Item model uses current_price, not price attribute
            high_value_items = sorted(untested_items, key=lambda x: getattr(x, 'current_price', 0.0) if hasattr(x, 'current_price') else getattr(x, 'price', 0.0), reverse=True)[:3]
            
            new_experiments.append({
                "experiment_id": f"exp_{datetime.now().strftime('%Y%m%d_%H%M')}",
                "name": "Premium Item Price Test",
                "type": "a_b_test",
                "items": [item.id for item in high_value_items],
                "hypothesis": "5% price increase on premium items will not significantly impact demand",
                "design": {
                    "control": {"price_multiplier": 1.0, "allocation": 0.5},
                    "treatment": {"price_multiplier": 1.05, "allocation": 0.5}
                },
                "success_criteria": {
                    "primary": "revenue_lift > 3%",
                    "secondary": "units_sold_decline < 5%"
                },
                "duration_days": 14,
                "minimum_sample_size": 200,
                "risk_assessment": "low"
            })
        
        # Design multi-armed bandit for dynamic optimization
        if len(all_items) > 10:
            mab_items = random.sample(all_items, 5)
            
            new_experiments.append({
                "experiment_id": f"mab_{datetime.now().strftime('%Y%m%d_%H%M')}",
                "name": "Dynamic Price Optimization",
                "type": "multi_armed_bandit",
                "items": [item.id for item in mab_items],
                "hypothesis": "Dynamic pricing will find optimal price points faster than fixed tests",
                "design": {
                    "algorithm": "thompson_sampling",
                    "price_arms": [0.95, 0.98, 1.0, 1.02, 1.05],
                    "exploration_rate": 0.15,
                    "update_frequency": "daily"
                },
                "success_criteria": {
                    "convergence": "within_21_days",
                    "revenue_improvement": "> 5%"
                },
                "duration_days": 21,
                "risk_assessment": "medium"
            })
        
        # Design bundle experiment
        if len(results) > 0:
            new_experiments.append({
                "experiment_id": f"bundle_{datetime.now().strftime('%Y%m%d_%H%M')}",
                "name": "Complementary Bundle Test",
                "type": "factorial_design",
                "items": [1, 4],  # Coffee + Pastry
                "hypothesis": "10% bundle discount will increase total revenue through higher volume",
                "design": {
                    "factors": {
                        "bundle_discount": [0, 0.05, 0.10],
                        "promotion_visibility": ["low", "high"]
                    }
                },
                "success_criteria": {
                    "revenue_per_customer": "> 8%",
                    "bundle_adoption": "> 20%"
                },
                "duration_days": 14,
                "minimum_sample_size": 300,
                "risk_assessment": "low"
            })
        
        return new_experiments
    
    def _update_active_experiments(self, experiments: List[Dict], db) -> List[Dict[str, Any]]:
        """Update status and metrics of active experiments"""
        updated = []
        
        for exp in experiments:
            # Simulate metric updates
            days_active = (datetime.now() - datetime.fromisoformat(exp["started_at"].replace('Z', '+00:00'))).days
            
            # Update metrics with simulated data
            exp["metrics"]["revenue"]["control"] += random.randint(800, 1200)
            exp["metrics"]["revenue"]["treatment"] += random.randint(850, 1250)
            exp["metrics"]["units_sold"]["control"] += random.randint(150, 250)
            exp["metrics"]["units_sold"]["treatment"] += random.randint(140, 240)
            
            # Check if experiment should be concluded
            if exp["type"] == "a_b_test":
                sample_size = exp["control_group"]["size"] + exp["treatment_group"]["size"]
                if sample_size > 1000 or days_active > 14:
                    exp["status"] = "ready_to_conclude"
                    exp["recommendation"] = "Analyze results and make decision"
            
            # Calculate current performance
            control_rev = exp["metrics"]["revenue"]["control"]
            treatment_rev = exp["metrics"]["revenue"]["treatment"]
            current_lift = (treatment_rev - control_rev) / control_rev if control_rev > 0 else 0
            
            exp["current_performance"] = {
                "revenue_lift": current_lift,
                "days_active": days_active,
                "sample_size": exp["control_group"]["size"] + exp["treatment_group"]["size"]
            }
            
            updated.append(exp)
        
        return updated
    
    def _convert_numpy_to_python(self, obj):
        """Convert NumPy types to standard Python types for JSON serialization"""
        import numpy as np
        
        if isinstance(obj, dict):
            return {k: self._convert_numpy_to_python(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_to_python(item) for item in obj]
        elif isinstance(obj, (np.int_, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64, 
                            np.uint8, np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.bool_, np.bool)):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return self._convert_numpy_to_python(obj.tolist())
        else:
            return obj
    
    def _generate_experiment_insights(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from experiment data using LLM"""
        # Extract key data
        active = data["active_experiments"]
        completed = data["completed_results"]
        proposals = data["new_experiments"]
        
        # Generate insights
        insights = {
            "current_strategy": "diversified_testing" if len(active) > 1 else "focused_testing",
    
            "success_rate": f"{sum(1 for r in completed if r.get('recommendation') == 'implement_treatment') / len(completed) * 100:.1f}%" if completed else "No completed experiments",
            "key_findings": [],
            "recommended_focus_areas": []
        }
        
        return insights
        
    def _generate_experiment_insights_with_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from experiment data using LLM with memory enhancement"""
        # Get base insights
        insights = self._generate_experiment_insights(data)
        
        # Enhance with historical context if available
        if 'experiment_history' in data and data['experiment_history']:
            history = data['experiment_history']
            memory_context = data.get('memory_context', {})
            
            # Calculate historical success metrics
            successful_experiments = sum(1 for exp in history 
                                      if exp.get('status') == 'completed' and 
                                      exp.get('results', {}).get('revenue_lift', 0) > 0)
            total_completed = sum(1 for exp in history if exp.get('status') == 'completed')
            historical_success_rate = f"{(successful_experiments / total_completed * 100) if total_completed > 0 else 0:.1f}%"
            
            # Add historical context to insights
            insights['historical_success_rate'] = historical_success_rate
            insights['experiments_to_date'] = len(history)
            insights['trend'] = 'improving' if successful_experiments > 0 and total_completed > 0 and successful_experiments/total_completed > 0.5 else 'needs_improvement'
            
            # Add learning patterns
            all_learnings = []
            for exp in history:
                all_learnings.extend(exp.get('learnings', []))
            
            # Find recurring learnings
            from collections import Counter
            learning_texts = [l.get('learning') for l in all_learnings if isinstance(l, dict) and 'learning' in l]
            if not learning_texts:
                learning_texts = [l for l in all_learnings if isinstance(l, str)]
            
            if learning_texts:
                # Simple approach - look for common substrings/themes
                common_themes = []
                if 'price' in ' '.join(learning_texts).lower():
                    common_themes.append('price_sensitivity')
                if 'elastic' in ' '.join(learning_texts).lower():
                    common_themes.append('elasticity_patterns')
                if 'season' in ' '.join(learning_texts).lower() or 'time' in ' '.join(learning_texts).lower():
                    common_themes.append('seasonal_effects')
                
                insights['recurring_patterns'] = common_themes
        
        return insights

    def _generate_experimentation_recommendations(self, results: List[Dict], 
                                                 active: List[Dict], 
                                                 proposals: List[Dict]) -> List[Dict[str, Any]]:
        """Generate recommendations for experimentation strategy"""
        recommendations = []
        
        # Based on completed experiments
        successful_experiments = [r for r in results if r.get("revenue_lift", 0) > 0.05 and r.get("statistically_significant", False)]
        if successful_experiments:
            recommendations.append({
                "priority": "high",
                "category": "scale_success",
                "recommendation": "Roll out successful experiment results to all customers",
                "experiments": [exp["name"] for exp in successful_experiments],
                "expected_impact": f"{np.mean([exp.get('revenue_lift', 0) for exp in successful_experiments])*100:.1f}% revenue increase"
            })
        
        # Based on active experiments
        ready_to_conclude = [exp for exp in active if exp.get("status") == "ready_to_conclude"]
        if ready_to_conclude:
            recommendations.append({
                "priority": "high",
                "category": "conclude_experiments",
                "recommendation": "Analyze and conclude experiments that have reached significance",
                "experiments": [exp["name"] for exp in ready_to_conclude],
                "action": "Make go/no-go decisions within 48 hours"
            })
        
        # Based on proposals
        if proposals:
            high_priority = [p for p in proposals if p["risk_assessment"] == "low"]
            recommendations.append({
                "priority": "medium",
                "category": "launch_new",
                "recommendation": "Launch low-risk experiments to continue learning",
                "experiments": [exp["name"] for exp in high_priority],
            })
        
        return recommendations
    
    def _generate_experimentation_recommendations_with_memory(self, results: List[Dict], 
                                                       active: List[Dict], 
                                                       proposals: List[Dict],
                                                       memory_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate recommendations for experimentation strategy with memory enhancement"""
        # Get base recommendations
        recommendations = self._generate_experimentation_recommendations(results, active, proposals)
        
        # Enhance with memory context
        if memory_context:
            # Incorporate market insights if available
            market_insights = memory_context.get('market_insight', [])
            if market_insights:
                # Extract relevant insights about seasonality, trends, etc.
                seasonal_insights = [insight for insight in market_insights 
                                  if 'season' in str(insight.get('content', {})).lower() or 
                                  'trend' in str(insight.get('content', {})).lower()]
                
                if seasonal_insights:
                    # Add seasonal testing recommendation
                    recommendations.append({
                        "priority": "medium",
                        "category": "seasonal_testing",
                        "recommendation": "Design experiments accounting for identified seasonal patterns",
                        "rationale": "Historical market data shows seasonal patterns that should be accounted for in experiment design"
                    })
            
            # Incorporate past experiment learnings
            experiment_learning = memory_context.get('experiment_learning', [])
            if experiment_learning:
                # Find common successful experiment types
                experiment_types = {}
                for learning in experiment_learning:
                    content = learning.get('content', {})
                    exp_type = content.get('experiment_type', 'unknown')
                    if exp_type not in experiment_types:
                        experiment_types[exp_type] = {
                            'count': 0,
                            'success_count': 0
                        }
                    experiment_types[exp_type]['count'] += 1
                    if content.get('successful', False):
                        experiment_types[exp_type]['success_count'] += 1
                
                # Find most successful experiment type
                most_successful_type = None
                highest_success_rate = 0
                for exp_type, stats in experiment_types.items():
                    if stats['count'] >= 3:  # Need minimum sample size
                        success_rate = stats['success_count'] / stats['count']
                        if success_rate > highest_success_rate:
                            highest_success_rate = success_rate
                            most_successful_type = exp_type
                
                if most_successful_type:
                    # Add recommendation to focus on successful experiment type
                    recommendations.append({
                        "priority": "high",
                        "category": "focus_on_success",
                        "recommendation": f"Prioritize {most_successful_type} experiments based on historical success",
                        "rationale": f"This experiment type has shown a {highest_success_rate:.0%} success rate historically"
                    })
        
        return recommendations
    
    def _analyze_experiment_results_with_memory(self, experiments: List[Dict], 
                                               experiment_history: List[Dict], 
                                               db) -> List[Dict[str, Any]]:
        """Analyze results from completed experiments with memory enhancement"""
        # Get base experiment results
        results = self._analyze_experiment_results(experiments, db)
        
        # Enhance with historical patterns from memory
        if experiment_history and results:
            # Create a mapping of item_id to historical performance
            item_history = {}
            for hist_exp in experiment_history:
                if hist_exp.get('status') == 'completed' and 'items' in hist_exp and 'results' in hist_exp:
                    for item_id in hist_exp.get('items', []):
                        if item_id not in item_history:
                            item_history[item_id] = []
                        item_history[item_id].append({
                            'experiment_name': hist_exp.get('name'),
                            'experiment_type': hist_exp.get('type'),
                            'treatment': hist_exp.get('results', {}).get('treatment', {}),
                            'revenue_lift': hist_exp.get('results', {}).get('revenue_lift', 0),
                            'units_lift': hist_exp.get('results', {}).get('units_lift', 0)
                        })
            
            # Enhance current results with historical context
            for result in results:
                relevant_history = []
                for item_id in result.get('items', []):
                    if item_id in item_history:
                        relevant_history.extend(item_history[item_id])
                
                if relevant_history:
                    # Add historical context to the result
                    result['historical_context'] = {
                        'previous_experiments': len(relevant_history),
                        'avg_revenue_lift': np.mean([h.get('revenue_lift', 0) for h in relevant_history]),
                        'avg_units_lift': np.mean([h.get('units_lift', 0) for h in relevant_history]),
                        'consistent_pattern': self._detect_consistent_pattern(relevant_history),
                        'similar_experiments': relevant_history[:2]  # Include top 2 similar experiments
                    }
                    
                    # Adjust confidence based on historical data
                    if 'confidence' in result:
                        # Higher confidence if results match historical patterns
                        if result.get('historical_context', {}).get('consistent_pattern'):
                            result['confidence'] = min(result.get('confidence', 0.5) + 0.2, 0.95)
        
        return results
    
    def _detect_consistent_pattern(self, experiment_history: List[Dict]) -> bool:
        """Detect if there's a consistent pattern in experiment history"""
        if len(experiment_history) < 2:
            return False
            
        # Check for consistent revenue lift direction
        revenue_lifts = [h.get('revenue_lift', 0) for h in experiment_history]
        all_positive = all(lift > 0 for lift in revenue_lifts)
        all_negative = all(lift < 0 for lift in revenue_lifts)
        
        return all_positive or all_negative
        
    def _design_new_experiments_with_memory(self, strategy: Dict, active: List[Dict], 
                                      results: List[Dict], memory_context: Dict[str, Any],
                                      db, user_id: int) -> List[Dict[str, Any]]:
        """Design new experiments based on strategy, past results, and memory"""
        # Get base experiment designs
        new_experiments = self._design_new_experiments(strategy, active, results, db, user_id)
        
        # Enhance with memory context
        if memory_context:
            # Look for successful experiments in memory to replicate
            past_experiments = []
            for mem_type in ['pricing_experiment', 'experiment_learning']:
                for memory in memory_context.get(mem_type, []):
                    content = memory.get('content', {})
                    if isinstance(content, dict):
                        if content.get('results', {}).get('revenue_lift', 0) > 0.05 and \
                           content.get('status', '') == 'completed':
                            past_experiments.append(content)
            
            # Use successful past experiments to inform new ones
            if past_experiments and new_experiments:
                for i, new_exp in enumerate(new_experiments):
                    # Find a similar past experiment that was successful
                    similar_past = next((p for p in past_experiments 
                                       if p.get('experiment_type', '') == new_exp.get('type', '')), None)
                    
                    if similar_past:
                        # Adjust experiment parameters based on past success
                        if 'design' in new_exp and 'treatment' in new_exp['design']:
                            # Use successful treatment from past as starting point
                            if 'price_multiplier' in new_exp['design']['treatment'] and \
                               'price_multiplier' in similar_past.get('treatment_group', {}):
                                past_multiplier = similar_past['treatment_group']['price_multiplier']
                                new_exp['design']['treatment']['price_multiplier'] = past_multiplier
                                
                                # Add context about why this design was chosen
                                new_exp['historical_basis'] = {
                                    'based_on_experiment': similar_past.get('name', 'Past experiment'),
                                    'past_revenue_lift': similar_past.get('results', {}).get('revenue_lift', 0),
                                    'confidence': 'high' if similar_past.get('results', {}).get('statistically_significant', False) else 'medium'
                                }
        
        return new_experiments
        
    def _save_experiments_to_memory(self, db: Session, user_id: int, active_experiments: List[Dict], experiment_results: List[Dict]):
        """Save experiments to memory for future reference"""
        import numpy as np
        
        # Convert NumPy data types to Python native types before database operations
        active_experiments = self._convert_numpy_to_python(active_experiments)
        experiment_results = self._convert_numpy_to_python(experiment_results)
        
        # Save active experiments
        for experiment in active_experiments:
            exp_id = experiment.get('experiment_id')
            if not exp_id:
                continue
                
            # Check if experiment already exists in database
            existing = db.query(PricingExperiment).filter(
                PricingExperiment.user_id == user_id,
                PricingExperiment.experiment_id == exp_id
            ).first()
            
            if existing:
                # Update existing experiment
                existing.metrics = experiment.get('metrics', {})
                existing.status = 'active'
                existing.last_updated = datetime.now()
            else:
                # Create new experiment record
                new_experiment = PricingExperiment(
                    user_id=user_id,
                    experiment_id=exp_id,
                    name=experiment.get('name', 'Unnamed Experiment'),
                    experiment_type=experiment.get('type', 'a_b_test'),
                    item_ids=experiment.get('items', []),  # Changed from items to item_ids
                    started_at=datetime.now(),  # Changed from start_date to started_at
                    status='active',
                    control_prices=experiment.get('control_group', {}),  # Changed from control_group to control_prices
                    treatment_prices=experiment.get('treatment_group', {}),  # Changed from treatment_group to treatment_prices
                    control_metrics={},  # Added control_metrics instead of metrics
                    treatment_metrics={},  # Added treatment_metrics 
                    success_criteria=experiment.get('success_criteria', {})  # Changed from success_metrics to success_criteria
                )
                db.add(new_experiment)
        
        # Save completed experiments
        for result in experiment_results:
            exp_id = result.get('experiment_id')
            if not exp_id:
                continue
                
            # Check if experiment already exists in database
            existing = db.query(PricingExperiment).filter(
                PricingExperiment.user_id == user_id,
                PricingExperiment.experiment_id == exp_id
            ).first()
            
            if existing:
                # Update existing experiment
                existing.status = 'completed'
                existing.ended_at = datetime.now()  # Changed from end_date to ended_at
                
                # Set individual metrics fields instead of results
                existing.control_metrics = existing.control_metrics or {}
                existing.treatment_metrics = existing.treatment_metrics or {}
                
                # Add performance metrics - convert NumPy values to Python types
                existing.p_value = float(self._convert_numpy_to_python(result.get('p_value', 1)))
                existing.confidence_interval = self._convert_numpy_to_python({
                    'lower': result.get('confidence_interval_lower', 0),
                    'upper': result.get('confidence_interval_upper', 0)
                })
                
                # Update treatment metrics with lift information - convert NumPy values to Python types
                if existing.treatment_metrics:
                    existing.treatment_metrics.update(self._convert_numpy_to_python({
                        'revenue_lift': result.get('revenue_lift', 0),
                        'units_lift': result.get('units_lift', 0),
                        'statistically_significant': result.get('statistically_significant', False)
                    }))
            else:
                # Create new completed experiment record
                new_experiment = PricingExperiment(
                    user_id=user_id,
                    experiment_id=exp_id,
                    name=result.get('name', 'Unnamed Experiment'),
                    experiment_type='a_b_test',
                    item_ids=[],  # No item data available in results
                    started_at=datetime.now() - timedelta(days=14),  # Estimate
                    ended_at=datetime.now(),
                    status='completed',
                    control_metrics={},
                    treatment_metrics=self._convert_numpy_to_python({
                        'revenue_lift': result.get('revenue_lift', 0),
                        'units_lift': result.get('units_lift', 0),
                        'statistically_significant': result.get('statistically_significant', False)
                    }),
                    p_value=float(self._convert_numpy_to_python(result.get('p_value', 1))),
                    confidence_interval=self._convert_numpy_to_python({
                        'lower': result.get('confidence_interval_lower', 0),
                        'upper': result.get('confidence_interval_upper', 0)
                    }),
                    success_criteria=result.get('success_criteria', {})
                )
                db.add(new_experiment)
        
        db.commit()
    
    def _save_experiment_learnings(self, db: Session, user_id: int, experiment_results: List[Dict]):
        """Save learnings from experiments to memory"""
        for result in experiment_results:
            exp_id = result.get('experiment_id')
            if not exp_id or not result.get('learnings'):
                continue
                
            # Save each learning as a separate record
            for learning in result.get('learnings', []):
                new_learning = ExperimentLearning(
                    user_id=user_id,
                    experiment_id=exp_id,
                    learning=learning,
                    confidence=0.8 if result.get('statistically_significant', False) else 0.5,
                    created_at=datetime.now()
                )
                db.add(new_learning)
        
        db.commit()
    
    def _analyze_historical_experiment_performance(self, experiment_history: List[Dict]) -> Dict[str, Any]:
        """Analyze historical experiment performance patterns"""
        if not experiment_history:
            return {"message": "No historical data available"}
            
        # Calculate aggregate statistics
        total_experiments = len(experiment_history)
        completed_experiments = sum(1 for exp in experiment_history if exp.get('status') == 'completed')
        successful_experiments = sum(1 for exp in experiment_history 
                                   if exp.get('status') == 'completed' and 
                                   exp.get('results', {}).get('revenue_lift', 0) > 0)
        
        # Calculate success rate
        success_rate = successful_experiments / completed_experiments if completed_experiments > 0 else 0
        
        # Identify most successful experiment types
        experiment_types = {}
        for exp in experiment_history:
            if exp.get('status') == 'completed':
                exp_type = exp.get('type', 'unknown')
                if exp_type not in experiment_types:
                    experiment_types[exp_type] = {
                        'count': 0,
                        'success_count': 0,
                        'avg_revenue_lift': 0
                    }
                    
                experiment_types[exp_type]['count'] += 1
                if exp.get('results', {}).get('revenue_lift', 0) > 0:
                    experiment_types[exp_type]['success_count'] += 1
                experiment_types[exp_type]['avg_revenue_lift'] += exp.get('results', {}).get('revenue_lift', 0)
        
        # Calculate averages
        for exp_type in experiment_types:
            if experiment_types[exp_type]['count'] > 0:
                experiment_types[exp_type]['avg_revenue_lift'] /= experiment_types[exp_type]['count']
                experiment_types[exp_type]['success_rate'] = experiment_types[exp_type]['success_count'] / experiment_types[exp_type]['count']
        
        return {
            "total_experiments": total_experiments,
            "completed_experiments": completed_experiments,
            "successful_experiments": successful_experiments,
            "overall_success_rate": success_rate,
            "experiment_type_performance": experiment_types,
            "avg_experiment_duration_days": np.mean([((datetime.fromisoformat(exp.get('end_date', datetime.now().isoformat())) - 
                                         datetime.fromisoformat(exp.get('start_date', datetime.now().isoformat()))).days) 
                                       for exp in experiment_history if exp.get('start_date') and exp.get('end_date')]) 
                                      if any(exp.get('start_date') and exp.get('end_date') for exp in experiment_history) else 14
        }
    
    def _create_experiment_calendar(self, active: List[Dict], proposals: List[Dict]) -> Dict[str, Any]:
        """Create experiment timeline and calendar"""
        # Simple calendar showing experiment timelines
        calendar = {
            "current_month": datetime.now().strftime("%B %Y"),
            "next_month": (datetime.now() + timedelta(days=30)).strftime("%B %Y"),
            "active_timelines": [],
            "proposed_timelines": []
        }
        
        # Add active experiments
        for exp in active:
            start_date = datetime.fromisoformat(exp["started_at"].replace('Z', '+00:00')) if "started_at" in exp else datetime.now() - timedelta(days=7)
            calendar["active_timelines"].append({
                "experiment": exp["name"],
                "type": exp.get("type", "a_b_test"),
                "phase": "active",
                "start_date": start_date.isoformat(),
                "end_date": (start_date + timedelta(days=14)).isoformat(),
                "status": exp["status"]
            })
        
        # Add proposed experiments
        next_start = datetime.now() + timedelta(days=3)  # Start in 3 days
        for exp in proposals:
            calendar["proposed_timelines"].append({
                "experiment": exp["name"],
                "type": exp.get("type", "a_b_test"),
                "phase": "proposed",
                "start_date": next_start.isoformat(),
                "end_date": (next_start + timedelta(days=exp.get("duration_days", 14))).isoformat(),
                "status": "pending_approval"
            })
            next_start += timedelta(days=7)  # Stagger starts by a week
        
        return calendar
    
    # Helper methods
    def _calculate_p_value(self, control_value: float, treatment_value: float,
                           control_size: int, treatment_size: int) -> float:
        """Calculate p-value for experiment results (simplified)"""
        # In production, would use proper statistical tests (t-test, chi-square, etc.)
        # This is a simplified simulation
        diff = abs(treatment_value - control_value)
        pooled_value = (control_value + treatment_value) / 2
        
        if pooled_value > 0:
            effect_size = diff / pooled_value
            # Simulate p-value based on effect size and sample size
            total_size = control_size + treatment_size
            p_value = max(0.001, 1 - (effect_size * np.sqrt(total_size) / 10))
            return min(0.99, p_value)
        return 0.5
    
    def _generate_experiment_recommendation(self, revenue_lift: float, 
                                            units_lift: float, p_value: float) -> str:
        """Generate recommendation based on experiment results"""
        if p_value >= 0.05:
            return "insufficient_evidence"
        elif revenue_lift > 0.05 and units_lift > -0.10:
            return "implement_treatment"
        elif revenue_lift > 0 and units_lift > -0.05:
            return "cautious_implementation"
        else:
            return "maintain_control"
    
    def _extract_learnings(self, experiment: Dict, revenue_lift: float, units_lift: float) -> List[str]:
        """Extract key learnings from experiment"""
        learnings = []
        
        if revenue_lift > 0 and units_lift < 0:
            learnings.append("Price increase was successful despite volume decline")
            learnings.append("Customers showed low price sensitivity for these items")
        elif revenue_lift < 0 and units_lift > 0:
            learnings.append("Price decrease increased volume but not enough to offset revenue loss")
            learnings.append("Consider non-price factors to drive demand")
        
        if abs(units_lift) < 0.05:
            learnings.append("Demand was relatively inelastic to price changes")
        
        return learnings
    
    def _get_experiment_history(self, db: Session, user_id: int) -> List[Dict[str, Any]]:
        """Get historical experiments from memory"""
        # Query experiment records from memory
        experiments = db.query(PricingExperiment).filter(
            PricingExperiment.user_id == user_id
        ).order_by(desc(PricingExperiment.ended_at)).limit(10).all()
        
        # Query experiment learnings from memory
        learnings = db.query(ExperimentLearning).filter(
            ExperimentLearning.user_id == user_id
        ).order_by(desc(ExperimentLearning.created_at)).limit(20).all()
        
        # Create a mapping of experiment IDs to learnings
        learning_map = {}
        for learning in learnings:
            if learning.experiment_id not in learning_map:
                learning_map[learning.experiment_id] = []
            learning_map[learning.experiment_id].append({
                "learning": learning.learning,
                "confidence": learning.confidence,
                "created_at": learning.created_at.isoformat()
            })
        
        # Combine experiments with their learnings
        history = []
        for exp in experiments:
            exp_dict = {
                "experiment_id": exp.experiment_id,
                "name": exp.name,
                "type": exp.experiment_type,
                "items": exp.item_ids,  # Changed from exp.items to exp.item_ids
                "start_date": exp.started_at.isoformat() if exp.started_at else None,  # Changed from start_date to started_at
                "end_date": exp.ended_at.isoformat() if exp.ended_at else None,  # Changed from end_date to ended_at
                "status": exp.status,
                "results": {
                    "control": exp.control_metrics,
                    "treatment": exp.treatment_metrics,
                    "p_value": exp.p_value,
                    "confidence_interval": exp.confidence_interval
                },  # Restructured from exp.results to actual model attributes
                "success_metrics": exp.success_criteria,  # Changed from success_metrics to success_criteria
                "learnings": learning_map.get(exp.experiment_id, [])
            }
            history.append(exp_dict)
        
        return history
    
    def _get_active_experiments_with_memory(self, db: Session, user_id: int, memory_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get active experiments with memory enhancement"""
        # Get base active experiments
        active_experiments = self._get_active_experiments(db, user_id)
        
        # Enhance with memory data if available
        experiment_memories = memory_context.get('pricing_experiment', [])
        if experiment_memories:
            # Find active experiments in memory
            for memory in experiment_memories:
                content = memory.get('content', {})
                if content.get('status') == 'active':
                    # Check if this experiment is already in our list
                    exp_id = content.get('experiment_id')
                    if exp_id:
                        existing = next((e for e in active_experiments if e.get('experiment_id') == exp_id), None)
                        if not existing:
                            # Add this experiment from memory
                            active_experiments.append(content)
                        else:
                            # Enhance existing experiment with memory data
                            for key, value in content.items():
                                if key not in existing or not existing[key]:
                                    existing[key] = value
        
        return active_experiments
    
    def _get_completed_experiments_with_memory(self, db: Session, user_id: int, memory_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get completed experiments with memory enhancement"""
        # Get base completed experiments
        completed_experiments = self._get_completed_experiments(db, user_id)
        
        # Enhance with memory data if available
        experiment_memories = memory_context.get('pricing_experiment', [])
        if experiment_memories:
            # Find completed experiments in memory
            for memory in experiment_memories:
                content = memory.get('content', {})
                if content.get('status') == 'completed':
                    # Check if this experiment is already in our list
                    exp_id = content.get('experiment_id')
                    if exp_id:
                        existing = next((e for e in completed_experiments if e.get('experiment_id') == exp_id), None)
                        if not existing:
                            # Add this experiment from memory
                            completed_experiments.append(content)
                        else:
                            # Enhance existing experiment with memory data
                            for key, value in content.items():
                                if key not in existing or not existing[key]:
                                    existing[key] = value
        
        return completed_experiments
