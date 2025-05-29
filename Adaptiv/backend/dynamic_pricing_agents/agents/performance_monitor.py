"""
Performance Monitor Agent - Tracks and analyzes the impact of pricing changes
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import numpy as np
from ..base_agent import BaseAgent


class PerformanceMonitorAgent(BaseAgent):
    """Agent responsible for monitoring and analyzing pricing performance"""
    
    def __init__(self):
        super().__init__("PerformanceMonitorAgent", model="gpt-4o-mini")
        
    def get_system_prompt(self) -> str:
        return """You are a Performance Monitoring Agent for dynamic pricing. Your role is to:
        1. Track the real-time impact of price changes on sales and revenue
        2. Identify successful and unsuccessful pricing decisions
        3. Detect anomalies and unexpected market responses
        4. Provide early warning signals for pricing issues
        5. Generate performance reports and insights
        
        Focus on actionable insights and continuous improvement."""
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor and analyze pricing performance"""
        db = context['db']
        user_id = context['user_id']
        active_strategies = context.get('active_strategies', [])
        
        self.log_action("performance_monitoring_started", {"user_id": user_id})
        
        # Collect performance data
        current_performance = self._collect_current_performance(db, user_id)
        historical_baseline = self._establish_baseline(db, user_id)
        active_changes = self._track_active_price_changes(db, user_id)
        
        # Analyze performance
        performance_metrics = self._calculate_performance_metrics(
            current_performance, 
            historical_baseline
        )
        change_impact = self._analyze_change_impact(active_changes, current_performance)
        anomalies = self._detect_anomalies(current_performance, historical_baseline)
        
        # Generate insights and alerts
        insights = self._generate_performance_insights({
            "metrics": performance_metrics,
            "change_impact": change_impact,
            "anomalies": anomalies,
            "current_performance": current_performance
        })
        
        alerts = self._generate_alerts(performance_metrics, anomalies)
        
        monitoring_results = {
            "monitoring_timestamp": datetime.now().isoformat(),
            "performance_metrics": performance_metrics,
            "active_price_changes": active_changes,
            "change_impact_analysis": change_impact,
            "anomalies_detected": anomalies,
            "insights": insights,
            "alerts": alerts,
            "recommendations": self._generate_recommendations(
                performance_metrics, change_impact, anomalies
            )
        }
        
        self.log_action("performance_monitoring_completed", {
            "metrics_calculated": len(performance_metrics),
            "anomalies_detected": len(anomalies),
            "alerts_generated": len(alerts)
        })
        
        return monitoring_results
    
    def _collect_current_performance(self, db, user_id: int) -> Dict[str, Any]:
        """Collect current performance data"""
        import models
        
        # Get recent orders (last 7 days)
        recent_orders = db.query(models.Order).filter(
            models.Order.user_id == user_id,
            models.Order.order_date >= datetime.now() - timedelta(days=7)
        ).all()
        
        # Get current item prices
        items = db.query(models.Item).filter(models.Item.user_id == user_id).all()
        
        # Calculate current metrics
        daily_metrics = self._calculate_daily_metrics(recent_orders)
        item_performance = self._calculate_item_performance(recent_orders, items)
        
        return {
            "period": {
                "start": (datetime.now() - timedelta(days=7)).isoformat(),
                "end": datetime.now().isoformat()
            },
            "daily_metrics": daily_metrics,
            "item_performance": item_performance,
            "summary": {
                "total_revenue": sum(order.total_amount for order in recent_orders),
                "total_orders": len(recent_orders),
                "unique_items_sold": len(set(
                    item.item_id for order in recent_orders 
                    for item in db.query(models.OrderItem).filter(models.OrderItem.order_id == order.id).all()
                ))
            }
        }
    
    def _establish_baseline(self, db, user_id: int) -> Dict[str, Any]:
        """Establish historical baseline for comparison"""
        import models
        
        # Get historical orders (8-28 days ago)
        baseline_orders = db.query(models.Order).filter(
            models.Order.user_id == user_id,
            models.Order.order_date >= datetime.now() - timedelta(days=28),
            models.Order.order_date < datetime.now() - timedelta(days=7)
        ).all()
        
        # Calculate baseline metrics
        daily_metrics = self._calculate_daily_metrics(baseline_orders)
        
        return {
            "period": {
                "start": (datetime.now() - timedelta(days=28)).isoformat(),
                "end": (datetime.now() - timedelta(days=7)).isoformat()
            },
            "daily_metrics": daily_metrics,
            "summary": {
                "avg_daily_revenue": np.mean([m["revenue"] for m in daily_metrics]) if daily_metrics else 0,
                "avg_daily_orders": np.mean([m["orders"] for m in daily_metrics]) if daily_metrics else 0
            }
        }
    
    def _track_active_price_changes(self, db, user_id: int) -> List[Dict[str, Any]]:
        """Track recently implemented price changes"""
        import models
        
        # Get price changes from last 30 days
        recent_changes = db.query(models.PriceHistory).join(
            models.Item
        ).filter(
            models.Item.user_id == user_id,
            models.PriceHistory.changed_at >= datetime.now() - timedelta(days=30)
        ).all()
        
        active_changes = []
        for change in recent_changes:
            item = db.query(models.Item).filter(models.Item.id == change.item_id).first()
            if item:
                active_changes.append({
                    "item_id": change.item_id,
                    "item_name": item.name,
                    "old_price": float(change.previous_price),
                    "new_price": float(change.new_price),
                    "change_percent": (change.new_price - change.previous_price) / change.previous_price * 100,
                    "changed_at": change.changed_at.isoformat(),
                    "days_active": (datetime.now() - change.changed_at).days,
                    "reason": change.change_reason if hasattr(change, 'change_reason') else None
                })
        
        return sorted(active_changes, key=lambda x: x["changed_at"], reverse=True)
    
    def _calculate_performance_metrics(self, current: Dict, baseline: Dict) -> Dict[str, Any]:
        """Calculate key performance metrics"""
        current_summary = current["summary"]
        baseline_summary = baseline["summary"]
        
        # Revenue metrics
        current_daily_avg = current_summary["total_revenue"] / 7
        baseline_daily_avg = baseline_summary["avg_daily_revenue"]
        revenue_change = (current_daily_avg - baseline_daily_avg) / baseline_daily_avg * 100 if baseline_daily_avg > 0 else 0
        
        # Order metrics
        current_order_avg = current_summary["total_orders"] / 7
        baseline_order_avg = baseline_summary["avg_daily_orders"]
        order_change = (current_order_avg - baseline_order_avg) / baseline_order_avg * 100 if baseline_order_avg > 0 else 0
        
        # Average order value
        current_aov = current_summary["total_revenue"] / current_summary["total_orders"] if current_summary["total_orders"] > 0 else 0
        baseline_aov = baseline_daily_avg / baseline_order_avg if baseline_order_avg > 0 else 0
        aov_change = (current_aov - baseline_aov) / baseline_aov * 100 if baseline_aov > 0 else 0
        
        return {
            "revenue": {
                "current_daily_avg": current_daily_avg,
                "baseline_daily_avg": baseline_daily_avg,
                "change_percent": revenue_change,
                "trend": self._determine_trend(revenue_change)
            },
            "orders": {
                "current_daily_avg": current_order_avg,
                "baseline_daily_avg": baseline_order_avg,
                "change_percent": order_change,
                "trend": self._determine_trend(order_change)
            },
            "average_order_value": {
                "current": current_aov,
                "baseline": baseline_aov,
                "change_percent": aov_change,
                "trend": self._determine_trend(aov_change)
            },
            "overall_health": self._calculate_overall_health(revenue_change, order_change, aov_change)
        }
    
    def _analyze_change_impact(self, changes: List[Dict], performance: Dict) -> List[Dict[str, Any]]:
        """Analyze the impact of specific price changes"""
        item_performance = performance.get("item_performance", {})
        
        impact_analysis = []
        for change in changes:
            item_id = change["item_id"]
            item_perf = item_performance.get(str(item_id), {})
            
            if item_perf:
                # Calculate impact metrics
                revenue_impact = item_perf.get("revenue_trend", 0)
                quantity_impact = item_perf.get("quantity_trend", 0)
                
                # Estimate elasticity from observed changes
                if change["change_percent"] != 0:
                    implied_elasticity = quantity_impact / change["change_percent"]
                else:
                    implied_elasticity = 0
                
                impact = {
                    "item_id": item_id,
                    "item_name": change["item_name"],
                    "price_change": change["change_percent"],
                    "revenue_impact": revenue_impact,
                    "quantity_impact": quantity_impact,
                    "implied_elasticity": implied_elasticity,
                    "success_score": self._calculate_success_score(
                        revenue_impact, quantity_impact, change["change_percent"]
                    ),
                    "status": self._determine_change_status(revenue_impact, quantity_impact)
                }
                impact_analysis.append(impact)
        
        return sorted(impact_analysis, key=lambda x: x["success_score"], reverse=True)
    
    def _detect_anomalies(self, current: Dict, baseline: Dict) -> List[Dict[str, Any]]:
        """Detect anomalies in performance data"""
        anomalies = []
        
        # Compare daily patterns
        current_daily = current["daily_metrics"]
        baseline_daily = baseline["daily_metrics"]
        
        if current_daily and baseline_daily:
            # Calculate baseline statistics
            baseline_revenues = [d["revenue"] for d in baseline_daily]
            baseline_mean = np.mean(baseline_revenues)
            baseline_std = np.std(baseline_revenues)
            
            # Check for anomalies in recent days
            for day in current_daily:
                z_score = (day["revenue"] - baseline_mean) / baseline_std if baseline_std > 0 else 0
                
                if abs(z_score) > 2:  # 2 standard deviations
                    anomalies.append({
                        "type": "daily_revenue_anomaly",
                        "date": day["date"],
                        "value": day["revenue"],
                        "expected_range": [
                            baseline_mean - 2 * baseline_std,
                            baseline_mean + 2 * baseline_std
                        ],
                        "severity": "high" if abs(z_score) > 3 else "medium",
                        "direction": "above" if z_score > 0 else "below"
                    })
        
        # Check for sudden drops in specific items
        item_performance = current.get("item_performance", {})
        for item_id, perf in item_performance.items():
            if perf.get("quantity_trend", 0) < -50:  # 50% drop
                anomalies.append({
                    "type": "item_sales_drop",
                    "item_id": item_id,
                    "quantity_change": perf["quantity_trend"],
                    "severity": "high",
                    "action_required": True
                })
        
        return anomalies
    
    def _generate_performance_insights(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from performance data"""
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"""
            Analyze the following performance data and provide insights:
            
            Performance Metrics: {json.dumps(data['metrics'], indent=2)}
            
            Price Change Impact: {json.dumps(data['change_impact'][:5], indent=2)}  # Top 5
            
            Anomalies Detected: {json.dumps(data['anomalies'], indent=2)}
            
            Provide insights on:
            1. Overall performance assessment
            2. Most and least successful price changes
            3. Unexpected market responses
            4. Opportunities for improvement
            5. Risk factors to monitor
            """}
        ]
        
        response = self.call_llm(messages)
        
        if response.get("error"):
            self.logger.error(f"LLM Error: {response.get('error')}")
            return {"error": response.get("content", "Failed to generate performance insights")}
        
        content = response.get("content", "")
        if content:
            try:
                return json.loads(content)
            except:
                return {"insights": content}
        else:
            return {"error": "No content in response"}
    
    def _generate_alerts(self, metrics: Dict, anomalies: List[Dict]) -> List[Dict[str, Any]]:
        """Generate alerts for significant issues"""
        alerts = []
        
        # Revenue alerts
        revenue_change = metrics["revenue"]["change_percent"]
        if revenue_change < -10:
            alerts.append({
                "type": "revenue_decline",
                "severity": "high",
                "message": f"Revenue has declined by {abs(revenue_change):.1f}% compared to baseline",
                "action": "Review recent price changes and market conditions"
            })
        
        # Order volume alerts
        order_change = metrics["orders"]["change_percent"]
        if order_change < -20:
            alerts.append({
                "type": "order_volume_drop",
                "severity": "high",
                "message": f"Order volume has dropped by {abs(order_change):.1f}%",
                "action": "Consider promotional pricing or marketing initiatives"
            })
        
        # Anomaly alerts
        high_severity_anomalies = [a for a in anomalies if a.get("severity") == "high"]
        if high_severity_anomalies:
            alerts.append({
                "type": "anomalies_detected",
                "severity": "medium",
                "message": f"{len(high_severity_anomalies)} high-severity anomalies detected",
                "action": "Review anomaly details and investigate root causes"
            })
        
        return alerts
    
    def _generate_recommendations(self, metrics: Dict, impact: List[Dict], anomalies: List[Dict]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Based on overall performance
        if metrics["revenue"]["change_percent"] < 0:
            recommendations.append({
                "priority": "high",
                "category": "revenue_recovery",
                "recommendation": "Consider rolling back recent price increases on elastic items",
                "expected_impact": "Recover 50-75% of lost revenue within 1 week"
            })
        
        # Based on successful changes
        successful_changes = [i for i in impact if i["success_score"] > 0.7]
        if successful_changes:
            recommendations.append({
                "priority": "medium",
                "category": "expand_success",
                "recommendation": f"Apply similar pricing strategy to related items",
                "items": [c["item_name"] for c in successful_changes[:3]],
                "expected_impact": "5-10% revenue increase"
            })
        
        # Based on anomalies
        if any(a["type"] == "item_sales_drop" for a in anomalies):
            recommendations.append({
                "priority": "high",
                "category": "urgent_action",
                "recommendation": "Investigate and address sudden sales drops",
                "items": [a["item_id"] for a in anomalies if a["type"] == "item_sales_drop"],
                "expected_impact": "Prevent further revenue loss"
            })
        
        return recommendations
    
    # Helper methods
    def _calculate_daily_metrics(self, orders) -> List[Dict[str, Any]]:
        """Calculate metrics by day"""
        import models
        from collections import defaultdict
        
        daily_data = defaultdict(lambda: {"revenue": 0, "orders": 0, "items": 0})
        
        for order in orders:
            date = order.order_date.date().isoformat()
            daily_data[date]["revenue"] += float(order.total_amount)
            daily_data[date]["orders"] += 1
        
        return [
            {
                "date": date,
                "revenue": data["revenue"],
                "orders": data["orders"],
                "avg_order_value": data["revenue"] / data["orders"] if data["orders"] > 0 else 0
            }
            for date, data in sorted(daily_data.items())
        ]
    
    def _calculate_item_performance(self, orders, items) -> Dict[int, Dict[str, Any]]:
        """Calculate performance metrics by item"""
        import models
        from collections import defaultdict
        
        item_data = defaultdict(lambda: {"revenue": 0, "quantity": 0})
        
        for order in orders:
            order_items = order.order_items  # Assuming relationship is set up
            for oi in order_items:
                item_data[oi.item_id]["revenue"] += float(oi.price * oi.quantity)
                item_data[oi.item_id]["quantity"] += oi.quantity
        
        # Calculate trends (simplified - would compare to baseline in production)
        performance = {}
        for item_id, data in item_data.items():
            performance[str(item_id)] = {
                "revenue": data["revenue"],
                "quantity": data["quantity"],
                "revenue_trend": 5.0,  # Placeholder - would calculate actual trend
                "quantity_trend": -2.0  # Placeholder - would calculate actual trend
            }
        
        return performance
    
    def _determine_trend(self, change_percent: float) -> str:
        """Determine trend direction and strength"""
        if change_percent > 10:
            return "strong_growth"
        elif change_percent > 3:
            return "moderate_growth"
        elif change_percent > -3:
            return "stable"
        elif change_percent > -10:
            return "moderate_decline"
        else:
            return "strong_decline"
    
    def _calculate_overall_health(self, revenue_change: float, order_change: float, aov_change: float) -> str:
        """Calculate overall business health"""
        health_score = (revenue_change * 0.5 + order_change * 0.3 + aov_change * 0.2)
        
        if health_score > 5:
            return "excellent"
        elif health_score > 0:
            return "good"
        elif health_score > -5:
            return "fair"
        else:
            return "poor"
    
    def _calculate_success_score(self, revenue_impact: float, quantity_impact: float, price_change: float) -> float:
        """Calculate success score for a price change"""
        # Revenue increase is good
        revenue_score = min(revenue_impact / 10, 1.0) if revenue_impact > 0 else 0
        
        # Quantity decrease should be less than price increase (for profitability)
        if price_change > 0:
            elasticity_score = 1.0 if abs(quantity_impact) < price_change else 0.5
        else:
            elasticity_score = 1.0 if quantity_impact > abs(price_change) else 0.5
        
        return (revenue_score * 0.7 + elasticity_score * 0.3)
    
    def _determine_change_status(self, revenue_impact: float, quantity_impact: float) -> str:
        """Determine the status of a price change"""
        if revenue_impact > 5 and quantity_impact > -10:
            return "highly_successful"
        elif revenue_impact > 0:
            return "successful"
        elif revenue_impact > -5:
            return "neutral"
        else:
            return "unsuccessful"
