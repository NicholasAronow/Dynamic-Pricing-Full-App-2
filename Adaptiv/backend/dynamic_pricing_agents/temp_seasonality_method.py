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
        cal_month = row.date.month  # 1 = January, 12 = December
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
    seasonality_strength = "strong" if monthly_variation > 0.3 or quarterly_variation > 0.25 else \
                           "moderate" if monthly_variation > 0.2 or quarterly_variation > 0.15 else \
                           "weak"
                           
    # Calculate confidence based on data span
    first_date = min(row.date for row in daily_sales)
    last_date = max(row.date for row in daily_sales)
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
