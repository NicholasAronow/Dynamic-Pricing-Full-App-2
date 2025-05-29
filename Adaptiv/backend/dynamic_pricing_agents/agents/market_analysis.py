"""
Market Analysis Agent - Analyzes market conditions and competitive landscape
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from ..base_agent import BaseAgent
import numpy as np


class MarketAnalysisAgent(BaseAgent):
    """Agent responsible for analyzing market conditions and competitive positioning"""
    
    def __init__(self):
        super().__init__("MarketAnalysisAgent", model="gpt-4o-mini")
        self.logger.info("Market Analysis Agent initialized")
        
    def get_system_prompt(self) -> str:
        return """You are a Market Analysis Agent specializing in competitive pricing intelligence. Your role is to:
        1. Analyze competitor pricing strategies and market positioning
        2. Identify market trends and seasonal patterns
        3. Determine price elasticity from historical data
        4. Assess competitive threats and opportunities
        5. Provide market-based pricing recommendations
        
        Use statistical analysis and market intelligence to provide actionable insights."""
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market conditions and competitive landscape"""
        data = context['consolidated_data']
        
        self.log_action("market_analysis_started", {"user_id": data['user_id']})
        
        # Perform various market analyses
        competitive_analysis = self._analyze_competitive_landscape(data)
        elasticity_analysis = self._calculate_price_elasticity(data)
        market_trends = self._identify_market_trends(data)
        positioning_analysis = self._analyze_market_positioning(data)
        
        # Use LLM to generate insights
        insights = self._generate_market_insights({
            "competitive_analysis": competitive_analysis,
            "elasticity_analysis": elasticity_analysis,
            "market_trends": market_trends,
            "positioning_analysis": positioning_analysis
        })
        
        analysis_results = {
            "analysis_timestamp": datetime.now().isoformat(),
            "competitive_landscape": competitive_analysis,
            "price_elasticity": elasticity_analysis,
            "market_trends": market_trends,
            "market_positioning": positioning_analysis,
            "insights": insights,
            "recommendations": self._generate_strategic_recommendations(insights)
        }
        
        self.log_action("market_analysis_completed", {
            "competitors_analyzed": len(competitive_analysis.get("competitors", [])),
            "items_analyzed": len(elasticity_analysis.get("item_elasticities", []))
        })
        
        return analysis_results
    
    def _analyze_competitive_landscape(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze competitor pricing and strategies"""
        competitors_data = data.get("competitor_data", {}).get("competitors", [])
        our_items = data.get("pos_data", {}).get("items", [])
        
        competitor_analysis = []
        for competitor in competitors_data:
            comp_items = competitor.get("items", [])
            
            # Calculate price differences
            price_comparisons = []
            for our_item in our_items:
                matching_comp_items = [
                    ci for ci in comp_items 
                    if self._items_match(our_item["name"], ci["name"])
                ]
                if matching_comp_items:
                    comp_item = matching_comp_items[0]
                    price_diff = (comp_item["price"] - our_item["current_price"]) / our_item["current_price"] * 100
                    price_comparisons.append({
                        "item": our_item["name"],
                        "our_price": our_item["current_price"],
                        "competitor_price": comp_item["price"],
                        "difference_percent": price_diff
                    })
            
            if price_comparisons:
                avg_price_diff = np.mean([pc["difference_percent"] for pc in price_comparisons])
                competitor_analysis.append({
                    "competitor": competitor["name"],
                    "avg_price_difference": avg_price_diff,
                    "price_comparisons": price_comparisons,
                    "strategy": self._infer_pricing_strategy(avg_price_diff)
                })
        
        return {
            "competitors": competitor_analysis,
            "market_summary": {
                "total_competitors": len(competitor_analysis),
                "avg_market_price_diff": np.mean([ca["avg_price_difference"] for ca in competitor_analysis]) if competitor_analysis else 0
            }
        }
    
    def _calculate_price_elasticity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate price elasticity for items with price history"""
        price_history = data.get("price_history", {}).get("changes", [])
        orders = data.get("pos_data", {}).get("orders", [])
        
        # Group price changes by item
        item_changes = {}
        for change in price_history:
            item_id = change["item_id"]
            if item_id not in item_changes:
                item_changes[item_id] = []
            item_changes[item_id].append(change)
        
        elasticities = []
        for item_id, changes in item_changes.items():
            if len(changes) >= 2:  # Need at least 2 price points
                elasticity = self._calculate_item_elasticity(item_id, changes, orders)
                if elasticity is not None:
                    elasticities.append({
                        "item_id": item_id,
                        "elasticity": elasticity,
                        "interpretation": self._interpret_elasticity(elasticity)
                    })
        
        return {
            "item_elasticities": elasticities,
            "summary": {
                "avg_elasticity": np.mean([e["elasticity"] for e in elasticities]) if elasticities else None,
                "elastic_items": len([e for e in elasticities if abs(e["elasticity"]) > 1]),
                "inelastic_items": len([e for e in elasticities if abs(e["elasticity"]) <= 1])
            }
        }
    
    def _identify_market_trends(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Identify market trends from sales and external data"""
        orders = data.get("pos_data", {}).get("orders", [])
        market_conditions = data.get("market_data", {}).get("market_conditions", {})
        
        # Analyze sales trends
        daily_sales = self._aggregate_daily_sales(orders)
        weekly_trends = self._calculate_weekly_trends(daily_sales)
        seasonal_patterns = self._detect_seasonal_patterns(orders)
        
        return {
            "sales_trends": {
                "weekly_growth": weekly_trends,
                "seasonal_patterns": seasonal_patterns
            },
            "market_factors": market_conditions,
            "trend_summary": self._summarize_trends(weekly_trends, seasonal_patterns, market_conditions)
        }
    
    def _analyze_market_positioning(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market positioning relative to competitors"""
        competitive_data = self._analyze_competitive_landscape(data)
        our_items = data.get("pos_data", {}).get("items", [])
        
        positioning = {
            "price_position": self._determine_price_position(competitive_data),
            "category_positioning": self._analyze_category_positioning(our_items, competitive_data),
            "value_proposition": self._assess_value_proposition(data)
        }
        
        return positioning
    
    def _generate_market_insights(self, analyses: Dict[str, Any]) -> Dict[str, Any]:
        """Generate market insights using LLM"""
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"""
            Based on the following market analyses, provide strategic insights:
            
            Competitive Analysis: {json.dumps(analyses['competitive_analysis'], indent=2)}
            
            Price Elasticity: {json.dumps(analyses['elasticity_analysis'], indent=2)}
            
            Market Trends: {json.dumps(analyses['market_trends'], indent=2)}
            
            Market Positioning: {json.dumps(analyses['positioning_analysis'], indent=2)}
            
            Provide insights on:
            1. Key competitive threats and opportunities
            2. Items with pricing power vs. price-sensitive items
            3. Market trend implications for pricing
            4. Strategic positioning recommendations
            """}
        ]
        
        response = self.call_llm(messages)
        
        if response.get("error"):
            self.logger.error(f"LLM Error: {response.get('error')}")
            return {"error": response.get("content", "Failed to generate insights")}
        
        content = response.get("content", "")
        if content:
            try:
                return json.loads(content)
            except:
                return {"insights": content}
        else:
            return {"error": "No content in response"}
    
    def _generate_strategic_recommendations(self, insights: Dict[str, Any]) -> List[str]:
        """Generate strategic recommendations based on market analysis"""
        recommendations = []
        
        # Add specific recommendations based on insights
        if isinstance(insights, dict) and "insights" in insights:
            # Parse insights and generate recommendations
            recommendations.append("Review pricing strategy based on market analysis")
            
        return recommendations
    
    # Helper methods
    def _items_match(self, name1: str, name2: str) -> bool:
        """Check if two item names match (fuzzy matching)"""
        # Simple implementation - could be enhanced with fuzzy matching
        return name1.lower() in name2.lower() or name2.lower() in name1.lower()
    
    def _infer_pricing_strategy(self, avg_price_diff: float) -> str:
        """Infer competitor pricing strategy based on price differences"""
        if avg_price_diff < -10:
            return "discount_leader"
        elif avg_price_diff < -5:
            return "value_pricing"
        elif avg_price_diff < 5:
            return "competitive_parity"
        elif avg_price_diff < 10:
            return "premium_pricing"
        else:
            return "luxury_positioning"
    
    def _calculate_item_elasticity(self, item_id: int, changes: List[Dict], orders: List[Dict]) -> Optional[float]:
        """Calculate price elasticity for a specific item"""
        try:
            # Sort changes by date
            changes.sort(key=lambda x: x["changed_at"])
            
            elasticities = []
            for i in range(len(changes) - 1):
                # Get sales before and after price change
                price1 = changes[i]["new_price"]
                price2 = changes[i + 1]["new_price"]
                date1 = datetime.fromisoformat(changes[i]["changed_at"].replace('Z', '+00:00'))
                date2 = datetime.fromisoformat(changes[i + 1]["changed_at"].replace('Z', '+00:00'))
                
                sales1 = self._get_item_sales_in_period(item_id, orders, date1, date2)
                sales2 = self._get_item_sales_after_date(item_id, orders, date2)
                
                if sales1 > 0 and sales2 > 0:
                    # Calculate elasticity
                    price_change = (price2 - price1) / price1
                    quantity_change = (sales2 - sales1) / sales1
                    if price_change != 0:
                        elasticity = quantity_change / price_change
                        elasticities.append(elasticity)
            
            return np.mean(elasticities) if elasticities else None
        except Exception as e:
            self.logger.error(f"Error calculating elasticity: {str(e)}")
            return None
    
    def _get_item_sales_in_period(self, item_id: int, orders: List[Dict], start: datetime, end: datetime) -> int:
        """Get total sales for an item in a specific period"""
        total = 0
        for order in orders:
            order_date = datetime.fromisoformat(order["date"].replace('Z', '+00:00'))
            if start <= order_date < end:
                for item in order.get("items", []):
                    if item["item_id"] == item_id:
                        total += item["quantity"]
        return total
    
    def _get_item_sales_after_date(self, item_id: int, orders: List[Dict], date: datetime) -> int:
        """Get average daily sales for an item after a specific date (30 days)"""
        total = 0
        days = 0
        for order in orders:
            order_date = datetime.fromisoformat(order["date"].replace('Z', '+00:00'))
            if order_date >= date and (order_date - date).days <= 30:
                days = max(days, (order_date - date).days + 1)
                for item in order.get("items", []):
                    if item["item_id"] == item_id:
                        total += item["quantity"]
        return total / days if days > 0 else 0
    
    def _interpret_elasticity(self, elasticity: float) -> str:
        """Interpret elasticity value"""
        abs_elasticity = abs(elasticity)
        if abs_elasticity > 1.5:
            return "highly_elastic"
        elif abs_elasticity > 1:
            return "elastic"
        elif abs_elasticity > 0.5:
            return "moderately_inelastic"
        else:
            return "inelastic"
    
    def _aggregate_daily_sales(self, orders: List[Dict]) -> Dict[str, float]:
        """Aggregate orders into daily sales"""
        daily_sales = {}
        for order in orders:
            date = order["date"].split('T')[0]
            if date not in daily_sales:
                daily_sales[date] = 0
            daily_sales[date] += order["total"]
        return daily_sales
    
    def _calculate_weekly_trends(self, daily_sales: Dict[str, float]) -> Dict[str, Any]:
        """Calculate week-over-week trends"""
        # Implementation would calculate weekly growth rates
        return {
            "recent_trend": "stable",
            "growth_rate": 0.05
        }
    
    def _detect_seasonal_patterns(self, orders: List[Dict]) -> List[str]:
        """Detect seasonal patterns in sales"""
        # Implementation would analyze sales by time of year
        return ["holiday_boost", "weekend_peaks"]
    
    def _determine_price_position(self, competitive_data: Dict[str, Any]) -> str:
        """Determine overall price positioning"""
        avg_diff = competitive_data.get("market_summary", {}).get("avg_market_price_diff", 0)
        if avg_diff < -10:
            return "significantly_below_market"
        elif avg_diff < -5:
            return "below_market"
        elif avg_diff < 5:
            return "at_market"
        elif avg_diff < 10:
            return "above_market"
        else:
            return "premium_to_market"
    
    def _analyze_category_positioning(self, items: List[Dict], competitive_data: Dict[str, Any]) -> Dict[str, str]:
        """Analyze positioning by category"""
        # Implementation would break down positioning by product category
        return {
            "beverages": "competitive",
            "food": "premium"
        }
    
    def _assess_value_proposition(self, data: Dict[str, Any]) -> str:
        """Assess overall value proposition"""
        # Implementation would analyze quality indicators vs price
        return "quality_focused"
    
    def _summarize_trends(self, weekly: Dict, seasonal: List[str], market: Dict) -> str:
        """Summarize all trend data"""
        return "Stable growth with seasonal variations"
