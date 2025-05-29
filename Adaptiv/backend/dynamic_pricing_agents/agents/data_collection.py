"""
Data Collection Agent - Gathers and consolidates data from multiple sources
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import json
from sqlalchemy.orm import Session
from ..base_agent import BaseAgent
import models
import requests
import os


class DataCollectionAgent(BaseAgent):
    """Agent responsible for collecting and consolidating data from various sources"""
    
    def __init__(self):
        super().__init__("DataCollectionAgent", model="gpt-4o-mini")
        
    def get_system_prompt(self) -> str:
        return """You are a Data Collection Agent for a dynamic pricing system. Your role is to:
        1. Gather POS data (orders, sales, inventory)
        2. Collect competitor pricing data from the web
        3. Track historical price changes and their impact
        4. Identify data quality issues and missing data
        5. Prepare consolidated datasets for analysis
        
        Focus on accuracy, completeness, and data integrity."""
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing method for data collection"""
        db = context.get("db")
        user_id = context.get("user_id")
        
        self.log_action("data_collection_started", {"user_id": user_id})
        self.logger.info(f"Starting data collection for user {user_id}")
        
        try:
            # Gather all data sources
            self.logger.info("Collecting POS data...")
            pos_data = self._collect_pos_data(db, user_id)
            
            self.logger.info("Collecting price history...")
            price_history = self._collect_price_history(db, user_id)
            
            self.logger.info("Collecting competitor data...")
            competitor_data = self._collect_competitor_data(db, user_id)
            
            self.logger.info("Collecting market data...")
            market_data = self._collect_market_data(db, user_id)
            
            self.logger.info("Assessing data quality...")
            # Analyze data quality
            data_quality = self._assess_data_quality({
                "pos_data": pos_data,
                "price_history": price_history,
                "competitor_data": competitor_data,
                "market_data": market_data
            })
            
            # Prepare consolidated dataset
            consolidated_data = {
                "collection_timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "pos_data": pos_data,
                "price_history": price_history,
                "competitor_data": competitor_data,
                "market_data": market_data,
                "data_quality": data_quality,
                "recommendations": self._generate_data_recommendations(data_quality)
            }
            
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
    
    def _assess_data_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality and completeness of collected data"""
        quality_metrics = {
            "pos_data": {
                "completeness": min(len(data["pos_data"]["orders"]) / 90, 1.0),  # Expect ~1 order per day
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
        ) / 8  # Average of all metrics
        
        return {
            "metrics": quality_metrics,
            "overall_score": overall_quality,
            "issues": self._identify_data_issues(quality_metrics)
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
        """Generate recommendations for improving data quality"""
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
