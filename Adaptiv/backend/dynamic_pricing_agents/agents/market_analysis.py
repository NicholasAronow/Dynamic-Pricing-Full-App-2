"""
Market Analysis Agent with Memory - Analyzes market conditions and competitive landscape
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..base_agent import BaseAgent
import numpy as np
# Import memory models directly from models.py
from models import (
    MarketAnalysisSnapshot,
    CompetitorPriceHistory,
    AgentMemory,
    PricingDecision
)


class MarketAnalysisAgent(BaseAgent):
    """Agent responsible for analyzing market conditions and competitive positioning with memory"""
    
    def __init__(self):
        super().__init__("MarketAnalysisAgent", model="gpt-4o-mini")
        self.logger.info("Market Analysis Agent with memory initialized")
        
    def get_system_prompt(self) -> str:
        return """You are a Market Analysis Agent specializing in competitive pricing intelligence with memory capabilities. Your role is to:
        1. Analyze competitor pricing strategies and market positioning
        2. Determine price elasticity from historical data
        3. Assess competitive threats and opportunities
        4. Provide market-based pricing recommendations
        5. Track competitor strategy changes over time
        
        Use statistical analysis, market intelligence, and historical patterns to provide actionable insights."""
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market conditions and competitive landscape with memory"""
        data = context['consolidated_data']
        db = context.get('db')
        user_id = data['user_id']
        
        self.log_action("market_analysis_started", {"user_id": user_id})
        
        # Get memory context
        memory_context = self.get_memory_context(
            db, user_id,
            memory_types=['market_insight', 'competitive_analysis', 'elasticity_learning', 'seasonal_pattern'],
            days_back=180  # Look back 6 months for seasonal patterns
        )
        
        # Get previous market snapshots
        previous_snapshots = self._get_previous_snapshots(db, user_id, limit=10)
        
        # Perform various market analyses with historical context
        competitive_analysis = self._analyze_competitive_landscape_with_memory(data, db, user_id, memory_context)
        elasticity_analysis = self._calculate_price_elasticity_with_memory(data, db, user_id, memory_context)
        market_trends = self._identify_market_trends_with_memory(data, previous_snapshots, memory_context, db)
        positioning_analysis = self._analyze_market_positioning_with_memory(data, previous_snapshots)
        
        # Predict future market conditions based on history
        market_predictions = self._predict_market_conditions(previous_snapshots, market_trends, memory_context, db, user_id)
        
        # Use LLM to generate insights with historical context
        insights = self._generate_market_insights_with_memory({
            "competitive_analysis": competitive_analysis,
            "elasticity_analysis": elasticity_analysis,
            "market_trends": market_trends,
            "positioning_analysis": positioning_analysis,
            "market_predictions": market_predictions,
            "historical_accuracy": self._evaluate_prediction_accuracy(db, user_id)
        }, db, user_id)
        
        # Generate strategic recommendations
        recommendations = self._generate_strategic_recommendations_with_memory(
            insights, memory_context, db, user_id
        )
        
        analysis_results = {
            "analysis_timestamp": datetime.now().isoformat(),
            "competitive_landscape": competitive_analysis,
            "price_elasticity": elasticity_analysis,
            "market_trends": market_trends,
            "market_positioning": positioning_analysis,
            "market_predictions": market_predictions,
            "insights": insights,
            "recommendations": recommendations,
            "historical_context": {
                "previous_predictions_accuracy": self._evaluate_prediction_accuracy(db, user_id),
                "recurring_patterns": self._identify_recurring_patterns(memory_context),
                "strategy_evolution": self._analyze_strategy_evolution(previous_snapshots)
            }
        }
        
        # Save market analysis snapshot
        self._save_analysis_snapshot(db, user_id, analysis_results)
        
        # Track key insights as memories
        self._track_key_insights(db, user_id, insights)
        
        self.log_action("market_analysis_completed", {
            "competitors_analyzed": len(competitive_analysis.get("competitors", [])),
            "items_analyzed": len(elasticity_analysis.get("item_elasticities", [])),
            "predictions_made": len(market_predictions.get("predictions", []))
        })
        
        return analysis_results
    
    def _get_previous_snapshots(self, db: Session, user_id: int, limit: int = 10) -> List[MarketAnalysisSnapshot]:
        """Get previous market analysis snapshots"""
        return db.query(MarketAnalysisSnapshot).filter(
            MarketAnalysisSnapshot.user_id == user_id
        ).order_by(desc(MarketAnalysisSnapshot.analysis_date)).limit(limit).all()
    
    def _analyze_competitive_landscape_with_memory(self, data: Dict[str, Any], db: Session, 
                                               user_id: int, memory_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze competitor pricing and strategies with historical context"""
        competitors_data = data.get("competitor_data", {}).get("competitors", [])
        our_items = data.get("pos_data", {}).get("items", [])
        
        # Get historical competitor strategies from memory
        competitor_memories = memory_context.get('competitive_analysis', [])
        
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
                    # Protect against division by zero
                    if our_item["current_price"] > 0:
                        price_diff = (comp_item["price"] - our_item["current_price"]) / our_item["current_price"] * 100
                    else:
                        price_diff = 0  # Default when current price is zero
                    price_comparisons.append({
                        "item": our_item["name"],
                        "our_price": our_item["current_price"],
                        "competitor_price": comp_item["price"],
                        "difference_percent": price_diff,
                        "price_trend": comp_item.get("price_trend", "unknown")
                    })
            
            if price_comparisons:
                avg_price_diff = np.mean([pc["difference_percent"] for pc in price_comparisons])
                
                # Get historical strategy for this competitor
                historical_strategy = self._get_competitor_historical_strategy(
                    competitor["name"], competitor_memories
                )
                
                # Detect strategy changes
                current_strategy = self._infer_pricing_strategy(avg_price_diff)
                strategy_changed = (historical_strategy and 
                                   historical_strategy != current_strategy)
                
                competitor_analysis.append({
                    "competitor": competitor["name"],
                    "avg_price_difference": avg_price_diff,
                    "price_comparisons": price_comparisons,
                    "current_strategy": current_strategy,
                    "historical_strategy": historical_strategy,
                    "strategy_changed": strategy_changed,
                    "price_volatility": self._calculate_competitor_volatility(
                        competitor["name"], db, user_id
                    ),
                    "competitive_threat_level": self._assess_threat_level(
                        avg_price_diff, strategy_changed, len(price_comparisons)
                    )
                })
        
        # Save competitor analysis as memory
        if competitor_analysis:
            self.save_memory(
                db, user_id, 'competitive_analysis',
                {
                    'competitors': [{
                        'name': ca['competitor'],
                        'strategy': ca['current_strategy'],
                        'avg_price_diff': ca['avg_price_difference'],
                        'threat_level': ca['competitive_threat_level']
                    } for ca in competitor_analysis],
                    'analysis_date': datetime.now().isoformat()
                }
            )
        
        return {
            "competitors": competitor_analysis,
            "market_summary": {
                "total_competitors": len(competitor_analysis),
                "avg_market_price_diff": np.mean([ca["avg_price_difference"] for ca in competitor_analysis]) if competitor_analysis else 0,
                "high_threat_competitors": len([ca for ca in competitor_analysis if ca["competitive_threat_level"] == "high"]),
                "strategy_changes_detected": len([ca for ca in competitor_analysis if ca["strategy_changed"]])
            }
        }
        
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
                    # Protect against division by zero
                    if our_item["current_price"] > 0:
                        price_diff = (comp_item["price"] - our_item["current_price"]) / our_item["current_price"] * 100
                    else:
                        price_diff = 0  # Default when current price is zero
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
    
    def _calculate_price_elasticity_with_memory(self, data: Dict[str, Any], db: Session,
                                              user_id: int, memory_context: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate price elasticity with learning from past calculations"""
        price_history = data.get("price_history", {}).get("changes", [])
        orders = data.get("pos_data", {}).get("orders", [])
        
        # Get previous elasticity learnings
        elasticity_memories = memory_context.get('elasticity_learning', [])
        
        # Group price changes by item
        item_changes = {}
        for change in price_history:
            item_id = change["item_id"]
            if item_id not in item_changes:
                item_changes[item_id] = []
            item_changes[item_id].append(change)
        
        elasticities = []
        for item_id, changes in item_changes.items():
            if len(changes) >= 2:
                elasticity = self._calculate_item_elasticity(item_id, changes, orders)
                if elasticity is not None:
                    # Check if we have historical elasticity for this item
                    historical_elasticity = self._get_historical_elasticity(
                        item_id, elasticity_memories
                    )
                    
                    # Calculate confidence based on consistency with history
                    confidence = self._calculate_elasticity_confidence(
                        elasticity, historical_elasticity, len(changes)
                    )
                    
                    elasticities.append({
                        "item_id": item_id,
                        "elasticity": elasticity,
                        "historical_elasticity": historical_elasticity,
                        "confidence": confidence,
                        "interpretation": self._interpret_elasticity(elasticity),
                        "stability": "stable" if historical_elasticity and abs(elasticity - historical_elasticity) < 0.2 else "changing"
                    })
        
        # Save elasticity learnings
        if elasticities:
            self.save_memory(
                db, user_id, 'elasticity_learning',
                {
                    'elasticities': {str(e['item_id']): e['elasticity'] for e in elasticities},
                    'calculation_date': datetime.now().isoformat(),
                    'confidence_scores': {str(e['item_id']): e['confidence'] for e in elasticities}
                }
            )
        
        return {
            "item_elasticities": elasticities,
            "summary": {
                "avg_elasticity": np.mean([e["elasticity"] for e in elasticities]) if elasticities else None,
                "elastic_items": len([e for e in elasticities if abs(e["elasticity"]) > 1]),
                "inelastic_items": len([e for e in elasticities if abs(e["elasticity"]) <= 1]),
                "high_confidence_items": len([e for e in elasticities if e["confidence"] > 0.8])
            },
            "category_elasticities": self._calculate_category_elasticities(elasticities, data)
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
    
    def _identify_market_trends_with_memory(self, data: Dict[str, Any], 
                                          previous_snapshots: List[MarketAnalysisSnapshot],
                                          memory_context: Dict[str, Any],
                                          db: Session) -> Dict[str, Any]:
        """Identify market trends with seasonal pattern recognition"""
        orders = data.get("pos_data", {}).get("orders", [])
        market_conditions = data.get("market_data", {}).get("market_conditions", {})
        
        # Get seasonal patterns from memory
        seasonal_memories = memory_context.get('seasonal_pattern', [])
        
        # Analyze sales trends
        daily_sales = self._aggregate_daily_sales(orders)
        weekly_trends = self._calculate_weekly_trends(daily_sales)
        
        # Detect seasonal patterns with historical context
        current_patterns = self._detect_seasonal_patterns(orders)
        historical_patterns = self._get_historical_seasonal_patterns(seasonal_memories)
        
        # Identify recurring vs new patterns
        recurring_patterns = []
        new_patterns = []
        for pattern in current_patterns:
            if pattern in historical_patterns:
                recurring_patterns.append(pattern)
            else:
                new_patterns.append(pattern)
        
        # Predict upcoming seasonal events
        upcoming_events = self._predict_seasonal_events(
            historical_patterns, datetime.now()
        )
        
        # Save seasonal patterns as memory
        if current_patterns:
            self.save_memory(
                db, data['user_id'], 'seasonal_pattern',
                {
                    'patterns': current_patterns,
                    'detection_date': datetime.now().isoformat(),
                    'confidence': 0.8 if recurring_patterns else 0.5
                }
            )
        
        return {
            "sales_trends": {
                "weekly_growth": weekly_trends,
                "seasonal_patterns": {
                    "current": current_patterns,
                    "recurring": recurring_patterns,
                    "new": new_patterns
                },
                "upcoming_seasonal_events": upcoming_events
            },
            "market_factors": market_conditions,
            "trend_summary": self._summarize_trends_with_history(
                weekly_trends, current_patterns, market_conditions, previous_snapshots
            ),
            "trend_confidence": self._calculate_trend_confidence(
                recurring_patterns, historical_patterns
            )
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
    
    def _analyze_market_positioning_with_memory(self, data: Dict[str, Any], 
                                              previous_snapshots: List[MarketAnalysisSnapshot]) -> Dict[str, Any]:
        """Analyze market positioning with historical context"""
        competitive_data = self._analyze_competitive_landscape(
            data  # Simplified call, no memory context here
        )
        our_items = data.get("pos_data", {}).get("items", [])
        
        # Current positioning
        current_position = self._determine_price_position(competitive_data)
        
        # Historical positions
        historical_positions = [s.market_position for s in previous_snapshots if s.market_position]
        
        # Check position stability
        position_stable = True
        if historical_positions and len(set(historical_positions[:3])) > 1:
            position_stable = False
        
        positioning = {
            "price_position": current_position,
            "historical_positions": historical_positions[:5],
            "position_stable": position_stable,
            "category_positioning": self._analyze_category_positioning(our_items, competitive_data),
            "value_proposition": self._assess_value_proposition(data),
            "positioning_trend": self._analyze_positioning_trend(historical_positions, current_position)
        }
        
        return positioning
    
    def _analyze_positioning_trend(self, historical: List[str], current: str) -> str:
        """Analyze trend in market positioning"""
        if not historical:
            return "new_data"
        
        position_values = {
            "significantly_below_market": -2,
            "below_market": -1,
            "at_market": 0,
            "above_market": 1,
            "premium_to_market": 2
        }
        
        current_value = position_values.get(current, 0)
        historical_values = [position_values.get(p, 0) for p in historical[:3]]
        
        if not historical_values:
            return "unknown"
        
        avg_historical = np.mean(historical_values)
        
        if current_value > avg_historical + 0.5:
            return "moving_upmarket"
        elif current_value < avg_historical - 0.5:
            return "moving_downmarket"
        else:
            return "maintaining_position"
    
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
    
    def _predict_market_conditions(self, snapshots: List[MarketAnalysisSnapshot],
                                 current_trends: Dict[str, Any],
                                 memory_context: Dict[str, Any],
                                 db: Session, user_id: int) -> Dict[str, Any]:
        """Predict future market conditions based on historical patterns"""
        if not snapshots:
            return {"predictions": [], "confidence": "low"}
        
        # Analyze historical market positions
        position_history = [s.market_position for s in snapshots if s.market_position]
        
        # Analyze competitive landscape evolution
        competitor_trends = self._analyze_competitor_evolution(snapshots)
        
        # Use LLM to generate predictions
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"""
            Based on historical market data and patterns, predict future market conditions:
            
            Historical Market Positions: {position_history[:5]}
            
            Current Trends: {json.dumps(current_trends, indent=2)}
            
            Competitor Evolution: {json.dumps(competitor_trends, indent=2)}
            
            Previous Predictions from Memory: {json.dumps([m['content'] for m in memory_context.get('market_insight', [])[:3]], indent=2)}
            
            Please provide:
            1. Market predictions for next 30 days
            2. Confidence levels for each prediction
            3. Key factors driving predictions
            4. Recommended actions
            
            Format as JSON.
            """}
        ]
        
        response = self.call_llm_with_memory(messages, db, user_id)
        
        predictions = {"predictions": [], "confidence": "medium"}
        if response.get("content") and not response.get("error"):
            try:
                predictions = json.loads(response["content"])
                
                # Save predictions as memory for future accuracy evaluation
                self.save_memory(
                    db, user_id, 'market_prediction',
                    {
                        'predictions': predictions,
                        'prediction_date': datetime.now().isoformat(),
                        'based_on_trends': current_trends
                    }
                )
            except:
                self.logger.warning("Failed to parse market predictions")
        
        return predictions
        
    def _analyze_competitor_evolution(self, snapshots: List[MarketAnalysisSnapshot]) -> Dict[str, Any]:
        """Analyze how competitor strategies have evolved"""
        if not snapshots:
            return {}
        
        evolution = {}
        for snapshot in snapshots[:5]:  # Last 5 snapshots
            if snapshot.competitor_strategies:
                for comp, strategy in snapshot.competitor_strategies.items():
                    if comp not in evolution:
                        evolution[comp] = []
                    evolution[comp].append({
                        "date": snapshot.analysis_date.isoformat(),
                        "strategy": strategy
                    })
        
        # Analyze strategy changes
        strategy_changes = {}
        for comp, history in evolution.items():
            if len(history) > 1:
                changes = sum(1 for i in range(1, len(history)) 
                            if history[i]['strategy'] != history[i-1]['strategy'])
                strategy_changes[comp] = {
                    "stability": "stable" if changes == 0 else "dynamic",
                    "change_count": changes,
                    "current_strategy": history[0]['strategy'] if history else "unknown"
                }
        
        return strategy_changes
        
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
                # Try to parse as JSON
                return json.loads(content)
            except:
                # Otherwise return as text
                return {"insights": content}
        else:
            return {"error": "No content in response"}
    
    def _generate_market_insights_with_memory(self, analyses: Dict[str, Any], 
                                            db: Session, user_id: int) -> Dict[str, Any]:
        """Generate market insights using LLM with historical context"""
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"""
            Based on the following market analyses with historical context, provide strategic insights:
            
            Competitive Analysis: {json.dumps(analyses['competitive_analysis'], indent=2)}
            
            Price Elasticity: {json.dumps(analyses['elasticity_analysis'], indent=2)}
            
            Market Trends: {json.dumps(analyses['market_trends'], indent=2)}
            
            Market Positioning: {json.dumps(analyses['positioning_analysis'], indent=2)}
            
            Market Predictions: {json.dumps(analyses['market_predictions'], indent=2)}
            
            Historical Prediction Accuracy: {json.dumps(analyses['historical_accuracy'], indent=2)}
            
            Provide insights on:
            1. Key competitive threats and opportunities
            2. Items with pricing power vs. price-sensitive items
            3. Market trend implications for pricing
            4. Strategic positioning recommendations
            5. Confidence in market predictions based on historical accuracy
            6. Seasonal considerations for next 90 days
            
            Format as JSON with categories: competitive_insights, elasticity_insights, trend_insights, positioning_insights, prediction_confidence
            """}
        ]
        
        response = self.call_llm_with_memory(messages, db, user_id)
        
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
        """Generate strategic recommendations based on insights"""
        recommendations = []
        
        # Add specific recommendations based on insights
        if isinstance(insights, dict):
            for key, value in insights.items():
                if isinstance(value, list):
                    recommendations.extend(value)
                elif isinstance(value, str):
                    recommendations.append(value)
        
        return recommendations[:5]  # Top 5 recommendations
    
    def _generate_strategic_recommendations_with_memory(self, insights: Dict[str, Any],
                                                      memory_context: Dict[str, Any],
                                                      db: Session, user_id: int) -> List[str]:
        """Generate strategic recommendations based on insights and memory"""
        recommendations = []
        
        # Extract recommendations from insights
        if isinstance(insights, dict):
            for key, value in insights.items():
                if isinstance(value, list):
                    recommendations.extend(value[:2])  # Take top 2 from each category
                elif isinstance(value, str):
                    recommendations.append(value)
        
        # Add recommendations based on recurring patterns
        recurring_patterns = self._identify_recurring_patterns(memory_context)
        for pattern in recurring_patterns[:3]:
            recommendations.append(f"Prepare for recurring pattern: {pattern['pattern']}")
        
        # Track strategic recommendations
        if recommendations:
            self.track_decision(
                db, user_id,
                decision_type="market_analysis_recommendations",
                affected_items=[],  # General market recommendations
                rationale="Market analysis based on competitive landscape and trends",
                supporting_data={
                    "insights": insights,
                    "patterns": recurring_patterns
                },
                confidence=0.8
            )
        
        return recommendations[:10]  # Top 10 recommendations
    
    def _save_analysis_snapshot(self, db: Session, user_id: int, analysis: Dict[str, Any]):
        """Save market analysis snapshot"""
        competitive = analysis['competitive_landscape']
        elasticity = analysis['price_elasticity']
        
        snapshot = MarketAnalysisSnapshot(
            user_id=user_id,
            market_position=analysis['market_positioning']['price_position'],
            avg_price_vs_market=competitive['market_summary']['avg_market_price_diff'],
            avg_elasticity=elasticity['summary']['avg_elasticity'],
            elastic_items_count=elasticity['summary']['elastic_items'],
            inelastic_items_count=elasticity['summary']['inelastic_items'],
            market_trends=analysis['market_trends']['sales_trends'],
            seasonal_patterns=analysis['market_trends']['sales_trends']['seasonal_patterns']['current'],
            competitor_strategies={c['competitor']: c['current_strategy'] for c in competitive['competitors']},
            competitive_threats=[c['competitor'] for c in competitive['competitors'] if c['competitive_threat_level'] == 'high'],
            competitive_opportunities=analysis['recommendations'][:3],
            key_insights=analysis['insights'],
            strategic_recommendations=analysis['recommendations']
        )
        
        db.add(snapshot)
        db.commit()
        
        self.logger.info(f"Saved market analysis snapshot for user {user_id}")
    
    def _track_key_insights(self, db: Session, user_id: int, insights: Dict[str, Any]):
        """Track key market insights as memories"""
        if isinstance(insights, dict):
            # Extract key insights
            for insight_type, insight_content in insights.items():
                if insight_content and insight_type in ['competitive_insights', 'elasticity_insights', 'trend_insights']:
                    self.save_memory(
                        db, user_id, 'market_insight',
                        {
                            'type': insight_type,
                            'insight': insight_content,
                            'timestamp': datetime.now().isoformat()
                        }
                    )
    
    def _evaluate_prediction_accuracy(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Evaluate accuracy of past market predictions"""
        # Get predictions made 30+ days ago
        cutoff = datetime.now() - timedelta(days=30)
        
        past_predictions = db.query(AgentMemory).filter(
            AgentMemory.agent_name == self.agent_name,
            AgentMemory.user_id == user_id,
            AgentMemory.memory_type == 'market_prediction',
            AgentMemory.created_at <= cutoff
        ).order_by(desc(AgentMemory.created_at)).limit(10).all()
        
        if not past_predictions:
            return {"message": "No past predictions to evaluate"}
        
        # Compare predictions with actual outcomes
        accuracy_scores = []
        for pred_memory in past_predictions:
            prediction = pred_memory.content
            # This is simplified - in production, you'd compare specific metrics
            # For now, we'll use a placeholder accuracy score
            accuracy_scores.append({
                "prediction_date": pred_memory.created_at.isoformat(),
                "accuracy_score": 0.75,  # Placeholder
                "prediction_summary": prediction.get('predictions', [])[:1]
            })
        
        return {
            "evaluations": accuracy_scores,
            "average_accuracy": np.mean([s['accuracy_score'] for s in accuracy_scores]),
            "improving": accuracy_scores[0]['accuracy_score'] > accuracy_scores[-1]['accuracy_score'] if len(accuracy_scores) > 1 else False
        }
    
    def _identify_recurring_patterns(self, memory_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify recurring patterns from memory"""
        patterns = []
        
        # Analyze seasonal patterns
        seasonal_memories = memory_context.get('seasonal_pattern', [])
        if seasonal_memories:
            from collections import Counter
            all_patterns = []
            for mem in seasonal_memories:
                all_patterns.extend(mem.get('content', {}).get('patterns', []))
            
            pattern_counts = Counter(all_patterns)
            for pattern, count in pattern_counts.most_common(5):
                if count >= 2:
                    patterns.append({
                        "pattern": pattern,
                        "frequency": count,
                        "type": "seasonal"
                    })
        
        return patterns
    
    def _analyze_strategy_evolution(self, snapshots: List[MarketAnalysisSnapshot]) -> Dict[str, Any]:
        """Analyze how market strategies have evolved over time"""
        if not snapshots:
            return {"message": "No historical data"}
        
        positions = [s.market_position for s in snapshots if s.market_position]
        if not positions:
            return {"message": "No position data"}
        
        # Analyze position changes
        position_changes = []
        for i in range(1, len(positions)):
            if positions[i] != positions[i-1]:
                position_changes.append({
                    "from": positions[i-1],
                    "to": positions[i],
                    "snapshot_date": snapshots[i-1].analysis_date.isoformat()
                })
        
        return {
            "position_changes": position_changes,
            "current_position": positions[0] if positions else "unknown",
            "stability": "stable" if len(position_changes) == 0 else "evolving"
        }
    def _get_competitor_historical_strategy(self, competitor_name: str, 
                                          competitor_memories: List[Dict]) -> Optional[str]:
        """Get historical strategy for a competitor"""
        for memory in competitor_memories:
            competitors = memory.get('content', {}).get('competitors', [])
            for comp in competitors:
                if comp['name'] == competitor_name:
                    return comp.get('strategy')
        return None
    
    def _calculate_competitor_volatility(self, competitor_name: str, 
                                       db: Session, user_id: int) -> str:
        """Calculate competitor price volatility"""
        # Get competitor price history
        history = db.query(CompetitorPriceHistory).filter(
            CompetitorPriceHistory.user_id == user_id,
            CompetitorPriceHistory.competitor_name == competitor_name,
            CompetitorPriceHistory.captured_at >= datetime.now() - timedelta(days=90)
        ).all()
        
        if len(history) < 5:
            return "unknown"
        
        # Calculate price changes
        price_changes = [abs(h.percent_change_from_last) for h in history if h.percent_change_from_last]
        
        if not price_changes:
            return "stable"
        
        avg_change = np.mean(price_changes)
        if avg_change < 2:
            return "low"
        elif avg_change < 5:
            return "medium"
        else:
            return "high"
    
    def _assess_threat_level(self, avg_price_diff: float, strategy_changed: bool, 
                           item_count: int) -> str:
        """Assess competitive threat level"""
        threat_score = 0
        
        # Price aggressiveness
        if avg_price_diff < -10:  # Competitor significantly cheaper
            threat_score += 3
        elif avg_price_diff < -5:
            threat_score += 2
        elif avg_price_diff < 0:
            threat_score += 1
        
        # Strategy change
        if strategy_changed:
            threat_score += 2
        
        # Market coverage
        if item_count > 20:
            threat_score += 2
        elif item_count > 10:
            threat_score += 1
        
        if threat_score >= 5:
            return "high"
        elif threat_score >= 3:
            return "medium"
        else:
            return "low"
            
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
    
    def _get_historical_elasticity(self, item_id: int, elasticity_memories: List[Dict]) -> Optional[float]:
        """Get historical elasticity for an item"""
        for memory in elasticity_memories:
            elasticities = memory.get('content', {}).get('elasticities', {})
            if str(item_id) in elasticities:
                return elasticities[str(item_id)]
        return None
    
    def _calculate_elasticity_confidence(self, current: float, historical: Optional[float], 
                                       data_points: int) -> float:
        """Calculate confidence in elasticity measurement"""
        confidence = 0.5  # Base confidence
        
        # More data points = higher confidence
        confidence += min(data_points * 0.05, 0.25)
        
        # Consistency with history = higher confidence
        if historical is not None:
            consistency = 1 - min(abs(current - historical) / max(abs(historical), 1), 1)
            confidence += consistency * 0.25
        
        return min(confidence, 1.0)
        
    def _calculate_category_elasticities(self, elasticities: List[Dict], data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Calculate elasticity by category"""
        items = data.get("pos_data", {}).get("items", [])
        
        # Create item to category mapping
        item_categories = {item["id"]: item.get("category", "Other") for item in items}
        
        # Group elasticities by category
        from collections import defaultdict
        category_elasticities = defaultdict(list)
        
        for e in elasticities:
            category = item_categories.get(e["item_id"], "Other")
            category_elasticities[category].append(e["elasticity"])
        
        # Calculate category averages
        category_summary = {}
        for category, elasts in category_elasticities.items():
            if elasts:
                category_summary[category] = {
                    "avg_elasticity": np.mean(elasts),
                    "item_count": len(elasts),
                    "interpretation": self._interpret_elasticity(np.mean(elasts))
                }
        
        return category_summary
        
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
        if not daily_sales:
            return {"trend": "unknown", "growth_rate": 0}
        
        # Group by week
        from collections import defaultdict
        weekly_sales = defaultdict(float)
        
        for date_str, sales in daily_sales.items():
            date = datetime.fromisoformat(date_str)
            week = date.isocalendar()[1]
            year = date.year
            weekly_sales[f"{year}-W{week}"] += sales
        
        # Calculate trend
        weeks = sorted(weekly_sales.keys())
        if len(weeks) >= 2:
            recent_week = weekly_sales[weeks[-1]]
            previous_week = weekly_sales[weeks[-2]]
            
            if previous_week > 0:
                growth_rate = (recent_week - previous_week) / previous_week
                trend = "growing" if growth_rate > 0.05 else "declining" if growth_rate < -0.05 else "stable"
                return {"trend": trend, "growth_rate": growth_rate}
        
        return {"trend": "stable", "growth_rate": 0}
    
    def _get_historical_seasonal_patterns(self, seasonal_memories: List[Dict]) -> List[str]:
        """Extract historical seasonal patterns"""
        all_patterns = []
        for memory in seasonal_memories:
            patterns = memory.get('content', {}).get('patterns', [])
            all_patterns.extend(patterns)
        
        # Return unique patterns that appear multiple times
        from collections import Counter
        pattern_counts = Counter(all_patterns)
        return [pattern for pattern, count in pattern_counts.items() if count >= 2]
    
    def _predict_seasonal_events(self, historical_patterns: List[str], 
                               current_date: datetime) -> List[Dict[str, Any]]:
        """Predict upcoming seasonal events"""
        predictions = []
        
        # Simple seasonal predictions based on patterns
        month = current_date.month
        
        if "holiday_season" in historical_patterns and month in [10, 11, 12]:
            predictions.append({
                "event": "holiday_season",
                "expected_start": "Within 30 days",
                "confidence": 0.9,
                "recommended_action": "Prepare holiday pricing strategy"
            })
        
        if "summer_peak" in historical_patterns and month in [4, 5]:
            predictions.append({
                "event": "summer_peak",
                "expected_start": "Within 60 days",
                "confidence": 0.8,
                "recommended_action": "Plan for increased summer demand"
            })
        
        return predictions
    
    def _detect_seasonal_patterns(self, orders: List[Dict]) -> List[str]:
        """Detect seasonal patterns in sales"""
        # Implementation would analyze sales by time of year
        return ["holiday_boost", "weekend_peaks"]
    
    def _items_match(self, item1_name: str, item2_name: str) -> bool:
        """Check if two item names match, allowing for fuzzy matching"""
        # Remove common words and standardize
        item1 = item1_name.lower().strip()
        item2 = item2_name.lower().strip()
        
        # Exact match
        if item1 == item2:
            return True
            
        # Check if one is contained in the other
        if item1 in item2 or item2 in item1:
            return True
            
        # Check for word-level similarity
        words1 = set(item1.split())
        words2 = set(item2.split())
        
        # If they share at least half of their words, consider it a match
        common_words = words1.intersection(words2)
        if len(common_words) >= min(len(words1), len(words2)) / 2:
            return True
            
        return False
    
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
        summary_parts = []
        
        # Weekly trend
        if weekly.get("trend") == "growing":
            summary_parts.append(f"Growing {weekly.get('growth_rate', 0)*100:.1f}% week-over-week")
        elif weekly.get("trend") == "declining":
            summary_parts.append(f"Declining {abs(weekly.get('growth_rate', 0))*100:.1f}% week-over-week")
        else:
            summary_parts.append("Stable weekly performance")
        
        # Seasonal patterns
        if seasonal:
            summary_parts.append(f"Seasonal patterns: {', '.join(seasonal)}")
        
        # Market conditions
        if market.get("inflation_rate", 0) > 3:
            summary_parts.append("High inflation environment")
        
        return ". ".join(summary_parts)
    
    def _summarize_trends_with_history(self, weekly: Dict, patterns: List[str], 
                                     market: Dict, snapshots: List[MarketAnalysisSnapshot]) -> str:
        """Summarize trends with historical context"""
        base_summary = self._summarize_trends(weekly, patterns, market)
        
        # Add historical context
        if snapshots:
            historical_trends = [s.market_trends for s in snapshots[:3] if s.market_trends]
            if historical_trends:
                # Check if trends are consistent
                current_trend = weekly.get("trend", "unknown")
                historical_trend_types = [t.get("weekly_growth", {}).get("trend") for t in historical_trends if t.get("weekly_growth")]
                
                if historical_trend_types and all(t == current_trend for t in historical_trend_types):
                    base_summary += ". Trend has been consistent over past analyses"
                elif historical_trend_types:
                    base_summary += ". Trend has shifted from previous patterns"
        
        return base_summary
    
    def _calculate_trend_confidence(self, recurring: List[str], historical: List[str]) -> float:
        """Calculate confidence in trend identification"""
        if not historical:
            return 0.5
        
        if not recurring:
            return 0.3
        
        # Higher confidence if current patterns match historical
        overlap = len(set(recurring) & set(historical))
        confidence = 0.5 + (overlap / len(historical)) * 0.5
        
        return min(confidence, 1.0)
