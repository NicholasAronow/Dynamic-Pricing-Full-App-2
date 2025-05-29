"""
Pricing Strategy Agent - Develops and optimizes pricing strategies
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import numpy as np
from ..base_agent import BaseAgent


class PricingStrategyAgent(BaseAgent):
    """Agent responsible for developing optimal pricing strategies"""
    
    def __init__(self):
        super().__init__("PricingStrategyAgent", model="gpt-4o-mini")
        self.logger.info("Pricing Strategy Agent initialized")
        
    def get_system_prompt(self) -> str:
        return """You are a Pricing Strategy Agent specializing in dynamic pricing optimization. Your role is to:
        1. Develop optimal pricing strategies based on market analysis and business goals
        2. Balance profit maximization with market competitiveness
        3. Consider price elasticity, competitor pricing, and demand patterns
        4. Design pricing experiments to test hypotheses
        5. Recommend specific price points and timing for changes
        
        Focus on data-driven decisions that maximize revenue while maintaining market position."""
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Develop optimal pricing strategies"""
        market_analysis = context['market_analysis']
        consolidated_data = context['consolidated_data']
        business_goals = context.get('business_goals', self._default_business_goals())
        
        self.log_action("pricing_strategy_started", {"user_id": consolidated_data['user_id']})
        
        # Analyze current pricing performance
        performance_analysis = self._analyze_pricing_performance(consolidated_data)
        
        # Generate pricing strategies for each item
        item_strategies = self._generate_item_strategies(
            consolidated_data,
            market_analysis,
            business_goals
        )
        
        # Develop bundle and category strategies
        bundle_strategies = self._develop_bundle_strategies(consolidated_data, market_analysis)
        category_strategies = self._develop_category_strategies(item_strategies)
        
        # Create pricing experiments
        experiments = self._design_pricing_experiments(
            item_strategies,
            market_analysis,
            performance_analysis
        )
        
        # Generate comprehensive strategy
        comprehensive_strategy = self._generate_comprehensive_strategy({
            "performance_analysis": performance_analysis,
            "item_strategies": item_strategies,
            "bundle_strategies": bundle_strategies,
            "category_strategies": category_strategies,
            "experiments": experiments,
            "market_analysis": market_analysis,
            "business_goals": business_goals
        })
        
        strategy_results = {
            "strategy_timestamp": datetime.now().isoformat(),
            "current_performance": performance_analysis,
            "item_strategies": item_strategies,
            "bundle_strategies": bundle_strategies,
            "category_strategies": category_strategies,
            "experiments": experiments,
            "comprehensive_strategy": comprehensive_strategy,
            "implementation_plan": self._create_implementation_plan(comprehensive_strategy)
        }
        
        self.log_action("pricing_strategy_completed", {
            "items_analyzed": len(item_strategies),
            "experiments_designed": len(experiments)
        })
        
        return strategy_results
    
    def _default_business_goals(self) -> Dict[str, Any]:
        """Default business goals if none specified"""
        return {
            "primary_objective": "maximize_revenue",
            "constraints": {
                "maintain_market_position": True,
                "minimum_margin": 0.20,
                "customer_retention": 0.85
            },
            "risk_tolerance": "moderate"
        }
    
    def _analyze_pricing_performance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current pricing performance"""
        items = data.get("pos_data", {}).get("items", [])
        orders = data.get("pos_data", {}).get("orders", [])
        price_history = data.get("price_history", {}).get("changes", [])
        
        # Calculate key metrics
        revenue_by_item = self._calculate_revenue_by_item(orders)
        margin_by_item = self._calculate_margins(items, revenue_by_item)
        price_change_impact = self._analyze_price_change_impact(price_history, orders)
        
        return {
            "revenue_performance": {
                "total_revenue": sum(revenue_by_item.values()),
                "top_revenue_items": self._get_top_items(revenue_by_item, 5),
                "revenue_concentration": self._calculate_concentration(revenue_by_item)
            },
            "margin_performance": {
                "avg_margin": np.mean(list(margin_by_item.values())) if margin_by_item else 0,
                "margin_by_item": margin_by_item,
                "low_margin_items": [item_id for item_id, margin in margin_by_item.items() if margin < 0.15]
            },
            "price_change_effectiveness": price_change_impact,
            "optimization_opportunities": self._identify_optimization_opportunities(
                revenue_by_item, margin_by_item, price_change_impact
            )
        }
    
    def _generate_item_strategies(self, data: Dict[str, Any], market: Dict[str, Any], goals: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate pricing strategies for each item"""
        items = data.get("pos_data", {}).get("items", [])
        elasticities = {e["item_id"]: e for e in market.get("price_elasticity", {}).get("item_elasticities", [])}
        competitive_data = market.get("competitive_landscape", {})
        competitor_items = data.get("competitor_data", {}).get("items", [])
        
        # Create lookup for competitor prices
        competitor_prices = {}
        for comp_item in competitor_items:
            if comp_item.get("item_name") not in competitor_prices:
                competitor_prices[comp_item.get("item_name")] = []
            competitor_prices[comp_item.get("item_name")].append(comp_item.get("price"))
        
        strategies = []
        for item in items:
            item_id = item["id"]
            item_name = item["name"]
            current_price = item["current_price"]
            elasticity_data = elasticities.get(item_id, {})
            
            # Calculate optimal price
            optimal_price = self._calculate_optimal_price(
                item, elasticity_data, competitive_data, goals
            )
            
            # Calculate price change percentage
            price_change = optimal_price - current_price
            price_change_pct = (price_change / current_price) * 100 if current_price > 0 else 0
            
            # Generate specific rationale for this recommendation
            rationale = self._generate_price_change_rationale(
                item, 
                current_price,
                optimal_price, 
                elasticity_data, 
                competitor_prices.get(item_name, []),
                goals
            )
            
            strategy = {
                "item_id": item_id,
                "item_name": item_name,
                "category": item.get("category", "Uncategorized"),
                "current_price": current_price,
                "recommended_price": optimal_price,
                "price_change": round(price_change, 2),
                "price_change_percent": round(price_change_pct, 1),
                "rationale": rationale,
                "strategy_type": self._determine_strategy_type(item, elasticity_data, market),
                "implementation_timing": self._recommend_timing(item, market),
                "expected_impact": self._estimate_impact(item, elasticity_data),
                "confidence": self._calculate_confidence(elasticity_data, competitive_data)
            }
            strategies.append(strategy)
        
        # Sort strategies by absolute price change (largest changes first)
        strategies.sort(key=lambda x: abs(x.get("price_change", 0)), reverse=True)
        
        return strategies
    
    def _develop_bundle_strategies(self, data: Dict[str, Any], market: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Develop bundle pricing strategies"""
        orders = data.get("pos_data", {}).get("orders", [])
        items = data.get("pos_data", {}).get("items", [])
        
        # Analyze frequently bought together items
        item_associations = self._analyze_item_associations(orders)
        
        bundles = []
        for (item1_id, item2_id), frequency in item_associations.items():
            if frequency > 10:  # Minimum frequency threshold
                item1 = next((i for i in items if i["id"] == item1_id), None)
                item2 = next((i for i in items if i["id"] == item2_id), None)
                
                if item1 and item2:
                    bundle = {
                        "items": [item1_id, item2_id],
                        "item_names": [item1["name"], item2["name"]],
                        "individual_total": item1["current_price"] + item2["current_price"],
                        "recommended_bundle_price": (item1["current_price"] + item2["current_price"]) * 0.9,
                        "discount_percent": 10,
                        "frequency": frequency,
                        "expected_lift": 0.15  # 15% sales lift estimate
                    }
                    bundles.append(bundle)
        
        return sorted(bundles, key=lambda x: x["frequency"], reverse=True)[:5]  # Top 5 bundles
    
    def _develop_category_strategies(self, item_strategies: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Develop category-level pricing strategies"""
        # Group items by category
        categories = {}
        for strategy in item_strategies:
            # Assume category info is available in the strategy
            category = "default"  # This would come from item data
            if category not in categories:
                categories[category] = []
            categories[category].append(strategy)
        
        category_strategies = {}
        for category, items in categories.items():
            avg_price_change = np.mean([
                (s["recommended_price"] - s["current_price"]) / s["current_price"] 
                for s in items
            ])
            
            category_strategies[category] = {
                "recommended_adjustment": avg_price_change,
                "strategy": self._determine_category_strategy(avg_price_change),
                "item_count": len(items),
                "coordination_required": abs(avg_price_change) > 0.05
            }
        
        return category_strategies
    
    def _design_pricing_experiments(self, strategies: List[Dict], market: Dict, performance: Dict) -> List[Dict[str, Any]]:
        """Design pricing experiments to test strategies"""
        experiments = []
        
        # Select items for experimentation
        high_confidence_items = [s for s in strategies if s["confidence"] > 0.7]
        uncertain_items = [s for s in strategies if 0.3 < s["confidence"] <= 0.7]
        
        # A/B test for high-impact items
        if high_confidence_items:
            exp = {
                "type": "a_b_test",
                "name": "High-Confidence Price Optimization",
                "items": [s["item_id"] for s in high_confidence_items[:3]],
                "duration_days": 14,
                "test_prices": {
                    s["item_id"]: {
                        "control": s["current_price"],
                        "treatment": s["recommended_price"]
                    } for s in high_confidence_items[:3]
                },
                "success_metrics": ["revenue", "units_sold", "margin"],
                "minimum_sample_size": 100
            }
            experiments.append(exp)
        
        # Multi-armed bandit for exploration
        if uncertain_items:
            exp = {
                "type": "multi_armed_bandit",
                "name": "Price Discovery Experiment",
                "items": [s["item_id"] for s in uncertain_items[:5]],
                "duration_days": 21,
                "price_range": {
                    s["item_id"]: {
                        "min": s["current_price"] * 0.9,
                        "max": s["current_price"] * 1.1,
                        "steps": 5
                    } for s in uncertain_items[:5]
                },
                "exploration_rate": 0.2,
                "update_frequency": "daily"
            }
            experiments.append(exp)
        
        return experiments
    
    def _generate_comprehensive_strategy(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive pricing strategy using LLM"""
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"""
            Based on the following analyses, develop a comprehensive pricing strategy:
            
            Performance Analysis: {json.dumps(inputs['performance_analysis'], indent=2)}
            
            Market Analysis Summary: {json.dumps({
                'positioning': inputs['market_analysis'].get('market_positioning'),
                'competitive_summary': inputs['market_analysis'].get('competitive_landscape', {}).get('market_summary')
            }, indent=2)}
            
            Business Goals: {json.dumps(inputs['business_goals'], indent=2)}
            
            Item Strategies: {len(inputs['item_strategies'])} items analyzed
            Bundle Opportunities: {len(inputs['bundle_strategies'])} bundles identified
            Experiments Planned: {len(inputs['experiments'])}
            
            Provide a comprehensive strategy including:
            1. Executive summary of pricing approach
            2. Key strategic initiatives (top 3-5)
            3. Risk assessment and mitigation
            4. Expected outcomes (revenue, margin, market share)
            5. Success metrics and KPIs
            """}
        ]
        
        response = self.call_llm(messages)
        
        if response.get("error"):
            self.logger.error(f"LLM Error: {response.get('error')}")
            return {"error": response.get("content", "Failed to generate pricing strategy")}
        
        content = response.get("content", "")
        if content:
            try:
                return json.loads(content)
            except:
                return {"strategy": content}
        else:
            return {"error": "No content in response"}
    
    def _create_implementation_plan(self, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create step-by-step implementation plan"""
        plan = [
            {
                "phase": "preparation",
                "duration_days": 3,
                "actions": [
                    "Review and approve pricing changes",
                    "Update POS systems",
                    "Brief staff on changes"
                ]
            },
            {
                "phase": "pilot",
                "duration_days": 7,
                "actions": [
                    "Implement prices for test items",
                    "Monitor initial customer reactions",
                    "Adjust if necessary"
                ]
            },
            {
                "phase": "rollout",
                "duration_days": 14,
                "actions": [
                    "Implement full pricing strategy",
                    "Launch pricing experiments",
                    "Begin performance tracking"
                ]
            },
            {
                "phase": "optimization",
                "duration_days": 30,
                "actions": [
                    "Analyze experiment results",
                    "Fine-tune prices based on data",
                    "Expand successful strategies"
                ]
            }
        ]
        
        return plan
    
    # Helper methods
    def _calculate_revenue_by_item(self, orders: List[Dict]) -> Dict[int, float]:
        """Calculate total revenue by item"""
        revenue = {}
        for order in orders:
            for item in order.get("items", []):
                item_id = item["item_id"]
                if item_id not in revenue:
                    revenue[item_id] = 0
                revenue[item_id] += item["price"] * item["quantity"]
        return revenue
    
    def _calculate_margins(self, items: List[Dict], revenue: Dict[int, float]) -> Dict[int, float]:
        """Calculate profit margins by item"""
        margins = {}
        for item in items:
            if item["cost"] and item["id"] in revenue:
                margin = (item["current_price"] - item["cost"]) / item["current_price"]
                margins[item["id"]] = margin
        return margins
    
    def _analyze_price_change_impact(self, changes: List[Dict], orders: List[Dict]) -> Dict[str, Any]:
        """Analyze the impact of historical price changes"""
        impacts = []
        for change in changes:
            # Calculate sales before and after change
            change_date = datetime.fromisoformat(change["changed_at"].replace('Z', '+00:00'))
            before_sales = self._calculate_sales_in_period(
                change["item_id"], orders, change_date - timedelta(days=30), change_date
            )
            after_sales = self._calculate_sales_in_period(
                change["item_id"], orders, change_date, change_date + timedelta(days=30)
            )
            
            if before_sales > 0:
                impact = (after_sales - before_sales) / before_sales
                impacts.append({
                    "item_id": change["item_id"],
                    "price_change_percent": (change["new_price"] - change["old_price"]) / change["old_price"],
                    "sales_impact_percent": impact * 100
                })
        
        return {
            "changes_analyzed": len(impacts),
            "avg_impact": np.mean([i["sales_impact_percent"] for i in impacts]) if impacts else 0,
            "successful_changes": len([i for i in impacts if i["sales_impact_percent"] > 0])
        }
    
    def _calculate_sales_in_period(self, item_id: int, orders: List[Dict], start: datetime, end: datetime) -> float:
        """Calculate total sales revenue for an item in a period"""
        total = 0
        for order in orders:
            order_date = datetime.fromisoformat(order["date"].replace('Z', '+00:00'))
            if start <= order_date <= end:
                for item in order.get("items", []):
                    if item["item_id"] == item_id:
                        total += item["price"] * item["quantity"]
        return total
    
    def _identify_optimization_opportunities(self, revenue: Dict, margins: Dict, impact: Dict) -> List[str]:
        """Identify specific optimization opportunities"""
        opportunities = []
        
        # Low margin, high revenue items
        high_rev_low_margin = [
            item_id for item_id, margin in margins.items()
            if margin < 0.2 and revenue.get(item_id, 0) > np.mean(list(revenue.values()))
        ]
        if high_rev_low_margin:
            opportunities.append(f"Price increase opportunity for {len(high_rev_low_margin)} high-volume, low-margin items")
        
        # Items with no recent price changes
        opportunities.append("Test price elasticity for items without recent price changes")
        
        return opportunities
    
    def _calculate_optimal_price(self, item: Dict, elasticity: Dict, competitive: Dict, goals: Dict) -> float:
        """Calculate optimal price for an item"""
        current_price = item["current_price"]
        
        # Base calculation on elasticity if available
        if elasticity and "elasticity" in elasticity:
            e = elasticity["elasticity"]
            if abs(e) > 0:
                # Optimal markup formula
                optimal_markup = abs(e) / (abs(e) - 1) if abs(e) > 1 else 2
                if item.get("cost"):
                    optimal_price = item["cost"] * optimal_markup
                else:
                    # Estimate based on current margin
                    optimal_price = current_price * (1 + 0.05)  # Conservative 5% increase
            else:
                optimal_price = current_price
        else:
            # No elasticity data - use competitive positioning
            optimal_price = current_price * 1.02  # Conservative 2% increase
        
        # Apply constraints
        min_margin = goals["constraints"]["minimum_margin"]
        if item.get("cost"):
            min_price = item["cost"] / (1 - min_margin)
            optimal_price = max(optimal_price, min_price)
        
        # Don't deviate too far from current price
        max_change = 0.15  # 15% max change
        optimal_price = max(
            current_price * (1 - max_change),
            min(optimal_price, current_price * (1 + max_change))
        )
        
        return round(optimal_price, 2)
    
    def _generate_price_change_rationale(self, item: Dict, current_price: float, optimal_price: float, 
                                    elasticity_data: Dict, competitor_prices: List[float], goals: Dict) -> str:
        """Generate a specific rationale for the price change recommendation"""
        price_change = optimal_price - current_price
        price_change_pct = (price_change / current_price) * 100 if current_price > 0 else 0
        
        rationale = ""
        
        # Base rationale on elasticity if available
        if elasticity_data and "elasticity" in elasticity_data:
            e = elasticity_data["elasticity"]
            if abs(e) < 0.5:  # Inelastic demand
                if price_change > 0:
                    rationale = f"Low price sensitivity (elasticity: {e:.2f}) indicates customers value this item regardless of price. "
                    rationale += f"A {abs(price_change_pct):.1f}% price increase could increase margin without significantly impacting sales volume."
                else:
                    rationale = f"Despite low price sensitivity (elasticity: {e:.2f}), recommend {abs(price_change_pct):.1f}% price decrease "
                    rationale += f"to align with strategic goals or market positioning."
            elif abs(e) > 1.5:  # Elastic demand
                if price_change < 0:
                    rationale = f"High price sensitivity (elasticity: {e:.2f}) suggests price is a key factor in purchase decisions. "
                    rationale += f"A {abs(price_change_pct):.1f}% price decrease could drive significant volume increase and overall revenue growth."
                else:
                    rationale = f"Despite high price sensitivity (elasticity: {e:.2f}), recommend {abs(price_change_pct):.1f}% price increase "
                    rationale += f"based on cost structure and margin requirements."
            else:  # Moderate elasticity
                direction = "increase" if price_change > 0 else "decrease"
                rationale = f"Moderate price sensitivity (elasticity: {e:.2f}) suggests a balanced approach. "
                rationale += f"Recommend {abs(price_change_pct):.1f}% price {direction} to optimize margin while maintaining sales volume."
        
        # Add competitor context if available
        if competitor_prices:
            avg_competitor_price = sum(competitor_prices) / len(competitor_prices)
            price_vs_competitors = ((current_price / avg_competitor_price) - 1) * 100 if avg_competitor_price > 0 else 0
            new_price_vs_competitors = ((optimal_price / avg_competitor_price) - 1) * 100 if avg_competitor_price > 0 else 0
            
            if abs(price_vs_competitors) > 10:  # Significant deviation from competitors
                if price_vs_competitors > 0:
                    rationale += f" Currently priced {price_vs_competitors:.1f}% above competitors. "
                else:
                    rationale += f" Currently priced {abs(price_vs_competitors):.1f}% below competitors. "
                    
            rationale += f" New price would position item {new_price_vs_competitors:.1f}% "
            rationale += "above" if new_price_vs_competitors > 0 else "below"
            rationale += f" the competitor average of ${avg_competitor_price:.2f}."
        
        # Add cost context if available
        if item.get("cost"):
            current_margin = (current_price - item["cost"]) / current_price if current_price > 0 else 0
            optimal_margin = (optimal_price - item["cost"]) / optimal_price if optimal_price > 0 else 0
            margin_change = optimal_margin - current_margin
            
            rationale += f" Current margin: {current_margin:.1%}. Recommended margin: {optimal_margin:.1%} "
            direction = "increase" if margin_change > 0 else "decrease"
            rationale += f"({direction} of {abs(margin_change):.1%})."
        
        return rationale.strip()
        
    def _determine_strategy_type(self, item: Dict, elasticity: Dict, market: Dict) -> str:
        """Determine the type of pricing strategy for an item"""
        if elasticity and abs(elasticity.get("elasticity", 0)) < 0.5:
            return "premium_pricing"
        elif elasticity and abs(elasticity.get("elasticity", 0)) > 1.5:
            return "penetration_pricing"
        else:
            return "competitive_pricing"
    
    def _recommend_timing(self, item: Dict, market: Dict) -> str:
        """Recommend timing for price changes"""
        # Consider seasonal patterns and market trends
        seasonal = market.get("market_trends", {}).get("sales_trends", {}).get("seasonal_patterns", [])
        
        if "holiday_season" in seasonal:
            return "implement_before_holidays"
        elif "weekend_peaks" in seasonal:
            return "implement_midweek"
        else:
            return "implement_immediately"
    
    def _estimate_impact(self, item: Dict, elasticity: Dict) -> Dict[str, float]:
        """Estimate impact of price change"""
        if elasticity and "elasticity" in elasticity:
            e = elasticity["elasticity"]
            price_change = 0.05  # 5% change assumption
            quantity_change = e * price_change
            revenue_change = (1 + price_change) * (1 + quantity_change) - 1
            
            return {
                "expected_quantity_change": quantity_change,
                "expected_revenue_change": revenue_change
            }
        else:
            return {
                "expected_quantity_change": -0.02,  # Conservative estimate
                "expected_revenue_change": 0.03
            }
    
    def _calculate_confidence(self, elasticity: Dict, competitive: Dict) -> float:
        """Calculate confidence in the recommendation"""
        confidence = 0.5  # Base confidence
        
        if elasticity and "elasticity" in elasticity:
            confidence += 0.3  # Have elasticity data
        
        if competitive and competitive.get("competitors"):
            confidence += 0.2  # Have competitive data
        
        return min(confidence, 1.0)
    
    def _get_top_items(self, revenue: Dict[int, float], n: int) -> List[Tuple[int, float]]:
        """Get top n items by revenue"""
        sorted_items = sorted(revenue.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:n]
    
    def _calculate_concentration(self, revenue: Dict[int, float]) -> float:
        """Calculate revenue concentration (Herfindahl index)"""
        if not revenue:
            return 0
        total = sum(revenue.values())
        shares = [r/total for r in revenue.values()]
        return sum(s**2 for s in shares)
    
    def _analyze_item_associations(self, orders: List[Dict]) -> Dict[Tuple[int, int], int]:
        """Analyze which items are frequently bought together"""
        associations = {}
        for order in orders:
            items = order.get("items", [])
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    pair = tuple(sorted([items[i]["item_id"], items[j]["item_id"]]))
                    associations[pair] = associations.get(pair, 0) + 1
        return associations
    
    def _determine_category_strategy(self, avg_change: float) -> str:
        """Determine category-level strategy"""
        if avg_change > 0.05:
            return "category_wide_increase"
        elif avg_change < -0.05:
            return "category_wide_decrease"
        else:
            return "item_specific_optimization"
