from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text, Float, Table, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

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
