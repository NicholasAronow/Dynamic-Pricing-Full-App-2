"""
Data Collection Agent with Memory - Gathers and consolidates data from multiple sources
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import json
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..base_agent import BaseAgent
import models
import requests
import os
# Import memory models directly from models.py
from models import (
    AgentMemory,
    DataCollectionSnapshot, 
    CompetitorPriceHistory,
    PricingDecision
)


class DataCollectionAgent(BaseAgent):
    """Agent responsible for collecting and consolidating data from various sources with memory"""
    
    def __init__(self):
        super().__init__("DataCollectionAgent", model="gpt-4o-mini")
        
    def get_system_prompt(self) -> str:
        return """You are a Data Collection Agent for a dynamic pricing system with memory capabilities. Your role is to:
        1. Gather POS data (orders, sales, inventory)
        2. Collect competitor pricing data from the web
        3. Track historical price changes and their impact
        4. Identify data quality issues and missing data
        5. Prepare consolidated datasets for analysis
        6. Learn from past data collection patterns to improve quality
        7. Track competitor pricing changes over time
        8. Remember data quality issues and their resolutions
        
        Focus on accuracy, completeness, data integrity, and continuous improvement based on historical patterns."""
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing method for data collection with memory integration"""
        db = context.get("db")
        user_id = context.get("user_id")
        
        self.log_action("data_collection_started", {"user_id": user_id})
        self.logger.info(f"Starting data collection for user {user_id}")
        
        try:
            # Get memory context
            memory_context = self.get_memory_context(
                db, user_id, 
                memory_types=['data_quality', 'collection_issues', 'competitor_changes'],
                days_back=90
            )
            
            # Get previous snapshots for comparison
            previous_snapshots = self._get_previous_snapshots(db, user_id, limit=5)
            
            # Gather all data sources
            self.logger.info("Collecting POS data...")
            pos_data = self._collect_pos_data(db, user_id)
            
            self.logger.info("Collecting price history...")
            price_history = self._collect_price_history(db, user_id)
            
            self.logger.info("Collecting competitor data...")
            competitor_data = self._collect_competitor_data_with_memory(db, user_id, memory_context)
            
            self.logger.info("Collecting market data...")
            market_data = self._collect_market_data(db, user_id)
            
            self.logger.info("Assessing data quality...")
            # Analyze data quality with historical context
            data_quality = self._assess_data_quality_with_memory({
                "pos_data": pos_data,
                "price_history": price_history,
                "competitor_data": competitor_data,
                "market_data": market_data
            }, previous_snapshots)
            
            # Generate recommendations using memory
            recommendations = self._generate_data_recommendations_with_memory(
                data_quality, memory_context, db, user_id
            )
            
            # Prepare consolidated dataset
            consolidated_data = {
                "collection_timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "pos_data": pos_data,
                "price_history": price_history,
                "competitor_data": competitor_data,
                "market_data": market_data,
                "data_quality": data_quality,
                "recommendations": recommendations,
                "historical_context": {
                    "quality_trend": self._analyze_quality_trend(previous_snapshots),
                    "recurring_issues": self._identify_recurring_issues(memory_context),
                    "competitor_price_trends": self._analyze_competitor_trends(db, user_id)
                }
            }
            
            # Save snapshot
            self._save_collection_snapshot(db, user_id, consolidated_data)
            
            # Track any data quality issues
            self._track_data_issues(db, user_id, data_quality)
            
            self.log_action("data_collection_completed", {
                "records_collected": sum([
                    len(pos_data.get("orders", [])),
                    len(price_history.get("changes", [])),
                    len(competitor_data.get("competitors", []))
                ]),
                "quality_score": data_quality.get("overall_score", 0)
            })
            
            self.logger.info(f"Data collection completed for user {user_id}")
            return consolidated_data
            
        except Exception as e:
            self.logger.error(f"Error in data collection process: {str(e)}")
            # Save error as memory for future reference
            self.save_memory(
                db, user_id, 'collection_error',
                {'error': str(e), 'timestamp': datetime.now().isoformat()},
                metadata={'error_type': type(e).__name__}
            )
            raise
    
    def _collect_pos_data(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Collect Point of Sale data"""
        self.logger.info(f"Collecting POS data for user {user_id}")
        
        # Get recent orders
        recent_orders = db.query(models.Order).filter(
            models.Order.user_id == user_id,
            models.Order.order_date >= datetime.now(timezone.utc) - timedelta(days=90)
        ).order_by(models.Order.order_date.desc()).limit(1000).all()  # Limit to 1000 most recent orders
        
        self.logger.info(f"Found {len(recent_orders)} recent orders")
        
        # Get all order IDs
        order_ids = [order.id for order in recent_orders]
        
        # Get all order items in one query
        all_order_items = []
        if order_ids:
            all_order_items = db.query(models.OrderItem).filter(
                models.OrderItem.order_id.in_(order_ids)
            ).all()
        
        # Create a mapping of order_id to order_items
        order_items_map = {}
        for item in all_order_items:
            if item.order_id not in order_items_map:
                order_items_map[item.order_id] = []
            order_items_map[item.order_id].append(item)
        
        # Get items and their sales
        items = db.query(models.Item).filter(models.Item.user_id == user_id).all()
        
        # Aggregate sales data
        order_data = []
        for order in recent_orders:
            order_items = order_items_map.get(order.id, [])
            
            order_data.append({
                "id": order.id,
                "date": order.order_date.isoformat(),
                "total": float(order.total_amount),
                "items": [{
                    "item_id": oi.item_id,
                    "quantity": oi.quantity,
                    "price": float(oi.unit_price)
                } for oi in order_items]
            })
        
        return {
            "orders": order_data,
            "items": [{
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "current_price": float(item.current_price),
                "cost": float(item.cost) if item.cost else None
            } for item in items],
            "summary": {
                "total_orders": len(recent_orders),
                "date_range": {
                    "start": (datetime.now(timezone.utc) - timedelta(days=90)).isoformat(),
                    "end": datetime.now(timezone.utc).isoformat()
                }
            }
        }
    
    def _collect_price_history(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Collect historical price change data"""
        price_changes = db.query(models.PriceHistory).join(
            models.Item
        ).filter(
            models.Item.user_id == user_id,
            models.PriceHistory.changed_at >= datetime.now(timezone.utc) - timedelta(days=180)
        ).all()
        
        return {
            "changes": [{
                "item_id": pc.item_id,
                "old_price": float(pc.previous_price),
                "new_price": float(pc.new_price),
                "changed_at": pc.changed_at.isoformat(),
                "reason": pc.change_reason
            } for pc in price_changes],
            "summary": {
                "total_changes": len(price_changes),
                "items_changed": len(set(pc.item_id for pc in price_changes))
            }
        }
    
    def _get_previous_snapshots(self, db: Session, user_id: int, limit: int = 5) -> List[DataCollectionSnapshot]:
        """Get previous data collection snapshots"""
        return db.query(DataCollectionSnapshot).filter(
            DataCollectionSnapshot.user_id == user_id
        ).order_by(desc(DataCollectionSnapshot.snapshot_date)).limit(limit).all()
    
    def _collect_competitor_data_with_memory(self, db: Session, user_id: int, 
                                           memory_context: Dict[str, Any]) -> Dict[str, Any]:
        """Collect competitor pricing data with historical tracking"""
        self.logger.info(f"Collecting competitor data with memory for user {user_id}")
        
        # Get current competitor items
        current_competitor_items = db.query(models.CompetitorItem).all()
        
        self.logger.info(f"Found {len(current_competitor_items)} competitor items")
        
        # Get historical competitor prices for comparison
        historical_prices = self._get_historical_competitor_prices(db, user_id, days_back=30)
        
        # Track price changes
        price_changes = []
        competitors_dict = {}
        
        for item in current_competitor_items:
            # Save to history
            history_entry = CompetitorPriceHistory(
                user_id=user_id,
                competitor_name=item.competitor_name,
                item_name=item.item_name,
                price=float(item.price) if hasattr(item, 'price') else 0.0,
                category=item.category,
                similarity_score=float(item.similarity_score) if item.similarity_score else None,
                captured_at=datetime.now(timezone.utc)
            )
            
            # Check for price changes
            historical_price = historical_prices.get(
                (item.competitor_name, item.item_name), {}
            ).get('price')
            
            if historical_price and historical_price != history_entry.price:
                price_change = history_entry.price - historical_price
                percent_change = (price_change / historical_price) * 100
                
                history_entry.price_change_from_last = price_change
                history_entry.percent_change_from_last = percent_change
                
                price_changes.append({
                    "competitor": item.competitor_name,
                    "item": item.item_name,
                    "old_price": historical_price,
                    "new_price": history_entry.price,
                    "change_percent": percent_change
                })
            
            db.add(history_entry)
            
            # Build competitor dictionary
            if item.competitor_name not in competitors_dict:
                competitors_dict[item.competitor_name] = {
                    "name": item.competitor_name,
                    "items": []
                }
            
            competitors_dict[item.competitor_name]["items"].append({
                "name": item.item_name,
                "price": float(item.price) if hasattr(item, 'price') else 0.0,
                "category": item.category,
                "similarity_score": float(item.similarity_score) if item.similarity_score else None,
                "last_updated": item.updated_at.isoformat() if item.updated_at else item.created_at.isoformat(),
                "price_trend": self._get_price_trend(
                    historical_prices.get((item.competitor_name, item.item_name), {})
                )
            })
        
        db.commit()
        
        # Save significant price changes as memory
        if price_changes:
            self.save_memory(
                db, user_id, 'competitor_changes',
                {
                    'price_changes': price_changes,
                    'change_count': len(price_changes),
                    'avg_change_percent': sum(pc['change_percent'] for pc in price_changes) / len(price_changes)
                },
                metadata={'capture_date': datetime.now().isoformat()}
            )
        
        return {
            "competitors": list(competitors_dict.values()),
            "price_changes": price_changes,
            "historical_summary": self._summarize_competitor_history(historical_prices)
        }
    
    def _get_historical_competitor_prices(self, db: Session, user_id: int, 
                                        days_back: int = 30) -> Dict[tuple, Dict]:
        """Get historical competitor prices for comparison"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        historical = db.query(CompetitorPriceHistory).filter(
            CompetitorPriceHistory.user_id == user_id,
            CompetitorPriceHistory.captured_at >= cutoff_date
        ).all()
        
        # Group by competitor-item combination
        price_history = {}
        for entry in historical:
            key = (entry.competitor_name, entry.item_name)
            if key not in price_history:
                price_history[key] = {
                    'prices': [],
                    'dates': []
                }
            price_history[key]['prices'].append(entry.price)
            price_history[key]['dates'].append(entry.captured_at)
            price_history[key]['price'] = entry.price  # Latest price
        
        return price_history
    
    def _get_price_trend(self, history: Dict) -> str:
        """Determine price trend from historical data"""
        if not history or 'prices' not in history or len(history['prices']) < 2:
            return "stable"
        
        prices = history['prices']
        # Simple trend: compare first and last
        if prices[-1] > prices[0] * 1.05:
            return "increasing"
        elif prices[-1] < prices[0] * 0.95:
            return "decreasing"
        else:
            return "stable"
            
    def _collect_competitor_data(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Collect competitor pricing data"""
        self.logger.info(f"Collecting competitor data for user {user_id}")
        
        # Get all competitor items grouped by competitor name
        competitor_items = db.query(models.CompetitorItem).all()
        
        self.logger.info(f"Found {len(competitor_items)} competitor items")
        
        # Group items by competitor name
        competitors_dict = {}
        for item in competitor_items:
            if item.competitor_name not in competitors_dict:
                competitors_dict[item.competitor_name] = {
                    "name": item.competitor_name,
                    "items": []
                }
            # Since we're working with CompetitorItem objects, we should use item.price
            competitors_dict[item.competitor_name]["items"].append({
                "name": item.item_name,
                "price": float(item.price) if hasattr(item, 'price') else 0.0,
                "category": item.category,
                "similarity_score": float(item.similarity_score) if item.similarity_score else None,
                "last_updated": item.updated_at.isoformat() if item.updated_at else item.created_at.isoformat()
            })
        
        return {
            "competitors": list(competitors_dict.values())
        }
    
    def _collect_market_data(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Collect market-level data and trends"""
        # Get COGS data
        cogs_data = db.query(models.COGS).filter(
            models.COGS.user_id == user_id
        ).order_by(models.COGS.week_end_date.desc()).limit(12).all()
        
        return {
            "cogs": [{
                "week_end": cog.week_end_date.isoformat(),
                "amount": float(cog.amount)
            } for cog in cogs_data],
            "market_conditions": self._fetch_market_conditions()
        }
    
    def _fetch_market_conditions(self) -> Dict[str, Any]:
        """Fetch current market conditions (placeholder for external API)"""
        # This would connect to external data sources in production
        return {
            "inflation_rate": 3.2,
            "consumer_confidence": 102.5,
            "seasonal_factors": ["holiday_season", "cold_weather"]
        }
    
    def _assess_data_quality_with_memory(self, data: Dict[str, Any], 
                                       previous_snapshots: List[DataCollectionSnapshot]) -> Dict[str, Any]:
        """Assess data quality with historical context"""
        # Current quality metrics
        quality_metrics = {
            "pos_data": {
                "completeness": min(len(data["pos_data"]["orders"]) / 90, 1.0),
                "recency": self._calculate_recency(data["pos_data"]["orders"])
            },
            "price_history": {
                "coverage": len(set(pc["item_id"] for pc in data["price_history"]["changes"])) / max(len(data["pos_data"]["items"]), 1),
                "frequency": len(data["price_history"]["changes"]) / max(len(data["pos_data"]["items"]), 1)
            },
            "competitor_data": {
                "freshness": self._calculate_competitor_freshness(data["competitor_data"]["competitors"]),
                "coverage": len(data["competitor_data"]["competitors"])
            }
        }
        
        overall_quality = sum(
            metrics.get("completeness", 0) + metrics.get("recency", 0) + 
            metrics.get("coverage", 0) + metrics.get("frequency", 0) + 
            metrics.get("freshness", 0)
            for metrics in quality_metrics.values()
        ) / 8
        
        # Compare with historical quality
        quality_trend = "stable"
        if previous_snapshots:
            recent_qualities = [s.overall_quality_score for s in previous_snapshots[:3] if s.overall_quality_score]
            if recent_qualities:
                avg_recent = sum(recent_qualities) / len(recent_qualities)
                if overall_quality > avg_recent * 1.1:
                    quality_trend = "improving"
                elif overall_quality < avg_recent * 0.9:
                    quality_trend = "declining"
        
        return {
            "metrics": quality_metrics,
            "overall_score": overall_quality,
            "quality_trend": quality_trend,
            "issues": self._identify_data_issues(quality_metrics),
            "historical_comparison": {
                "previous_scores": [s.overall_quality_score for s in previous_snapshots[:5]],
                "trend": quality_trend
            }
        }
    
    def _calculate_recency(self, orders: List[Dict]) -> float:
        """Calculate how recent the data is"""
        if not orders:
            return 0.0
        latest_order = max(datetime.fromisoformat(o["date"].replace('Z', '+00:00')).replace(tzinfo=timezone.utc) if 'Z' in o["date"] else datetime.fromisoformat(o["date"]).replace(tzinfo=timezone.utc) for o in orders)
        days_old = (datetime.now(timezone.utc) - latest_order).days
        return max(0, 1 - (days_old / 7))  # Penalize if older than a week
    
    def _calculate_competitor_freshness(self, competitors: List[Dict]) -> float:
        """Calculate how fresh competitor data is"""
        if not competitors:
            return 0.0
        
        all_dates = []
        for comp in competitors:
            for item in comp.get("items", []):
                if item.get("last_updated"):
                    try:
                        dt = datetime.fromisoformat(item["last_updated"].replace('Z', '+00:00'))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        all_dates.append(dt)
                    except:
                        # Handle dates that are already timezone-aware
                        dt = datetime.fromisoformat(item["last_updated"])
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        all_dates.append(dt)
        
        if not all_dates:
            return 0.0
            
        latest_update = max(all_dates)
        days_old = (datetime.now(timezone.utc) - latest_update).days
        return max(0, 1 - (days_old / 30))  # Penalize if older than 30 days
    
    def _identify_data_issues(self, metrics: Dict[str, Any]) -> List[str]:
        """Identify specific data quality issues"""
        issues = []
        
        if metrics["pos_data"]["completeness"] < 0.5:
            issues.append("Insufficient order history - need more sales data")
        if metrics["pos_data"]["recency"] < 0.5:
            issues.append("Order data is stale - check POS integration")
        if metrics["price_history"]["coverage"] < 0.3:
            issues.append("Limited price change history - need more pricing experiments")
        if metrics["competitor_data"]["freshness"] < 0.5:
            issues.append("Competitor data is outdated - refresh competitor prices")
            
        return issues
    
    def _generate_data_recommendations(self, quality: Dict[str, Any]) -> List[str]:
        """Generate recommendations for data improvement"""
        recommendations = []
        
        if quality["overall_score"] < 0.7:
            recommendations.append("Overall data quality needs improvement before optimal pricing can be achieved")
            
        for issue in quality["issues"]:
            if "order history" in issue:
                recommendations.append("Ensure POS system is properly syncing all transactions")
            elif "price change" in issue:
                recommendations.append("Consider implementing small price tests to gather elasticity data")
            elif "competitor data" in issue:
                recommendations.append("Schedule regular competitor price checks (weekly recommended)")
            
        return recommendations
    
    def _generate_data_recommendations_with_memory(self, quality: Dict[str, Any], 
                                                  memory_context: Dict[str, Any],
                                                  db: Session, user_id: int) -> List[str]:
        """Generate recommendations using historical context and LLM"""
        # Get basic recommendations
        basic_recommendations = []
        
        if quality["overall_score"] < 0.7:
            basic_recommendations.append("Overall data quality needs improvement before optimal pricing can be achieved")
            
        for issue in quality["issues"]:
            if "order history" in issue:
                basic_recommendations.append("Ensure POS system is properly syncing all transactions")
            elif "price change" in issue:
                basic_recommendations.append("Consider implementing small price tests to gather elasticity data")
            elif "competitor data" in issue:
                basic_recommendations.append("Schedule regular competitor price checks (weekly recommended)")
        
        # Use LLM to generate more sophisticated recommendations
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"""
            Based on the current data quality assessment and historical patterns, provide specific recommendations:
            
            Current Quality Metrics: {json.dumps(quality, indent=2)}
            
            Recurring Issues from Memory: {json.dumps(memory_context.get('collection_issues', [])[:5], indent=2)}
            
            Quality Trend: {quality.get('quality_trend', 'unknown')}
            
            Please provide:
            1. Top 3 actionable recommendations to improve data quality
            2. Specific steps to address recurring issues
            3. Preventive measures based on historical patterns
            
            Format as JSON with 'recommendations' array.
            """}
        ]
        
        response = self.call_llm_with_memory(messages, db, user_id, context={'quality_assessment': quality})
        
        if response.get("content") and not response.get("error"):
            try:
                llm_recommendations = json.loads(response["content"])
                if isinstance(llm_recommendations, dict) and 'recommendations' in llm_recommendations:
                    basic_recommendations.extend(llm_recommendations['recommendations'])
            except:
                self.logger.warning("Failed to parse LLM recommendations")
        
        return basic_recommendations
        
    def _save_collection_snapshot(self, db: Session, user_id: int, data: Dict[str, Any]):
        """Save a snapshot of the data collection"""
        snapshot = DataCollectionSnapshot(
            user_id=user_id,
            pos_data_completeness=data['data_quality']['metrics']['pos_data']['completeness'],
            price_history_coverage=data['data_quality']['metrics']['price_history']['coverage'],
            competitor_data_freshness=data['data_quality']['metrics']['competitor_data']['freshness'],
            overall_quality_score=data['data_quality']['overall_score'],
            total_orders=len(data['pos_data']['orders']),
            total_items=len(data['pos_data']['items']),
            total_competitors=len(data['competitor_data']['competitors']),
            date_range_start=datetime.fromisoformat(data['pos_data']['summary']['date_range']['start'].replace('Z', '+00:00')),
            date_range_end=datetime.fromisoformat(data['pos_data']['summary']['date_range']['end'].replace('Z', '+00:00')),
            data_issues=data['data_quality']['issues'],
            recommendations=data['recommendations'],
            full_data=data  # Store complete data for reference
        )
        
        db.add(snapshot)
        db.commit()
        
        self.logger.info(f"Saved data collection snapshot for user {user_id}")
    
    def _track_data_issues(self, db: Session, user_id: int, quality: Dict[str, Any]):
        """Track data quality issues for learning"""
        if quality['issues']:
            self.save_memory(
                db, user_id, 'data_quality',
                {
                    'issues': quality['issues'],
                    'overall_score': quality['overall_score'],
                    'metrics': quality['metrics']
                },
                metadata={'severity': 'high' if quality['overall_score'] < 0.5 else 'medium'}
            )
    
    def _analyze_quality_trend(self, snapshots: List[DataCollectionSnapshot]) -> Dict[str, Any]:
        """Analyze data quality trends over time"""
        if not snapshots:
            return {"trend": "unknown", "message": "No historical data"}
        
        scores = [s.overall_quality_score for s in snapshots if s.overall_quality_score is not None]
        if not scores:
            return {"trend": "unknown", "message": "No quality scores available"}
        
        # Simple trend analysis
        if len(scores) >= 2:
            recent_avg = sum(scores[:2]) / 2
            older_avg = sum(scores[2:]) / len(scores[2:]) if len(scores) > 2 else scores[1]
            
            if recent_avg > older_avg * 1.1:
                return {"trend": "improving", "change": (recent_avg - older_avg) / older_avg}
            elif recent_avg < older_avg * 0.9:
                return {"trend": "declining", "change": (recent_avg - older_avg) / older_avg}
        
        return {"trend": "stable", "change": 0}
    
    def _identify_recurring_issues(self, memory_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify recurring data collection issues"""
        issue_memories = memory_context.get('collection_issues', [])
        
        if not issue_memories:
            return []
        
        # Count issue types
        issue_counts = {}
        for memory in issue_memories:
            issues = memory.get('content', {}).get('issues', [])
            for issue in issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        # Find recurring issues
        recurring = []
        for issue, count in issue_counts.items():
            if count >= 2:  # Appears at least twice
                recurring.append({
                    "issue": issue,
                    "frequency": count,
                    "severity": "high" if count >= 5 else "medium"
                })
        
        return sorted(recurring, key=lambda x: x['frequency'], reverse=True)
    
    def _analyze_competitor_trends(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Analyze competitor pricing trends"""
        # Get recent competitor price history
        recent_history = db.query(CompetitorPriceHistory).filter(
            CompetitorPriceHistory.user_id == user_id,
            CompetitorPriceHistory.captured_at >= datetime.now(timezone.utc) - timedelta(days=30)
        ).all()
        
        if not recent_history:
            return {"message": "No competitor price history available"}
        
        # Analyze trends by competitor
        competitor_trends = {}
        for entry in recent_history:
            if entry.competitor_name not in competitor_trends:
                competitor_trends[entry.competitor_name] = {
                    "price_changes": 0,
                    "avg_change_percent": 0,
                    "trend": "stable"
                }
            
            if entry.percent_change_from_last:
                competitor_trends[entry.competitor_name]["price_changes"] += 1
                competitor_trends[entry.competitor_name]["avg_change_percent"] += entry.percent_change_from_last
        
        # Calculate averages and determine trends
        for competitor, data in competitor_trends.items():
            if data["price_changes"] > 0:
                data["avg_change_percent"] /= data["price_changes"]
                if data["avg_change_percent"] > 5:
                    data["trend"] = "increasing"
                elif data["avg_change_percent"] < -5:
                    data["trend"] = "decreasing"
        
        return competitor_trends
    
    def _summarize_competitor_history(self, historical_prices: Dict[tuple, Dict]) -> Dict[str, Any]:
        """Summarize competitor price history"""
        if not historical_prices:
            return {"message": "No historical competitor data"}
        
        total_items = len(historical_prices)
        items_with_changes = sum(1 for data in historical_prices.values() 
                               if 'prices' in data and len(data['prices']) > 1)
        
        avg_price_changes = []
        for data in historical_prices.values():
            if 'prices' in data and len(data['prices']) > 1:
                change = (data['prices'][-1] - data['prices'][0]) / data['prices'][0] * 100
                avg_price_changes.append(change)
        
        return {
            "total_tracked_items": total_items,
            "items_with_price_changes": items_with_changes,
            "average_price_change": sum(avg_price_changes) / len(avg_price_changes) if avg_price_changes else 0,
            "price_volatility": "high" if items_with_changes / total_items > 0.3 else "low"
        }
