# LangGraph Tools Testing Examples

This document provides example commands for testing all available LangGraph tools.

## 🔧 Pricing Tools (No User ID Required)

### 1. Search Web for Pricing
```bash
python3 test_langgraph_tools.py --tool search_web_for_pricing "premium coffee beans"
python3 test_langgraph_tools.py --tool search_web_for_pricing "artisan pastries"
```

### 2. Competitor Analysis
```bash
python3 test_langgraph_tools.py --tool search_competitor_analysis "Espresso Blend" "coffee"
python3 test_langgraph_tools.py --tool search_competitor_analysis "Croissant" "pastry"
```

### 3. Market Trends
```bash
python3 test_langgraph_tools.py --tool get_market_trends "coffee"
python3 test_langgraph_tools.py --tool get_market_trends "bakery"
```

### 4. Pricing Algorithm Selection
```bash
python3 test_langgraph_tools.py --tool select_pricing_algorithm "premium coffee" "competitive market" "increase market share"
python3 test_langgraph_tools.py --tool select_pricing_algorithm "pastries" "low competition" "maximize profit"
```

## 🗄️ Database Tools (Require --user-id)

### Basic Data Tools

#### 1. User Menu Items
```bash
python3 test_langgraph_tools.py --tool get_user_items_data --user-id 2
```

#### 2. Sales Data
```bash
python3 test_langgraph_tools.py --tool get_user_sales_data --user-id 2
python3 test_langgraph_tools.py --tool get_user_sales_data 10 --user-id 2  # limit to 10 orders
```

#### 3. Business Profile
```bash
python3 test_langgraph_tools.py --tool get_business_profile_data --user-id 2
```

#### 4. Competitor Data
```bash
python3 test_langgraph_tools.py --tool get_competitor_data --user-id 2
```

#### 5. Price History
```bash
python3 test_langgraph_tools.py --tool get_price_history_data --user-id 2
python3 test_langgraph_tools.py --tool get_price_history_data "coffee" --user-id 2  # filter by item name
```

### Analytics Tools

#### 6. Sales Analytics
```bash
python3 test_langgraph_tools.py --tool get_sales_analytics_structured --user-id 2
python3 test_langgraph_tools.py --tool get_sales_analytics_structured "weekly" true --user-id 2
```

#### 7. Item Performance Metrics
```bash
python3 test_langgraph_tools.py --tool get_item_performance_metrics --user-id 2
```

#### 8. Cost Analysis
```bash
python3 test_langgraph_tools.py --tool get_cost_analysis_structured --user-id 2
```

#### 9. Price Elasticity
```bash
python3 test_langgraph_tools.py --tool calculate_price_elasticity --user-id 2
```

#### 10. Sales by Time Period
```bash
python3 test_langgraph_tools.py --tool get_sales_by_time_period --user-id 2
python3 test_langgraph_tools.py --tool get_sales_by_time_period "weekly" --user-id 2
python3 test_langgraph_tools.py --tool get_sales_by_time_period "daily" --user-id 2
```

#### 11. Seasonal Trends
```bash
python3 test_langgraph_tools.py --tool get_seasonal_trends --user-id 2
```

#### 12. Recent Performance Changes
```bash
python3 test_langgraph_tools.py --tool get_recent_performance_changes --user-id 2
```

### Comparison & Competitive Tools

#### 13. Compare Item Performance
```bash
python3 test_langgraph_tools.py --tool compare_item_performance --user-id 2
```

#### 14. Competitor Price Gaps
```bash
python3 test_langgraph_tools.py --tool get_competitor_price_gaps --user-id 2
```

#### 15. Industry Benchmarking
```bash
python3 test_langgraph_tools.py --tool benchmark_against_industry --user-id 2
```

### Business Intelligence Tools

#### 16. Inventory Insights
```bash
python3 test_langgraph_tools.py --tool get_inventory_insights --user-id 2
```

#### 17. Customer Behavior Patterns
```bash
python3 test_langgraph_tools.py --tool get_customer_behavior_patterns --user-id 2
```

#### 18. Profitability Breakdown
```bash
python3 test_langgraph_tools.py --tool get_profitability_breakdown --user-id 2
```

## 🚀 Batch Testing Commands

### Test All Pricing Tools
```bash
python3 test_langgraph_tools.py --test-pricing
```

### Test All Database Tools
```bash
python3 test_langgraph_tools.py --test-database --user-id 2
```

### Test Everything
```bash
python3 test_langgraph_tools.py --test-all --user-id 2
```

### Interactive Mode
```bash
python3 test_langgraph_tools.py --interactive --user-id 2
```

### List All Available Tools
```bash
python3 test_langgraph_tools.py --list-tools
```

### Test Database Connectivity
```bash
python3 test_langgraph_tools.py --test-connectivity --user-id 2
```

## 💡 Interactive Mode Commands

When in interactive mode (`--interactive --user-id 2`), you can use these commands:

- `help` - Show available commands
- `list` - List all tools
- `pricing` - Test all pricing tools
- `database` - Test all database tools
- `connectivity` - Test database connectivity
- `tool <name> [args]` - Test specific tool
- `exit` or `quit` - Exit interactive mode

### Interactive Examples:
```
> tool get_user_items_data
> tool get_user_sales_data 5
> tool search_web_for_pricing "coffee beans"
> tool search_competitor_analysis "Latte" "beverage"
```

## 📊 Expected Output Types

- **Pricing Tools**: Simulated market data, competitor analysis, trends, algorithm recommendations
- **Database Tools**: Real data from your database including menu items, sales, orders, business profile
- **Analytics Tools**: Calculated metrics, performance indicators, growth rates, comparisons
- **Intelligence Tools**: Insights on inventory, customer behavior, profitability breakdowns

## 🔍 Troubleshooting

1. **"Tool not found"**: Check tool name spelling and available tools with `--list-tools`
2. **"No user ID"**: Database tools require `--user-id` parameter
3. **"Database connection failed"**: Check database is running and accessible
4. **"No data found"**: Verify user ID exists and has data in the database

## 🎯 Use Cases

- **Development**: Test individual tools during development
- **Debugging**: Isolate and debug specific tool issues
- **Data Validation**: Verify tools return expected data formats
- **Integration Testing**: Test tools before adding to multi-agent workflows
- **Performance Testing**: Check tool response times and data quality
