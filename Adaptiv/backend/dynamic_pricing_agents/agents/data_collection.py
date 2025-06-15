"""
Data Collection Agent with Memory - Gathers, analyzes, and distills data to extract meaningful insights
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
import json
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import numpy as np
from collections import defaultdict
import pandas as pd
import uuid
import numbers
from scipy import stats
from ..base_agent import BaseAgent
import models
import requests
import os
# Import memory models directly from models.py
from models import (
    AgentMemory,
    DataCollectionSnapshot, 
    CompetitorPriceHistory,
    PricingDecision,
    Order,
    OrderItem,
    Item
)


class DataCollectionAgent(BaseAgent):
    """Agent responsible for collecting, analyzing, and distilling data to extract item-specific insights"""
    
    def __init__(self):
        super().__init__("DataCollectionAgent", model="gpt-4o-mini")
        
    def get_system_prompt(self) -> str:
        return """You are a Data Collection and Analysis Agent for a dynamic pricing system with memory capabilities. Your role is to:
        1. Gather POS data, competitor pricing, and market information
        2. Analyze trends and patterns for each menu item
        3. Calculate metrics like sales momentum, price elasticity, and seasonal patterns
        4. Identify correlations between item sales and external factors
        5. Distill raw data into actionable quantitative insights
        6. Learn from past data collection and analysis to improve future recommendations
        7. Produce concise, item-specific takeaways that minimize context window usage
        
        Focus on extracting meaningful quantitative insights rather than just presenting raw data. Each menu item should have clear, data-driven takeaways that can inform pricing decisions."""
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing method for data collection with memory integration and quantitative analysis"""
        db = context.get("db")
        user_id = context.get("user_id")
        test_mode = context.get("test_mode", False)
        
        self.log_action("data_collection_started", {"user_id": user_id})
        self.logger.info(f"Starting data collection and analysis for user {user_id}")
        
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
            
            # Get menu items
            menu_items = self._get_menu_items(db, user_id)
            
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
            
            self.logger.info("Performing quantitative analysis for menu items...")
            
            quantitative_insights = {}
            
            for item in menu_items:
                item_id = item["id"]
                item_name = item["name"]
                
                self.logger.info(f"Analyzing item: {item_name} (ID: {item_id})")
                
                # Calculate sales momentum
                momentum_data = self._calculate_sales_momentum(db, item_id)
                
                # Calculate price elasticity
                elasticity_data = self._calculate_price_elasticity(db, item_id)
                
                # Find sales correlations
                correlation_data = self._find_sales_correlations(db, item_id)
                
                # Analyze seasonality 
                seasonality_data = self._analyze_seasonality(db, item_id)
                
                # Compile item insights
                item_insights = {
                    "item_id": item_id,
                    "item_name": item_name,
                    "sales_momentum": momentum_data,
                    "price_elasticity": elasticity_data,
                    "correlations": correlation_data,
                    "seasonality": seasonality_data
                }
                
                quantitative_insights[item_id] = item_insights
            
            # Prepare consolidated dataset with both traditional data and new quantitative insights
            consolidated_data = {
                "collection_timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "pos_data": pos_data,
                "price_history": price_history,
                "competitor_data": competitor_data,
                "market_data": market_data,
                "data_quality": data_quality,
                "recommendations": recommendations,
                "quantitative_insights": quantitative_insights,
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
                "quality_score": data_quality.get("overall_score", 0),
                "items_analyzed": len(quantitative_insights)
            })
            
            self.logger.info(f"Data collection completed for user {user_id}")
            
            # Debug: Convert all data before returning
            final_data = self._convert_numpy_types(consolidated_data)
            
            # Extra debug: Verify no numpy.bool_ types remain
            self._debug_find_numpy_types(final_data)
            
            final_data_copy = self._convert_numpy_types(consolidated_data)

            final_data_copy["menu_items"] = pos_data["items"]
            # Remove pos_data from the copy to reduce response size
            if "pos_data" in final_data_copy:
                del final_data_copy["pos_data"]

            return final_data_copy
            
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
        """Collect historical price change data based on orders"""
        # Get orders from the past 180 days
        start_date = datetime.now(timezone.utc) - timedelta(days=180)
        orders = db.query(models.Order).filter(
            models.Order.user_id == user_id,
            models.Order.order_date >= start_date
        ).order_by(models.Order.order_date).all()
        
        # Get all order items to analyze price changes
        order_items = []
        for order in orders:
            items = db.query(models.OrderItem).filter(
                models.OrderItem.order_id == order.id
            ).all()
            for item in items:
                item_data = {
                    "item_id": item.item_id,
                    "price": float(item.price_at_time),
                    "order_date": order.order_date
                }
                order_items.append(item_data)
        
        # Track price changes by item
        price_history = {}
        price_changes = []
        
        # Group order items by item_id
        items_by_id = {}
        for item in order_items:
            if item["item_id"] not in items_by_id:
                items_by_id[item["item_id"]] = []
            items_by_id[item["item_id"]].append(item)
        
        # Sort each item's orders by date
        for item_id, items in items_by_id.items():
            sorted_items = sorted(items, key=lambda x: x["order_date"])
            last_price = None
            
            for item in sorted_items:
                current_price = item["price"]
                if last_price is not None and abs(current_price - last_price) > 0.001:  # Small epsilon for float comparison
                    # Price change detected
                    change = {
                        "item_id": item_id,
                        "old_price": last_price,
                        "new_price": current_price,
                        "changed_at": item["order_date"].isoformat(),
                        "reason": "Detected from order history"
                    }
                    price_changes.append(change)
                
                last_price = current_price
        
        # Get item names for reference
        item_names = {}
        items = db.query(models.Item).filter(models.Item.user_id == user_id).all()
        for item in items:
            item_names[item.id] = item.name
        
        # Add item names to changes for clarity
        for change in price_changes:
            item_id = change["item_id"]
            if item_id in item_names:
                change["item_name"] = item_names[item_id]
        
        return {
            "changes": price_changes,
            "summary": {
                "total_changes": len(price_changes),
                "items_changed": len(set(change["item_id"] for change in price_changes))
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
                # Protect against division by zero
                if historical_price > 0:
                    percent_change = (price_change / historical_price) * 100
                else:
                    percent_change = 0 if price_change == 0 else 100
                
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
                    'avg_change_percent': sum(pc['change_percent'] for pc in price_changes) / len(price_changes) if price_changes else 0
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
            
    def _get_menu_items(self, db: Session, user_id: int) -> List[Dict[str, Any]]:
        """Retrieve menu items for a user"""
        self.logger.info(f"Retrieving menu items for user {user_id}")
        
        menu_items = db.query(models.Item).filter(
            models.Item.user_id == user_id
        ).all()
        
        result = []
        for item in menu_items:
            result.append({
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "current_price": item.current_price,
                "cost": item.cost,
                "description": item.description
            })
        
        self.logger.info(f"Retrieved {len(result)} menu items")
        return result

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
    
    def _find_sales_correlations(self, db: Session, item_id: int, days_back: int = 90) -> Dict[str, Any]:
        """Find correlations between sales of this item and other variables
        
        Analyzes correlations between:
        - This item's sales and other items (complementary or substitute products)
        - This item's sales and price changes
        - This item's sales and competitor prices
        - This item's sales and day of week/seasonality
        
        Args:
            db: Database session
            item_id: ID of the menu item
            days_back: Number of days to analyze
            
        Returns:
            Dictionary containing correlation insights
        """
        self.logger.info(f"Finding sales correlations for item {item_id}")
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        # Get daily sales data for this item
        daily_sales_query = db.query(
            func.date(Order.order_date).label('date'),
            func.sum(OrderItem.quantity).label('quantity'),
            func.avg(OrderItem.unit_price).label('price')
        ).join(
            Order, OrderItem.order_id == Order.id
        ).filter(
            OrderItem.item_id == item_id,
            Order.order_date >= cutoff_date
        ).group_by(
            func.date(Order.order_date)
        ).order_by(
            func.date(Order.order_date)
        )
        
        daily_sales = daily_sales_query.all()
        
        if not daily_sales or len(daily_sales) < 7:  # Need at least a week of data
            return {
                "correlations": [],
                "complementary_items": [],
                "substitute_items": [],
                "day_of_week_effect": {"effect": "unknown"},
                "analysis": "insufficient_data"
            }
        
        # Extract dates, quantities, and prices
        dates = [row.date for row in daily_sales]
        quantities = [row.quantity for row in daily_sales]
        prices = [row.price for row in daily_sales]
        
        # Find correlations with top 10 other items
        # First identify orders where this item appears
        orders_with_item = db.query(OrderItem.order_id).filter(
            OrderItem.item_id == item_id,
            OrderItem.order_id.in_(
                db.query(Order.id).filter(Order.order_date >= cutoff_date)
            )
        ).distinct().subquery()
        
        # Find other items in those same orders
        other_items = db.query(
            OrderItem.item_id,
            func.count(OrderItem.id).label('frequency'),
            Item.name
        ).join(
            Item, OrderItem.item_id == Item.id
        ).filter(
            OrderItem.order_id.in_(db.query(orders_with_item.c.order_id)),
            OrderItem.item_id != item_id
        ).group_by(
            OrderItem.item_id, Item.name
        ).order_by(
            func.count(OrderItem.id).desc()
        ).limit(10).all()
        
        # Calculate item correlations
        item_correlations = []
        for other_item in other_items:
            other_item_id = other_item.item_id
            
            # Get daily sales of the other item
            other_daily_sales = db.query(
                func.date(Order.order_date).label('date'),
                func.sum(OrderItem.quantity).label('quantity')
            ).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                OrderItem.item_id == other_item_id,
                Order.order_date >= cutoff_date
            ).group_by(
                func.date(Order.order_date)
            ).all()
            
            # Create maps for easy lookup
            other_quantities = {row.date: row.quantity for row in other_daily_sales}
            
            # Match dates and calculate correlation
            matched_quantities = []
            matched_other_quantities = []
            for date, qty in zip(dates, quantities):
                if date in other_quantities:
                    matched_quantities.append(qty)
                    matched_other_quantities.append(other_quantities[date])
            
            if len(matched_quantities) >= 7:  # Need at least a week of overlapping data
                correlation = np.corrcoef(matched_quantities, matched_other_quantities)[0, 1]
                relationship_type = "complementary" if correlation > 0.3 else "substitute" if correlation < -0.3 else "independent"
                
                item_correlations.append({
                    "item_id": other_item_id,
                    "item_name": other_item.name,
                    "correlation": round(float(correlation), 2),
                    "relationship": relationship_type,
                    "confidence": round(min(len(matched_quantities) / 30, 1.0), 2),  # More data = higher confidence
                    "frequency": other_item.frequency
                })
        
        # Price-quantity correlation (elasticity check)
        if len(prices) == len(quantities) and len(prices) >= 7 and len(set(prices)) > 1:
            price_correlation = np.corrcoef(prices, quantities)[0, 1]
        else:
            price_correlation = None
        
        # Day of week analysis
        day_of_week_effect = {}
        weekday_sales = defaultdict(list)
        
        for row in daily_sales:
            # Convert string date to datetime object before calling weekday()
            if isinstance(row.date, str):
                date_obj = datetime.strptime(row.date, '%Y-%m-%d').date()
            else:
                date_obj = row.date
                
            weekday = date_obj.weekday()  # 0 = Monday, 6 = Sunday
            weekday_sales[weekday].append(row.quantity)
        
        if len(weekday_sales.keys()) >= 4:  # Need at least 4 different days of the week
            weekday_avgs = {day: sum(sales)/len(sales) for day, sales in weekday_sales.items() if sales}
            overall_avg = sum(quantities) / len(quantities) if quantities else 0
            
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            weekday_effects = []
            
            for day in range(7):
                if day in weekday_avgs and overall_avg > 0:
                    effect = (weekday_avgs[day] - overall_avg) / overall_avg
                    weekday_effects.append({
                        "day": day_names[day],
                        "effect": round(effect * 100, 1),  # As percentage
                        "avg_sales": round(float(weekday_avgs[day]), 1)
                    })
            
            # Sort by effect
            weekday_effects.sort(key=lambda x: x["effect"], reverse=True)
            
            # Determine peak days
            peak_days = [day["day"] for day in weekday_effects if day["effect"] > 20]  # 20% above average
            slow_days = [day["day"] for day in weekday_effects if day["effect"] < -20]  # 20% below average
            
            day_of_week_effect = {
                "effect": "strong" if peak_days or slow_days else "moderate" if any(abs(day["effect"]) > 10 for day in weekday_effects) else "minimal",
                "peak_days": peak_days,
                "slow_days": slow_days,
                "day_data": weekday_effects
            }
        else:
            day_of_week_effect = {"effect": "unknown", "reason": "insufficient_data"}
        
        # Filter correlations
        complementary_items = [item for item in item_correlations if item["relationship"] == "complementary"]
        substitute_items = [item for item in item_correlations if item["relationship"] == "substitute"]
        
        return {
            "correlations": item_correlations,
            "complementary_items": complementary_items,
            "substitute_items": substitute_items,
            "price_sales_correlation": round(float(price_correlation), 2) if price_correlation is not None else None,
            "day_of_week_effect": day_of_week_effect
        }
    
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
        
    def _debug_find_numpy_types(self, obj, path=""):
        """Debug helper: Find any remaining numpy types in the data structure"""
        import numpy as np
        import inspect
        
        if isinstance(obj, dict):
            for k, v in obj.items():
                self._debug_find_numpy_types(v, f"{path}.{k}" if path else str(k))
        elif isinstance(obj, (list, tuple)):
            for i, item in enumerate(obj):
                self._debug_find_numpy_types(item, f"{path}[{i}]")
        else:
            # Check if it's a numpy type
            if hasattr(obj, '__module__') and obj.__module__ == 'numpy':
                self.logger.error(f"Found numpy type at {path}: {type(obj)} - {obj}")
                # Print more details to help debug
                self.logger.error(f"Object representation: {repr(obj)}")
                self.logger.error(f"Object dir: {dir(obj)}")
                self.logger.error(f"Is numpy scalar: {isinstance(obj, np.generic)}")
                if hasattr(obj, 'dtype'):
                    self.logger.error(f"Dtype: {obj.dtype}")
    
    def _convert_numpy_types(self, obj):
        """Recursively convert NumPy types to native Python types for JSON serialization"""
        import numpy as np
        
        # Handle dictionaries
        if isinstance(obj, dict):
            return {self._convert_numpy_types(k): self._convert_numpy_types(v) 
                   for k, v in obj.items()}
        
        # Handle lists and other iterables
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._convert_numpy_types(item) for item in obj)
        elif isinstance(obj, set):
            return set(self._convert_numpy_types(item) for item in obj)
        
        # Handle numpy types more comprehensively
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return self._convert_numpy_types(obj.tolist())
        # Check for boolean types by name as well as instance
        elif isinstance(obj, (np.bool_, np.bool8)) or (hasattr(obj, 'dtype') and str(obj.dtype) == 'bool'):
            return bool(obj)  # Convert numpy booleans to native Python boolean values
        # Handle numpy scalar types generally
        elif isinstance(obj, np.generic):
            return obj.item()  # Convert any numpy scalar to its Python equivalent
        # Additional type check by module name
        elif hasattr(obj, '__module__') and obj.__module__ == 'numpy':
            self.logger.warning(f"Converting unknown numpy type: {type(obj)}")
            # Try different conversion methods
            if hasattr(obj, 'tolist'):
                return self._convert_numpy_types(obj.tolist())
            elif hasattr(obj, 'item'):
                return obj.item()
            else:
                return str(obj)  # Last resort - convert to string
        
        # Handle datetime objects
        elif hasattr(obj, 'isoformat') and callable(getattr(obj, 'isoformat')):
            return obj.isoformat()
        
        # Handle special types that might contain numpy values
        elif hasattr(obj, '__dict__'):
            # Convert custom objects with __dict__ attribute
            return self._convert_numpy_types(obj.__dict__)
        
        # Return everything else as-is
        else:
            return obj

    def _save_collection_snapshot(self, db: Session, user_id: int, data: Dict[str, Any]):
        """Save a snapshot of the collected data"""
        # Convert NumPy types to native Python types for JSON serialization
        converted_data = self._convert_numpy_types(data)
        
        snapshot = DataCollectionSnapshot(
            user_id=user_id,
            snapshot_date=datetime.now(timezone.utc),
            pos_data_completeness=converted_data['data_quality']['metrics']['pos_data']['completeness'],
            price_history_coverage=converted_data['data_quality']['metrics']['price_history']['coverage'],
            competitor_data_freshness=converted_data['data_quality']['metrics']['competitor_data']['freshness'],
            overall_quality_score=converted_data['data_quality']['overall_score'],
            total_orders=converted_data['pos_data']['summary']['total_orders'],
            total_items=len(converted_data['pos_data']['items']),  # Count items from the items list
            total_competitors=converted_data['competitor_data'].get('summary', {}).get('total_competitors', 0),  # Use safe access
            date_range_start=datetime.fromisoformat(converted_data['pos_data']['summary']['date_range']['start'].replace('Z', '+00:00')),
            date_range_end=datetime.fromisoformat(converted_data['pos_data']['summary']['date_range']['end'].replace('Z', '+00:00')),
            data_issues=converted_data['data_quality']['issues'],
            recommendations=converted_data['recommendations'],
            full_data=converted_data  # Store complete data for reference
        )
        
        try:
            db.add(snapshot)
            db.commit()
            self.logger.info(f"Saved data collection snapshot for user {user_id}")
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error saving data collection snapshot: {str(e)}")
            raise

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
                return {"trend": "improving", "change": (recent_avg - older_avg) / older_avg if older_avg != 0 else 0}
            elif recent_avg < older_avg * 0.9:
                return {"trend": "declining", "change": (recent_avg - older_avg) / older_avg if older_avg != 0 else 0}

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

    def _calculate_price_elasticity(self, db: Session, item_id: int, days_back: int = 180) -> Dict[str, Any]:
        """Calculate price elasticity for a specific menu item

    Analyzes how changes in price affect sales volume to calculate price elasticity.
    Elasticity > 1 indicates price-sensitive item (elastic)
        Elasticity < 1 indicates price-insensitive item (inelastic)

        Args:
            db: Database session
            item_id: ID of the menu item
            days_back: Number of days to analyze

        Returns:
            Dictionary containing elasticity metrics and supporting data
        """
        self.logger.info(f"Calculating price elasticity for item {item_id}")

        # Get price history for this item
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)

        price_changes = db.query(models.PriceHistory).filter(
            models.PriceHistory.item_id == item_id,
            models.PriceHistory.changed_at >= cutoff_date
        ).order_by(models.PriceHistory.changed_at).all()

        # Need at least one price change to calculate elasticity
        if not price_changes:
            return {
                "elasticity": None,
                "is_elastic": None,
                "confidence": 0,
                "price_changes": 0,
                "analysis": "insufficient_data"
            }

        # Get orders containing this item, grouped by day and price point
        elasticity_data = []

        # Add current price to the price history for analysis
        current_price = db.query(models.Item).filter(models.Item.id == item_id).first()
        if current_price:
            price_points = [(pc.previous_price, pc.changed_at, pc.new_price) for pc in price_changes]
            price_points.append((price_changes[-1].new_price, price_changes[-1].changed_at, current_price.current_price))
        else:
            price_points = [(pc.previous_price, pc.changed_at, pc.new_price) for pc in price_changes]

        # For each price change, analyze sales before and after
        for i in range(len(price_points)):
            old_price = price_points[i][0]
            change_date = price_points[i][1]
            new_price = price_points[i][2]

            # Skip if no actual price change
            if old_price == new_price:
                continue

            # Get sales 14 days before price change
            before_start = change_date - timedelta(days=14)
            before_sales = db.query(func.sum(OrderItem.quantity).label('total_qty')).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                OrderItem.item_id == item_id,
                Order.order_date >= before_start,
                Order.order_date < change_date
            ).scalar() or 0

            # Get sales 14 days after price change
            after_end = change_date + timedelta(days=14)
            after_sales = db.query(func.sum(OrderItem.quantity).label('total_qty')).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                OrderItem.item_id == item_id,
                Order.order_date >= change_date,
                Order.order_date < after_end
            ).scalar() or 0

            # Calculate elasticity for this price change
            # Elasticity = % change in quantity / % change in price
            if old_price > 0 and before_sales > 0:  # Avoid division by zero
                percent_price_change = (new_price - old_price) / old_price
                percent_sales_change = (after_sales - before_sales) / before_sales

                # Only record meaningful changes
                if abs(percent_price_change) > 0.01 and abs(percent_sales_change) > 0.01:
                    point_elasticity = abs(percent_sales_change / percent_price_change)

                    elasticity_data.append({
                        "date": change_date.isoformat(),
                        "price_change_percent": round(percent_price_change * 100, 2),
                        "sales_change_percent": round(percent_sales_change * 100, 2),
                        "point_elasticity": round(float(point_elasticity), 2),
                        "old_price": float(old_price),
                        "new_price": float(new_price),
                        "before_sales": before_sales,
                        "after_sales": after_sales
                    })

        # Return after processing all price changes, not inside the loop
        return {
            "elasticity": sum(e.get('point_elasticity', 0) for e in elasticity_data) / len(elasticity_data) if elasticity_data else None,
            "data_points": len(elasticity_data),
            "elasticity_history": elasticity_data,
            "data_completeness": "high" if len(elasticity_data) >= 3 else "medium" if len(elasticity_data) >= 1 else "low"
        }
    
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
                return {"trend": "improving", "change": (recent_avg - older_avg) / older_avg if older_avg != 0 else 0}
            elif recent_avg < older_avg * 0.9:
                return {"trend": "declining", "change": (recent_avg - older_avg) / older_avg if older_avg != 0 else 0}
        
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
    
    def _calculate_price_elasticity(self, db: Session, item_id: int, days_back: int = 180) -> Dict[str, Any]:
        """Calculate price elasticity for a specific menu item
        
        Analyzes how changes in price affect sales volume to calculate price elasticity.
        Elasticity > 1 indicates price-sensitive item (elastic)
        Elasticity < 1 indicates price-insensitive item (inelastic)
        
        Args:
            db: Database session
            item_id: ID of the menu item
            days_back: Number of days to analyze
            
        Returns:
            Dictionary containing elasticity metrics and supporting data
        """
        self.logger.info(f"Calculating price elasticity for item {item_id}")
        
        # Get price history for this item
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        price_changes = db.query(models.PriceHistory).filter(
            models.PriceHistory.item_id == item_id,
            models.PriceHistory.changed_at >= cutoff_date
        ).order_by(models.PriceHistory.changed_at).all()
        
        # Need at least one price change to calculate elasticity
        if not price_changes:
            return {
                "elasticity": None,
                "is_elastic": None,
                "confidence": 0,
                "price_changes": 0,
                "analysis": "insufficient_data"
            }
        
        # Get orders containing this item, grouped by day and price point
        elasticity_data = []
        
        # Add current price to the price history for analysis
        current_price = db.query(models.Item).filter(models.Item.id == item_id).first()
        if current_price:
            price_points = [(pc.previous_price, pc.changed_at, pc.new_price) for pc in price_changes]
            price_points.append((price_changes[-1].new_price, price_changes[-1].changed_at, current_price.current_price))
        else:
            price_points = [(pc.previous_price, pc.changed_at, pc.new_price) for pc in price_changes]
        
        # For each price change, analyze sales before and after
        for i in range(len(price_points)):
            old_price = price_points[i][0]
            change_date = price_points[i][1]
            new_price = price_points[i][2]
            
            # Skip if no actual price change
            if old_price == new_price:
                continue
                
            # Get sales 14 days before price change
            before_start = change_date - timedelta(days=14)
            before_sales = db.query(func.sum(OrderItem.quantity).label('total_qty')).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                OrderItem.item_id == item_id,
                Order.order_date >= before_start,
                Order.order_date < change_date
            ).scalar() or 0
            
            # Get sales 14 days after price change
            after_end = change_date + timedelta(days=14)
            after_sales = db.query(func.sum(OrderItem.quantity).label('total_qty')).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                OrderItem.item_id == item_id,
                Order.order_date >= change_date,
                Order.order_date < after_end
            ).scalar() or 0
            
            # Calculate elasticity for this price change
            # Elasticity = % change in quantity / % change in price
            if old_price > 0 and before_sales > 0:  # Avoid division by zero
                percent_price_change = (new_price - old_price) / old_price
                percent_sales_change = (after_sales - before_sales) / before_sales
                
                # Only record meaningful changes
                if abs(percent_price_change) > 0.01 and abs(percent_sales_change) > 0.01:
                    point_elasticity = abs(percent_sales_change / percent_price_change)
                    
                    elasticity_data.append({
                        "date": change_date.isoformat(),
                        "price_change_percent": round(percent_price_change * 100, 2),
                        "sales_change_percent": round(percent_sales_change * 100, 2),
                        "point_elasticity": round(float(point_elasticity), 2),
                        "old_price": float(old_price),
                        "new_price": float(new_price),
                        "before_sales": before_sales,
                        "after_sales": after_sales
                    })
        
        # If we have elasticity data points, calculate average
        if elasticity_data:
            avg_elasticity = sum(point["point_elasticity"] for point in elasticity_data) / len(elasticity_data)
            confidence = min(len(elasticity_data) / 3, 1.0)  # Max confidence with 3+ data points
            
            return {
                "elasticity": round(float(avg_elasticity), 2),
                "is_elastic": avg_elasticity > 1,  # Elastic if > 1
                "confidence": round(float(confidence), 2),
                "price_changes": len(price_changes),
                "data_points": len(elasticity_data),
                "price_sensitivity": "high" if avg_elasticity > 1.5 else 
                                    "medium" if avg_elasticity > 0.7 else "low",
                "historical_elasticity": elasticity_data
            }
        else:
            return {
                "elasticity": None,
                "is_elastic": None,
                "confidence": 0,
                "price_changes": len(price_changes),
                "analysis": "insufficient_data_for_elasticity"
            }
    
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
                if data["price_changes"] > 0:
                    data["avg_change_percent"] /= data["price_changes"]
                else:
                    data["avg_change_percent"] = 0
                if data["avg_change_percent"] > 5:
                    data["trend"] = "increasing"
                elif data["avg_change_percent"] < -5:
                    data["trend"] = "decreasing"
        
        return competitor_trends
    
    def _calculate_sales_momentum(self, db: Session, item_id: int, days_back: int = 90) -> Dict[str, Any]:
        """Calculate sales momentum for a specific menu item
        
        Analyzes recent sales trends to determine if an item's popularity is increasing, decreasing or stable.
        Uses weighted recent sales data to calculate momentum score.
        
        Args:
            db: Database session
            item_id: ID of the menu item
            days_back: Number of days to analyze
            
        Returns:
            Dictionary containing momentum score, trend direction, and supporting metrics
        """
        self.logger.info(f"Calculating sales momentum for item {item_id}")
        
        # Get order items for this menu item within the specified time period
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        # Query to get orders containing this item, ordered by date
        order_items_query = db.query(
            OrderItem, Order.order_date
        ).join(
            Order, OrderItem.order_id == Order.id
        ).filter(
            OrderItem.item_id == item_id,
            Order.order_date >= cutoff_date
        ).order_by(Order.order_date)
        
        order_items = order_items_query.all()
        
        if not order_items:
            return {
                "momentum_score": 0,
                "trend": "insufficient_data",
                "confidence": 0,
                "total_sales": 0,
                "days_with_data": 0
            }
            
        # Group by week to smooth out daily fluctuations
        weekly_sales = defaultdict(int)
        start_date = min(order_date for _, order_date in order_items)
        
        for item, order_date in order_items:
            # Calculate week number (0-indexed from start_date)
            week_num = (order_date - start_date).days // 7
            weekly_sales[week_num] += item.quantity
        
        # Convert to list for analysis
        weeks = sorted(weekly_sales.keys())
        sales = [weekly_sales[w] for w in weeks]
        
        if len(sales) < 2:
            return {
                "momentum_score": 0,
                "trend": "insufficient_data",
                "confidence": 0,
                "total_sales": sum(sales),
                "days_with_data": (max(order_date for _, order_date in order_items) - 
                                 min(order_date for _, order_date in order_items)).days + 1
            }
            
        # Calculate weighted momentum score giving more importance to recent sales
        total_weight = sum(range(1, len(sales) + 1))
        weighted_changes = 0
        
        for i in range(1, len(sales)):
            week_weight = i / total_weight  # More recent weeks have higher weight
            percent_change = ((sales[i] - sales[i-1]) / max(sales[i-1], 1)) * 100
            weighted_changes += percent_change * week_weight
            
        # Normalize momentum score between -1 and 1
        momentum_score = np.clip(weighted_changes / 100, -1, 1)
        
        # Determine trend direction
        if momentum_score > 0.15:
            trend = "increasing"
        elif momentum_score < -0.15:
            trend = "decreasing"
        else:
            trend = "stable"
        
        # Calculate confidence based on amount of data
        confidence = min(len(sales) / 12, 1.0)  # Max confidence with 12+ weeks of data
        
        return {
            "momentum_score": round(float(momentum_score), 2),
            "trend": trend,
            "confidence": round(float(confidence), 2),
            "total_sales": sum(sales),
            "weekly_pattern": sales,
            "days_with_data": (max(order_date for _, order_date in order_items) - 
                             min(order_date for _, order_date in order_items)).days + 1
        }
        
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
                # Protect against division by zero
                if data['prices'][0] > 0:
                    change = (data['prices'][-1] - data['prices'][0]) / data['prices'][0] * 100
                else:
                    # If initial price is zero, use absolute change or a default
                    change = 0 if data['prices'][-1] == 0 else 100  # 100% increase if going from 0 to any value
                avg_price_changes.append(change)
        
        return {
            "total_tracked_items": total_items,
            "items_with_price_changes": items_with_changes,
            "average_price_change": sum(avg_price_changes) / len(avg_price_changes) if avg_price_changes else 0,
            "price_volatility": "high" if total_items > 0 and items_with_changes / total_items > 0.3 else "low"
        }

    def _analyze_seasonality(self, db: Session, item_id: int, days_back: int = 365) -> Dict[str, Any]:
        """Analyze seasonal patterns in item sales
    
        Detects monthly, quarterly, and holiday-related seasonal patterns in sales.
        Also identifies any trends over the analyzed period.
        
        Args:
            db: Database session
            item_id: ID of the menu item
            days_back: Number of days to analyze (ideally at least a year for seasonality)
            
        Returns:
            Dictionary containing seasonal insights and patterns
        """
        self.logger.info(f"Analyzing seasonality for item {item_id}")
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        # Get daily sales data for this item
        daily_sales_query = db.query(
            func.date(Order.order_date).label('date'),
            func.sum(OrderItem.quantity).label('quantity')
        ).join(
            Order, OrderItem.order_id == Order.id
        ).filter(
            OrderItem.item_id == item_id,
            Order.order_date >= cutoff_date
        ).group_by(
            func.date(Order.order_date)
        ).order_by(
            func.date(Order.order_date)
        )
        
        daily_sales = daily_sales_query.all()
        
        # If we don't have enough data, return limited analysis
        if not daily_sales:
            return {
                "seasonality_detected": False,
                "reason": "no_data",
                "monthly_pattern": None,
                "quarterly_pattern": None
            }
        
        if len(daily_sales) < 60:  # Need at least 2 months of data
            return {
                "seasonality_detected": False,
                "reason": "insufficient_data",
                "confidence": 0,
                "data_span_days": len(daily_sales),
                "monthly_pattern": None,
                "quarterly_pattern": None
            }
        
        # Group sales by month for monthly seasonality
        monthly_sales = defaultdict(float)
        for row in daily_sales:
            # Convert string date to datetime object before calling strftime()
            if isinstance(row.date, str):
                date_obj = datetime.strptime(row.date, '%Y-%m-%d').date()
                month_key = date_obj.strftime("%Y-%m")
            else:
                month_key = row.date.strftime("%Y-%m")
            monthly_sales[month_key] += row.quantity
        
        # Convert to sorted lists for analysis
        months = sorted(monthly_sales.keys())
        month_quantities = [monthly_sales[m] for m in months]
        
        # Extract month names for better readability
        month_names = [datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in months]
        
        # Calculate month-over-month changes
        mom_changes = []
        for i in range(1, len(month_quantities)):
            if month_quantities[i-1] > 0:
                change = (month_quantities[i] - month_quantities[i-1]) / month_quantities[i-1] * 100
                mom_changes.append({
                    "period": month_names[i],
                    "change": round(change, 1),
                    "previous": month_quantities[i-1],
                    "current": month_quantities[i]
                })
        
        # Group by calendar month to detect annual seasonality
        calendar_month_sales = defaultdict(list)
        for row in daily_sales:
            # Convert string date to datetime object if needed
            if isinstance(row.date, str):
                date_obj = datetime.strptime(row.date, '%Y-%m-%d').date()
                cal_month = date_obj.month  # 1 = January, 12 = December
            else:
                cal_month = row.date.month
                
            calendar_month_sales[cal_month].append(row.quantity)
        
        # Calculate average sales by calendar month
        monthly_pattern = []
        for month in range(1, 13):  # 1 to 12
            if month in calendar_month_sales and calendar_month_sales[month]:
                avg_sales = sum(calendar_month_sales[month]) / len(calendar_month_sales[month])
                monthly_pattern.append({
                    "month": datetime(2000, month, 1).strftime("%B"),  # Month name
                    "month_number": month,
                    "avg_sales": round(float(avg_sales), 2),
                    "data_points": len(calendar_month_sales[month])
                })
        
        # Sort by month number for consistent ordering
        monthly_pattern.sort(key=lambda x: x["month_number"])
        
        # Calculate quarterly data
        quarter_sales = defaultdict(list)
        for row in daily_sales:
            # Convert string date to datetime object if needed
            if isinstance(row.date, str):
                date_obj = datetime.strptime(row.date, '%Y-%m-%d').date()
                quarter = (date_obj.month - 1) // 3 + 1  # 1-4
            else:
                quarter = (row.date.month - 1) // 3 + 1  # 1-4
                
            quarter_sales[quarter].append(row.quantity)
        
        quarterly_pattern = []
        for q in range(1, 5):  # Q1 to Q4
            if q in quarter_sales and quarter_sales[q]:
                avg_sales = sum(quarter_sales[q]) / len(quarter_sales[q])
                quarterly_pattern.append({
                    "quarter": f"Q{q}",
                    "avg_sales": round(float(avg_sales), 2),
                    "data_points": len(quarter_sales[q])
                })
        
        # Evaluate overall seasonality strength
        # Looking for significant differences between months/quarters
        monthly_avgs = [p["avg_sales"] for p in monthly_pattern]
        if monthly_avgs:
            monthly_variation = np.std(monthly_avgs) / np.mean(monthly_avgs) if np.mean(monthly_avgs) > 0 else 0
        else:
            monthly_variation = 0
            
        quarterly_avgs = [p["avg_sales"] for p in quarterly_pattern]
        if quarterly_avgs:
            quarterly_variation = np.std(quarterly_avgs) / np.mean(quarterly_avgs) if np.mean(quarterly_avgs) > 0 else 0
        else:
            quarterly_variation = 0
        
        # Identify peak periods
        peak_month = None
        peak_month_value = 0
        for month in monthly_pattern:
            if month["avg_sales"] > peak_month_value:
                peak_month_value = month["avg_sales"]
                peak_month = month["month"]
                
        peak_quarter = None
        peak_quarter_value = 0
        for quarter in quarterly_pattern:
            if quarter["avg_sales"] > peak_quarter_value:
                peak_quarter_value = quarter["avg_sales"]
                peak_quarter = quarter["quarter"]
                
        # Determine seasonality strength
        has_seasonality = monthly_variation > 0.2 or quarterly_variation > 0.15
        if monthly_variation > 0.3 or quarterly_variation > 0.25:
            seasonality_strength = "strong"
        elif monthly_variation > 0.2 or quarterly_variation > 0.15:
            seasonality_strength = "moderate"
        else:
            seasonality_strength = "weak"
                            
        # Calculate confidence based on data span
        # Convert string dates to datetime objects for comparison
        date_objects = []
        for row in daily_sales:
            if isinstance(row.date, str):
                date_obj = datetime.strptime(row.date, '%Y-%m-%d').date()
            else:
                date_obj = row.date
            date_objects.append(date_obj)
            
        first_date = min(date_objects)
        last_date = max(date_objects)
        days_span = (last_date - first_date).days + 1
        confidence = min(days_span / 365, 1.0)  # Max confidence with 1+ year of data
        
        # Identify pattern type (strongest variation)
        pattern_type = "monthly" if monthly_variation > quarterly_variation else "quarterly"
        
        return {
            "seasonality_detected": has_seasonality,
            "pattern_type": pattern_type if has_seasonality else None,
            "strength": seasonality_strength,
            "confidence": round(confidence, 2),
            "data_span_days": days_span,
            "months_analyzed": len(months),
            "peak_month": peak_month,
            "peak_quarter": peak_quarter,
            "monthly_variation": round(float(monthly_variation * 100), 1),  # As percentage
            "quarterly_variation": round(float(quarterly_variation * 100), 1),  # As percentage
            "monthly_pattern": monthly_pattern,
            "quarterly_pattern": quarterly_pattern,
            "month_over_month": mom_changes[:6]  # Show most recent 6 changes
        }
