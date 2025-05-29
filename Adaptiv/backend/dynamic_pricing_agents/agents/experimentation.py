"""
Experimentation Agent - Manages pricing experiments and A/B tests
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import numpy as np
import random
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
        """Design and manage pricing experiments"""
        db = context['db']
        user_id = context['user_id']
        strategy_recommendations = context.get('strategy_recommendations', {})
        performance_data = context.get('performance_data', {})
        
        self.log_action("experimentation_started", {"user_id": user_id})
        
        # Get current experiments
        active_experiments = self._get_active_experiments(db, user_id)
        completed_experiments = self._get_completed_experiments(db, user_id)
        
        # Analyze completed experiments
        experiment_results = self._analyze_experiment_results(completed_experiments, db)
        
        # Design new experiments
        new_experiments = self._design_new_experiments(
            strategy_recommendations,
            active_experiments,
            experiment_results,
            db,
            user_id
        )
        
        # Update active experiments
        updated_experiments = self._update_active_experiments(active_experiments, db)
        
        # Generate experiment insights
        insights = self._generate_experiment_insights({
            "active_experiments": updated_experiments,
            "completed_results": experiment_results,
            "new_experiments": new_experiments
        })
        
        experimentation_results = {
            "experimentation_timestamp": datetime.now().isoformat(),
            "active_experiments": updated_experiments,
            "completed_experiments": experiment_results,
            "new_experiment_proposals": new_experiments,
            "insights": insights,
            "recommendations": self._generate_experimentation_recommendations(
                experiment_results, updated_experiments, new_experiments
            ),
            "experiment_calendar": self._create_experiment_calendar(
                updated_experiments, new_experiments
            )
        }
        
        self.log_action("experimentation_completed", {
            "active_experiments": len(updated_experiments),
            "new_proposals": len(new_experiments),
            "completed_analyzed": len(experiment_results)
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
        import json
        
        # Convert any NumPy types to Python native types for JSON serialization
        safe_data = self._convert_numpy_to_python(data)
        
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"""
            Analyze the following experimentation data and provide insights:
            
            Active Experiments: {json.dumps(safe_data['active_experiments'], indent=2)}
            
            Completed Results: {json.dumps(safe_data['completed_results'], indent=2)}
            
            New Proposals: {json.dumps([{
                    "name": exp["name"],
                    "type": exp["type"],
                    "hypothesis": exp["hypothesis"],
                    "duration": exp["duration_days"]
                } for exp in safe_data['new_experiments']], indent=2)}
            
            Provide insights on:
            1. Key learnings from completed experiments
            2. Current experiment performance and early indicators
            3. Recommendations for new experiment priorities
            4. Overall experimentation strategy effectiveness
            5. Risk management considerations
            """}
        ]
        
        response = self.call_llm(messages)
        
        if response.get("error"):
            self.logger.error(f"LLM Error: {response.get('error')}")
            return {"error": response.get("content", "Failed to generate experiments")}
        
        content = response.get("content", "")
        if content:
            try:
                return json.loads(content)
            except:
                return {"experiments": content}
        else:
            return {"error": "No content in response"}
    
    def _generate_experimentation_recommendations(self, results: List[Dict], 
                                                   active: List[Dict], 
                                                   proposals: List[Dict]) -> List[Dict[str, Any]]:
        """Generate recommendations for experimentation strategy"""
        recommendations = []
        
        # Based on completed experiments
        successful_experiments = [r for r in results if r["revenue_lift"] > 0.05 and r["statistically_significant"]]
        if successful_experiments:
            recommendations.append({
                "priority": "high",
                "category": "scale_success",
                "recommendation": "Roll out successful experiment results to all customers",
                "experiments": [exp["name"] for exp in successful_experiments],
                "expected_impact": f"{np.mean([exp['revenue_lift'] for exp in successful_experiments])*100:.1f}% revenue increase"
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
                "timeline": "Within next week"
            })
        
        return recommendations
    
    def _create_experiment_calendar(self, active: List[Dict], proposals: List[Dict]) -> List[Dict[str, Any]]:
        """Create experiment timeline and calendar"""
        calendar = []
        
        # Add active experiments
        for exp in active:
            start_date = datetime.fromisoformat(exp["started_at"].replace('Z', '+00:00'))
            calendar.append({
                "experiment": exp["name"],
                "type": exp["type"],
                "phase": "active",
                "start_date": start_date.isoformat(),
                "end_date": (start_date + timedelta(days=14)).isoformat(),
                "status": exp["status"]
            })
        
        # Add proposed experiments
        next_start = datetime.now() + timedelta(days=3)  # Start in 3 days
        for exp in proposals:
            calendar.append({
                "experiment": exp["name"],
                "type": exp["type"],
                "phase": "proposed",
                "start_date": next_start.isoformat(),
                "end_date": (next_start + timedelta(days=exp["duration_days"])).isoformat(),
                "status": "pending_approval"
            })
            next_start += timedelta(days=7)  # Stagger starts by a week
        
        return sorted(calendar, key=lambda x: x["start_date"])
    
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
