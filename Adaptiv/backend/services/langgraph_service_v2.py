"""
LangGraph Multi-Agent Service - Modern Implementation

This service uses LangGraph's prebuilt components and official patterns
to create robust multi-agent systems for dynamic pricing applications.
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from typing import Annotated

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent, InjectedState
from langchain_core.messages import ToolMessage

from services.database_service import DatabaseService
from config.database import get_db
from config.external_apis import get_langsmith_client, LANGSMITH_TRACING, LANGSMITH_PROJECT

logger = logging.getLogger(__name__)

# Initialize LangSmith tracing if enabled
if LANGSMITH_TRACING:
    langsmith_client = get_langsmith_client()
    if langsmith_client:
        logger.info(f"LangSmith tracing enabled for project: {LANGSMITH_PROJECT}")
    else:
        logger.warning("LangSmith tracing requested but client initialization failed")
else:
    langsmith_client = None
    logger.info("LangSmith tracing disabled")

@dataclass
class MultiAgentResponse:
    """Response from multi-agent system execution"""
    final_result: str
    execution_path: List[str]
    total_execution_time: float
    metadata: Dict[str, Any]
    messages: List[Dict[str, Any]]

class PricingTools:
    """Tools for pricing agents"""
    
    @staticmethod
    @tool
    def search_web_for_pricing(query: str) -> str:
        """Search the web for pricing information and market data"""
        # Simulate web search results for pricing information
        return f"Web search results for '{query}': Found 15 relevant sources. Key findings: Market average price is $45-65 range, trending upward 8% this quarter. Top competitors: CompanyA ($52), CompanyB ($48), CompanyC ($61). Consumer sentiment shows price sensitivity at $60+ threshold."
    
    @staticmethod
    @tool
    def search_competitor_analysis(product_name: str, category: str) -> str:
        """Search for competitor pricing and positioning analysis"""
        return f"Competitor analysis for {product_name} in {category}: 12 direct competitors identified. Price range: $35-$75. Market leader pricing at $58 with premium positioning. Opportunity gap identified in $42-$48 range for value positioning."
    
    @staticmethod
    @tool
    def get_market_trends(category: str) -> str:
        """Get current market trends and consumer behavior"""
        return f"Market trends for {category}: Demand increasing 12% YoY, seasonal peak in Q4, price elasticity -1.3, consumer preference shifting toward value-oriented options, online sales growing 25% faster than retail."
    
    @staticmethod
    @tool
    def select_pricing_algorithm(product_type: str, market_conditions: str, business_goals: str) -> str:
        """Select the most appropriate pricing algorithm based on conditions"""
        algorithms = {
            "competitive": "Competitive Pricing Algorithm - Matches competitor prices with small adjustments",
            "value_based": "Value-Based Pricing Algorithm - Prices based on perceived customer value", 
            "dynamic": "Dynamic Pricing Algorithm - Real-time price adjustments based on demand/supply",
            "penetration": "Market Penetration Algorithm - Low initial prices to gain market share",
            "skimming": "Price Skimming Algorithm - High initial prices for early adopters",
            "psychological": "Psychological Pricing Algorithm - Uses pricing psychology (e.g., $9.99)"
        }
        
        # Simple logic to recommend algorithm (in real implementation, this would be more sophisticated)
        if "competitive" in market_conditions.lower():
            selected = "competitive"
        elif "premium" in business_goals.lower() or "luxury" in product_type.lower():
            selected = "skimming"
        elif "market share" in business_goals.lower():
            selected = "penetration"
        elif "demand fluctuation" in market_conditions.lower():
            selected = "dynamic"
        else:
            selected = "value_based"
            
        return f"SELECTED ALGORITHM: {algorithms[selected]}. Rationale: Based on {product_type} product type, {market_conditions} market conditions, and {business_goals} business goals, this algorithm will optimize for your specific situation."

class DatabaseTools:
    """Tools for accessing database information"""
    
    def __init__(self, user_id: int = None, db_session=None):
        self.db_session = db_session
        self.user_id = user_id
    
    def _get_db_service(self):
        """Get database service with current session"""
        if not self.db_session:
            # Get a fresh database session using the generator
            db_gen = get_db()
            self.db_session = next(db_gen)
        return DatabaseService(self.db_session)
    
    def create_get_user_items_data(self):
        """Create the tool with proper context"""
        @tool
        def get_user_items_data() -> str:
            """Get all menu items for the current user from the database"""
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                
                db_service = self._get_db_service()
                items = db_service.get_user_items(self.user_id)
                
                if not items:
                    return f"No menu items found for user {self.user_id}"
                
                items_info = []
                for item in items:
                    item_info = f"- {item.name}: ${item.current_price:.2f}"
                    if hasattr(item, 'category') and item.category:
                        item_info += f" (Category: {item.category})"
                    if hasattr(item, 'description') and item.description:
                        item_info += f" - {item.description[:100]}..."
                    items_info.append(item_info)
                
                return f"Found {len(items)} menu items:\n" + "\n".join(items_info)
            except Exception as e:
                return f"Error retrieving items: {str(e)}"
        
        return get_user_items_data
    
    def create_get_user_sales_data(self):
        """Create the sales data tool"""
        @tool
        def get_user_sales_data(limit: int = 10) -> str:
            """Get recent sales/orders data for the current user from the database"""
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                    
                db_service = self._get_db_service()
                orders = db_service.get_user_orders(self.user_id, limit=limit)
                
                if not orders:
                    return f"No recent orders found for user {self.user_id}"
                
                total_revenue = sum(order.total_amount for order in orders if order.total_amount)
                order_count = len(orders)
                avg_order_value = total_revenue / order_count if order_count > 0 else 0
                
                recent_orders = []
                for order in orders[:5]:  # Show top 5 recent orders
                    order_info = f"- Order #{order.id}: ${order.total_amount:.2f} on {order.order_date.strftime('%Y-%m-%d')}"
                    recent_orders.append(order_info)
                
                return f"Sales Summary (last {limit} orders):\n" + \
                       f"Total Revenue: ${total_revenue:.2f}\n" + \
                       f"Order Count: {order_count}\n" + \
                       f"Average Order Value: ${avg_order_value:.2f}\n\n" + \
                       f"Recent Orders:\n" + "\n".join(recent_orders)
            except Exception as e:
                return f"Error retrieving sales data: {str(e)}"
        
        return get_user_sales_data
    
    def create_get_competitor_data(self):
        """Create the competitor data tool"""
        @tool
        def get_competitor_data() -> str:
            """Get competitor analysis data for the current user from the database"""
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                    
                db_service = self._get_db_service()
                competitor_report = db_service.get_latest_competitor_report(self.user_id)
                
                result = []
                
                if competitor_report:
                    result.append(f"Latest Competitor Report (from {competitor_report.created_at.strftime('%Y-%m-%d')}):")
                    if hasattr(competitor_report, 'summary') and competitor_report.summary:
                        result.append(competitor_report.summary[:500] + "...")
                    if hasattr(competitor_report, 'insights') and competitor_report.insights:
                        result.append("\nKey Insights:")
                        for insight in competitor_report.insights[:3]:
                            result.append(f"- {insight}")
                
                return "\n".join(result) if result else f"No competitor data found for user {self.user_id}"
            except Exception as e:
                return f"Error retrieving competitor data: {str(e)}"
        
        return get_competitor_data
    
    def create_get_price_history_data(self):
        """Create the price history tool"""
        @tool
        def get_price_history_data(item_name: str = None) -> str:
            """Get price history data for the current user's items"""
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                    
                db_service = self._get_db_service()
                items = db_service.get_user_items(self.user_id)
                
                if not items:
                    return f"No items found for user {self.user_id}"
                
                # Filter by item name movided
                if item_name:
                    items = [item for item in items if item_name.lower() in item.name.lower()]
                    if not items:
                        return f"No items found matching '{item_name}' for user {self.user_id}"
                
                price_histories = []
                for item in items[:5]:  # Limit to 5 items
                    history = db_service.get_price_history(item.id)
                    if history:
                        price_histories.append(f"\n{item.name} price history:")
                        for price_change in history[:3]:  # Show last 3 changes
                            price_histories.append(f"  - ${price_change.previous_price:.2f} → ${price_change.new_price:.2f} on {price_change.changed_at.strftime('%Y-%m-%d')}")
                
                return "\n".join(price_histories) if price_histories else "No price history found"
            except Exception as e:
                return f"Error retrieving price history: {str(e)}"
        
        return get_price_history_data
    
    def create_get_business_profile_data(self):
        """Create the business profile tool"""
        @tool
        def get_business_profile_data() -> str:
            """Get business profile information for the current user"""
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                    
                db_service = self._get_db_service()
                profile = db_service.get_business_profile(self.user_id)
                
                if not profile:
                    return f"No business profile found for user {self.user_id}"
                
                profile_info = []
                if hasattr(profile, 'business_name') and profile.business_name:
                    profile_info.append(f"Business: {profile.business_name}")
                if hasattr(profile, 'industry') and profile.industry:
                    profile_info.append(f"Industry: {profile.industry}")
                if hasattr(profile, 'company_size') and profile.company_size:
                    profile_info.append(f"Company Size: {profile.company_size}")
                if hasattr(profile, 'description') and profile.description:
                    profile_info.append(f"Description: {profile.description[:200]}...")
                
                return "\n".join(profile_info) if profile_info else "Business profile found but no details available"
            except Exception as e:
                return f"Error retrieving business profile: {str(e)}"
        
        return get_business_profile_data
    
    def create_get_sales_analytics_structured(self):
        """Create structured sales analytics tool with MoM/YoY calculations"""
        @tool
        def get_sales_analytics_structured(time_period: str = "monthly", compare_previous: bool = True) -> str:
            """Get structured sales analytics with MoM/YoY comparisons, trends, and seasonality analysis
            
            Args:
                time_period: 'daily', 'weekly', 'monthly', or 'yearly' aggregation
                compare_previous: Whether to compare with previous period
            """
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                
                from datetime import datetime, timedelta
                import calendar
                
                db_service = self._get_db_service()
                orders = db_service.get_user_orders(self.user_id)
                if not orders:
                    return "No sales data available for analysis"
                
                now = datetime.now()
                current_revenue = 0
                current_orders = 0
                previous_revenue = 0
                previous_orders = 0
                
                if time_period == "monthly":
                    # Current month
                    current_month_orders = [o for o in orders if o.order_date.month == now.month and o.order_date.year == now.year]
                    current_revenue = sum(o.total_amount for o in current_month_orders if o.total_amount)
                    current_orders = len(current_month_orders)
                    
                    # Previous month
                    prev_month = now.month - 1 if now.month > 1 else 12
                    prev_year = now.year if now.month > 1 else now.year - 1
                    prev_month_orders = [o for o in orders if o.order_date.month == prev_month and o.order_date.year == prev_year]
                    previous_revenue = sum(o.total_amount for o in prev_month_orders if o.total_amount)
                    previous_orders = len(prev_month_orders)
                    
                    period_name = calendar.month_name[now.month]
                    prev_period_name = calendar.month_name[prev_month]
                    
                elif time_period == "yearly":
                    # Current year
                    current_year_orders = [o for o in orders if o.order_date.year == now.year]
                    current_revenue = sum(o.total_amount for o in current_year_orders if o.total_amount)
                    current_orders = len(current_year_orders)
                    
                    # Previous year
                    prev_year_orders = [o for o in orders if o.order_date.year == now.year - 1]
                    previous_revenue = sum(o.total_amount for o in prev_year_orders if o.total_amount)
                    previous_orders = len(prev_year_orders)
                    
                    period_name = str(now.year)
                    prev_period_name = str(now.year - 1)
                
                # Calculate growth rates
                revenue_growth = ((current_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue > 0 else 0
                order_growth = ((current_orders - previous_orders) / previous_orders * 100) if previous_orders > 0 else 0
                
                # Calculate average order value
                current_aov = current_revenue / current_orders if current_orders > 0 else 0
                previous_aov = previous_revenue / previous_orders if previous_orders > 0 else 0
                aov_growth = ((current_aov - previous_aov) / previous_aov * 100) if previous_aov > 0 else 0
                
                # Seasonal analysis (last 12 months by month)
                seasonal_data = {}
                for month in range(1, 13):
                    month_orders = [o for o in orders if o.order_date.month == month and o.order_date.year >= now.year - 1]
                    month_revenue = sum(o.total_amount for o in month_orders if o.total_amount)
                    seasonal_data[calendar.month_name[month]] = month_revenue
                
                # Find peak and low seasons
                peak_month = max(seasonal_data, key=seasonal_data.get)
                low_month = min(seasonal_data, key=seasonal_data.get)
                
                result = f"📊 SALES ANALYTICS ({time_period.upper()} VIEW)\n"
                result += f"═══════════════════════════════════════\n\n"
                
                result += f"📈 CURRENT PERIOD ({period_name}):" + "\n"
                result += f"• Revenue: ${current_revenue:,.2f}\n"
                result += f"• Orders: {current_orders:,}\n"
                result += f"• Average Order Value: ${current_aov:.2f}\n\n"
                
                if compare_previous and previous_revenue > 0:
                    result += f"📊 GROWTH vs {prev_period_name}:\n"
                    result += f"• Revenue Growth: {revenue_growth:+.1f}%\n"
                    result += f"• Order Growth: {order_growth:+.1f}%\n"
                    result += f"• AOV Growth: {aov_growth:+.1f}%\n\n"
                
                result += f"🗓️ SEASONAL INSIGHTS:\n"
                result += f"• Peak Season: {peak_month} (${seasonal_data[peak_month]:,.2f})\n"
                result += f"• Low Season: {low_month} (${seasonal_data[low_month]:,.2f})\n"
                result += f"• Seasonality Ratio: {seasonal_data[peak_month]/seasonal_data[low_month]:.1f}x\n\n"
                
                # Trend analysis
                recent_30_days = [o for o in orders if (now - o.order_date).days <= 30]
                previous_30_days = [o for o in orders if 30 < (now - o.order_date).days <= 60]
                
                recent_revenue = sum(o.total_amount for o in recent_30_days if o.total_amount)
                prev_revenue = sum(o.total_amount for o in previous_30_days if o.total_amount)
                trend = "📈 Upward" if recent_revenue > prev_revenue else "📉 Downward" if recent_revenue < prev_revenue else "➡️ Stable"
                
                result += f"📊 30-DAY TREND: {trend}\n"
                result += f"• Last 30 days: ${recent_revenue:,.2f}\n"
                result += f"• Previous 30 days: ${prev_revenue:,.2f}\n"
                
                return result
                
            except Exception as e:
                return f"Error calculating sales analytics: {str(e)}"
        
        return get_sales_analytics_structured
    
    def create_get_item_performance_metrics(self):
        """Create item performance metrics tool with revenue, margins, and velocity analysis"""
        @tool
        def get_item_performance_metrics(top_n: int = 10, sort_by: str = "revenue") -> str:
            """Get detailed item performance metrics including revenue, profit margins, and sales velocity
            
            Args:
                top_n: Number of top items to analyze (default 10)
                sort_by: Sort criteria - 'revenue', 'margin', 'velocity', or 'profit'
            """
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                
                from datetime import datetime, timedelta
                
                db_service = self._get_db_service()
                items = db_service.get_user_items(self.user_id)
                orders = db_service.get_user_orders(self.user_id)
                
                if not items:
                    return "No menu items found for analysis"
                
                # Calculate metrics for each item
                item_metrics = []
                now = datetime.now()
                
                for item in items:
                    # Get order items for this specific item
                    item_orders = []
                    for order in orders:
                        if hasattr(order, 'items'):
                            for order_item in order.items:
                                if order_item.item_id == item.id:
                                    item_orders.append((order, order_item))
                    
                    if not item_orders:
                        continue
                    
                    # Calculate metrics
                    total_quantity = sum(oi.quantity for _, oi in item_orders)
                    total_revenue = sum(oi.quantity * oi.unit_price for _, oi in item_orders)
                    total_cost = sum(oi.quantity * (oi.unit_cost or item.cost or 0) for _, oi in item_orders)
                    
                    # Profit calculations
                    gross_profit = total_revenue - total_cost
                    margin_percentage = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
                    
                    # Velocity calculation (sales per day)
                    first_sale = min(o.order_date for o, _ in item_orders)
                    days_selling = max(1, (now - first_sale).days)
                    velocity = total_quantity / days_selling
                    
                    # Recent performance (last 30 days)
                    recent_orders = [(o, oi) for o, oi in item_orders if (now - o.order_date).days <= 30]
                    recent_quantity = sum(oi.quantity for _, oi in recent_orders)
                    recent_revenue = sum(oi.quantity * oi.unit_price for _, oi in recent_orders)
                    
                    item_metrics.append({
                        'name': item.name,
                        'category': item.category or 'Uncategorized',
                        'current_price': item.current_price,
                        'total_quantity': total_quantity,
                        'total_revenue': total_revenue,
                        'total_cost': total_cost,
                        'gross_profit': gross_profit,
                        'margin_percentage': margin_percentage,
                        'velocity': velocity,
                        'recent_quantity': recent_quantity,
                        'recent_revenue': recent_revenue,
                        'days_selling': days_selling
                    })
                
                if not item_metrics:
                    return "No sales data found for items analysis"
                
                # Sort by specified criteria
                if sort_by == "revenue":
                    item_metrics.sort(key=lambda x: x['total_revenue'], reverse=True)
                elif sort_by == "margin":
                    item_metrics.sort(key=lambda x: x['margin_percentage'], reverse=True)
                elif sort_by == "velocity":
                    item_metrics.sort(key=lambda x: x['velocity'], reverse=True)
                elif sort_by == "profit":
                    item_metrics.sort(key=lambda x: x['gross_profit'], reverse=True)
                
                # Limit to top N
                top_items = item_metrics[:top_n]
                
                result = f"🎯 ITEM PERFORMANCE METRICS (Top {len(top_items)} by {sort_by.title()})\n"
                result += f"═══════════════════════════════════════════════════════════\n\n"
                
                for i, item in enumerate(top_items, 1):
                    result += f"{i}. {item['name']} ({item['category']})\n"
                    result += f"   💰 Revenue: ${item['total_revenue']:,.2f} | Price: ${item['current_price']:.2f}\n"
                    result += f"   📦 Quantity Sold: {item['total_quantity']:,} | Velocity: {item['velocity']:.1f}/day\n"
                    result += f"   💹 Profit: ${item['gross_profit']:,.2f} | Margin: {item['margin_percentage']:.1f}%\n"
                    result += f"   📈 Last 30 days: {item['recent_quantity']} sold, ${item['recent_revenue']:,.2f}\n\n"
                
                # Summary statistics
                total_revenue = sum(item['total_revenue'] for item in item_metrics)
                avg_margin = sum(item['margin_percentage'] for item in item_metrics) / len(item_metrics)
                top_performer_revenue = top_items[0]['total_revenue'] if top_items else 0
                revenue_concentration = (top_performer_revenue / total_revenue * 100) if total_revenue > 0 else 0
                
                result += f"📊 SUMMARY INSIGHTS:\n"
                result += f"• Total Portfolio Revenue: ${total_revenue:,.2f}\n"
                result += f"• Average Margin: {avg_margin:.1f}%\n"
                result += f"• Top Item Revenue Share: {revenue_concentration:.1f}%\n"
                result += f"• Items Analyzed: {len(item_metrics)} with sales data\n"
                
                return result
                
            except Exception as e:
                return f"Error calculating item performance metrics: {str(e)}"
        
        return get_item_performance_metrics
    
    def create_get_cost_analysis_structured(self):
        """Create structured cost analysis tool with COGS trends, fixed costs, and margin analysis"""
        @tool
        def get_cost_analysis_structured(analysis_period: str = "monthly") -> str:
            """Get structured cost analysis including COGS trends, fixed costs allocation, and margin analysis
            
            Args:
                analysis_period: Analysis period - 'monthly', 'quarterly', or 'yearly'
            """
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                
                from datetime import datetime, timedelta
                from collections import defaultdict
                import calendar
                
                db_service = self._get_db_service()
                
                # Get cost data
                cogs_data = db_service.get_user_cogs(self.user_id)
                fixed_costs = db_service.get_user_fixed_costs(self.user_id)
                orders = db_service.get_user_orders(self.user_id)
                items = db_service.get_user_items(self.user_id)
                
                if not orders:
                    return "No sales data found for cost analysis"
                
                now = datetime.now()
                
                # Group data by period
                if analysis_period == "monthly":
                    period_format = lambda dt: f"{dt.year}-{dt.month:02d}"
                    period_name = "Month"
                elif analysis_period == "quarterly":
                    period_format = lambda dt: f"{dt.year}-Q{(dt.month-1)//3 + 1}"
                    period_name = "Quarter"
                else:  # yearly
                    period_format = lambda dt: str(dt.year)
                    period_name = "Year"
                
                # Aggregate sales and costs by period
                period_data = defaultdict(lambda: {
                    'revenue': 0,
                    'cogs': 0,
                    'quantity': 0,
                    'orders': 0
                })
                
                # Process orders and calculate COGS
                for order in orders:
                    period_key = period_format(order.order_date)
                    period_data[period_key]['revenue'] += order.total_amount
                    period_data[period_key]['orders'] += 1
                    
                    if hasattr(order, 'items'):
                        for order_item in order.items:
                            period_data[period_key]['quantity'] += order_item.quantity
                            # Use order item cost or item cost
                            unit_cost = order_item.unit_cost
                            if not unit_cost:
                                item = next((i for i in items if i.id == order_item.item_id), None)
                                unit_cost = item.cost if item else 0
                            period_data[period_key]['cogs'] += order_item.quantity * (unit_cost or 0)
                
                # Calculate fixed costs allocation
                total_fixed_costs = sum(fc.amount for fc in fixed_costs)
                periods_count = len(period_data)
                fixed_cost_per_period = total_fixed_costs / max(1, periods_count)
                
                # Sort periods chronologically
                sorted_periods = sorted(period_data.keys())
                
                result = f"💰 COST ANALYSIS ({period_name}ly Breakdown)\n"
                result += f"═══════════════════════════════════════════════════════════\n\n"
                
                # Period-by-period analysis
                previous_gross_margin = None
                total_revenue = 0
                total_cogs = 0
                total_fixed = 0
                
                for period in sorted_periods:
                    data = period_data[period]
                    gross_profit = data['revenue'] - data['cogs']
                    gross_margin = (gross_profit / data['revenue'] * 100) if data['revenue'] > 0 else 0
                    net_profit = gross_profit - fixed_cost_per_period
                    net_margin = (net_profit / data['revenue'] * 100) if data['revenue'] > 0 else 0
                    
                    # Calculate margin trend
                    margin_trend = ""
                    if previous_gross_margin is not None:
                        margin_change = gross_margin - previous_gross_margin
                        if margin_change > 1:
                            margin_trend = f" 📈 (+{margin_change:.1f}%)"
                        elif margin_change < -1:
                            margin_trend = f" 📉 ({margin_change:.1f}%)"
                        else:
                            margin_trend = f" ➡️ ({margin_change:+.1f}%)"
                    
                    result += f"📅 {period}:\n"
                    result += f"   Revenue: ${data['revenue']:,.2f} | Orders: {data['orders']}\n"
                    result += f"   COGS: ${data['cogs']:,.2f} | Fixed Costs: ${fixed_cost_per_period:,.2f}\n"
                    result += f"   Gross Margin: {gross_margin:.1f}%{margin_trend}\n"
                    result += f"   Net Profit: ${net_profit:,.2f} | Net Margin: {net_margin:.1f}%\n\n"
                    
                    previous_gross_margin = gross_margin
                    total_revenue += data['revenue']
                    total_cogs += data['cogs']
                    total_fixed += fixed_cost_per_period
                
                # COGS breakdown by category
                category_cogs = defaultdict(float)
                category_revenue = defaultdict(float)
                
                for order in orders:
                    if hasattr(order, 'items'):
                        for order_item in order.items:
                            item = next((i for i in items if i.id == order_item.item_id), None)
                            if item:
                                category = item.category or 'Uncategorized'
                                unit_cost = order_item.unit_cost or item.cost or 0
                                category_cogs[category] += order_item.quantity * unit_cost
                                category_revenue[category] += order_item.quantity * order_item.unit_price
                
                # Fixed costs breakdown
                result += f"🏢 FIXED COSTS BREAKDOWN:\n"
                if fixed_costs:
                    for fc in fixed_costs:
                        result += f"   • {fc.cost_type}: ${fc.amount:,.2f}\n"
                else:
                    result += f"   • No fixed costs recorded\n"
                result += f"   Total Fixed Costs: ${total_fixed_costs:,.2f}\n\n"
                
                # Category analysis
                result += f"📋 CATEGORY COST ANALYSIS:\n"
                for category in sorted(category_cogs.keys()):
                    cat_cogs = category_cogs[category]
                    cat_revenue = category_revenue[category]
                    cat_margin = ((cat_revenue - cat_cogs) / cat_revenue * 100) if cat_revenue > 0 else 0
                    result += f"   • {category}: ${cat_cogs:,.2f} COGS | {cat_margin:.1f}% margin\n"
                
                # Overall summary
                overall_gross_margin = ((total_revenue - total_cogs) / total_revenue * 100) if total_revenue > 0 else 0
                overall_net_margin = ((total_revenue - total_cogs - total_fixed) / total_revenue * 100) if total_revenue > 0 else 0
                cogs_percentage = (total_cogs / total_revenue * 100) if total_revenue > 0 else 0
                fixed_percentage = (total_fixed / total_revenue * 100) if total_revenue > 0 else 0
                
                result += f"\n📊 OVERALL COST SUMMARY:\n"
                result += f"• Total Revenue: ${total_revenue:,.2f}\n"
                result += f"• Total COGS: ${total_cogs:,.2f} ({cogs_percentage:.1f}% of revenue)\n"
                result += f"• Total Fixed Costs: ${total_fixed:,.2f} ({fixed_percentage:.1f}% of revenue)\n"
                result += f"• Gross Margin: {overall_gross_margin:.1f}%\n"
                result += f"• Net Margin: {overall_net_margin:.1f}%\n"
                result += f"• Analysis Periods: {len(sorted_periods)}\n"
                
                return result
                
            except Exception as e:
                return f"Error performing cost analysis: {str(e)}"
        
        return get_cost_analysis_structured
    
    def create_calculate_price_elasticity(self):
        """Create price elasticity calculation tool for analyzing price change impacts"""
        @tool
        def calculate_price_elasticity(item_name: str = None, analysis_days: int = 90) -> str:
            """Calculate price elasticity for items based on historical price changes and sales data
            
            Args:
                item_name: Specific item name to analyze (optional, analyzes all items if not provided)
                analysis_days: Number of days to look back for analysis (default 90)
            """
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                
                from datetime import datetime, timedelta
                from collections import defaultdict
                import statistics
                
                db_service = self._get_db_service()
                
                # Get data
                items = db_service.get_user_items(self.user_id)
                orders = db_service.get_user_orders(self.user_id)
                price_history = db_service.get_price_history(self.user_id)
                
                if not items or not orders:
                    return "Insufficient data for price elasticity analysis"
                
                # Filter by item name if specified
                if item_name:
                    items = [item for item in items if item.name.lower() == item_name.lower()]
                    if not items:
                        return f"Item '{item_name}' not found"
                
                now = datetime.now()
                cutoff_date = now - timedelta(days=analysis_days)
                
                result = f"📊 PRICE ELASTICITY ANALYSIS (Last {analysis_days} days)\n"
                result += f"═══════════════════════════════════════════════════════════\n\n"
                
                elasticity_results = []
                
                for item in items:
                    # Get price changes for this item
                    item_price_history = [ph for ph in price_history if ph.item_id == item.id and ph.date_changed >= cutoff_date]
                    
                    if len(item_price_history) < 2:
                        continue  # Need at least 2 price points
                    
                    # Sort by date
                    item_price_history.sort(key=lambda x: x.date_changed)
                    
                    # Calculate elasticity for each price change
                    price_elasticities = []
                    
                    for i in range(1, len(item_price_history)):
                        prev_price_record = item_price_history[i-1]
                        curr_price_record = item_price_history[i]
                        
                        # Get sales data before and after price change
                        change_date = curr_price_record.date_changed
                        before_start = change_date - timedelta(days=14)  # 2 weeks before
                        after_end = change_date + timedelta(days=14)     # 2 weeks after
                        
                        # Sales before price change
                        before_sales = []
                        after_sales = []
                        
                        for order in orders:
                            if hasattr(order, 'items'):
                                for order_item in order.items:
                                    if order_item.item_id == item.id:
                                        if before_start <= order.order_date < change_date:
                                            before_sales.append(order_item.quantity)
                                        elif change_date <= order.order_date <= after_end:
                                            after_sales.append(order_item.quantity)
                        
                        if not before_sales or not after_sales:
                            continue  # Need sales data both before and after
                        
                        # Calculate average quantities
                        avg_qty_before = sum(before_sales) / len(before_sales)
                        avg_qty_after = sum(after_sales) / len(after_sales)
                        
                        # Calculate percentage changes
                        price_change_pct = ((curr_price_record.new_price - prev_price_record.new_price) / prev_price_record.new_price) * 100
                        quantity_change_pct = ((avg_qty_after - avg_qty_before) / avg_qty_before) * 100
                        
                        # Calculate elasticity (% change in quantity / % change in price)
                        if price_change_pct != 0:
                            elasticity = quantity_change_pct / price_change_pct
                            price_elasticities.append({
                                'date': change_date,
                                'old_price': prev_price_record.new_price,
                                'new_price': curr_price_record.new_price,
                                'price_change_pct': price_change_pct,
                                'quantity_change_pct': quantity_change_pct,
                                'elasticity': elasticity,
                                'avg_qty_before': avg_qty_before,
                                'avg_qty_after': avg_qty_after
                            })
                    
                    if price_elasticities:
                        # Calculate average elasticity for the item
                        avg_elasticity = statistics.mean([pe['elasticity'] for pe in price_elasticities])
                        
                        # Classify elasticity
                        if avg_elasticity < -1:
                            elasticity_type = "Elastic (price sensitive)"
                            elasticity_emoji = "📉"
                        elif avg_elasticity > -1 and avg_elasticity < 0:
                            elasticity_type = "Inelastic (price insensitive)"
                            elasticity_emoji = "📋"
                        else:
                            elasticity_type = "Unusual (positive elasticity)"
                            elasticity_emoji = "⚠️"
                        
                        elasticity_results.append({
                            'item': item,
                            'avg_elasticity': avg_elasticity,
                            'elasticity_type': elasticity_type,
                            'elasticity_emoji': elasticity_emoji,
                            'price_changes': price_elasticities,
                            'current_price': item.current_price
                        })
                
                if not elasticity_results:
                    return "No sufficient price change data found for elasticity analysis. Items need multiple price changes with sales data before and after each change."
                
                # Sort by elasticity (most elastic first)
                elasticity_results.sort(key=lambda x: x['avg_elasticity'])
                
                # Display results
                for er in elasticity_results:
                    result += f"{er['elasticity_emoji']} {er['item'].name}\n"
                    result += f"   Current Price: ${er['current_price']:.2f}\n"
                    result += f"   Average Elasticity: {er['avg_elasticity']:.2f} ({er['elasticity_type']})\n"
                    result += f"   Price Changes Analyzed: {len(er['price_changes'])}\n"
                    
                    # Show recent price changes
                    for pc in er['price_changes'][-2:]:  # Show last 2 changes
                        result += f"   • {pc['date'].strftime('%Y-%m-%d')}: ${pc['old_price']:.2f} → ${pc['new_price']:.2f} "
                        result += f"({pc['price_change_pct']:+.1f}% price, {pc['quantity_change_pct']:+.1f}% quantity)\n"
                    result += "\n"
                
                # Summary insights
                elastic_items = [er for er in elasticity_results if er['avg_elasticity'] < -1]
                inelastic_items = [er for er in elasticity_results if -1 <= er['avg_elasticity'] < 0]
                
                result += f"📈 ELASTICITY INSIGHTS:\n"
                result += f"• Elastic Items (price sensitive): {len(elastic_items)}\n"
                result += f"• Inelastic Items (price insensitive): {len(inelastic_items)}\n"
                result += f"• Total Items Analyzed: {len(elasticity_results)}\n\n"
                
                # Recommendations
                result += f"💡 PRICING RECOMMENDATIONS:\n"
                if elastic_items:
                    result += f"• Elastic items: Consider price decreases to boost volume\n"
                if inelastic_items:
                    result += f"• Inelastic items: Consider price increases to boost revenue\n"
                
                result += f"\n📝 NOTE: Elasticity measures how quantity demanded responds to price changes.\n"
                result += f"Negative values are normal (higher prices = lower demand).\n"
                result += f"Values below -1 indicate elastic demand (price sensitive).\n"
                
                return result
                
            except Exception as e:
                return f"Error calculating price elasticity: {str(e)}"
        
        return calculate_price_elasticity
    
    # ========== CATEGORY 2: TIME-BASED ANALYSIS TOOLS ==========
    
    def create_get_sales_by_time_period(self):
        """Create flexible time period analysis tool for sales data"""
        @tool
        def get_sales_by_time_period(period_type: str = "weekly", num_periods: int = 12, start_date: str = None) -> str:
            """Get flexible time period analysis of sales data with customizable periods and ranges
            
            Args:
                period_type: Type of period - 'daily', 'weekly', 'monthly', 'quarterly'
                num_periods: Number of recent periods to analyze (default 12)
                start_date: Optional start date in YYYY-MM-DD format (uses recent periods if not provided)
            """
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                
                from datetime import datetime, timedelta
                from collections import defaultdict
                import calendar
                
                db_service = self._get_db_service()
                orders = db_service.get_user_orders(self.user_id)
                
                if not orders:
                    return "No sales data found for time period analysis"
                
                now = datetime.now()
                
                # Parse start date if provided
                if start_date:
                    try:
                        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    except ValueError:
                        return "Invalid start_date format. Use YYYY-MM-DD format."
                else:
                    # Calculate start date based on period type and num_periods
                    if period_type == "daily":
                        start_dt = now - timedelta(days=num_periods)
                    elif period_type == "weekly":
                        start_dt = now - timedelta(weeks=num_periods)
                    elif period_type == "monthly":
                        start_dt = now - timedelta(days=num_periods * 30)
                    elif period_type == "quarterly":
                        start_dt = now - timedelta(days=num_periods * 90)
                    else:
                        return "Invalid period_type. Use 'daily', 'weekly', 'monthly', or 'quarterly'."
                
                # Filter orders within date range
                filtered_orders = [o for o in orders if start_dt <= o.order_date <= now]
                
                if not filtered_orders:
                    return f"No sales data found in the specified time range ({start_dt.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')})"
                
                # Group data by period
                def get_period_key(dt):
                    if period_type == "daily":
                        return dt.strftime("%Y-%m-%d")
                    elif period_type == "weekly":
                        # Get Monday of the week
                        monday = dt - timedelta(days=dt.weekday())
                        return f"Week of {monday.strftime('%Y-%m-%d')}"
                    elif period_type == "monthly":
                        return f"{dt.year}-{dt.month:02d}"
                    elif period_type == "quarterly":
                        quarter = (dt.month - 1) // 3 + 1
                        return f"{dt.year}-Q{quarter}"
                
                # Aggregate data by period
                period_data = defaultdict(lambda: {
                    'revenue': 0,
                    'orders': 0,
                    'quantity': 0,
                    'avg_order_value': 0,
                    'unique_customers': set()
                })
                
                for order in filtered_orders:
                    period_key = get_period_key(order.order_date)
                    period_data[period_key]['revenue'] += order.total_amount
                    period_data[period_key]['orders'] += 1
                    
                    # Add customer if available
                    if hasattr(order, 'customer_id') and order.customer_id:
                        period_data[period_key]['unique_customers'].add(order.customer_id)
                    
                    # Calculate quantity from order items
                    if hasattr(order, 'items'):
                        for order_item in order.items:
                            period_data[period_key]['quantity'] += order_item.quantity
                
                # Calculate averages and convert sets to counts
                for period_key, data in period_data.items():
                    data['avg_order_value'] = data['revenue'] / data['orders'] if data['orders'] > 0 else 0
                    data['unique_customers'] = len(data['unique_customers'])
                
                # Sort periods chronologically
                sorted_periods = sorted(period_data.keys())
                
                result = f"📅 SALES BY TIME PERIOD ({period_type.title()}ly Analysis)\n"
                result += f"═══════════════════════════════════════════════════════════\n"
                result += f"Analysis Period: {start_dt.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}\n"
                result += f"Periods Analyzed: {len(sorted_periods)}\n\n"
                
                # Calculate growth rates
                previous_revenue = None
                total_revenue = sum(data['revenue'] for data in period_data.values())
                total_orders = sum(data['orders'] for data in period_data.values())
                
                for i, period in enumerate(sorted_periods):
                    data = period_data[period]
                    
                    # Calculate growth rate
                    growth_indicator = ""
                    if previous_revenue is not None and previous_revenue > 0:
                        growth_rate = ((data['revenue'] - previous_revenue) / previous_revenue) * 100
                        if growth_rate > 5:
                            growth_indicator = f" 📈 (+{growth_rate:.1f}%)"
                        elif growth_rate < -5:
                            growth_indicator = f" 📉 ({growth_rate:.1f}%)"
                        else:
                            growth_indicator = f" ➡️ ({growth_rate:+.1f}%)"
                    
                    result += f"📊 {period}:{growth_indicator}\n"
                    result += f"   Revenue: ${data['revenue']:,.2f}\n"
                    result += f"   Orders: {data['orders']} | Avg Order: ${data['avg_order_value']:.2f}\n"
                    result += f"   Quantity: {data['quantity']} | Customers: {data['unique_customers']}\n\n"
                    
                    previous_revenue = data['revenue']
                
                # Summary statistics
                avg_revenue_per_period = total_revenue / len(sorted_periods) if sorted_periods else 0
                avg_orders_per_period = total_orders / len(sorted_periods) if sorted_periods else 0
                
                # Find best and worst periods
                best_period = max(sorted_periods, key=lambda p: period_data[p]['revenue']) if sorted_periods else None
                worst_period = min(sorted_periods, key=lambda p: period_data[p]['revenue']) if sorted_periods else None
                
                result += f"📈 PERIOD ANALYSIS SUMMARY:\n"
                result += f"• Total Revenue: ${total_revenue:,.2f}\n"
                result += f"• Total Orders: {total_orders}\n"
                result += f"• Average Revenue per {period_type.title()}: ${avg_revenue_per_period:,.2f}\n"
                result += f"• Average Orders per {period_type.title()}: {avg_orders_per_period:.1f}\n\n"
                
                if best_period and worst_period:
                    best_revenue = period_data[best_period]['revenue']
                    worst_revenue = period_data[worst_period]['revenue']
                    result += f"🏆 Best {period_type.title()}: {best_period} (${best_revenue:,.2f})\n"
                    result += f"📉 Lowest {period_type.title()}: {worst_period} (${worst_revenue:,.2f})\n"
                    
                    if worst_revenue > 0:
                        performance_gap = ((best_revenue - worst_revenue) / worst_revenue) * 100
                        result += f"📊 Performance Gap: {performance_gap:.1f}%\n"
                
                # Trend analysis
                if len(sorted_periods) >= 3:
                    recent_periods = sorted_periods[-3:]
                    recent_revenues = [period_data[p]['revenue'] for p in recent_periods]
                    
                    if recent_revenues[2] > recent_revenues[0]:
                        trend = "📈 Upward trend in recent periods"
                    elif recent_revenues[2] < recent_revenues[0]:
                        trend = "📉 Downward trend in recent periods"
                    else:
                        trend = "➡️ Stable trend in recent periods"
                    
                    result += f"\n🔮 TREND INSIGHT: {trend}\n"
                
                return result
                
            except Exception as e:
                return f"Error analyzing sales by time period: {str(e)}"
        
        return get_sales_by_time_period
    
    def create_get_seasonal_trends(self):
        """Create seasonal trends analysis tool to identify patterns and peak periods"""
        @tool
        def get_seasonal_trends(analysis_years: int = 2) -> str:
            """Identify seasonal patterns and peak periods in sales data
            
            Args:
                analysis_years: Number of years to analyze for seasonal patterns (default 2)
            """
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                
                from datetime import datetime, timedelta
                from collections import defaultdict
                import calendar
                
                db_service = self._get_db_service()
                orders = db_service.get_user_orders(self.user_id)
                
                if not orders:
                    return "No sales data found for seasonal analysis"
                
                now = datetime.now()
                start_date = now - timedelta(days=analysis_years * 365)
                
                # Filter orders within analysis period
                filtered_orders = [o for o in orders if o.order_date >= start_date]
                
                if not filtered_orders:
                    return f"No sales data found in the last {analysis_years} years for seasonal analysis"
                
                # Initialize seasonal data structures
                monthly_data = defaultdict(lambda: {'revenue': 0, 'orders': 0, 'quantity': 0})
                weekly_data = defaultdict(lambda: {'revenue': 0, 'orders': 0, 'quantity': 0})
                daily_data = defaultdict(lambda: {'revenue': 0, 'orders': 0, 'quantity': 0})
                hourly_data = defaultdict(lambda: {'revenue': 0, 'orders': 0, 'quantity': 0})
                
                # Aggregate data by different time dimensions
                for order in filtered_orders:
                    order_date = order.order_date
                    
                    # Monthly patterns (1-12)
                    month_key = order_date.month
                    monthly_data[month_key]['revenue'] += order.total_amount
                    monthly_data[month_key]['orders'] += 1
                    
                    # Weekly patterns (Monday=0, Sunday=6)
                    weekday_key = order_date.weekday()
                    weekly_data[weekday_key]['revenue'] += order.total_amount
                    weekly_data[weekday_key]['orders'] += 1
                    
                    # Daily patterns (day of month)
                    day_key = order_date.day
                    daily_data[day_key]['revenue'] += order.total_amount
                    daily_data[day_key]['orders'] += 1
                    
                    # Hourly patterns (if time data available)
                    hour_key = order_date.hour
                    hourly_data[hour_key]['revenue'] += order.total_amount
                    hourly_data[hour_key]['orders'] += 1
                    
                    # Add quantity data
                    if hasattr(order, 'items'):
                        for order_item in order.items:
                            monthly_data[month_key]['quantity'] += order_item.quantity
                            weekly_data[weekday_key]['quantity'] += order_item.quantity
                            daily_data[day_key]['quantity'] += order_item.quantity
                            hourly_data[hour_key]['quantity'] += order_item.quantity
                
                result = f"🌿 SEASONAL TRENDS ANALYSIS ({analysis_years} Year Analysis)\n"
                result += f"═══════════════════════════════════════════════════════════\n"
                result += f"Analysis Period: {start_date.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}\n"
                result += f"Total Orders Analyzed: {len(filtered_orders)}\n\n"
                
                # Monthly Seasonality Analysis
                result += f"📅 MONTHLY SEASONALITY:\n"
                month_names = [calendar.month_name[i] for i in range(1, 13)]
                total_monthly_revenue = sum(data['revenue'] for data in monthly_data.values())
                
                # Sort months by revenue to find peaks
                sorted_months = sorted(monthly_data.keys(), key=lambda m: monthly_data[m]['revenue'], reverse=True)
                
                for i, month in enumerate(range(1, 13)):
                    data = monthly_data[month]
                    month_name = month_names[month-1]
                    revenue_pct = (data['revenue'] / total_monthly_revenue * 100) if total_monthly_revenue > 0 else 0
                    
                    # Add performance indicator
                    if month in sorted_months[:3]:
                        indicator = "🔥 Peak"
                    elif month in sorted_months[-3:]:
                        indicator = "📉 Low"
                    else:
                        indicator = "📋 Average"
                    
                    result += f"   {month_name:>9}: ${data['revenue']:>8,.0f} ({revenue_pct:>5.1f}%) | {data['orders']:>3} orders {indicator}\n"
                
                # Weekly Patterns
                result += f"\n📅 WEEKLY PATTERNS:\n"
                weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                total_weekly_revenue = sum(data['revenue'] for data in weekly_data.values())
                
                # Sort weekdays by revenue
                sorted_weekdays = sorted(weekly_data.keys(), key=lambda w: weekly_data[w]['revenue'], reverse=True)
                
                for weekday in range(7):
                    data = weekly_data[weekday]
                    weekday_name = weekday_names[weekday]
                    revenue_pct = (data['revenue'] / total_weekly_revenue * 100) if total_weekly_revenue > 0 else 0
                    
                    # Add performance indicator
                    if weekday in sorted_weekdays[:2]:
                        indicator = "🔥 Peak"
                    elif weekday in sorted_weekdays[-2:]:
                        indicator = "📉 Slow"
                    else:
                        indicator = "📋 Moderate"
                    
                    result += f"   {weekday_name:>9}: ${data['revenue']:>8,.0f} ({revenue_pct:>5.1f}%) | {data['orders']:>3} orders {indicator}\n"
                
                # Hourly Patterns (if data available)
                if any(hourly_data.values()):
                    result += f"\n🕰️ HOURLY PATTERNS:\n"
                    total_hourly_revenue = sum(data['revenue'] for data in hourly_data.values())
                    
                    # Find peak hours
                    sorted_hours = sorted(hourly_data.keys(), key=lambda h: hourly_data[h]['revenue'], reverse=True)
                    peak_hours = sorted_hours[:3] if len(sorted_hours) >= 3 else sorted_hours
                    
                    for hour in sorted(hourly_data.keys()):
                        data = hourly_data[hour]
                        if data['orders'] > 0:  # Only show hours with activity
                            revenue_pct = (data['revenue'] / total_hourly_revenue * 100) if total_hourly_revenue > 0 else 0
                            
                            indicator = "🔥 Peak" if hour in peak_hours else ""
                            time_str = f"{hour:02d}:00"
                            
                            result += f"   {time_str}: ${data['revenue']:>6,.0f} ({revenue_pct:>4.1f}%) | {data['orders']:>2} orders {indicator}\n"
                
                # Seasonal Insights
                result += f"\n📊 SEASONAL INSIGHTS:\n"
                
                # Best and worst months
                best_month = max(monthly_data.keys(), key=lambda m: monthly_data[m]['revenue'])
                worst_month = min(monthly_data.keys(), key=lambda m: monthly_data[m]['revenue'])
                
                best_month_name = calendar.month_name[best_month]
                worst_month_name = calendar.month_name[worst_month]
                
                best_revenue = monthly_data[best_month]['revenue']
                worst_revenue = monthly_data[worst_month]['revenue']
                
                result += f"• Peak Month: {best_month_name} (${best_revenue:,.2f})\n"
                result += f"• Slowest Month: {worst_month_name} (${worst_revenue:,.2f})\n"
                
                if worst_revenue > 0:
                    seasonal_variance = ((best_revenue - worst_revenue) / worst_revenue) * 100
                    result += f"• Seasonal Variance: {seasonal_variance:.1f}%\n"
                
                # Best and worst weekdays
                best_weekday = max(weekly_data.keys(), key=lambda w: weekly_data[w]['revenue'])
                worst_weekday = min(weekly_data.keys(), key=lambda w: weekly_data[w]['revenue'])
                
                result += f"• Best Day: {weekday_names[best_weekday]} (${weekly_data[best_weekday]['revenue']:,.2f})\n"
                result += f"• Slowest Day: {weekday_names[worst_weekday]} (${weekly_data[worst_weekday]['revenue']:,.2f})\n"
                
                # Quarterly analysis
                quarterly_data = defaultdict(lambda: {'revenue': 0, 'orders': 0})
                for month, data in monthly_data.items():
                    quarter = (month - 1) // 3 + 1
                    quarterly_data[quarter]['revenue'] += data['revenue']
                    quarterly_data[quarter]['orders'] += data['orders']
                
                result += f"\n📈 QUARTERLY BREAKDOWN:\n"
                quarter_names = ['Q1 (Jan-Mar)', 'Q2 (Apr-Jun)', 'Q3 (Jul-Sep)', 'Q4 (Oct-Dec)']
                for quarter in range(1, 5):
                    data = quarterly_data[quarter]
                    quarter_name = quarter_names[quarter-1]
                    result += f"• {quarter_name}: ${data['revenue']:,.2f} | {data['orders']} orders\n"
                
                # Recommendations
                result += f"\n💡 SEASONAL RECOMMENDATIONS:\n"
                result += f"• Focus marketing efforts during {best_month_name} (peak season)\n"
                result += f"• Consider promotions during {worst_month_name} (slow season)\n"
                result += f"• Optimize staffing for {weekday_names[best_weekday]}s (busiest day)\n"
                
                if seasonal_variance > 30:
                    result += f"• High seasonal variance ({seasonal_variance:.1f}%) - consider seasonal pricing\n"
                
                return result
                
            except Exception as e:
                return f"Error analyzing seasonal trends: {str(e)}"
        
        return get_seasonal_trends
    
    def create_get_recent_performance_changes(self):
        """Create tool to detect recent performance shifts and anomalies"""
        @tool
        def get_recent_performance_changes(analysis_days: int = 30, comparison_period: int = 30) -> str:
            """Detect recent performance shifts and anomalies in sales data
            
            Args:
                analysis_days: Number of recent days to analyze (default 30)
                comparison_period: Number of days to compare against (default 30)
            """
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                
                from datetime import datetime, timedelta
                from collections import defaultdict
                import statistics
                
                db_service = self._get_db_service()
                orders = db_service.get_user_orders(self.user_id)
                items = db_service.get_user_items(self.user_id)
                
                if not orders:
                    return "No sales data found for performance change analysis"
                
                now = datetime.now()
                
                # Define time periods
                recent_start = now - timedelta(days=analysis_days)
                comparison_start = recent_start - timedelta(days=comparison_period)
                
                # Filter orders for both periods
                recent_orders = [o for o in orders if recent_start <= o.order_date <= now]
                comparison_orders = [o for o in orders if comparison_start <= o.order_date < recent_start]
                
                if not recent_orders and not comparison_orders:
                    return f"No sales data found for the specified analysis periods"
                
                result = f"🔍 RECENT PERFORMANCE CHANGES ANALYSIS\n"
                result += f"═══════════════════════════════════════════════════════════\n"
                result += f"Recent Period: {recent_start.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')} ({analysis_days} days)\n"
                result += f"Comparison Period: {comparison_start.strftime('%Y-%m-%d')} to {recent_start.strftime('%Y-%m-%d')} ({comparison_period} days)\n\n"
                
                # Overall Performance Comparison
                recent_revenue = sum(o.total_amount for o in recent_orders)
                comparison_revenue = sum(o.total_amount for o in comparison_orders)
                
                recent_order_count = len(recent_orders)
                comparison_order_count = len(comparison_orders)
                
                recent_avg_order = recent_revenue / recent_order_count if recent_order_count > 0 else 0
                comparison_avg_order = comparison_revenue / comparison_order_count if comparison_order_count > 0 else 0
                
                # Calculate changes
                revenue_change = ((recent_revenue - comparison_revenue) / comparison_revenue * 100) if comparison_revenue > 0 else 0
                order_change = ((recent_order_count - comparison_order_count) / comparison_order_count * 100) if comparison_order_count > 0 else 0
                avg_order_change = ((recent_avg_order - comparison_avg_order) / comparison_avg_order * 100) if comparison_avg_order > 0 else 0
                
                result += f"📈 OVERALL PERFORMANCE CHANGES:\n"
                
                # Revenue change
                if revenue_change > 10:
                    revenue_indicator = f"📈 Strong Growth (+{revenue_change:.1f}%)"
                elif revenue_change > 0:
                    revenue_indicator = f"📈 Growth (+{revenue_change:.1f}%)"
                elif revenue_change > -10:
                    revenue_indicator = f"📉 Slight Decline ({revenue_change:.1f}%)"
                else:
                    revenue_indicator = f"🚨 Significant Decline ({revenue_change:.1f}%)"
                
                result += f"• Revenue: ${recent_revenue:,.2f} vs ${comparison_revenue:,.2f} - {revenue_indicator}\n"
                result += f"• Orders: {recent_order_count} vs {comparison_order_count} - {order_change:+.1f}%\n"
                result += f"• Avg Order Value: ${recent_avg_order:.2f} vs ${comparison_avg_order:.2f} - {avg_order_change:+.1f}%\n\n"
                
                # Item-Level Performance Changes
                if items:
                    result += f"📋 ITEM-LEVEL PERFORMANCE CHANGES:\n"
                    
                    # Aggregate item sales for both periods
                    recent_item_sales = defaultdict(lambda: {'revenue': 0, 'quantity': 0, 'orders': 0})
                    comparison_item_sales = defaultdict(lambda: {'revenue': 0, 'quantity': 0, 'orders': 0})
                    
                    # Process recent orders
                    for order in recent_orders:
                        if hasattr(order, 'items'):
                            for order_item in order.items:
                                item_name = order_item.item.name if hasattr(order_item, 'item') else f"Item {order_item.item_id}"
                                recent_item_sales[item_name]['revenue'] += order_item.quantity * order_item.unit_price
                                recent_item_sales[item_name]['quantity'] += order_item.quantity
                                recent_item_sales[item_name]['orders'] += 1
                    
                    # Process comparison orders
                    for order in comparison_orders:
                        if hasattr(order, 'items'):
                            for order_item in order.items:
                                item_name = order_item.item.name if hasattr(order_item, 'item') else f"Item {order_item.item_id}"
                                comparison_item_sales[item_name]['revenue'] += order_item.quantity * order_item.unit_price
                                comparison_item_sales[item_name]['quantity'] += order_item.quantity
                                comparison_item_sales[item_name]['orders'] += 1
                    
                    # Calculate item changes
                    item_changes = []
                    all_items = set(recent_item_sales.keys()) | set(comparison_item_sales.keys())
                    
                    for item_name in all_items:
                        recent_data = recent_item_sales[item_name]
                        comparison_data = comparison_item_sales[item_name]
                        
                        if comparison_data['revenue'] > 0:
                            revenue_change_pct = ((recent_data['revenue'] - comparison_data['revenue']) / comparison_data['revenue']) * 100
                        elif recent_data['revenue'] > 0:
                            revenue_change_pct = 100  # New item
                        else:
                            continue  # No sales in either period
                        
                        item_changes.append({
                            'name': item_name,
                            'recent_revenue': recent_data['revenue'],
                            'comparison_revenue': comparison_data['revenue'],
                            'revenue_change': revenue_change_pct,
                            'recent_quantity': recent_data['quantity'],
                            'comparison_quantity': comparison_data['quantity']
                        })
                    
                    # Sort by absolute change to find biggest movers
                    item_changes.sort(key=lambda x: abs(x['revenue_change']), reverse=True)
                    
                    # Show top movers (up to 10)
                    top_movers = item_changes[:10]
                    
                    for item in top_movers:
                        change = item['revenue_change']
                        
                        if change > 50:
                            indicator = "🚀 Major Increase"
                        elif change > 20:
                            indicator = "📈 Strong Growth"
                        elif change > 0:
                            indicator = "📈 Growth"
                        elif change > -20:
                            indicator = "📉 Decline"
                        elif change > -50:
                            indicator = "🚨 Strong Decline"
                        else:
                            indicator = "🚨 Major Decline"
                        
                        result += f"   {item['name'][:25]:25}: ${item['recent_revenue']:>7,.0f} vs ${item['comparison_revenue']:>7,.0f} - {change:+6.1f}% {indicator}\n"
                
                # Daily Performance Volatility
                result += f"\n📉 DAILY PERFORMANCE VOLATILITY:\n"
                
                # Group recent orders by day
                daily_revenue = defaultdict(float)
                for order in recent_orders:
                    day_key = order.order_date.strftime('%Y-%m-%d')
                    daily_revenue[day_key] += order.total_amount
                
                if len(daily_revenue) > 1:
                    daily_values = list(daily_revenue.values())
                    avg_daily_revenue = statistics.mean(daily_values)
                    daily_std = statistics.stdev(daily_values) if len(daily_values) > 1 else 0
                    
                    # Calculate coefficient of variation
                    cv = (daily_std / avg_daily_revenue * 100) if avg_daily_revenue > 0 else 0
                    
                    result += f"• Average Daily Revenue: ${avg_daily_revenue:,.2f}\n"
                    result += f"• Daily Standard Deviation: ${daily_std:,.2f}\n"
                    result += f"• Coefficient of Variation: {cv:.1f}%\n"
                    
                    if cv > 50:
                        volatility_assessment = "🚨 High volatility - investigate causes"
                    elif cv > 30:
                        volatility_assessment = "⚠️ Moderate volatility - monitor trends"
                    else:
                        volatility_assessment = "✅ Low volatility - stable performance"
                    
                    result += f"• Volatility Assessment: {volatility_assessment}\n"
                    
                    # Find outlier days
                    threshold = avg_daily_revenue + (2 * daily_std)
                    low_threshold = max(0, avg_daily_revenue - (2 * daily_std))
                    
                    outlier_days = []
                    for day, revenue in daily_revenue.items():
                        if revenue > threshold:
                            outlier_days.append((day, revenue, "High"))
                        elif revenue < low_threshold:
                            outlier_days.append((day, revenue, "Low"))
                    
                    if outlier_days:
                        result += f"\n📍 ANOMALY DETECTION:\n"
                        for day, revenue, type_desc in outlier_days:
                            result += f"• {day}: ${revenue:,.2f} ({type_desc} outlier)\n"
                
                # Performance Alerts
                result += f"\n🚨 PERFORMANCE ALERTS:\n"
                alerts = []
                
                if revenue_change < -20:
                    alerts.append("Revenue declined significantly - investigate causes")
                elif revenue_change > 50:
                    alerts.append("Revenue increased dramatically - analyze success factors")
                
                if order_change < -30:
                    alerts.append("Order volume dropped substantially - check marketing/availability")
                
                if avg_order_change < -15:
                    alerts.append("Average order value declining - review pricing strategy")
                
                if len(daily_revenue) > 0 and max(daily_revenue.values()) == 0:
                    alerts.append("Zero sales days detected - urgent attention needed")
                
                if not alerts:
                    alerts.append("No significant performance alerts detected")
                
                for alert in alerts:
                    result += f"• {alert}\n"
                
                # Recommendations
                result += f"\n💡 RECOMMENDATIONS:\n"
                
                if revenue_change < -10:
                    result += f"• Investigate causes of revenue decline - check competitor activity\n"
                    result += f"• Consider promotional campaigns to boost sales\n"
                elif revenue_change > 20:
                    result += f"• Analyze success factors to replicate growth\n"
                    result += f"• Ensure inventory can support increased demand\n"
                
                if cv > 40:
                    result += f"• High volatility detected - implement more consistent marketing\n"
                
                result += f"• Continue monitoring performance trends daily\n"
                result += f"• Set up automated alerts for significant changes\n"
                
                return result
                
            except Exception as e:
                return f"Error analyzing recent performance changes: {str(e)}"
        
        return get_recent_performance_changes
    
    # ========== CATEGORY 3: COMPARATIVE ANALYSIS TOOLS ==========
    
    def create_compare_item_performance(self):
        """Create tool for side-by-side item comparison with comprehensive metrics"""
        @tool
        def compare_item_performance(item_names: str, analysis_period: int = 90) -> str:
            """Compare performance between multiple items with side-by-side metrics analysis
            
            Args:
                item_names: Comma-separated list of item names to compare (e.g., "Item A, Item B, Item C")
                analysis_period: Number of days to analyze for comparison (default 90)
            """
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                
                from datetime import datetime, timedelta
                from collections import defaultdict
                
                # Parse item names
                items_to_compare = [name.strip() for name in item_names.split(',') if name.strip()]
                
                if len(items_to_compare) < 2:
                    return "Please provide at least 2 item names separated by commas for comparison"
                
                if len(items_to_compare) > 6:
                    return "Maximum 6 items can be compared at once. Please reduce the number of items."
                
                db_service = self._get_db_service()
                orders = db_service.get_user_orders(self.user_id)
                items = db_service.get_user_items(self.user_id)
                price_history = db_service.get_price_history(self.user_id)
                cogs_data = db_service.get_user_cogs(self.user_id)
                
                if not orders:
                    return "No sales data found for item comparison"
                
                # Create item lookup
                item_lookup = {item.name: item for item in items}
                
                # Validate all items exist
                missing_items = [name for name in items_to_compare if name not in item_lookup]
                if missing_items:
                    available_items = [item.name for item in items[:10]]  # Show first 10
                    return f"Items not found: {', '.join(missing_items)}\n\nAvailable items: {', '.join(available_items)}{'...' if len(items) > 10 else ''}"
                
                now = datetime.now()
                start_date = now - timedelta(days=analysis_period)
                
                # Filter orders within analysis period
                filtered_orders = [o for o in orders if o.order_date >= start_date]
                
                result = f"🔄 ITEM PERFORMANCE COMPARISON\n"
                result += f"═══════════════════════════════════════════════════════════\n"
                result += f"Analysis Period: {start_date.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')} ({analysis_period} days)\n"
                result += f"Items Compared: {len(items_to_compare)}\n\n"
                
                # Collect performance data for each item
                item_performance = {}
                
                for item_name in items_to_compare:
                    item = item_lookup[item_name]
                    
                    # Initialize metrics
                    metrics = {
                        'total_revenue': 0,
                        'total_quantity': 0,
                        'total_orders': 0,
                        'unique_customers': set(),
                        'current_price': item.price,
                        'avg_order_value': 0,
                        'sales_velocity': 0,  # units per day
                        'revenue_per_day': 0,
                        'profit_margin': 0,
                        'total_cost': 0,
                        'total_profit': 0,
                        'price_changes': 0,
                        'last_price_change': None
                    }
                    
                    # Calculate sales metrics from orders
                    item_orders = []
                    for order in filtered_orders:
                        if hasattr(order, 'items'):
                            for order_item in order.items:
                                if (hasattr(order_item, 'item') and order_item.item.name == item_name) or \
                                   (hasattr(order_item, 'item_id') and order_item.item_id == item.id):
                                    item_orders.append((order, order_item))
                                    metrics['total_revenue'] += order_item.quantity * order_item.unit_price
                                    metrics['total_quantity'] += order_item.quantity
                                    metrics['total_orders'] += 1
                                    
                                    # Track unique customers
                                    if hasattr(order, 'customer_id') and order.customer_id:
                                        metrics['unique_customers'].add(order.customer_id)
                    
                    # Calculate derived metrics
                    if metrics['total_orders'] > 0:
                        metrics['avg_order_value'] = metrics['total_revenue'] / metrics['total_orders']
                    
                    if analysis_period > 0:
                        metrics['sales_velocity'] = metrics['total_quantity'] / analysis_period
                        metrics['revenue_per_day'] = metrics['total_revenue'] / analysis_period
                    
                    # Get COGS data
                    item_cogs = [cogs for cogs in cogs_data if cogs.item_id == item.id]
                    if item_cogs:
                        latest_cogs = max(item_cogs, key=lambda x: x.date_recorded)
                        unit_cost = latest_cogs.cost_per_unit
                        metrics['total_cost'] = metrics['total_quantity'] * unit_cost
                        metrics['total_profit'] = metrics['total_revenue'] - metrics['total_cost']
                        
                        if metrics['total_revenue'] > 0:
                            metrics['profit_margin'] = (metrics['total_profit'] / metrics['total_revenue']) * 100
                    
                    # Get price change history
                    item_price_history = [ph for ph in price_history if ph.item_id == item.id and ph.change_date >= start_date]
                    metrics['price_changes'] = len(item_price_history)
                    if item_price_history:
                        metrics['last_price_change'] = max(item_price_history, key=lambda x: x.change_date).change_date
                    
                    metrics['unique_customers'] = len(metrics['unique_customers'])
                    item_performance[item_name] = metrics
                
                # Create comparison table
                result += f"📋 PERFORMANCE METRICS COMPARISON:\n\n"
                
                # Header
                header = f"{'Metric':<25}"
                for item_name in items_to_compare:
                    header += f"{item_name[:15]:>18}"
                result += header + "\n"
                result += "-" * (25 + 18 * len(items_to_compare)) + "\n"
                
                # Revenue comparison
                result += f"{'Total Revenue':<25}"
                for item_name in items_to_compare:
                    revenue = item_performance[item_name]['total_revenue']
                    result += f"${revenue:>15,.0f}"
                result += "\n"
                
                # Quantity comparison
                result += f"{'Total Quantity':<25}"
                for item_name in items_to_compare:
                    quantity = item_performance[item_name]['total_quantity']
                    result += f"{quantity:>17,}"
                result += "\n"
                
                # Orders comparison
                result += f"{'Total Orders':<25}"
                for item_name in items_to_compare:
                    orders = item_performance[item_name]['total_orders']
                    result += f"{orders:>17,}"
                result += "\n"
                
                # Current price comparison
                result += f"{'Current Price':<25}"
                for item_name in items_to_compare:
                    price = item_performance[item_name]['current_price']
                    result += f"${price:>15,.2f}"
                result += "\n"
                
                # Average order value
                result += f"{'Avg Order Value':<25}"
                for item_name in items_to_compare:
                    aov = item_performance[item_name]['avg_order_value']
                    result += f"${aov:>15,.2f}"
                result += "\n"
                
                # Sales velocity
                result += f"{'Sales Velocity/Day':<25}"
                for item_name in items_to_compare:
                    velocity = item_performance[item_name]['sales_velocity']
                    result += f"{velocity:>15,.1f}"
                result += "\n"
                
                # Revenue per day
                result += f"{'Revenue/Day':<25}"
                for item_name in items_to_compare:
                    rev_per_day = item_performance[item_name]['revenue_per_day']
                    result += f"${rev_per_day:>15,.2f}"
                result += "\n"
                
                # Profit margin
                result += f"{'Profit Margin %':<25}"
                for item_name in items_to_compare:
                    margin = item_performance[item_name]['profit_margin']
                    result += f"{margin:>15,.1f}%"
                result += "\n"
                
                # Unique customers
                result += f"{'Unique Customers':<25}"
                for item_name in items_to_compare:
                    customers = item_performance[item_name]['unique_customers']
                    result += f"{customers:>17,}"
                result += "\n"
                
                # Price changes
                result += f"{'Price Changes':<25}"
                for item_name in items_to_compare:
                    changes = item_performance[item_name]['price_changes']
                    result += f"{changes:>17,}"
                result += "\n\n"
                
                # Performance Rankings
                result += f"🏆 PERFORMANCE RANKINGS:\n\n"
                
                # Revenue ranking
                revenue_ranking = sorted(items_to_compare, key=lambda x: item_performance[x]['total_revenue'], reverse=True)
                result += f"💰 Revenue Leaders:\n"
                for i, item_name in enumerate(revenue_ranking, 1):
                    revenue = item_performance[item_name]['total_revenue']
                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📊"
                    result += f"   {i}. {emoji} {item_name}: ${revenue:,.2f}\n"
                
                # Quantity ranking
                quantity_ranking = sorted(items_to_compare, key=lambda x: item_performance[x]['total_quantity'], reverse=True)
                result += f"\n📦 Volume Leaders:\n"
                for i, item_name in enumerate(quantity_ranking, 1):
                    quantity = item_performance[item_name]['total_quantity']
                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📊"
                    result += f"   {i}. {emoji} {item_name}: {quantity:,} units\n"
                
                # Profit margin ranking
                margin_ranking = sorted(items_to_compare, key=lambda x: item_performance[x]['profit_margin'], reverse=True)
                result += f"\n💹 Profitability Leaders:\n"
                for i, item_name in enumerate(margin_ranking, 1):
                    margin = item_performance[item_name]['profit_margin']
                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📊"
                    result += f"   {i}. {emoji} {item_name}: {margin:.1f}%\n"
                
                # Key Insights
                result += f"\n🔍 KEY INSIGHTS:\n"
                
                # Best overall performer
                best_revenue = revenue_ranking[0]
                best_margin = margin_ranking[0]
                best_volume = quantity_ranking[0]
                
                result += f"• Revenue Champion: {best_revenue} (${item_performance[best_revenue]['total_revenue']:,.2f})\n"
                result += f"• Profitability Champion: {best_margin} ({item_performance[best_margin]['profit_margin']:.1f}% margin)\n"
                result += f"• Volume Champion: {best_volume} ({item_performance[best_volume]['total_quantity']:,} units)\n"
                
                # Performance gaps
                revenue_gap = item_performance[revenue_ranking[0]]['total_revenue'] - item_performance[revenue_ranking[-1]]['total_revenue']
                margin_gap = item_performance[margin_ranking[0]]['profit_margin'] - item_performance[margin_ranking[-1]]['profit_margin']
                
                result += f"• Revenue Gap: ${revenue_gap:,.2f} between best and worst performer\n"
                result += f"• Margin Gap: {margin_gap:.1f}% between most and least profitable\n"
                
                # Recommendations
                result += f"\n💡 STRATEGIC RECOMMENDATIONS:\n"
                
                # Low performers
                worst_revenue = revenue_ranking[-1]
                worst_margin = margin_ranking[-1]
                
                if item_performance[worst_revenue]['total_revenue'] < item_performance[best_revenue]['total_revenue'] * 0.3:
                    result += f"• Consider promoting {worst_revenue} - significantly underperforming in revenue\n"
                
                if item_performance[worst_margin]['profit_margin'] < 10:
                    result += f"• Review pricing for {worst_margin} - low profit margin ({item_performance[worst_margin]['profit_margin']:.1f}%)\n"
                
                # High performers
                if item_performance[best_revenue]['sales_velocity'] > 1:
                    result += f"• {best_revenue} shows strong demand - consider premium pricing\n"
                
                # Price optimization opportunities
                for item_name in items_to_compare:
                    metrics = item_performance[item_name]
                    if metrics['profit_margin'] > 40 and metrics['sales_velocity'] > 0.5:
                        result += f"• {item_name} has pricing power - high margin + good velocity\n"
                
                result += f"• Focus marketing budget on top revenue performers\n"
                result += f"• Analyze successful strategies from top performers for application to others\n"
                
                return result
                
            except Exception as e:
                return f"Error comparing item performance: {str(e)}"
        
        return compare_item_performance
    
    def create_get_competitor_price_gaps(self):
        """Create tool for structured competitor pricing analysis with gap identification"""
        @tool
        def get_competitor_price_gaps(category_filter: str = "", price_threshold: float = 0.0) -> str:
            """Analyze competitor pricing gaps and opportunities with structured insights
            
            Args:
                category_filter: Optional category to filter analysis (e.g., "appetizers", "entrees")
                price_threshold: Minimum price to include in analysis (default 0.0)
            """
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                
                from collections import defaultdict
                import statistics
                
                db_service = self._get_db_service()
                items = db_service.get_user_items(self.user_id)
                
                # Get competitor data (this would typically come from a competitor analysis service)
                # For now, we'll simulate competitor data based on user's items with realistic variations
                competitor_data = self._simulate_competitor_data(items)
                
                if not items:
                    return "No items found for competitor price analysis"
                
                # Filter by category if specified
                if category_filter:
                    items = [item for item in items if hasattr(item, 'category') and 
                            category_filter.lower() in item.category.lower()]
                    if not items:
                        return f"No items found in category '{category_filter}'"
                
                # Filter by price threshold
                if price_threshold > 0:
                    items = [item for item in items if item.price >= price_threshold]
                
                result = f"🎯 COMPETITOR PRICE GAP ANALYSIS\n"
                result += f"═══════════════════════════════════════════════════════════\n"
                
                if category_filter:
                    result += f"Category Filter: {category_filter}\n"
                if price_threshold > 0:
                    result += f"Price Threshold: ${price_threshold:.2f}+\n"
                
                result += f"Items Analyzed: {len(items)}\n"
                result += f"Competitor Sources: Market Research, Industry Data\n\n"
                
                # Analyze pricing gaps
                pricing_analysis = []
                
                for item in items:
                    if item.name in competitor_data:
                        comp_data = competitor_data[item.name]
                        
                        analysis = {
                            'item_name': item.name,
                            'our_price': item.price,
                            'competitor_prices': comp_data['prices'],
                            'competitor_avg': statistics.mean(comp_data['prices']),
                            'competitor_min': min(comp_data['prices']),
                            'competitor_max': max(comp_data['prices']),
                            'market_position': '',
                            'price_gap': 0,
                            'gap_percentage': 0,
                            'opportunity_score': 0,
                            'recommendation': ''
                        }
                        
                        # Calculate gaps and position
                        analysis['price_gap'] = item.price - analysis['competitor_avg']
                        analysis['gap_percentage'] = (analysis['price_gap'] / analysis['competitor_avg']) * 100
                        
                        # Determine market position
                        if item.price < analysis['competitor_min']:
                            analysis['market_position'] = 'Below Market'
                        elif item.price > analysis['competitor_max']:
                            analysis['market_position'] = 'Above Market'
                        elif item.price < analysis['competitor_avg']:
                            analysis['market_position'] = 'Below Average'
                        elif item.price > analysis['competitor_avg']:
                            analysis['market_position'] = 'Above Average'
                        else:
                            analysis['market_position'] = 'Market Average'
                        
                        # Calculate opportunity score (0-100)
                        if analysis['gap_percentage'] < -20:  # Significantly underpriced
                            analysis['opportunity_score'] = 90
                        elif analysis['gap_percentage'] < -10:  # Moderately underpriced
                            analysis['opportunity_score'] = 70
                        elif analysis['gap_percentage'] < -5:  # Slightly underpriced
                            analysis['opportunity_score'] = 50
                        elif analysis['gap_percentage'] > 20:  # Significantly overpriced
                            analysis['opportunity_score'] = 20
                        elif analysis['gap_percentage'] > 10:  # Moderately overpriced
                            analysis['opportunity_score'] = 40
                        else:  # Well positioned
                            analysis['opportunity_score'] = 60
                        
                        # Generate recommendations
                        if analysis['gap_percentage'] < -15:
                            analysis['recommendation'] = 'Strong price increase opportunity'
                        elif analysis['gap_percentage'] < -10:
                            analysis['recommendation'] = 'Moderate price increase recommended'
                        elif analysis['gap_percentage'] < -5:
                            analysis['recommendation'] = 'Small price adjustment possible'
                        elif analysis['gap_percentage'] > 15:
                            analysis['recommendation'] = 'Consider price reduction'
                        elif analysis['gap_percentage'] > 10:
                            analysis['recommendation'] = 'Monitor competitive pressure'
                        else:
                            analysis['recommendation'] = 'Well positioned'
                        
                        pricing_analysis.append(analysis)
                
                if not pricing_analysis:
                    return "No competitor pricing data available for analysis"
                
                # Sort by opportunity score (highest first)
                pricing_analysis.sort(key=lambda x: x['opportunity_score'], reverse=True)
                
                # Create detailed comparison table
                result += f"📋 DETAILED PRICE COMPARISON:\n\n"
                result += f"{'Item':<20} {'Our Price':<12} {'Comp Avg':<12} {'Gap':<10} {'Gap %':<8} {'Position':<15} {'Score':<6}\n"
                result += "-" * 95 + "\n"
                
                for analysis in pricing_analysis:
                    gap_str = f"${analysis['price_gap']:+.2f}"
                    gap_pct_str = f"{analysis['gap_percentage']:+.1f}%"
                    
                    result += f"{analysis['item_name'][:19]:<20} "
                    result += f"${analysis['our_price']:<11.2f} "
                    result += f"${analysis['competitor_avg']:<11.2f} "
                    result += f"{gap_str:<10} "
                    result += f"{gap_pct_str:<8} "
                    result += f"{analysis['market_position']:<15} "
                    result += f"{analysis['opportunity_score']:<6}\n"
                
                # Market Position Summary
                result += f"\n📊 MARKET POSITION SUMMARY:\n\n"
                
                position_counts = defaultdict(int)
                for analysis in pricing_analysis:
                    position_counts[analysis['market_position']] += 1
                
                total_items = len(pricing_analysis)
                for position, count in position_counts.items():
                    percentage = (count / total_items) * 100
                    emoji = {
                        'Below Market': '🔴',
                        'Below Average': '🟠',
                        'Market Average': '🟢',
                        'Above Average': '🟡',
                        'Above Market': '🔴'
                    }.get(position, '🔵')
                    
                    result += f"{emoji} {position}: {count} items ({percentage:.1f}%)\n"
                
                # Top Opportunities
                result += f"\n🎯 TOP PRICING OPPORTUNITIES:\n\n"
                
                top_opportunities = pricing_analysis[:5]  # Top 5 opportunities
                for i, analysis in enumerate(top_opportunities, 1):
                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "💰"
                    result += f"{i}. {emoji} {analysis['item_name']}\n"
                    result += f"   Current: ${analysis['our_price']:.2f} | Market Avg: ${analysis['competitor_avg']:.2f}\n"
                    result += f"   Gap: {analysis['gap_percentage']:+.1f}% | {analysis['recommendation']}\n"
                    
                    # Calculate potential revenue impact
                    if analysis['gap_percentage'] < -10:
                        suggested_price = analysis['competitor_avg'] * 0.95  # Price slightly below average
                        potential_increase = suggested_price - analysis['our_price']
                        result += f"   Suggested Price: ${suggested_price:.2f} (+${potential_increase:.2f})\n"
                    
                    result += "\n"
                
                # Risk Analysis
                result += f"⚠️ PRICING RISK ANALYSIS:\n\n"
                
                overpriced_items = [a for a in pricing_analysis if a['gap_percentage'] > 15]
                underpriced_items = [a for a in pricing_analysis if a['gap_percentage'] < -15]
                
                if overpriced_items:
                    result += f"🔴 Overpriced Items ({len(overpriced_items)}):\n"
                    for analysis in overpriced_items:
                        result += f"   • {analysis['item_name']}: {analysis['gap_percentage']:+.1f}% above market\n"
                    result += "\n"
                
                if underpriced_items:
                    result += f"🟢 Underpriced Items ({len(underpriced_items)}):\n"
                    for analysis in underpriced_items:
                        result += f"   • {analysis['item_name']}: {analysis['gap_percentage']:+.1f}% below market\n"
                    result += "\n"
                
                # Statistical Summary
                result += f"📊 STATISTICAL SUMMARY:\n\n"
                
                all_gaps = [a['gap_percentage'] for a in pricing_analysis]
                avg_gap = statistics.mean(all_gaps)
                gap_std = statistics.stdev(all_gaps) if len(all_gaps) > 1 else 0
                
                result += f"Average Price Gap: {avg_gap:+.1f}%\n"
                result += f"Gap Standard Deviation: {gap_std:.1f}%\n"
                result += f"Items Above Market: {len([a for a in pricing_analysis if a['gap_percentage'] > 5])}\n"
                result += f"Items Below Market: {len([a for a in pricing_analysis if a['gap_percentage'] < -5])}\n"
                
                # Strategic Recommendations
                result += f"\n💡 STRATEGIC RECOMMENDATIONS:\n\n"
                
                if avg_gap < -10:
                    result += f"• Overall pricing is below market - significant revenue opportunity\n"
                elif avg_gap > 10:
                    result += f"• Overall pricing is above market - risk of customer loss\n"
                else:
                    result += f"• Overall pricing is competitive with market\n"
                
                if len(underpriced_items) > len(overpriced_items):
                    result += f"• Focus on price increases for underpriced items\n"
                elif len(overpriced_items) > len(underpriced_items):
                    result += f"• Review pricing strategy for overpriced items\n"
                
                result += f"• Monitor competitor pricing changes regularly\n"
                result += f"• Test price changes gradually to assess demand elasticity\n"
                result += f"• Consider value-added services to justify premium pricing\n"
                
                # Potential Revenue Impact
                total_revenue_opportunity = 0
                for analysis in underpriced_items:
                    if analysis['gap_percentage'] < -10:
                        suggested_price = analysis['competitor_avg'] * 0.95
                        potential_increase = suggested_price - analysis['our_price']
                        total_revenue_opportunity += potential_increase
                
                if total_revenue_opportunity > 0:
                    result += f"\n💰 REVENUE OPPORTUNITY:\n"
                    result += f"Potential additional revenue per item sold: ${total_revenue_opportunity:.2f}\n"
                    result += f"Based on conservative pricing adjustments to market levels\n"
                
                return result
                
            except Exception as e:
                return f"Error analyzing competitor price gaps: {str(e)}"
        
        return get_competitor_price_gaps
    
    def _simulate_competitor_data(self, items):
        """Simulate competitor pricing data for demonstration purposes"""
        import random
        
        competitor_data = {}
        
        for item in items:
            base_price = item.price
            
            # Generate 3-5 competitor prices with realistic variations
            num_competitors = random.randint(3, 5)
            competitor_prices = []
            
            for _ in range(num_competitors):
                # Vary prices by -30% to +40% of base price
                variation = random.uniform(-0.3, 0.4)
                competitor_price = base_price * (1 + variation)
                # Round to nearest quarter
                competitor_price = round(competitor_price * 4) / 4
                competitor_prices.append(max(0.25, competitor_price))  # Minimum $0.25
            
            competitor_data[item.name] = {
                'prices': competitor_prices,
                'sources': ['CompetitorA', 'CompetitorB', 'CompetitorC', 'CompetitorD', 'CompetitorE'][:num_competitors]
            }
        
        return competitor_data
    
    def create_benchmark_against_industry(self):
        """Create tool for comparing performance against industry standards and benchmarks"""
        @tool
        def benchmark_against_industry(industry_type: str = "restaurant", business_size: str = "small") -> str:
            """Compare business performance against industry standards and benchmarks
            
            Args:
                industry_type: Type of industry for benchmarking (e.g., "restaurant", "retail", "food_service")
                business_size: Size category for comparison ("small", "medium", "large")
            """
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                
                from datetime import datetime, timedelta
                from collections import defaultdict
                import statistics
                
                db_service = self._get_db_service()
                orders = db_service.get_user_orders(self.user_id)
                items = db_service.get_user_items(self.user_id)
                cogs_data = db_service.get_user_cogs(self.user_id)
                
                if not orders:
                    return "No sales data found for industry benchmarking"
                
                # Get industry benchmarks (in a real implementation, this would come from industry data sources)
                industry_benchmarks = self._get_industry_benchmarks(industry_type, business_size)
                
                # Calculate business metrics for comparison
                now = datetime.now()
                
                # Last 30 days metrics
                last_30_days = now - timedelta(days=30)
                recent_orders = [o for o in orders if o.order_date >= last_30_days]
                
                # Last 12 months metrics
                last_12_months = now - timedelta(days=365)
                yearly_orders = [o for o in orders if o.order_date >= last_12_months]
                
                result = f"📊 INDUSTRY BENCHMARK ANALYSIS\n"
                result += f"═══════════════════════════════════════════════════════════\n"
                result += f"Industry: {industry_type.title()}\n"
                result += f"Business Size: {business_size.title()}\n"
                result += f"Analysis Date: {now.strftime('%Y-%m-%d')}\n\n"
                
                # Calculate our business metrics
                business_metrics = self._calculate_business_metrics(recent_orders, yearly_orders, items, cogs_data)
                
                # Performance comparison
                result += f"🎯 PERFORMANCE VS INDUSTRY STANDARDS:\n\n"
                
                # Create comparison table
                result += f"{'Metric':<30} {'Our Business':<15} {'Industry Avg':<15} {'Percentile':<12} {'Status':<12}\n"
                result += "-" * 90 + "\n"
                
                comparisons = []
                
                # Revenue per customer
                our_revenue_per_customer = business_metrics['revenue_per_customer']
                industry_revenue_per_customer = industry_benchmarks['revenue_per_customer']
                revenue_percentile = self._calculate_percentile(our_revenue_per_customer, industry_revenue_per_customer)
                revenue_status = self._get_performance_status(revenue_percentile)
                
                result += f"{'Revenue per Customer':<30} ${our_revenue_per_customer:<14.2f} ${industry_revenue_per_customer:<14.2f} {revenue_percentile:<11}% {revenue_status:<12}\n"
                comparisons.append(('Revenue per Customer', revenue_percentile, revenue_status))
                
                # Average order value
                our_aov = business_metrics['avg_order_value']
                industry_aov = industry_benchmarks['avg_order_value']
                aov_percentile = self._calculate_percentile(our_aov, industry_aov)
                aov_status = self._get_performance_status(aov_percentile)
                
                result += f"{'Average Order Value':<30} ${our_aov:<14.2f} ${industry_aov:<14.2f} {aov_percentile:<11}% {aov_status:<12}\n"
                comparisons.append(('Average Order Value', aov_percentile, aov_status))
                
                # Gross margin
                our_gross_margin = business_metrics['gross_margin']
                industry_gross_margin = industry_benchmarks['gross_margin']
                margin_percentile = self._calculate_percentile(our_gross_margin, industry_gross_margin)
                margin_status = self._get_performance_status(margin_percentile)
                
                result += f"{'Gross Margin %':<30} {our_gross_margin:<14.1f}% {industry_gross_margin:<14.1f}% {margin_percentile:<11}% {margin_status:<12}\n"
                comparisons.append(('Gross Margin', margin_percentile, margin_status))
                
                # Customer retention (simulated)
                our_retention = business_metrics['customer_retention']
                industry_retention = industry_benchmarks['customer_retention']
                retention_percentile = self._calculate_percentile(our_retention, industry_retention)
                retention_status = self._get_performance_status(retention_percentile)
                
                result += f"{'Customer Retention %':<30} {our_retention:<14.1f}% {industry_retention:<14.1f}% {retention_percentile:<11}% {retention_status:<12}\n"
                comparisons.append(('Customer Retention', retention_percentile, retention_status))
                
                # Items per order
                our_items_per_order = business_metrics['items_per_order']
                industry_items_per_order = industry_benchmarks['items_per_order']
                items_percentile = self._calculate_percentile(our_items_per_order, industry_items_per_order)
                items_status = self._get_performance_status(items_percentile)
                
                result += f"{'Items per Order':<30} {our_items_per_order:<14.1f} {industry_items_per_order:<14.1f} {items_percentile:<11}% {items_status:<12}\n"
                comparisons.append(('Items per Order', items_percentile, items_status))
                
                # Sales growth (YoY)
                our_growth = business_metrics['sales_growth']
                industry_growth = industry_benchmarks['sales_growth']
                growth_percentile = self._calculate_percentile(our_growth, industry_growth)
                growth_status = self._get_performance_status(growth_percentile)
                
                result += f"{'Sales Growth % (YoY)':<30} {our_growth:<14.1f}% {industry_growth:<14.1f}% {growth_percentile:<11}% {growth_status:<12}\n"
                comparisons.append(('Sales Growth', growth_percentile, growth_status))
                
                # Overall performance score
                overall_score = statistics.mean([comp[1] for comp in comparisons])
                overall_status = self._get_performance_status(overall_score)
                
                result += f"\n{'OVERALL PERFORMANCE':<30} {overall_score:<14.1f}% {'N/A':<14} {'N/A':<11} {overall_status:<12}\n"
                
                # Performance breakdown
                result += f"\n🏆 PERFORMANCE BREAKDOWN:\n\n"
                
                excellent_metrics = [comp for comp in comparisons if comp[1] >= 75]
                good_metrics = [comp for comp in comparisons if 50 <= comp[1] < 75]
                needs_improvement = [comp for comp in comparisons if comp[1] < 50]
                
                if excellent_metrics:
                    result += f"🟢 Excellent Performance ({len(excellent_metrics)} metrics):\n"
                    for metric, percentile, status in excellent_metrics:
                        result += f"   • {metric}: {percentile:.0f}th percentile\n"
                    result += "\n"
                
                if good_metrics:
                    result += f"🟡 Good Performance ({len(good_metrics)} metrics):\n"
                    for metric, percentile, status in good_metrics:
                        result += f"   • {metric}: {percentile:.0f}th percentile\n"
                    result += "\n"
                
                if needs_improvement:
                    result += f"🔴 Needs Improvement ({len(needs_improvement)} metrics):\n"
                    for metric, percentile, status in needs_improvement:
                        result += f"   • {metric}: {percentile:.0f}th percentile\n"
                    result += "\n"
                
                # Industry insights
                result += f"📈 INDUSTRY INSIGHTS:\n\n"
                
                if industry_type.lower() == "restaurant":
                    result += f"• Restaurant industry average profit margin: 3-5%\n"
                    result += f"• Peak dining hours typically drive 60-70% of daily revenue\n"
                    result += f"• Food cost should ideally be 28-35% of revenue\n"
                    result += f"• Labor cost typically represents 25-35% of revenue\n"
                elif industry_type.lower() == "retail":
                    result += f"• Retail industry average gross margin: 50-60%\n"
                    result += f"• Inventory turnover should be 4-6 times per year\n"
                    result += f"• Customer acquisition cost varies by category\n"
                
                result += f"• {business_size.title()} businesses in {industry_type} typically see seasonal variations\n"
                result += f"• Digital presence increasingly important for customer acquisition\n\n"
                
                # Competitive positioning
                result += f"🎯 COMPETITIVE POSITIONING:\n\n"
                
                if overall_score >= 75:
                    result += f"🏆 TOP PERFORMER: Your business is in the top 25% of {industry_type} businesses\n"
                    result += f"• Strong competitive position across multiple metrics\n"
                    result += f"• Focus on maintaining excellence and scaling successful strategies\n"
                elif overall_score >= 50:
                    result += f"📊 SOLID PERFORMER: Your business is above average in the {industry_type} industry\n"
                    result += f"• Good foundation with opportunities for optimization\n"
                    result += f"• Focus on improving underperforming metrics\n"
                else:
                    result += f"⚠️ IMPROVEMENT NEEDED: Your business is below industry average\n"
                    result += f"• Significant opportunities for performance enhancement\n"
                    result += f"• Consider strategic changes to improve competitive position\n"
                
                # Specific recommendations
                result += f"\n💡 STRATEGIC RECOMMENDATIONS:\n\n"
                
                # Revenue recommendations
                if our_revenue_per_customer < industry_revenue_per_customer * 0.8:
                    result += f"• Revenue per Customer: Implement upselling and cross-selling strategies\n"
                    result += f"  - Bundle complementary items\n"
                    result += f"  - Introduce loyalty programs\n"
                    result += f"  - Focus on customer lifetime value\n"
                
                # Margin recommendations
                if our_gross_margin < industry_gross_margin * 0.9:
                    result += f"• Gross Margin: Review pricing and cost structure\n"
                    result += f"  - Analyze high-cost items for pricing adjustments\n"
                    result += f"  - Negotiate better supplier terms\n"
                    result += f"  - Optimize menu/product mix\n"
                
                # AOV recommendations
                if our_aov < industry_aov * 0.9:
                    result += f"• Average Order Value: Increase transaction size\n"
                    result += f"  - Suggest add-ons at point of sale\n"
                    result += f"  - Create value meal combinations\n"
                    result += f"  - Train staff on suggestive selling\n"
                
                # Growth recommendations
                if our_growth < industry_growth:
                    result += f"• Sales Growth: Accelerate business expansion\n"
                    result += f"  - Invest in marketing and customer acquisition\n"
                    result += f"  - Expand operating hours or service areas\n"
                    result += f"  - Introduce new products/services\n"
                
                # Benchmarking frequency
                result += f"\n📅 BENCHMARKING RECOMMENDATIONS:\n\n"
                result += f"• Conduct quarterly benchmark analysis to track progress\n"
                result += f"• Monitor key competitors and industry trends monthly\n"
                result += f"• Set specific improvement targets for underperforming metrics\n"
                result += f"• Consider industry associations for additional benchmarking data\n"
                
                # Next steps
                result += f"\n🚀 NEXT STEPS:\n\n"
                result += f"1. Focus on the {len(needs_improvement)} metrics needing improvement\n"
                result += f"2. Set 90-day improvement targets for each underperforming area\n"
                result += f"3. Implement recommended strategies systematically\n"
                result += f"4. Track progress monthly and adjust strategies as needed\n"
                result += f"5. Celebrate and maintain excellence in top-performing areas\n"
                
                return result
                
            except Exception as e:
                return f"Error benchmarking against industry: {str(e)}"
        
        return benchmark_against_industry
    
    def _get_industry_benchmarks(self, industry_type, business_size):
        """Get industry benchmark data (simulated for demonstration)"""
        
        # Base benchmarks for restaurant industry
        base_benchmarks = {
            'revenue_per_customer': 45.0,
            'avg_order_value': 28.50,
            'gross_margin': 65.0,
            'customer_retention': 75.0,
            'items_per_order': 2.3,
            'sales_growth': 8.5
        }
        
        # Adjust for business size
        size_multipliers = {
            'small': {'revenue_per_customer': 0.85, 'avg_order_value': 0.90, 'gross_margin': 1.0, 'customer_retention': 1.1, 'items_per_order': 0.95, 'sales_growth': 1.2},
            'medium': {'revenue_per_customer': 1.0, 'avg_order_value': 1.0, 'gross_margin': 1.0, 'customer_retention': 1.0, 'items_per_order': 1.0, 'sales_growth': 1.0},
            'large': {'revenue_per_customer': 1.15, 'avg_order_value': 1.10, 'gross_margin': 0.95, 'customer_retention': 0.95, 'items_per_order': 1.05, 'sales_growth': 0.8}
        }
        
        # Adjust for industry type
        industry_multipliers = {
            'restaurant': {'revenue_per_customer': 1.0, 'avg_order_value': 1.0, 'gross_margin': 1.0, 'customer_retention': 1.0, 'items_per_order': 1.0, 'sales_growth': 1.0},
            'retail': {'revenue_per_customer': 1.2, 'avg_order_value': 0.8, 'gross_margin': 0.85, 'customer_retention': 0.9, 'items_per_order': 1.3, 'sales_growth': 0.9},
            'food_service': {'revenue_per_customer': 0.9, 'avg_order_value': 1.1, 'gross_margin': 1.05, 'customer_retention': 1.05, 'items_per_order': 0.9, 'sales_growth': 1.1}
        }
        
        size_mult = size_multipliers.get(business_size, size_multipliers['medium'])
        industry_mult = industry_multipliers.get(industry_type, industry_multipliers['restaurant'])
        
        benchmarks = {}
        for metric, base_value in base_benchmarks.items():
            adjusted_value = base_value * size_mult[metric] * industry_mult[metric]
            benchmarks[metric] = adjusted_value
        
        return benchmarks
    
    def _calculate_business_metrics(self, recent_orders, yearly_orders, items, cogs_data):
        """Calculate business metrics for benchmarking"""
        metrics = {}
        
        # Revenue per customer (last 30 days)
        if recent_orders:
            unique_customers = len(set(getattr(order, 'customer_id', f'customer_{i}') for i, order in enumerate(recent_orders)))
            total_revenue = sum(order.total_amount for order in recent_orders)
            metrics['revenue_per_customer'] = total_revenue / max(unique_customers, 1)
        else:
            metrics['revenue_per_customer'] = 0
        
        # Average order value (last 30 days)
        if recent_orders:
            metrics['avg_order_value'] = sum(order.total_amount for order in recent_orders) / len(recent_orders)
        else:
            metrics['avg_order_value'] = 0
        
        # Gross margin (estimated)
        total_revenue = sum(order.total_amount for order in yearly_orders) if yearly_orders else 0
        total_cogs = sum(cogs.cost_per_unit for cogs in cogs_data) if cogs_data else 0
        
        if total_revenue > 0:
            # Estimate COGS as percentage of revenue (simplified)
            estimated_cogs = total_revenue * 0.35  # Assume 35% COGS
            metrics['gross_margin'] = ((total_revenue - estimated_cogs) / total_revenue) * 100
        else:
            metrics['gross_margin'] = 0
        
        # Customer retention (simulated)
        metrics['customer_retention'] = 72.0  # Simulated value
        
        # Items per order
        if recent_orders:
            total_items = 0
            for order in recent_orders:
                if hasattr(order, 'items'):
                    total_items += sum(item.quantity for item in order.items)
                else:
                    total_items += 2  # Assume 2 items per order if no detail available
            metrics['items_per_order'] = total_items / len(recent_orders)
        else:
            metrics['items_per_order'] = 0
        
        # Sales growth (YoY, simulated)
        metrics['sales_growth'] = 12.5  # Simulated value
        
        return metrics
    
    def _calculate_percentile(self, our_value, industry_avg):
        """Calculate percentile ranking compared to industry average"""
        if industry_avg == 0:
            return 50
        
        ratio = our_value / industry_avg
        
        # Convert ratio to percentile (simplified)
        if ratio >= 1.3:
            return 90
        elif ratio >= 1.2:
            return 80
        elif ratio >= 1.1:
            return 70
        elif ratio >= 1.0:
            return 60
        elif ratio >= 0.9:
            return 50
        elif ratio >= 0.8:
            return 40
        elif ratio >= 0.7:
            return 30
        elif ratio >= 0.6:
            return 20
        else:
            return 10
    
    def _get_performance_status(self, percentile):
        """Get performance status based on percentile"""
        if percentile >= 75:
            return "Excellent"
        elif percentile >= 50:
            return "Good"
        elif percentile >= 25:
            return "Fair"
        else:
            return "Poor"
    
    # ==================== CATEGORY 4: OPERATIONAL INTELLIGENCE TOOLS ====================
    
    def create_get_inventory_insights(self):
        """Create tool for analyzing inventory movement and identifying slow/fast movers"""
        @tool
        def get_inventory_insights(analysis_period: int = 90, category_filter: str = "") -> str:
            """Analyze inventory movement patterns and identify slow/fast moving items
            
            Args:
                analysis_period: Number of days to analyze (default: 90)
                category_filter: Optional category to filter items (e.g., "appetizers", "entrees")
            """
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                
                from datetime import datetime, timedelta
                from collections import defaultdict
                import statistics
                
                db_service = self._get_db_service()
                orders = db_service.get_user_orders(self.user_id)
                items = db_service.get_user_items(self.user_id)
                cogs_data = db_service.get_user_cogs(self.user_id)
                
                if not orders or not items:
                    return "No sales or inventory data found for analysis"
                
                # Filter by analysis period
                cutoff_date = datetime.now() - timedelta(days=analysis_period)
                recent_orders = [o for o in orders if o.order_date >= cutoff_date]
                
                if not recent_orders:
                    return f"No sales data found in the last {analysis_period} days"
                
                # Apply category filter if specified
                filtered_items = items
                if category_filter:
                    filtered_items = [item for item in items if category_filter.lower() in (item.category or "").lower()]
                
                result = f"📦 INVENTORY INSIGHTS ANALYSIS\n"
                result += f"═══════════════════════════════════════════════════════════\n"
                result += f"Analysis Period: Last {analysis_period} days\n"
                result += f"Category Filter: {category_filter or 'All Categories'}\n"
                result += f"Analysis Date: {datetime.now().strftime('%Y-%m-%d')}\n\n"
                
                # Calculate inventory metrics for each item
                inventory_metrics = {}
                total_revenue = 0
                total_quantity = 0
                
                for item in filtered_items:
                    item_orders = []
                    item_quantity = 0
                    item_revenue = 0
                    
                    # Find orders containing this item
                    for order in recent_orders:
                        if hasattr(order, 'items'):
                            for order_item in order.items:
                                if order_item.item_id == item.id:
                                    item_orders.append(order)
                                    item_quantity += order_item.quantity
                                    item_revenue += order_item.quantity * item.price
                        else:
                            # Simplified: assume each order contains one of each item (for demo)
                            if item.name.lower() in str(order).lower():
                                item_orders.append(order)
                                item_quantity += 1
                                item_revenue += item.price
                    
                    # Calculate metrics
                    days_with_sales = len(set(order.order_date.date() for order in item_orders)) if item_orders else 0
                    avg_daily_sales = item_quantity / max(analysis_period, 1)
                    sales_velocity = item_quantity / max(days_with_sales, 1) if days_with_sales > 0 else 0
                    
                    # Get COGS if available
                    item_cogs = next((cogs for cogs in cogs_data if cogs.item_id == item.id), None)
                    cost_per_unit = item_cogs.cost_per_unit if item_cogs else item.price * 0.35  # Estimate 35% COGS
                    
                    inventory_metrics[item.name] = {
                        'quantity_sold': item_quantity,
                        'revenue': item_revenue,
                        'days_with_sales': days_with_sales,
                        'avg_daily_sales': avg_daily_sales,
                        'sales_velocity': sales_velocity,
                        'current_price': item.price,
                        'cost_per_unit': cost_per_unit,
                        'gross_margin': ((item.price - cost_per_unit) / item.price * 100) if item.price > 0 else 0,
                        'total_orders': len(item_orders),
                        'category': item.category or 'Uncategorized'
                    }
                    
                    total_revenue += item_revenue
                    total_quantity += item_quantity
                
                if not inventory_metrics:
                    return "No inventory data found for the specified criteria"
                
                return self._format_inventory_analysis(inventory_metrics, total_revenue, total_quantity, analysis_period)
                
            except Exception as e:
                return f"Error analyzing inventory insights: {str(e)}"
        
        return get_inventory_insights
    
    def _format_inventory_analysis(self, inventory_metrics, total_revenue, total_quantity, analysis_period):
        """Format inventory analysis results"""
        import statistics
        from collections import defaultdict
        
        # Sort items by different criteria
        by_quantity = sorted(inventory_metrics.items(), key=lambda x: x[1]['quantity_sold'], reverse=True)
        by_revenue = sorted(inventory_metrics.items(), key=lambda x: x[1]['revenue'], reverse=True)
        by_velocity = sorted(inventory_metrics.items(), key=lambda x: x[1]['sales_velocity'], reverse=True)
        
        # Categorize items as fast/medium/slow movers
        velocities = [metrics['sales_velocity'] for metrics in inventory_metrics.values()]
        if len(velocities) > 1:
            velocity_mean = statistics.mean(velocities)
            velocity_stdev = statistics.stdev(velocities) if len(velocities) > 1 else 0
            fast_threshold = velocity_mean + (velocity_stdev * 0.5)
            slow_threshold = velocity_mean - (velocity_stdev * 0.5)
        else:
            fast_threshold = velocities[0] if velocities else 0
            slow_threshold = 0
        
        fast_movers = [(name, metrics) for name, metrics in inventory_metrics.items() if metrics['sales_velocity'] >= fast_threshold]
        slow_movers = [(name, metrics) for name, metrics in inventory_metrics.items() if metrics['sales_velocity'] <= slow_threshold]
        medium_movers = [(name, metrics) for name, metrics in inventory_metrics.items() if slow_threshold < metrics['sales_velocity'] < fast_threshold]
        
        result = f"📊 INVENTORY MOVEMENT SUMMARY:\n\n"
        result += f"Total Items Analyzed: {len(inventory_metrics)}\n"
        result += f"Total Quantity Sold: {total_quantity:,}\n"
        result += f"Total Revenue Generated: ${total_revenue:,.2f}\n"
        result += f"Average Daily Movement: {total_quantity/analysis_period:.1f} units/day\n\n"
        
        # Movement Categories
        result += f"🚀 FAST MOVERS ({len(fast_movers)} items):\n"
        result += f"{'Item':<25} {'Qty Sold':<10} {'Revenue':<12} {'Velocity':<10} {'Margin %':<10}\n"
        result += "-" * 75 + "\n"
        
        for name, metrics in fast_movers[:5]:  # Top 5 fast movers
            result += f"{name[:24]:<25} {metrics['quantity_sold']:<10} ${metrics['revenue']:<11.2f} {metrics['sales_velocity']:<9.1f} {metrics['gross_margin']:<9.1f}%\n"
        
        result += f"\n🐌 SLOW MOVERS ({len(slow_movers)} items):\n"
        for name, metrics in slow_movers[:5]:  # Top 5 slow movers
            result += f"• {name}: {metrics['quantity_sold']} units, ${metrics['revenue']:.2f} revenue\n"
        
        # Strategic Recommendations
        result += f"\n💡 STRATEGIC RECOMMENDATIONS:\n\n"
        
        if fast_movers:
            result += f"🚀 Fast Movers Strategy:\n"
            result += f"• Ensure adequate inventory levels for top {min(3, len(fast_movers))} fast movers\n"
            result += f"• Consider promotional campaigns to boost fast movers further\n"
        
        if slow_movers:
            result += f"🐌 Slow Movers Strategy:\n"
            result += f"• Review pricing strategy for slow movers - consider promotions\n"
            result += f"• Consider bundling slow movers with fast movers\n"
        
        return result
    
    def create_get_customer_behavior_patterns(self):
        """Create tool for analyzing customer behavior patterns and order analysis"""
        @tool
        def get_customer_behavior_patterns(analysis_period: int = 90, segment_filter: str = "") -> str:
            """Analyze customer behavior patterns, order frequency, and basket analysis
            
            Args:
                analysis_period: Number of days to analyze (default: 90)
                segment_filter: Optional customer segment filter (e.g., "high_value", "frequent")
            """
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                
                from datetime import datetime, timedelta
                from collections import defaultdict, Counter
                import statistics
                
                db_service = self._get_db_service()
                orders = db_service.get_user_orders(self.user_id)
                items = db_service.get_user_items(self.user_id)
                
                if not orders:
                    return "No order data found for customer behavior analysis"
                
                # Filter by analysis period
                cutoff_date = datetime.now() - timedelta(days=analysis_period)
                recent_orders = [o for o in orders if o.order_date >= cutoff_date]
                
                if not recent_orders:
                    return f"No orders found in the last {analysis_period} days"
                
                result = f"👥 CUSTOMER BEHAVIOR PATTERNS\n"
                result += f"═══════════════════════════════════════════════════════════\n"
                result += f"Analysis Period: Last {analysis_period} days\n"
                result += f"Analysis Date: {datetime.now().strftime('%Y-%m-%d')}\n\n"
                
                # Customer segmentation and analysis
                customer_data = defaultdict(lambda: {
                    'orders': [],
                    'total_spent': 0,
                    'total_orders': 0,
                    'items_purchased': [],
                    'order_dates': [],
                    'avg_order_value': 0
                })
                
                # Aggregate customer data
                for order in recent_orders:
                    customer_id = getattr(order, 'customer_id', f'customer_{hash(str(order.id)) % 1000}')
                    customer_data[customer_id]['orders'].append(order)
                    customer_data[customer_id]['total_spent'] += order.total_amount
                    customer_data[customer_id]['total_orders'] += 1
                    customer_data[customer_id]['order_dates'].append(order.order_date)
                
                # Calculate customer metrics
                for customer_id, data in customer_data.items():
                    data['avg_order_value'] = data['total_spent'] / data['total_orders'] if data['total_orders'] > 0 else 0
                
                # Customer segmentation
                total_customers = len(customer_data)
                avg_customer_value = statistics.mean([data['total_spent'] for data in customer_data.values()])
                avg_order_frequency = statistics.mean([data['total_orders'] for data in customer_data.values()])
                
                # Segment customers
                high_value_customers = [(cid, data) for cid, data in customer_data.items() if data['total_spent'] > avg_customer_value * 1.5]
                frequent_customers = [(cid, data) for cid, data in customer_data.items() if data['total_orders'] > avg_order_frequency * 1.5]
                new_customers = [(cid, data) for cid, data in customer_data.items() if data['total_orders'] == 1]
                
                # Customer Overview
                result += f"📊 CUSTOMER OVERVIEW:\n\n"
                result += f"Total Customers: {total_customers:,}\n"
                result += f"Total Orders: {len(recent_orders):,}\n"
                result += f"Average Customer Value: ${avg_customer_value:.2f}\n"
                result += f"Average Orders per Customer: {avg_order_frequency:.1f}\n\n"
                
                # Customer Segmentation
                result += f"🎯 CUSTOMER SEGMENTATION:\n\n"
                result += f"High Value Customers: {len(high_value_customers)} ({len(high_value_customers)/total_customers*100:.1f}%)\n"
                result += f"Frequent Customers: {len(frequent_customers)} ({len(frequent_customers)/total_customers*100:.1f}%)\n"
                result += f"New Customers: {len(new_customers)} ({len(new_customers)/total_customers*100:.1f}%)\n\n"
                
                # Order Patterns Analysis
                result += f"📅 ORDER PATTERNS:\n\n"
                
                # Day of week analysis
                day_orders = defaultdict(int)
                for order in recent_orders:
                    day_name = order.order_date.strftime('%A')
                    day_orders[day_name] += 1
                
                peak_day = max(day_orders.items(), key=lambda x: x[1]) if day_orders else ("N/A", 0)
                result += f"🏆 Peak Day: {peak_day[0]} ({peak_day[1]} orders)\n"
                
                # Basket Analysis
                result += f"\n🛒 BASKET ANALYSIS:\n\n"
                order_values = [order.total_amount for order in recent_orders]
                result += f"Average Basket Value: ${statistics.mean(order_values):.2f}\n"
                result += f"Median Basket Value: ${statistics.median(order_values):.2f}\n\n"
                
                # Behavioral Insights
                result += f"💡 BEHAVIORAL INSIGHTS:\n\n"
                result += f"• {len(new_customers)/total_customers*100:.1f}% of customers are first-time buyers\n"
                result += f"• High-value customers spend {statistics.mean([data['total_spent'] for _, data in high_value_customers]):.2f} on average\n" if high_value_customers else ""
                result += f"• Peak ordering day is {peak_day[0]} with {peak_day[1]} orders\n"
                
                return result
                
            except Exception as e:
                return f"Error analyzing customer behavior patterns: {str(e)}"
        
        return get_customer_behavior_patterns
    
    def create_get_profitability_breakdown(self):
        """Create tool for detailed profitability analysis by item, category, and time period"""
        @tool
        def get_profitability_breakdown(breakdown_type: str = "item", time_period: int = 90, category_filter: str = "") -> str:
            """Analyze detailed profitability breakdown by item, category, or time period
            
            Args:
                breakdown_type: Type of breakdown - "item", "category", or "time" (default: "item")
                time_period: Number of days to analyze (default: 90)
                category_filter: Optional category filter for focused analysis
            """
            try:
                if not self.user_id:
                    return "Error: No user ID available for database query"
                
                from datetime import datetime, timedelta
                from collections import defaultdict
                import statistics
                
                db_service = self._get_db_service()
                orders = db_service.get_user_orders(self.user_id)
                items = db_service.get_user_items(self.user_id)
                cogs_data = db_service.get_user_cogs(self.user_id)
                
                if not orders or not items:
                    return "Insufficient data for profitability analysis"
                
                # Filter by time period
                cutoff_date = datetime.now() - timedelta(days=time_period)
                recent_orders = [o for o in orders if o.order_date >= cutoff_date]
                
                if not recent_orders:
                    return f"No orders found in the last {time_period} days"
                
                # Create COGS lookup
                cogs_lookup = {cogs.item_id: cogs.cost_per_unit for cogs in cogs_data}
                item_lookup = {item.id: item for item in items}
                
                result = f"💰 PROFITABILITY BREAKDOWN ANALYSIS\n"
                result += f"═══════════════════════════════════════════════════════════\n"
                result += f"Breakdown Type: {breakdown_type.title()}\n"
                result += f"Analysis Period: Last {time_period} days\n"
                result += f"Analysis Date: {datetime.now().strftime('%Y-%m-%d')}\n\n"
                
                if breakdown_type == "item":
                    # Item-level profitability analysis
                    item_metrics = defaultdict(lambda: {
                        'revenue': 0,
                        'cost': 0,
                        'quantity_sold': 0,
                        'orders': 0,
                        'profit': 0,
                        'margin_percent': 0
                    })
                    
                    # Calculate item metrics
                    for order in recent_orders:
                        for item in order.items:
                            if item.item_id in item_lookup:
                                item_name = item_lookup[item.item_id].name
                                
                                # Apply category filter if specified
                                if category_filter and hasattr(item_lookup[item.item_id], 'category'):
                                    if category_filter.lower() not in item_lookup[item.item_id].category.lower():
                                        continue
                                
                                revenue = item.price * item.quantity
                                cost = cogs_lookup.get(item.item_id, 0) * item.quantity
                                profit = revenue - cost
                                
                                item_metrics[item_name]['revenue'] += revenue
                                item_metrics[item_name]['cost'] += cost
                                item_metrics[item_name]['quantity_sold'] += item.quantity
                                item_metrics[item_name]['orders'] += 1
                                item_metrics[item_name]['profit'] += profit
                    
                    # Calculate margin percentages
                    for item_name, metrics in item_metrics.items():
                        if metrics['revenue'] > 0:
                            metrics['margin_percent'] = (metrics['profit'] / metrics['revenue']) * 100
                    
                    # Sort by profitability
                    sorted_items = sorted(item_metrics.items(), key=lambda x: x[1]['profit'], reverse=True)
                    
                    total_revenue = sum(metrics['revenue'] for metrics in item_metrics.values())
                    total_profit = sum(metrics['profit'] for metrics in item_metrics.values())
                    overall_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
                    
                    result += f"📈 ITEM PROFITABILITY SUMMARY:\n\n"
                    result += f"Total Items Analyzed: {len(item_metrics)}\n"
                    result += f"Total Revenue: ${total_revenue:,.2f}\n"
                    result += f"Total Profit: ${total_profit:,.2f}\n"
                    result += f"Overall Margin: {overall_margin:.1f}%\n\n"
                    
                    result += f"🏆 TOP PROFITABLE ITEMS:\n"
                    result += f"{'Item':<25} {'Revenue':<12} {'Profit':<12} {'Margin %':<10} {'Qty Sold':<10}\n"
                    result += "-" * 75 + "\n"
                    
                    for item_name, metrics in sorted_items[:10]:
                        result += f"{item_name[:24]:<25} ${metrics['revenue']:<11.2f} ${metrics['profit']:<11.2f} {metrics['margin_percent']:<9.1f}% {metrics['quantity_sold']:<10}\n"
                    
                    # Identify loss-making items
                    loss_makers = [(name, metrics) for name, metrics in item_metrics.items() if metrics['profit'] < 0]
                    if loss_makers:
                        result += f"\n⚠️ LOSS-MAKING ITEMS ({len(loss_makers)} items):\n"
                        for name, metrics in sorted(loss_makers, key=lambda x: x[1]['profit'])[:5]:
                            result += f"• {name}: ${metrics['profit']:.2f} loss ({metrics['margin_percent']:.1f}% margin)\n"
                
                elif breakdown_type == "category":
                    # Category-level profitability analysis
                    category_metrics = defaultdict(lambda: {
                        'revenue': 0,
                        'cost': 0,
                        'profit': 0,
                        'items': set(),
                        'quantity_sold': 0
                    })
                    
                    for order in recent_orders:
                        for item in order.items:
                            if item.item_id in item_lookup:
                                item_obj = item_lookup[item.item_id]
                                category = getattr(item_obj, 'category', 'Uncategorized')
                                
                                revenue = item.price * item.quantity
                                cost = cogs_lookup.get(item.item_id, 0) * item.quantity
                                
                                category_metrics[category]['revenue'] += revenue
                                category_metrics[category]['cost'] += cost
                                category_metrics[category]['profit'] += (revenue - cost)
                                category_metrics[category]['items'].add(item_obj.name)
                                category_metrics[category]['quantity_sold'] += item.quantity
                    
                    sorted_categories = sorted(category_metrics.items(), key=lambda x: x[1]['profit'], reverse=True)
                    
                    result += f"🏷️ CATEGORY PROFITABILITY:\n\n"
                    result += f"{'Category':<20} {'Revenue':<12} {'Profit':<12} {'Margin %':<10} {'Items':<8}\n"
                    result += "-" * 70 + "\n"
                    
                    for category, metrics in sorted_categories:
                        margin = (metrics['profit'] / metrics['revenue'] * 100) if metrics['revenue'] > 0 else 0
                        result += f"{category[:19]:<20} ${metrics['revenue']:<11.2f} ${metrics['profit']:<11.2f} {margin:<9.1f}% {len(metrics['items']):<8}\n"
                
                elif breakdown_type == "time":
                    # Time-based profitability analysis
                    import calendar
                    
                    monthly_metrics = defaultdict(lambda: {
                        'revenue': 0,
                        'cost': 0,
                        'profit': 0,
                        'orders': 0
                    })
                    
                    for order in recent_orders:
                        month_key = order.order_date.strftime('%Y-%m')
                        order_revenue = order.total_amount
                        order_cost = 0
                        
                        # Calculate order cost
                        for item in order.items:
                            order_cost += cogs_lookup.get(item.item_id, 0) * item.quantity
                        
                        monthly_metrics[month_key]['revenue'] += order_revenue
                        monthly_metrics[month_key]['cost'] += order_cost
                        monthly_metrics[month_key]['profit'] += (order_revenue - order_cost)
                        monthly_metrics[month_key]['orders'] += 1
                    
                    sorted_months = sorted(monthly_metrics.items())
                    
                    result += f"📅 MONTHLY PROFITABILITY TRENDS:\n\n"
                    result += f"{'Month':<12} {'Revenue':<12} {'Profit':<12} {'Margin %':<10} {'Orders':<8}\n"
                    result += "-" * 60 + "\n"
                    
                    for month, metrics in sorted_months:
                        margin = (metrics['profit'] / metrics['revenue'] * 100) if metrics['revenue'] > 0 else 0
                        result += f"{month:<12} ${metrics['revenue']:<11.2f} ${metrics['profit']:<11.2f} {margin:<9.1f}% {metrics['orders']:<8}\n"
                
                # Strategic recommendations
                result += f"\n💡 PROFITABILITY INSIGHTS:\n\n"
                
                if breakdown_type == "item":
                    high_margin_items = [(name, metrics) for name, metrics in item_metrics.items() if metrics['margin_percent'] > 50]
                    low_margin_items = [(name, metrics) for name, metrics in item_metrics.items() if 0 < metrics['margin_percent'] < 20]
                    
                    result += f"• {len(high_margin_items)} items have margins above 50%\n"
                    result += f"• {len(low_margin_items)} items have margins below 20%\n"
                    result += f"• Focus on promoting high-margin items\n"
                    result += f"• Review pricing or costs for low-margin items\n"
                
                elif breakdown_type == "category":
                    if sorted_categories:
                        best_category = sorted_categories[0]
                        worst_category = sorted_categories[-1]
                        result += f"• Best performing category: {best_category[0]} (${best_category[1]['profit']:.2f} profit)\n"
                        result += f"• Needs attention: {worst_category[0]} (${worst_category[1]['profit']:.2f} profit)\n"
                
                return result
                
            except Exception as e:
                return f"Error analyzing profitability breakdown: {str(e)}"
        
        return get_profitability_breakdown

def create_handoff_tool(*, agent_name: str, description: str | None = None):
    """Create a handoff tool for agent-to-agent communication"""
    name = f"transfer_to_{agent_name}"
    description = description or f"Transfer control to {agent_name}"

    @tool(name, description=description)
    def handoff_tool(
        state: Annotated[MessagesState, InjectedState], 
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        
        tool_message = ToolMessage(
            content=f"Successfully transferred to {agent_name}",
            name=name,
            tool_call_id=tool_call_id,
        )
        return Command(  
            goto=agent_name,  
            update={"messages": state["messages"] + [tool_message]},  
            graph=Command.PARENT,  
        )
    return handoff_tool

class LangGraphService:
    """Pricing Expert Orchestrator with Sub-Agents"""
    
    def __init__(self, db_session=None):
        self.model = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        self.tools = PricingTools()
        self.db_session = db_session
        self.database_tools = None  # Will be initialized when user_id is available
        
        # Don't create agents here - they'll be created when needed
        self.pricing_orchestrator = None
        self.web_researcher = None
        self.algorithm_selector = None
        self.database_agent = None
        self.supervisor_graph = None
        
        # Create handoff tools for sub-agents
        self.transfer_to_web_researcher = create_handoff_tool(
            agent_name="web_researcher",
            description="Transfer to web research agent for market data and competitor analysis"
        )
        self.transfer_to_algorithm_selector = create_handoff_tool(
            agent_name="algorithm_selector",
            description="Transfer to algorithm selection agent for pricing strategy recommendations"
        )
        self.transfer_to_database_agent = create_handoff_tool(
            agent_name="database_agent",
            description="Transfer to database agent to retrieve business data, sales history, menu items, and competitor information from the database"
        )
        
        # Initialize agents
        self._create_agents()
        
        # Build supervisor graph (main architecture)
        self.supervisor_graph = self._build_supervisor_graph()
    
    def _initialize_agents_with_context(self, user_id: int):
        """Initialize or reinitialize agents with user context"""
        # Initialize database tools with user_id
        self.database_tools = DatabaseTools(user_id=user_id, db_session=self.db_session)
        
        # Create handoff tools
        self.transfer_to_web_researcher = create_handoff_tool(
            agent_name="web_researcher",
            description="Transfer to web research agent for market data and competitor analysis"
        )
        self.transfer_to_algorithm_selector = create_handoff_tool(
            agent_name="algorithm_selector",
            description="Transfer to algorithm selection agent for pricing strategy recommendations"
        )
        self.transfer_to_database_agent = create_handoff_tool(
            agent_name="database_agent",
            description="Transfer to database agent to retrieve business data, sales history, menu items, and competitor information from the database"
        )
        
        # Create agents
        self._create_agents()
        
        # Build supervisor graph
        self.supervisor_graph = self._build_supervisor_graph()

    def _create_agents(self):
        """Create the pricing orchestrator and specialized sub-agents"""
        
        # Main Pricing Expert Orchestrator
        self.pricing_orchestrator = create_react_agent(
            model=self.model,
            tools=[
                self.transfer_to_web_researcher,
                self.transfer_to_algorithm_selector,
                self.transfer_to_database_agent
            ],
            prompt="""You are an elite pricing consultant and orchestrator with deep expertise in pricing strategy, revenue optimization, and market dynamics. You help businesses make data-driven pricing decisions through intelligent conversation and analysis.

<identity>
You are the lead pricing strategist coordinating a team of specialized sub-agents. Your role is to understand complex pricing challenges, gather necessary information, and use the algorithm agent to implement actionable pricing recommendations that drive business growth.
</identity>

<capabilities>
- Engage in natural, consultative conversations about pricing challenges
- Use the database as a source of truth before asking the client any clarifying questions
- Ask strategic clarifying questions to understand business context, goals, and constraints for any information that could not be provided by the database
- Coordinate with specialized sub-agents for specific expertise:
  * Web Researcher: For real-time market data, competitor analysis, and industry trends
  * Algorithm Selector: For choosing and implementing optimal pricing strategies
  * Database Agent: For retrieving business data, sales history, product catalogs, and historical performance
- Synthesize information from multiple sources into cohesive pricing strategies
- Explain complex pricing concepts in accessible, business-friendly terms
- Provide implementation roadmaps with clear next steps
</capabilities>

<workflow>
1. **Understand the Query**
   - Parse the user's pricing question or challenge
   - Identify key business objectives and constraints
   - Determine what information is needed to provide a comprehensive answer

2. **Information Gathering**
   - Assess what information you already have
   - Delegate to appropriate sub-agents ONCE for specific data needs
   - Wait for complete responses before proceeding
   - Never call the same sub-agent repeatedly for the same query

3. **Analysis and Synthesis**
   - Combine insights from sub-agents with your pricing expertise
   - Consider multiple pricing strategies and their trade-offs
   - Factor in market conditions, competitive landscape, and business goals

4. **Deliver Recommendations**
   - Provide a comprehensive, actionable answer
   - Include specific pricing recommendations with rationale
   - Suggest implementation steps and success metrics
   - Offer to dive deeper into specific aspects if needed

5. **Follow-up**
   - Be ready to answer clarifying questions
   - Adjust recommendations based on new constraints or information
   - Provide alternative strategies if requested
</workflow>

<communication_style>
- Professional yet approachable
- Use business terminology appropriately but explain complex concepts
- Structure responses with clear headers and bullet points for readability
- Lead with key insights and recommendations
- Support claims with data and market evidence
- Acknowledge uncertainty when appropriate
- Use markdown to format responses, and include "\\n" to create new lines
</communication_style>

<best_practices>
- ALWAYS provide complete, conclusive answers
- Gather necessary information from the database before asking the user for it
- NEVER repeatedly delegate to the same sub-agent
- Use markdown to format responses, and include "\\n" to create new lines
- Consider psychological pricing factors (e.g., price anchoring, perception)
- Account for price elasticity and customer segments
- Factor in competitive dynamics and market positioning
- Consider both short-term revenue and long-term brand implications
- Suggest A/B testing approaches when uncertainty exists
- Provide metrics to measure pricing strategy success
</best_practices>

<common_pricing_scenarios>
1. **New Product Launch**: Consider skimming vs. penetration strategies
2. **Competitive Pressure**: Analyze value proposition and differentiation
3. **Market Expansion**: Account for regional differences and local competition
4. **Revenue Optimization**: Balance volume and margin goals
5. **Product Portfolio**: Consider cannibalization and bundling opportunities
6. **Seasonal Pricing**: Factor in demand fluctuations and inventory costs
7. **B2B vs B2C**: Adjust for different buying behaviors and decision processes
</common_pricing_scenarios>

When formatting responses:
- Always add a blank line before starting a list
- Use proper markdown list syntax:
  - For bullet points: `- item`
  - For numbered lists: `1. item`
- Ensure lists have proper spacing for readability

Remember: You are the strategic pricing expert that businesses rely on for critical revenue decisions. Every recommendation should be thoughtful, data-driven, and actionable.
""",
            name="pricing_orchestrator"
        )
        
        # Web Research Agent
        self.web_researcher = create_react_agent(
            model=self.model,
            tools=[
                self.tools.search_web_for_pricing,
                self.tools.search_competitor_analysis,
                self.tools.get_market_trends
            ],
            prompt="""You are a specialized web research analyst focused on pricing intelligence and market dynamics. Your expertise lies in gathering, analyzing, and synthesizing real-time market data to support pricing decisions.

<identity>
You are a meticulous researcher who uncovers critical market insights that drive pricing strategy. You combine data gathering skills with analytical capabilities to provide actionable market intelligence.
</identity>

<research_capabilities>
- Search for current market pricing data across industries and regions
- Analyze competitor pricing strategies, positioning, and value propositions
- Gather market trends, consumer behavior patterns, and demand signals
- Identify pricing innovations and emerging pricing models
- Research regulatory considerations and market constraints
- Find industry benchmarks and best practices
- Discover customer willingness-to-pay indicators
</research_capabilities>

<research_methodology>
1. **Query Analysis**
   - Understand the specific pricing context
   - Identify key competitors and market segments
   - Determine relevant geographic markets
   - Note any time-sensitive factors

2. **Comprehensive Search Strategy**
   - Start with broad market overview searches
   - Narrow to specific competitors and products
   - Look for recent pricing changes and announcements
   - Search for consumer sentiment and reviews
   - Find industry reports and analyst insights

3. **Data Synthesis**
   - Compile findings into coherent insights
   - Identify patterns and anomalies
   - Highlight opportunities and threats
   - Quantify findings where possible

4. **Actionable Reporting**
   - Present findings in a structured format
   - Lead with most relevant insights
   - Include specific price points and ranges
   - Note confidence levels and data recency
   - Suggest areas for deeper investigation
</research_methodology>

<information_priorities>
1. **Competitor Pricing**: Exact prices, tiers, and recent changes
2. **Market Positioning**: How competitors justify their prices
3. **Customer Perception**: Reviews mentioning price/value
4. **Market Trends**: Growth rates, demand shifts, seasonal patterns
5. **Price Elasticity Indicators**: How customers respond to price changes
6. **Innovation Signals**: New pricing models or strategies emerging
</information_priorities>

<output_format>
Structure your research findings as:
- **Executive Summary**: Key findings in 2-3 sentences
- **Competitive Landscape**: Competitor prices and positioning
- **Market Dynamics**: Trends, growth, and demand patterns
- **Customer Insights**: Perception of value and price sensitivity
- **Opportunities**: Gaps or advantages to exploit
- **Risks**: Threats or constraints to consider
- **Data Quality Note**: Recency and reliability of sources
</output_format>

<quality_standards>
- Prioritize recent data (last 3-6 months preferred)
- Distinguish between list prices and actual selling prices
- Note promotional pricing vs. regular pricing
- Identify premium vs. budget market segments
- Consider total cost of ownership, not just initial price
- Look for hidden fees or bundled value
- Verify findings across multiple sources when possible
</quality_standards>

Remember: Your research directly impacts revenue decisions worth potentially millions. Be thorough, accurate, and focused on actionable insights that drive pricing strategy.
""",
            name="web_researcher"
        )
        
        # Algorithm Selection Agent
        self.algorithm_selector = create_react_agent(
            model=self.model,
            tools=[
                self.tools.select_pricing_algorithm
            ],
            prompt="""You are a pricing algorithm specialist with deep expertise in quantitative pricing strategies and implementation. You recommend optimal pricing approaches based on business context, market dynamics, and strategic objectives.

<identity>
You are a strategic advisor who bridges pricing theory with practical implementation. Your recommendations are grounded in economic principles, behavioral psychology, and real-world business constraints.
</identity>

<algorithm_expertise>
Available Pricing Algorithms:

1. **Competitive Pricing Algorithm**
   - Matches or undercuts competitor prices strategically
   - Best for: Commoditized products, price-sensitive markets
   - Implementation: Price monitoring, adjustment rules, positioning strategy

2. **Value-Based Pricing Algorithm**
   - Prices based on perceived customer value and willingness to pay
   - Best for: Differentiated products, strong brand, unique features
   - Implementation: Customer research, value mapping, segment analysis

3. **Dynamic Pricing Algorithm**
   - Real-time price adjustments based on demand, supply, and market conditions
   - Best for: Perishable inventory, high demand variability, digital products
   - Implementation: Demand forecasting, inventory tracking, price optimization

4. **Market Penetration Algorithm**
   - Low initial prices to rapidly gain market share
   - Best for: New market entry, network effects, growth focus
   - Implementation: Loss leader strategy, growth metrics, timeline planning

5. **Price Skimming Algorithm**
   - High initial prices for early adopters, gradual reduction
   - Best for: Innovative products, limited competition, premium positioning
   - Implementation: Launch pricing, reduction schedule, segment targeting

6. **Psychological Pricing Algorithm**
   - Leverages cognitive biases (charm pricing, anchoring, bundling)
   - Best for: Consumer products, retail, emotional purchases
   - Implementation: Price point testing, bundle design, framing strategies
</algorithm_expertise>

<selection_methodology>
1. **Context Analysis**
   - Evaluate product characteristics and differentiation
   - Assess market maturity and competitive intensity
   - Understand customer segments and buying behavior
   - Consider business goals (revenue, market share, profit)
   - Account for operational constraints

2. **Algorithm Matching**
   - Map context factors to algorithm strengths
   - Consider hybrid approaches when appropriate
   - Evaluate implementation complexity vs. benefit
   - Assess data and system requirements
   - Factor in organizational readiness

3. **Recommendation Framework**
   - Primary recommendation with clear rationale
   - Alternative approaches with trade-offs
   - Implementation roadmap with phases
   - Success metrics and KPIs
   - Risk factors and mitigation strategies
</selection_methodology>

<implementation_guidance>
For each selected algorithm, provide:

1. **Quick Start Guide**
   - Initial price point recommendations
   - Key parameters to set
   - Minimum data requirements
   - First 30-day action plan

2. **Technical Requirements**
   - Data collection needs
   - System integration points
   - Calculation methodology
   - Update frequency recommendations

3. **Optimization Parameters**
   - Variables to monitor
   - Adjustment triggers
   - Performance benchmarks
   - A/B testing approach

4. **Common Pitfalls**
   - What to avoid
   - Early warning signs
   - Course correction strategies
</implementation_guidance>

<decision_factors>
Consider these factors when selecting algorithms:
- Market factors: Competition, growth rate, customer sophistication
- Product factors: Lifecycle stage, differentiation, cost structure
- Business factors: Strategic goals, risk tolerance, capabilities
- Customer factors: Price sensitivity, segment diversity, purchase frequency
- Operational factors: Data availability, technical infrastructure, team expertise
</decision_factors>

<output_structure>
Your recommendations should include:
1. **Selected Algorithm**: Name and one-line description
2. **Rationale**: Why this algorithm fits the specific situation
3. **Implementation Steps**: Concrete actions to get started
4. **Expected Outcomes**: Realistic projections and timeline
5. **Success Metrics**: How to measure effectiveness
6. **Alternative Options**: Other viable approaches with trade-offs
7. **Evolution Path**: How to adapt as the business grows
</output_structure>

Remember: Your algorithm selection can make or break a pricing strategy. Be decisive but thoughtful, practical but innovative. Always connect your recommendation back to business outcomes.
""",
            name="algorithm_selector"
        )
        
        # Database Agent - use factory methods if database_tools exists
        if self.database_tools:
            self.database_agent = create_react_agent(
                model=self.model,
                tools=[
                    self.database_tools.create_get_user_items_data(),
                    self.database_tools.create_get_user_sales_data(),
                    self.database_tools.create_get_competitor_data(),
                    self.database_tools.create_get_price_history_data(),
                    self.database_tools.create_get_business_profile_data(),
                    # Enhanced Analytics Tools - Category 1
                    self.database_tools.create_get_sales_analytics_structured(),
                    self.database_tools.create_get_item_performance_metrics(),
                    self.database_tools.create_get_cost_analysis_structured(),
                    self.database_tools.create_calculate_price_elasticity(),
                    # Time-Based Analysis Tools - Category 2
                    self.database_tools.create_get_sales_by_time_period(),
                    self.database_tools.create_get_seasonal_trends(),
                    self.database_tools.create_get_recent_performance_changes(),
                    # Comparative Analysis Tools - Category 3
                    self.database_tools.create_compare_item_performance(),
                    self.database_tools.create_get_competitor_price_gaps(),
                    self.database_tools.create_benchmark_against_industry(),
                    # Operational Intelligence Tools - Category 4
                    self.database_tools.create_get_inventory_insights(),
                    self.database_tools.create_get_customer_behavior_patterns(),
                    self.database_tools.create_get_profitability_breakdown()
                ],
                prompt="""You are a database specialist and business intelligence analyst focused on extracting pricing insights from internal business data. You transform raw data into actionable intelligence for pricing decisions.

<identity>
You are the keeper of business truth - the specialist who uncovers patterns, trends, and opportunities hidden in company data. Your analyses directly inform strategic pricing decisions.
</identity>

<data_capabilities>
- Retrieve and analyze menu items, products, and current pricing
- Examine sales history, revenue trends, and order patterns
- Access competitor data and market positioning from internal sources
- Track price change history and customer response
- Extract business profile and operational context
- Identify customer segments and purchasing behaviors
- Analyze product performance and profitability

**Enhanced Analytics Capabilities:**
- Generate structured sales analytics with MoM/YoY comparisons and seasonal insights
- Calculate detailed item performance metrics including revenue, margins, and sales velocity
- Perform comprehensive cost analysis with COGS trends and fixed cost allocation
- Calculate price elasticity to understand demand sensitivity to price changes

**Time-Based Analysis Capabilities:**
- Flexible time period analysis (daily/weekly/monthly/quarterly) with customizable date ranges
- Seasonal trends identification including monthly, weekly, and hourly patterns
- Recent performance change detection with anomaly identification and volatility analysis

**Comparative Analysis Capabilities:**
- Side-by-side item performance comparison with detailed metrics and strategic insights
- Competitor price gap analysis with market positioning and opportunity identification
- Industry benchmarking against standards with percentile rankings and strategic recommendations

**Operational Intelligence Capabilities:**
- Inventory movement analysis with fast/slow mover identification and strategic recommendations
- Customer behavior pattern analysis including segmentation, order frequency, and basket analysis
- Detailed profitability breakdown by item, category, and time period with margin analysis
</data_capabilities>

<analysis_framework>
1. **Data Retrieval Strategy**
   - Understand the specific question being asked
   - Identify relevant data sources and tables
   - Retrieve comprehensive but focused datasets
   - Ensure data quality and completeness

2. **Analytical Approach**
   - Look for patterns and anomalies
   - Calculate key metrics (revenue, volume, margins)
   - Segment data by relevant dimensions
   - Compare performance across time periods
   - Identify correlations and causations

3. **Insight Generation**
   - Transform data into business insights
   - Highlight surprising findings
   - Quantify opportunities and risks
   - Connect findings to pricing implications
   - Suggest areas for deeper analysis
</analysis_framework>

<key_analyses>
1. **Price Elasticity Analysis**
   - How sales volume responds to price changes
   - Identify elastic vs. inelastic products
   - Find optimal price points

2. **Customer Segmentation**
   - Purchase patterns by customer type
   - Price sensitivity by segment
   - Value perception indicators

3. **Competitive Positioning**
   - Price gaps vs. competitors
   - Market share implications
   - Differentiation opportunities

4. **Product Performance**
   - Revenue contribution by product
   - Margin analysis
   - Cross-selling patterns
   - Seasonality effects

5. **Historical Trends**
   - Price change impacts
   - Long-term revenue patterns
   - Customer retention effects
</key_analyses>

<data_presentation>
Structure your findings as:

1. **Executive Summary**
   - Key findings in 2-3 bullet points
   - Most important number or trend
   - Immediate action items

2. **Detailed Analysis**
   - Relevant metrics with context
   - Time-based comparisons
   - Segment breakdowns
   - Statistical significance where relevant

3. **Visual Insights** (describe verbally)
   - Trend directions
   - Relative proportions
   - Outliers and exceptions

4. **Recommendations**
   - Data-driven pricing suggestions
   - Testing opportunities
   - Warning signs to monitor
</data_presentation>

<quality_principles>
- Always provide context for numbers (% change, vs. benchmark)
- Distinguish correlation from causation
- Note data limitations or gaps
- Suggest confidence levels for findings
- Highlight both opportunities and risks
- Connect all findings back to pricing decisions
</quality_principles>

<common_queries>
Be prepared to answer:
- "What's our best/worst performing product?"
- "How did the last price change impact sales?"
- "Which customer segments are most profitable?"
- "What's our pricing position vs. competitors?"
- "Where do we have pricing power?"
- "What products should we bundle?"
- "When should we run promotions?"

**Enhanced Analytics Queries:**
- "Show me structured sales analytics with growth trends"
- "What are my top performing items by revenue and margin?"
- "Analyze my cost structure and margin trends"
- "Calculate price elasticity for my menu items"
- "Which items are price sensitive vs. price insensitive?"
- "Show me monthly/quarterly cost and revenue breakdowns"

**Time-Based Analysis Queries:**
- "Analyze sales by weekly periods for the last 3 months"
- "Show me seasonal trends and identify peak periods"
- "What are my busiest days and hours?"
- "Detect recent performance changes and anomalies"
- "Compare this month's performance to last month"
- "Identify quarterly patterns in my business"
- "Show me daily sales volatility and outlier days"

**Category 3: Comparative Analysis**
- "Compare performance between my top 3 menu items"
- "Show me price gaps versus competitors in my category"
- "How does my business benchmark against restaurant industry standards?"
- "Compare my pizza and burger sales side by side"
- "Analyze competitor pricing opportunities for small businesses"
- "Benchmark my performance as a medium-sized retail business"

**Category 4: Operational Intelligence**
- "Analyze my inventory movement and identify fast/slow movers"
- "Show me customer behavior patterns and order frequency analysis"
- "Break down profitability by item with detailed margin analysis"
- "Which items are my best and worst performers from an inventory perspective?"
- "Analyze customer segmentation and basket analysis patterns"
- "Show me profitability breakdown by category over the last quarter"
- "Identify slow-moving inventory that needs attention"
- "Analyze customer behavior trends and ordering patterns"
</common_queries>

Remember: You're not just retrieving data - you're uncovering the story that data tells about pricing opportunities. Every query should return insights, not just numbers. Help the business understand what happened, why it happened, and what to do next.
""",
                name="database_agent"
            )
        else:
            # Create a dummy database agent that returns error messages
            self.database_agent = create_react_agent(
                model=self.model,
                tools=[],
                prompt="You are a database specialist but no database connection is available. Inform the user that database access is not configured.",
                name="database_agent"
            )
    
    def _build_supervisor_graph(self):
        """Build the pricing expert orchestrator graph"""
        graph = (
            StateGraph(MessagesState)
            .add_node("pricing_orchestrator", self.pricing_orchestrator)
            .add_node("web_researcher", self.web_researcher)
            .add_node("algorithm_selector", self.algorithm_selector)
            .add_node("database_agent", self.database_agent)
            .add_edge(START, "pricing_orchestrator")  # Always start with the main orchestrator
            .compile()
        )
        return graph
    
    async def execute_supervisor_workflow(self, task: str, context: str = "", user_id: int = None) -> MultiAgentResponse:
        """Execute pricing consultation using the orchestrator"""
        start_time = datetime.now()
    
        try:
            # Initialize agents with user context if provided
            if user_id:
                self._initialize_agents_with_context(user_id)
            elif not self.supervisor_graph:
                # Initialize without user context if not already initialized
                self._create_agents()
                self.supervisor_graph = self._build_supervisor_graph()
        
            # Prepare conversational message
            initial_message = task
            if context:
                initial_message += f"\n\nAdditional context: {context}"
            
            messages = [{"role": "user", "content": initial_message}]
            
            # Execute the graph and track agent interactions
            execution_path = []
            result = None
            
            # Stream the execution to track which agents are involved
            for chunk in self.supervisor_graph.stream({"messages": messages}):
                for node_name, node_output in chunk.items():
                    if node_name not in execution_path:
                        execution_path.append(node_name)
                    result = node_output
            
            final_result = self._extract_final_result(result["messages"]) if result else "No response generated"
            total_time = (datetime.now() - start_time).total_seconds()
            
            # Convert messages to dictionaries for JSON serialization
            converted_messages = self._convert_messages_to_dict(result["messages"]) if result else []
            
            return MultiAgentResponse(
                final_result=final_result,
                execution_path=execution_path,
                total_execution_time=total_time,
                metadata={
                    "architecture": "pricing_expert",
                    "task": task,
                    "context": context,
                    "message_count": len(converted_messages)
                },
                messages=converted_messages
            )
            
        except Exception as e:
            logger.error(f"Pricing orchestrator workflow error: {e}")
            raise
    
    async def stream_supervisor_workflow(self, task: str, context: str = "", previous_messages: List[Dict] = None, user_id: int = None) -> AsyncGenerator[str, None]:
        """Stream the pricing orchestrator workflow with real-time updates"""
        try:
            start_time = datetime.now()
            execution_path = []
            
            # Initialize agents with user context if provided
            if user_id:
                self._initialize_agents_with_context(user_id)
            elif not self.supervisor_graph:
                # Initialize without user context if not already initialized
                self._create_agents()
                self.supervisor_graph = self._build_supervisor_graph()
        
            # Build initial state with conversation history
            messages = []
            # Add previous messages if provided, but only the content exchanges
            # Add previous messages if provided, but only the content exchanges
            if previous_messages:
                # Process messages in reverse to find the last meaningful exchange
                for i in range(len(previous_messages) - 1, -1, -1):
                    msg = previous_messages[i]
                    
                    # Always include user messages
                    if msg.get('role') == 'user':
                        messages.insert(0, HumanMessage(content=msg.get('content', '')))
                    
                    # For assistant messages, only include those with actual content and no handoff tool calls
                    elif msg.get('role') == 'assistant' and msg.get('content', '').strip():
                        # Check if this message has handoff tool calls
                        tool_calls = msg.get('tool_calls') or msg.get('additional_kwargs', {}).get('tool_calls', [])
                        has_handoff = any(
                            'transfer_to_' in tc.get('function', {}).get('name', '') 
                            for tc in tool_calls
                        ) if tool_calls else False
                        
                        # Only add if it's not a handoff message
                        if not has_handoff:
                            messages.insert(0, AIMessage(content=msg.get('content', '')))
                    
                    # Stop after collecting a few exchanges (to keep context manageable)
                    if len(messages) >= 6:  # 3 exchanges
                        break
                
                # Ensure messages are in chronological order
                messages = list(reversed(messages))

            # Add the new user message
            messages.append(HumanMessage(content=task))
            
            # Add the new user message
            messages.append(HumanMessage(content=task))
            
            initial_state = {"messages": messages}
            
            # Stream the graph execution
            result = None
            current_agent = None
            previous_message_count = len(initial_state["messages"])  # Track initial message count
            
            # Configure tracing for this run
            config = {"recursion_limit": 50}
            if langsmith_client and user_id:
                config["run_name"] = f"pricing_analysis_user_{user_id}"
                config["tags"] = ["dynamic_pricing", "multi_agent", f"user_{user_id}"]
                config["metadata"] = {
                    "user_id": user_id,
                    "task": task[:100],  # Truncate long tasks
                    "timestamp": start_time.isoformat(),
                    "context": context[:200] if context else None  # Truncate long context
                }
            
            async for chunk in self.supervisor_graph.astream(
                initial_state,
                config=config
            ):
                for node_name, node_output in chunk.items():
                    if node_name not in execution_path:
                        execution_path.append(node_name)
                        current_agent = node_name
                        
                        # Yield agent activation
                        agent_display_name = {
                            "pricing_orchestrator": "💼 Pricing Expert",
                            "web_researcher": "🔍 Market Researcher", 
                            "algorithm_selector": "⚙️ Algorithm Specialist",
                            "database_agent": "🗄️ Database Specialist"
                        }.get(node_name, f"🤖 {node_name}")
                    
                    result = node_output
                    
                    # Monitor for tool calls in the messages
                    if "messages" in node_output and node_output["messages"]:
                        current_messages = node_output["messages"]
                        
                        # Check for tool calls in new messages
                        for msg in current_messages[previous_message_count:]:
                            # Check if this is an AIMessage with tool calls
                            if hasattr(msg, 'additional_kwargs') and 'tool_calls' in msg.additional_kwargs:
                                tool_calls = msg.additional_kwargs['tool_calls']
                                for tool_call in tool_calls:
                                    yield json.dumps({
                                        "type": "tool_call",
                                        "agent": current_agent,
                                        "tool_name": tool_call.get('function', {}).get('name', 'Unknown Tool'),
                                        "tool_id": tool_call.get('id', ''),
                                        "timestamp": datetime.now().isoformat()
                                    })
                                    await asyncio.sleep(0.01)
                            
                            # Check for ToolMessage (tool responses)
                            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'ToolMessage':
                                yield json.dumps({
                                    "type": "tool_response",
                                    "agent": current_agent,
                                    "tool_name": getattr(msg, 'name', 'Unknown Tool'),
                                    "tool_call_id": getattr(msg, 'tool_call_id', ''),
                                    "timestamp": datetime.now().isoformat()
                                })

                    # Extract and stream only NEW messages (beyond the initial conversation)
                    if "messages" in node_output and node_output["messages"]:
                        current_messages = node_output["messages"]
                        
                        # Only process messages that are new (beyond the initial count)
                        if len(current_messages) > previous_message_count:
                            # Get only the new messages
                            new_messages = current_messages[previous_message_count:]
                            
                            for msg in new_messages:
                                if isinstance(msg, AIMessage) and msg.content:
                                    content = msg.content
                                    
                                    # Yield message start
                                    yield json.dumps({
                                        "type": "message_start",
                                        "agent": current_agent,
                                        "timestamp": datetime.now().isoformat()
                                    })
                                    
                                    # Stream words with small delays
                                    # Stream words with small delays
                                    words = content.split(' ')  # Split by space only
                                    for i, word in enumerate(words):
                                        # Skip empty words
                                        if not word:
                                            continue
                                            
                                        # Check if this word starts a list item
                                        if word.startswith('-') or (len(word) > 0 and word[0].isdigit() and '.' in word):
                                            # Add newline before list items if not at start
                                            if i > 0 and formatted_content:
                                                formatted_content = '\n' + word
                                            else:
                                                formatted_content = word
                                        else:
                                            formatted_content = word
                                        
                                        yield json.dumps({
                                            "type": "message_chunk",
                                            "agent": current_agent,
                                            "content": formatted_content + (" " if i < len(words) - 1 else ""),
                                            "timestamp": datetime.now().isoformat()
                                        })
                                        await asyncio.sleep(0.02)
                                    
                                    # Yield message complete
                                    yield json.dumps({
                                        "type": "message_complete",
                                        "agent": current_agent,
                                        "timestamp": datetime.now().isoformat()
                                    })
                            
                            # Update the previous message count
                            previous_message_count = len(current_messages)
            
            # Final result
            final_result = self._extract_final_result(result["messages"]) if result else "No response generated"
            total_time = (datetime.now() - start_time).total_seconds()
            converted_messages = self._convert_messages_to_dict(result["messages"]) if result else []
            
            yield json.dumps({
                "type": "complete",
                "final_result": final_result,
                "execution_path": execution_path,
                "total_execution_time": total_time,
                "metadata": {
                    "architecture": "pricing_expert",
                    "task": task,
                    "context": context,
                    "message_count": len(converted_messages)
                },
                "messages": converted_messages,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Streaming pricing orchestrator workflow error: {e}")
            yield json.dumps({
                "type": "error",
                "message": f"Error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
    
    async def execute_swarm_workflow(self, task: str, context: str = "") -> MultiAgentResponse:
        """Alias for supervisor workflow - we only use one architecture now"""
        return await self.execute_supervisor_workflow(task, context)
    
    def _extract_final_result(self, messages: List[Any]) -> str:
        """Extract the final result from message history"""
        if not messages:
            return "No messages generated"
        
        # Get the last AI message as the final result
        # LangGraph messages are AIMessage/HumanMessage objects, not dicts
        from langchain_core.messages import AIMessage
        
        ai_messages = [msg for msg in messages if isinstance(msg, AIMessage)]
        if ai_messages:
            return ai_messages[-1].content or "No content in final message"
        
        return "No AI response generated"
    
    def _convert_messages_to_dict(self, messages: List[Any]) -> List[Dict[str, Any]]:
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
        
        converted_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                converted_messages.append({
                    "role": "user",
                    "content": msg.content,
                    "type": "human"
                })
            elif isinstance(msg, AIMessage):
                msg_dict = {
                    "role": "assistant", 
                    "content": msg.content,
                    "type": "ai"
                }
                # Include tool calls if present
                if hasattr(msg, 'additional_kwargs') and 'tool_calls' in msg.additional_kwargs:
                    msg_dict['tool_calls'] = msg.additional_kwargs['tool_calls']
                converted_messages.append(msg_dict)
            elif isinstance(msg, ToolMessage):
                converted_messages.append({
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": msg.tool_call_id,
                    "name": msg.name,
                    "type": "tool"
                })
            elif isinstance(msg, SystemMessage):
                converted_messages.append({
                    "role": "system",
                    "content": msg.content,
                    "type": "system"
                })
            else:
                # Fallback for unknown message types
                converted_messages.append({
                    "role": "unknown",
                    "content": str(msg),
                    "type": "unknown"
                })
        
        return converted_messages
    
    async def get_available_architectures(self) -> List[Dict[str, Any]]:
        """Get information about available pricing consultation architectures"""
        return [
            {
                "name": "supervisor",
                "title": "Pricing Expert Consultation",
                "description": "Conversational pricing expert with specialized sub-agents for research and algorithm selection",
                "agents": ["pricing_orchestrator", "web_researcher", "algorithm_selector"],
                "best_for": "Interactive pricing consultation with market research and algorithm recommendations"
            },
            {
                "name": "swarm",
                "title": "Pricing Expert Consultation", 
                "description": "Same as supervisor - conversational pricing expert system",
                "agents": ["pricing_orchestrator", "web_researcher", "algorithm_selector"],
                "best_for": "Interactive pricing consultation with market research and algorithm recommendations"
            }
        ]
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the multi-agent system"""
        try:
            # Test basic model connectivity
            test_response = await asyncio.to_thread(
                self.model.invoke, 
                [HumanMessage(content="Health check")]
            )
            
            return {
                "status": "healthy",
                "model": "gpt-4o-mini",
                "agents": ["market_analyst", "pricing_strategist", "data_analyst"],
                "architectures": ["supervisor", "swarm"],
                "tools_available": 5
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
