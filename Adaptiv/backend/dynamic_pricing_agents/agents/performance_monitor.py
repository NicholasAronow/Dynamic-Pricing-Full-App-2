"""
Performance Monitor Agent - Tracks and analyzes the impact of pricing changes
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import numpy as np
from sqlalchemy import desc
from sqlalchemy.orm import Session
from models import AgentMemory, PerformanceBaseline, PerformanceAnomaly, PricingDecision
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
        """Monitor and analyze pricing performance with memory integration"""
        db = context['db']
        user_id = context['user_id']
        active_strategies = context.get('active_strategies', [])
        
        self.log_action("performance_monitoring_started", {"user_id": user_id})
        
        # Retrieve memory context
        memory_context = self.get_memory_context(db, user_id, 
                                             memory_types=['performance_baseline', 'performance_anomaly',
                                                          'pricing_decision', 'performance_trend'])
        
        # Get historical performance snapshots
        historical_snapshots = self._get_performance_history(db, user_id)
        
        # Collect performance data
        current_performance = self._collect_current_performance(db, user_id)
        historical_baseline = self._establish_baseline_with_memory(db, user_id, memory_context)
        active_changes = self._track_active_price_changes_with_memory(db, user_id, memory_context)
        
        # Analyze performance
        performance_metrics = self._calculate_performance_metrics_with_memory(
            current_performance, 
            historical_baseline,
            historical_snapshots
        )
        change_impact = self._analyze_change_impact_with_memory(active_changes, current_performance, memory_context)
        anomalies = self._detect_anomalies_with_memory(current_performance, historical_baseline, memory_context)
        
        # Save performance baseline and anomalies to memory
        self._save_performance_snapshot(db, user_id, current_performance, performance_metrics)
        self._track_anomalies(db, user_id, anomalies)
        
        # Generate insights and alerts with memory
        insights = self._generate_performance_insights_with_memory({
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
    
    def _establish_baseline_with_memory(self, db, user_id: int, memory_context: Dict[str, Any]) -> Dict[str, Any]:
        """Establish historical baseline using both database and memory"""
        # Get baseline from database
        baseline = self._establish_baseline(db, user_id)
        
        # Enhance with memory data if available
        baseline_memories = memory_context.get('performance_baseline', [])
        if baseline_memories:
            # Get the most recent baseline memory
            recent_baseline = baseline_memories[0].get('content', {})
            
            # Compare with database baseline and use the most comprehensive data
            if recent_baseline:
                # Combine data, preferring database values but filling gaps from memory
                for period in ['daily', 'weekly', 'monthly']:
                    if period not in baseline and period in recent_baseline:
                        baseline[period] = recent_baseline[period]
                    elif period in baseline and period in recent_baseline:
                        # Fill in any missing metrics
                        for metric in ['revenue', 'orders', 'aov']:
                            if metric not in baseline[period] and metric in recent_baseline[period]:
                                baseline[period][metric] = recent_baseline[period][metric]
        
        return baseline
    
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
                    "change_percent": (change.new_price - change.previous_price) / change.previous_price * 100 if change.previous_price > 0 else 0,
                    "changed_at": change.changed_at.isoformat(),
                    "days_active": (datetime.now() - change.changed_at).days,
                    "reason": change.change_reason if hasattr(change, 'change_reason') else None
                })
        
        return sorted(active_changes, key=lambda x: x["changed_at"], reverse=True)
    
    def _track_active_price_changes_with_memory(self, db, user_id: int, memory_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Track recently implemented price changes with enhanced context from memory"""
        import models
        
        # Get basic active price changes
        active_changes = self._track_active_price_changes(db, user_id)
        
        # Enhance with pricing decisions from memory if available
        pricing_decisions = memory_context.get('pricing_decision', [])
        
        # If we have pricing decisions in memory, enhance our active changes with context
        if pricing_decisions:
            for change in active_changes:
                for decision in pricing_decisions:
                    # Match decisions to price changes by item_id and approximate time
                    if (str(change['item_id']) == str(decision.get('item_id')) and
                        self._dates_are_close(change['changed_at'], decision.get('decision_date', ''))):
                        
                        # Enhance the change with additional context
                        change['strategy'] = decision.get('strategy')
                        change['expected_impact'] = decision.get('expected_impact')
                        change['confidence'] = decision.get('confidence')
                        change['rationale'] = decision.get('rationale')
                        break
        
        self.logger.info(f"Found {len(active_changes)} active price changes with memory context")
        return active_changes
    
    def _dates_are_close(self, date_str1: str, date_str2: str, max_days: int = 2) -> bool:
        """Helper to check if two date strings are within max_days of each other"""
        try:
            date1 = datetime.fromisoformat(date_str1.replace('Z', '+00:00'))
            date2 = datetime.fromisoformat(date_str2.replace('Z', '+00:00'))
            diff = abs((date1 - date2).days)
            return diff <= max_days
        except (ValueError, TypeError):
            return False
    
    def _calculate_performance_metrics(self, current: Dict, baseline: Dict) -> Dict[str, Any]:
        """Calculate key performance metrics"""
        current_summary = current["summary"]
        baseline_summary = baseline["summary"]
        
        # Revenue metrics
        # Ensure we don't divide by zero when calculating daily averages
        days_in_period = 7  # Default period of 7 days
        current_daily_avg = current_summary["total_revenue"] / days_in_period
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
        
    def _calculate_performance_metrics_with_memory(self, current: Dict, baseline: Dict, historical_snapshots: List) -> Dict[str, Any]:
        """Calculate key performance metrics with historical context from memory"""
        # Get basic metrics
        metrics = self._calculate_performance_metrics(current, baseline)
        
        # Enhance with historical trends if we have snapshots
        if historical_snapshots:
            # Extract metrics from historical snapshots
            historical_revenue = []
            historical_orders = []
            historical_aov = []
            
            for snapshot in historical_snapshots:
                if hasattr(snapshot, 'data') and isinstance(snapshot.data, dict):
                    snapshot_data = snapshot.data
                    if 'revenue' in snapshot_data:
                        historical_revenue.append(snapshot_data['revenue'].get('current_daily_avg', 0))
                    if 'orders' in snapshot_data:
                        historical_orders.append(snapshot_data['orders'].get('current_daily_avg', 0))
                    if 'average_order_value' in snapshot_data:
                        historical_aov.append(snapshot_data['average_order_value'].get('current', 0))
            
            # Calculate longer-term trends if we have enough data
            if len(historical_revenue) >= 3:
                metrics['revenue']['historical_trend'] = self._calculate_historical_trend(historical_revenue)
                metrics['revenue']['trend_consistency'] = self._calculate_trend_consistency(historical_revenue)
            
            if len(historical_orders) >= 3:
                metrics['orders']['historical_trend'] = self._calculate_historical_trend(historical_orders)
                metrics['orders']['trend_consistency'] = self._calculate_trend_consistency(historical_orders)
            
            if len(historical_aov) >= 3:
                metrics['average_order_value']['historical_trend'] = self._calculate_historical_trend(historical_aov)
                metrics['average_order_value']['trend_consistency'] = self._calculate_trend_consistency(historical_aov)
        
        return metrics
    
    def _calculate_historical_trend(self, values: List[float]) -> str:
        """Calculate the trend direction from a list of historical values"""
        if not values or len(values) < 2:
            return "stable"
            
        # Simple linear regression to determine trend
        x = list(range(len(values)))
        slope, _, _, _, _ = stats.linregress(x, values)
        
        if abs(slope) < 0.01 * np.mean(values):
            return "stable"
        elif slope > 0:
            return "increasing"
        else:
            return "decreasing"
    
    def _calculate_trend_consistency(self, values: List[float]) -> float:
        """Calculate how consistent a trend has been (0-1 scale)"""
        if not values or len(values) < 3:
            return 0.5
            
        # Calculate standard deviation of percentage changes
        changes = []
        for i in range(1, len(values)):
            if values[i-1] > 0:
                changes.append((values[i] - values[i-1]) / values[i-1])
            
        if not changes:
            return 0.5
            
        # Lower standard deviation means more consistent trend
        std_dev = np.std(changes)
        consistency = 1.0 / (1.0 + 5.0 * std_dev)  # Scale to 0-1
        return min(max(consistency, 0), 1)  # Ensure within bounds
    
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
        
    def _analyze_change_impact_with_memory(self, changes: List[Dict], performance: Dict, memory_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze the impact of specific price changes with memory context"""
        # Get basic impact analysis
        impact_analysis = self._analyze_change_impact(changes, performance)
        
        # Get historical pricing decisions from memory
        pricing_decisions = memory_context.get('pricing_decision', [])
        
        # Enhance impact analysis with memory context
        for impact in impact_analysis:
            item_id = impact['item_id']
            
            # Look for previous decisions for this item
            previous_decisions = []
            for decision in pricing_decisions:
                if str(decision.get('item_id')) == str(item_id):
                    previous_decisions.append(decision)
            
            if previous_decisions:
                # Sort by decision date
                previous_decisions.sort(key=lambda x: x.get('decision_date', ''), reverse=True)
                
                # Add historical context
                impact['previous_changes'] = len(previous_decisions)
                impact['historical_success'] = self._calculate_historical_success(previous_decisions)
                impact['price_change_frequency'] = self._calculate_price_change_frequency(previous_decisions)
                
                # Compare current outcome with expected outcome
                if 'expected_impact' in changes and isinstance(changes.get('expected_impact'), dict):
                    expected = changes.get('expected_impact', {})
                    impact['expectation_accuracy'] = self._calculate_expectation_accuracy(
                        expected.get('revenue', 0), 
                        expected.get('quantity', 0),
                        impact['revenue_impact'],
                        impact['quantity_impact']
                    )
        
        return impact_analysis
    
    def _calculate_historical_success(self, decisions: List[Dict]) -> float:
        """Calculate average success score from historical decisions"""
        success_scores = []
        for decision in decisions:
            if 'success_score' in decision and isinstance(decision['success_score'], (int, float)):
                success_scores.append(decision['success_score'])
        
        if success_scores:
            return sum(success_scores) / len(success_scores)
        return 0.5  # Neutral score if no history
    
    def _calculate_price_change_frequency(self, decisions: List[Dict]) -> str:
        """Determine how frequently prices change for this item"""
        if len(decisions) >= 5:
            return "very_frequent"
        elif len(decisions) >= 3:
            return "frequent"
        elif len(decisions) >= 1:
            return "occasional"
        return "rare"
    
    def _calculate_expectation_accuracy(self, expected_revenue: float, expected_quantity: float, 
                                      actual_revenue: float, actual_quantity: float) -> float:
        """Calculate how accurately previous expectations matched reality"""
        if expected_revenue == 0 and expected_quantity == 0:
            return 0.5  # No expectations set
            
        revenue_accuracy = 1.0 - min(abs(actual_revenue - expected_revenue) / max(abs(expected_revenue), 0.01), 1.0)
        quantity_accuracy = 1.0 - min(abs(actual_quantity - expected_quantity) / max(abs(expected_quantity), 0.01), 1.0)
        
        return (revenue_accuracy + quantity_accuracy) / 2.0
    
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
    
    def _detect_anomalies_with_memory(self, current: Dict, baseline: Dict, memory_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect anomalies in performance data with memory context"""
        # Get basic anomalies
        anomalies = self._detect_anomalies(current, baseline)
        
        # Get previously identified anomalies from memory
        previous_anomalies = memory_context.get('performance_anomaly', [])
        
        # Categorize anomalies as new, recurring, or worsening
        categorized_anomalies = []
        for anomaly in anomalies:
            anomaly_copy = anomaly.copy()
            anomaly_copy['is_new'] = True
            anomaly_copy['is_recurring'] = False
            anomaly_copy['is_worsening'] = False
            
            # Check if this is similar to a previous anomaly
            for prev in previous_anomalies:
                if self._anomalies_are_similar(anomaly, prev):
                    anomaly_copy['is_new'] = False
                    anomaly_copy['is_recurring'] = True
                    anomaly_copy['first_detected'] = prev.get('detection_date', '')
                    
                    # Check if severity is increasing
                    if (anomaly.get('severity') == 'high' and prev.get('severity') != 'high') or \
                       (self._anomaly_magnitude(anomaly) > self._anomaly_magnitude(prev)):
                        anomaly_copy['is_worsening'] = True
                    
                    break
            
            categorized_anomalies.append(anomaly_copy)
        
        # Add historical context to recurring patterns
        if previous_anomalies:
            # Check for patterns by day of week
            day_patterns = self._detect_day_of_week_patterns(previous_anomalies)
            if day_patterns:
                for pattern in day_patterns:
                    categorized_anomalies.append({
                        'type': 'day_of_week_pattern',
                        'day': pattern['day'],
                        'pattern_type': pattern['type'],
                        'confidence': pattern['confidence'],
                        'is_new': False,
                        'is_pattern': True
                    })
            
            # Check for seasonal patterns
            seasonal_patterns = self._detect_seasonal_patterns_from_anomalies(previous_anomalies)
            if seasonal_patterns:
                for pattern in seasonal_patterns:
                    categorized_anomalies.append({
                        'type': 'seasonal_pattern',
                        'season': pattern['season'],
                        'pattern_type': pattern['type'],
                        'confidence': pattern['confidence'],
                        'is_new': False,
                        'is_pattern': True
                    })
        
        return categorized_anomalies
    
    def _anomalies_are_similar(self, anomaly1: Dict[str, Any], anomaly2: Dict[str, Any]) -> bool:
        """Check if two anomalies are similar enough to be considered the same issue"""
        # If types don't match, they're not similar
        if anomaly1.get('type') != anomaly2.get('type'):
            return False
            
        # For daily revenue anomalies
        if anomaly1.get('type') == 'daily_revenue_anomaly':
            # Consider day of week instead of exact date
            try:
                date1 = datetime.fromisoformat(anomaly1.get('date', '').replace('Z', '+00:00'))
                date2 = datetime.fromisoformat(anomaly2.get('date', '').replace('Z', '+00:00'))
                return date1.weekday() == date2.weekday() and anomaly1.get('direction') == anomaly2.get('direction')
            except (ValueError, TypeError):
                return False
                
        # For item sales drops
        elif anomaly1.get('type') == 'item_sales_drop':
            return str(anomaly1.get('item_id')) == str(anomaly2.get('item_id'))
            
        return False
    
    def _anomaly_magnitude(self, anomaly: Dict[str, Any]) -> float:
        """Calculate a numerical magnitude for an anomaly to compare severity"""
        if anomaly.get('type') == 'daily_revenue_anomaly':
            # Calculate standard deviations from mean
            expected_mean = sum(anomaly.get('expected_range', [0, 0])) / 2
            value = anomaly.get('value', expected_mean)
            return abs(value - expected_mean) / max(expected_mean, 1)
            
        elif anomaly.get('type') == 'item_sales_drop':
            return abs(anomaly.get('quantity_change', 0)) / 100
            
        return 0.0
    
    def _detect_day_of_week_patterns(self, anomalies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect patterns in anomalies by day of week"""
        # Count anomalies by day of week
        day_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}  # Mon to Sun
        total_anomalies = 0
        
        for anomaly in anomalies:
            if anomaly.get('type') == 'daily_revenue_anomaly' and 'date' in anomaly:
                try:
                    date = datetime.fromisoformat(anomaly.get('date', '').replace('Z', '+00:00'))
                    day_counts[date.weekday()] += 1
                    total_anomalies += 1
                except (ValueError, TypeError):
                    pass
        
        if total_anomalies < 3:  # Not enough data
            return []
            
        # Detect patterns
        patterns = []
        avg_count = total_anomalies / 7
        for day, count in day_counts.items():
            if count >= 3 and count > 2 * avg_count:  # At least 3 occurrences and 2x average
                day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day]
                patterns.append({
                    'day': day_name,
                    'type': 'high_anomaly_day',
                    'confidence': min(count / max(avg_count, 1), 1.0)
                })
        
        return patterns
    
    def _detect_seasonal_patterns_from_anomalies(self, anomalies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect seasonal patterns in anomalies"""
        # Group anomalies by month
        month_counts = {i: 0 for i in range(1, 13)}
        total_anomalies = 0
        
        for anomaly in anomalies:
            if 'detection_date' in anomaly:
                try:
                    date = datetime.fromisoformat(anomaly.get('detection_date', '').replace('Z', '+00:00'))
                    month_counts[date.month] += 1
                    total_anomalies += 1
                except (ValueError, TypeError):
                    pass
        
        if total_anomalies < 3:  # Not enough data
            return []
            
        # Detect seasonal patterns
        patterns = []
        avg_count = total_anomalies / 12
        
        # Check summer (Jun-Aug)
        summer_count = month_counts[6] + month_counts[7] + month_counts[8]
        if summer_count >= 3 and summer_count > 1.5 * avg_count * 3:
            patterns.append({
                'season': 'Summer',
                'type': 'high_anomaly_season',
                'confidence': min(summer_count / (avg_count * 3), 1.0)
            })
            
        # Check winter (Dec-Feb)
        winter_count = month_counts[12] + month_counts[1] + month_counts[2]
        if winter_count >= 3 and winter_count > 1.5 * avg_count * 3:
            patterns.append({
                'season': 'Winter',
                'type': 'high_anomaly_season',
                'confidence': min(winter_count / (avg_count * 3), 1.0)
            })
            
        return patterns
    
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
    
    def _generate_performance_insights_with_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from performance data with historical context from memory"""
        # Enhance the data with memory contexts if available
        if 'memory_context' in data and isinstance(data['memory_context'], dict):
            memory_context = data['memory_context']
            
            # Extract previous insights to provide context
            previous_insights = []
            if 'performance_trend' in memory_context:
                for trend in memory_context['performance_trend']:
                    if isinstance(trend, dict) and 'insights' in trend:
                        previous_insights.append(trend['insights'])
            
            # Extract recurring patterns from anomalies
            recurring_patterns = []
            if 'performance_anomaly' in memory_context:
                pattern_count = {}
                for anomaly in memory_context['performance_anomaly']:
                    if isinstance(anomaly, dict):
                        anomaly_type = anomaly.get('type', '')
                        if anomaly_type:
                            if anomaly_type not in pattern_count:
                                pattern_count[anomaly_type] = 0
                            pattern_count[anomaly_type] += 1
                
                # Identify recurring patterns (appearing 3+ times)
                for pattern_type, count in pattern_count.items():
                    if count >= 3:
                        recurring_patterns.append({
                            'type': pattern_type,
                            'frequency': count,
                            'recurring': True
                        })
            
            # Add memory context to the data
            data['previous_insights'] = previous_insights[-3:] if len(previous_insights) > 3 else previous_insights  # Last 3
            data['recurring_patterns'] = recurring_patterns
        
        # Add temporal context
        current_date = datetime.now()
        data['temporal_context'] = {
            'day_of_week': current_date.strftime('%A'),
            'month': current_date.strftime('%B'),
            'quarter': f"Q{(current_date.month-1)//3+1}",
            'is_weekend': current_date.weekday() >= 5,
            'is_holiday': self._is_holiday(current_date)  # Implement this if needed
        }
        
        # Call LLM with enhanced context
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"""
            Analyze the following performance data and provide insights with historical context:
            
            Performance Metrics: {json.dumps(data.get('metrics', {}), indent=2)}
            
            Price Change Impact: {json.dumps(data.get('change_impact', [])[:5], indent=2)}  # Top 5
            
            Anomalies Detected: {json.dumps(data.get('anomalies', []), indent=2)}
            
            Previous Insights: {json.dumps(data.get('previous_insights', []), indent=2)}
            
            Recurring Patterns: {json.dumps(data.get('recurring_patterns', []), indent=2)}
            
            Temporal Context: {json.dumps(data.get('temporal_context', {}), indent=2)}
            
            Provide insights on:
            1. Overall performance assessment compared to historical trends
            2. Most and least successful price changes
            3. Unexpected market responses and recurring patterns
            4. Opportunities for improvement based on historical learning
            5. Risk factors to monitor with increased/decreased importance
            6. Seasonal or day-of-week considerations
            """}
        ]
        
        response = self.call_llm(messages)
        
        if response.get("error"):
            self.logger.error(f"LLM Error: {response.get('error')}")
            return {"error": response.get("content", "Failed to generate performance insights with memory")}
        
        content = response.get("content", "")
        if content:
            try:
                insights = json.loads(content)
                
                # Add metadata about memory enhancement
                insights['memory_enhanced'] = True
                insights['historical_context_depth'] = len(data.get('previous_insights', []))
                insights['pattern_recognition'] = len(data.get('recurring_patterns', [])) > 0
                
                return insights
            except:
                return {"insights": content, "memory_enhanced": True}
        else:
            return {"error": "No content in response"}
    
    def _is_holiday(self, date: datetime) -> bool:
        """Simple check if a date is a major US holiday"""
        # Simplified holiday check - could be expanded
        month_day = (date.month, date.day)
        major_holidays = [
            (1, 1),    # New Year's Day
            (7, 4),    # Independence Day
            (12, 25),  # Christmas
            (11, 11),  # Veterans Day
            (5, 31),   # Memorial Day (simplified - last Monday in May)
            (11, 26),  # Thanksgiving (simplified - 4th Thursday in November)
        ]
        return month_day in major_holidays
    
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
            
    def _get_performance_history(self, db: Session, user_id: int) -> List[Dict]:
        """Get historical performance snapshots from memory"""
        # Query performance baselines from memory
        snapshots = db.query(PerformanceBaseline).filter(
            PerformanceBaseline.user_id == user_id
        ).order_by(desc(PerformanceBaseline.created_at)).limit(10).all()
        
        return [{
            "date": snapshot.baseline_date.isoformat(),
            "revenue": snapshot.avg_daily_revenue,
            "orders": snapshot.avg_daily_orders,
            "aov": snapshot.avg_order_value,
            "period_start": snapshot.period_start.isoformat() if snapshot.period_start else None,
            "period_end": snapshot.period_end.isoformat() if snapshot.period_end else None,
            "item_baselines": snapshot.item_baselines
        } for snapshot in snapshots]
    
    def _save_performance_snapshot(self, db: Session, user_id: int, 
                                 performance: Dict[str, Any], metrics: Dict[str, Any]):
        """Save current performance data as a baseline in memory"""
        # Extract key metrics
        baseline = PerformanceBaseline(
            user_id=user_id,
            baseline_date=datetime.now(),
            avg_daily_revenue=performance.get("daily", {}).get("revenue", 0),
            avg_daily_orders=performance.get("daily", {}).get("orders", 0),
            avg_order_value=metrics.get("aov", {}).get("current", 0),
            item_baselines=performance.get("top_items", []),
            period_start=datetime.now() - timedelta(days=30),  # Assuming 30-day baseline period
            period_end=datetime.now()
        )
        
        db.add(baseline)
        db.commit()
        
        self.logger.info(f"Saved performance baseline for user {user_id}")
        
    def _track_anomalies(self, db: Session, user_id: int, anomalies: List[Dict[str, Any]]):
        """Track detected performance anomalies in memory"""
        for anomaly in anomalies:
            if anomaly.get("severity", "") in ["high", "critical"]:
                # Save significant anomalies to memory
                anomaly_record = PerformanceAnomaly(
                    user_id=user_id,
                    detection_date=datetime.now(),
                    anomaly_type=anomaly.get("type", "unknown"),
                    metric=anomaly.get("metric", ""),
                    expected_value=anomaly.get("expected", 0),
                    actual_value=anomaly.get("actual", 0),
                    deviation_percent=anomaly.get("deviation_percent", 0),
                    severity=anomaly.get("severity", "medium"),
                    affected_items=anomaly.get("affected_items", []),
                    potential_causes=anomaly.get("potential_causes", []),
                    recommended_actions=anomaly.get("recommended_actions", [])
                )
                
                db.add(anomaly_record)
                
        if anomalies:
            db.commit()
            self.logger.info(f"Tracked {len(anomalies)} anomalies for user {user_id}")
