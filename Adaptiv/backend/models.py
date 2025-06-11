from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text, Float, Table, Enum, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    competitor_tracking_enabled = Column(Boolean, default=False)
    
    # Relationship to BusinessProfile
    business = relationship("BusinessProfile", back_populates="owner", uselist=False)

class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    business_name = Column(String, index=True)
    industry = Column(String)
    company_size = Column(String)
    founded_year = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    # Address fields
    street_address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    country = Column(String, nullable=True, default="USA")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to User
    owner = relationship("User", back_populates="business")
    
class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    category = Column(String, index=True)
    current_price = Column(Float)
    cost = Column(Float, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Add user_id for account-specific data
    pos_id = Column(String, nullable=True, index=True)  # Store external POS system ID (Square catalog ID)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Add relationship to User
    user = relationship("User", backref="items")
    
    # Relationships
    price_history = relationship("PriceHistory", back_populates="item")
    order_items = relationship("OrderItem", back_populates="item")

class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Add user_id for account-specific data
    previous_price = Column(Float)
    new_price = Column(Float)
    change_reason = Column(String, nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Add relationship to User
    user = relationship("User", backref="price_history")
    
    # Relationship to Item
    item = relationship("Item", back_populates="price_history")

class CompetitorItem(Base):
    __tablename__ = "competitor_items"
    
    id = Column(Integer, primary_key=True, index=True)
    competitor_name = Column(String, index=True)
    item_name = Column(String, index=True)
    description = Column(Text, nullable=True)
    category = Column(String, index=True)
    price = Column(Float)
    similarity_score = Column(Float, nullable=True)  # Similarity score to a comparable item
    url = Column(String, nullable=True)
    batch_id = Column(String, index=True)  # Unique identifier for a menu fetch batch
    sync_timestamp = Column(DateTime(timezone=True), index=True)  # When this batch was synced
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Index for efficient batch queries
    __table_args__ = (Index('idx_competitor_batch', 'competitor_name', 'batch_id'),)

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_date = Column(DateTime(timezone=True))
    total_amount = Column(Float)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Add user_id for account-specific data
    pos_id = Column(String, nullable=True, index=True)  # Store external POS system order ID (Square order ID)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Add relationship to User
    user = relationship("User", backref="orders")
    
    # Relationship to OrderItems
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    item_id = Column(Integer, ForeignKey("items.id"))
    quantity = Column(Integer)
    unit_price = Column(Float)
    
    # Relationships
    order = relationship("Order", back_populates="items")
    item = relationship("Item", back_populates="order_items")
    
    @property
    def subtotal(self):
        return self.quantity * self.unit_price

class COGS(Base):
    __tablename__ = "cogs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    week_start_date = Column(DateTime(timezone=True), index=True)
    week_end_date = Column(DateTime(timezone=True), index=True)
    amount = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to User
    user = relationship("User", backref="cogs_data")

class ActionItem(Base):
    __tablename__ = "action_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    priority = Column(Enum("low", "medium", "high", name="priority_enum"), default="medium")
    status = Column(Enum("pending", "in_progress", "completed", name="status_enum"), default="pending")
    action_type = Column(Enum("integration", "data_entry", "analysis", "configuration", "other", name="action_type_enum"), default="other")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship to User
    user = relationship("User", backref="action_items")

class POSIntegration(Base):
    __tablename__ = "pos_integrations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    provider = Column(String, index=True)  # e.g. "square", "clover", etc.
    access_token = Column(String)
    refresh_token = Column(String, nullable=True)
    merchant_id = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    token_type = Column(String, nullable=True)
    scope = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    pos_id = Column(String, nullable=True, index=True)  # Store external order IDs
    
    # Relationship to User
    user = relationship("User", backref="pos_integrations")
    

# Agent Models
class CompetitorReport(Base):
    __tablename__ = "competitor_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    summary = Column(Text, nullable=False)
    insights = Column(JSON, nullable=True)  # Store structured insights
    competitor_data = Column(JSON, nullable=True)  # Store structured competitor data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_selected = Column(Boolean, default=False)  # Flag to track if competitor is selected for tracking
    
    # Relationship to User
    user = relationship("User", backref="competitor_reports")

class CustomerReport(Base):
    __tablename__ = "customer_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    summary = Column(Text, nullable=False)
    demographics = Column(JSON, nullable=True)  # Store demographic data
    events = Column(JSON, nullable=True)  # Store upcoming events data
    trends = Column(JSON, nullable=True)  # Store customer trend data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to User
    user = relationship("User", backref="customer_reports")

class MarketReport(Base):
    __tablename__ = "market_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    summary = Column(Text, nullable=False)
    market_trends = Column(JSON, nullable=True)  # Store market trend data
    supply_chain = Column(JSON, nullable=True)  # Store supply chain data
    industry_insights = Column(JSON, nullable=True)  # Store industry insights
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to User
    user = relationship("User", backref="market_reports")

class PricingReport(Base):
    __tablename__ = "pricing_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    summary = Column(Text, nullable=False)
    recommended_changes = Column(JSON, nullable=True)  # Store recommended price changes
    rationale = Column(JSON, nullable=True)  # Store rationale for each recommendation
    competitor_report_id = Column(Integer, ForeignKey("competitor_reports.id"), nullable=True)
    customer_report_id = Column(Integer, ForeignKey("customer_reports.id"), nullable=True)
    market_report_id = Column(Integer, ForeignKey("market_reports.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to User
    user = relationship("User", backref="pricing_reports")
    competitor_report = relationship("CompetitorReport")
    customer_report = relationship("CustomerReport")
    market_report = relationship("MarketReport")

class ExperimentRecommendation(Base):
    __tablename__ = "experiment_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    pricing_report_id = Column(Integer, ForeignKey("pricing_reports.id"), nullable=True)
    summary = Column(Text, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    evaluation_date = Column(DateTime(timezone=True), nullable=False)
    recommendations = Column(JSON, nullable=False)  # Store product recommendations with prices
    status = Column(Enum("pending", "implemented", "evaluated", "cancelled", name="experiment_status_enum"), default="pending")
    evaluation_results = Column(JSON, nullable=True)  # Store results after evaluation
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to User
    user = relationship("User", backref="experiment_recommendations")
    pricing_report = relationship("PricingReport")
    
    # Relationship to actual price changes (if implemented)
    price_changes = relationship("ExperimentPriceChange", back_populates="experiment")

class ExperimentPriceChange(Base):
    __tablename__ = "experiment_price_changes"
    
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiment_recommendations.id"))
    item_id = Column(Integer, ForeignKey("items.id"))
    original_price = Column(Float, nullable=False)
    new_price = Column(Float, nullable=False)
    implemented = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    experiment = relationship("ExperimentRecommendation", back_populates="price_changes")
    item = relationship("Item")
    price_history_id = Column(Integer, ForeignKey("price_history.id"), nullable=True)
    price_history = relationship("PriceHistory")

class PriceRecommendationAction(Base):
    __tablename__ = "price_recommendation_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("pricing_reports.id"))
    product_id = Column(Integer, ForeignKey("items.id"))
    current_price = Column(Float, nullable=False)
    recommended_price = Column(Float, nullable=False)
    change_percentage = Column(Float, nullable=False)
    approved = Column(Boolean)
    action_taken_at = Column(String)
    implemented = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    report = relationship("PricingReport", backref="recommendation_actions")
    product = relationship("Item")


# =====================================================
# Dynamic Pricing Agent Memory Database Models
# =====================================================

# Base Agent Memory Model
class AgentMemory(Base):
    __tablename__ = 'agent_memories'
    
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(50), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    memory_type = Column(String(50), nullable=False)  # conversation, recommendation, insight, etc.
    content = Column(JSON, nullable=False)
    memory_metadata = Column(JSON)  # Renamed from 'metadata' as it's a reserved name
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to User
    user = relationship("User", backref="agent_memories")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_agent_user_type', 'agent_name', 'user_id', 'memory_type'),
        Index('idx_agent_user_created', 'agent_name', 'user_id', 'created_at'),
    )


# Data Collection Agent Memory
class DataCollectionSnapshot(Base):
    __tablename__ = 'data_collection_snapshots'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    snapshot_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Data quality metrics
    pos_data_completeness = Column(Float)
    price_history_coverage = Column(Float)
    competitor_data_freshness = Column(Float)
    overall_quality_score = Column(Float)
    
    # Summary statistics
    total_orders = Column(Integer)
    total_items = Column(Integer)
    total_competitors = Column(Integer)
    date_range_start = Column(DateTime)
    date_range_end = Column(DateTime)
    
    # Identified issues and recommendations
    data_issues = Column(JSON)  # List of identified issues
    recommendations = Column(JSON)  # List of recommendations
    
    # Full snapshot data (compressed)
    full_data = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to User
    user = relationship("User", backref="data_collection_snapshots")


# Market Analysis Agent Memory
class MarketAnalysisSnapshot(Base):
    __tablename__ = 'market_analysis_snapshots'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    analysis_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Competitive positioning
    market_position = Column(String(50))  # premium, competitive, discount, etc.
    avg_price_vs_market = Column(Float)  # Percentage difference from market average
    
    # Elasticity insights
    avg_elasticity = Column(Float)
    elastic_items_count = Column(Integer)
    inelastic_items_count = Column(Integer)
    
    # Market trends
    market_trends = Column(JSON)  # List of identified trends
    seasonal_patterns = Column(JSON)  # Identified seasonal patterns
    
    # Competitor analysis
    competitor_strategies = Column(JSON)  # Analysis of each competitor
    competitive_threats = Column(JSON)
    competitive_opportunities = Column(JSON)
    
    # LLM-generated insights
    key_insights = Column(JSON)
    strategic_recommendations = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to User
    user = relationship("User", backref="market_analysis_snapshots")


# Competitor Tracking (Historical)
class CompetitorPriceHistory(Base):
    __tablename__ = 'competitor_price_histories'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    competitor_name = Column(String(255), nullable=False, index=True)
    item_name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    category = Column(String(100))
    similarity_score = Column(Float)
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Track changes
    price_change_from_last = Column(Float)
    percent_change_from_last = Column(Float)
    
    # Relationship to User
    user = relationship("User", backref="competitor_price_histories")
    
    # Add an index for efficient querying of competitor items over time
    __table_args__ = (
        Index('idx_competitor_item_date', 'competitor_name', 'item_name', 'captured_at'),
    )


# Pricing Strategy Agent Memory
class PricingRecommendation(Base):
    __tablename__ = 'pricing_recommendations'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False, index=True)
    batch_id = Column(String(100), nullable=False, index=True)  # Unique identifier for a batch of recommendations
    recommendation_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Recommendation details
    current_price = Column(Float, nullable=False)
    recommended_price = Column(Float, nullable=False)
    price_change_amount = Column(Float, nullable=False)
    price_change_percent = Column(Float, nullable=False)
    
    # Strategy information
    strategy_type = Column(String(50))  # premium_pricing, penetration_pricing, etc.
    confidence_score = Column(Float)
    rationale = Column(Text)
    
    # Expected impact
    expected_revenue_change = Column(Float)
    expected_quantity_change = Column(Float)
    expected_margin_change = Column(Float)
    
    # Implementation
    implementation_status = Column(String(50), default='pending')  # pending, implemented, rejected, partial
    implemented_at = Column(DateTime)
    implemented_price = Column(Float)  # Actual price implemented (might differ from recommendation)
    reevaluation_date = Column(DateTime)  # Date when this price should be reevaluated
    
    # Outcomes (filled in later by performance monitor)
    actual_revenue_change = Column(Float)
    actual_quantity_change = Column(Float)
    actual_margin_change = Column(Float)
    outcome_measured_at = Column(DateTime)
    
    # User feedback
    user_action = Column(String(50))  # accepted, rejected, modified
    user_feedback = Column(Text)
    user_action_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="pricing_recommendations")
    item = relationship("Item", backref="pricing_recommendations")


# Bundle Recommendations
class BundleRecommendation(Base):
    __tablename__ = 'bundle_recommendations'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    batch_id = Column(String(100), nullable=False, index=True)  # Unique identifier for a batch of recommendations
    recommendation_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Bundle details
    bundle_items = Column(JSON)  # List of item IDs
    bundle_name = Column(String(255))
    individual_total = Column(Float)
    recommended_bundle_price = Column(Float)
    discount_percent = Column(Float)
    
    # Analysis
    frequency_together = Column(Integer)  # How often bought together
    expected_lift = Column(Float)
    confidence_score = Column(Float)
    
    # Implementation
    implementation_status = Column(String(50), default='pending')
    implemented_at = Column(DateTime)
    
    # Outcomes
    actual_adoption_rate = Column(Float)
    actual_revenue_impact = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to User
    user = relationship("User", backref="bundle_recommendations")


# Performance Monitor Agent Memory
class PerformanceBaseline(Base):
    __tablename__ = 'performance_baselines'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    baseline_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Baseline metrics
    avg_daily_revenue = Column(Float)
    avg_daily_orders = Column(Integer)
    avg_order_value = Column(Float)
    
    # Item-level baselines
    item_baselines = Column(JSON)  # Dict of item_id -> metrics
    
    # Time period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to User
    user = relationship("User", backref="performance_baselines")


class PerformanceAnomaly(Base):
    __tablename__ = 'performance_anomalies'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Anomaly details
    anomaly_type = Column(String(50))  # revenue_drop, order_spike, item_performance, etc.
    severity = Column(String(20))  # low, medium, high
    affected_items = Column(JSON)  # List of affected item IDs
    
    # Metrics
    metric_name = Column(String(50))
    expected_value = Column(Float)
    actual_value = Column(Float)
    deviation_percent = Column(Float)
    
    # Context
    description = Column(Text)
    potential_causes = Column(JSON)
    recommended_actions = Column(JSON)
    
    # Resolution
    resolution_status = Column(String(50), default='open')  # open, investigating, resolved
    resolution_notes = Column(Text)
    resolved_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to User
    user = relationship("User", backref="performance_anomalies")


# Experimentation Agent Memory
class PricingExperiment(Base):
    __tablename__ = 'pricing_experiments'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    experiment_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Experiment details
    name = Column(String(255), nullable=False)
    experiment_type = Column(String(50))  # a_b_test, multi_armed_bandit, factorial
    hypothesis = Column(Text)
    
    # Items and pricing
    item_ids = Column(JSON)  # List of item IDs
    control_prices = Column(JSON)  # Dict of item_id -> price
    treatment_prices = Column(JSON)  # Dict of item_id -> price variations
    
    # Design
    sample_size_required = Column(Integer)
    duration_days = Column(Integer)
    success_criteria = Column(JSON)
    
    # Status
    status = Column(String(50), default='planned')  # planned, active, completed, cancelled
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    
    # Results
    control_metrics = Column(JSON)  # Revenue, units sold, etc.
    treatment_metrics = Column(JSON)
    p_value = Column(Float)
    confidence_interval = Column(JSON)
    
    # Conclusions
    recommendation = Column(String(50))  # implement, reject, extend, modify
    key_learnings = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to User
    user = relationship("User", backref="pricing_experiments")


class ExperimentLearning(Base):
    __tablename__ = 'experiment_learnings'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    experiment_id = Column(String(100), ForeignKey('pricing_experiments.experiment_id'), nullable=False)
    
    # Learning details
    learning_type = Column(String(50))  # elasticity, segment_behavior, timing, etc.
    item_ids = Column(JSON)  # Affected items
    
    # Insights
    insight = Column(Text, nullable=False)
    confidence_level = Column(Float)
    
    # Application
    applicable_to_items = Column(JSON)  # Items this learning could apply to
    recommended_action = Column(Text)
    
    # Validation
    validated = Column(Boolean, default=False)
    validation_method = Column(String(100))
    validation_result = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="experiment_learnings")
    experiment = relationship("PricingExperiment", backref="learnings")


# Decision History (Cross-agent tracking)
class PricingDecision(Base):
    __tablename__ = 'pricing_decisions'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    decision_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Decision details
    decision_type = Column(String(50))  # price_change, bundle_creation, experiment_launch
    affected_items = Column(JSON)  # List of item IDs
    
    # Context at time of decision
    market_conditions = Column(JSON)
    performance_metrics = Column(JSON)
    competitive_landscape = Column(JSON)
    
    # Decision rationale
    primary_rationale = Column(Text)
    supporting_data = Column(JSON)
    confidence_score = Column(Float)
    
    # Implementation
    implementation_status = Column(String(50), default='pending')
    implemented_at = Column(DateTime)
    
    # Outcomes
    outcome_metrics = Column(JSON)
    success_rating = Column(Integer)  # 1-5 scale
    lessons_learned = Column(Text)
    
    # Links to other records
    recommendation_ids = Column(JSON)  # Related recommendation IDs
    experiment_ids = Column(JSON)  # Related experiment IDs
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to User
    user = relationship("User", backref="pricing_decisions")


# Add this to track overall strategy evolution
class StrategyEvolution(Base):
    __tablename__ = 'strategy_evolutions'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    evolution_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Strategy shift
    previous_strategy = Column(JSON)  # Overall approach
    new_strategy = Column(JSON)  # New approach
    
    # Drivers of change
    change_drivers = Column(JSON)  # What prompted the strategy shift
    market_changes = Column(JSON)
    performance_triggers = Column(JSON)
    
    # Expected impact
    expected_outcomes = Column(JSON)
    risk_assessment = Column(JSON)
    
    # Actual results (filled in later)
    actual_outcomes = Column(JSON)
    effectiveness_score = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to User
    user = relationship("User", backref="strategy_evolutions")
