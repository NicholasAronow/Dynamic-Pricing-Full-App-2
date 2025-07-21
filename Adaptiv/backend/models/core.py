from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text, Float, Enum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    name = Column(String, nullable=True)  # Added name field for Google auth users
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    competitor_tracking_enabled = Column(Boolean, default=False)
    pos_connected = Column(Boolean, default=False)
    stripe_customer_id = Column(String, nullable=True)  # For Stripe subscription integration
    subscription_tier = Column(String, nullable=True, default="free")  # free, basic, premium
    is_google_user = Column(Boolean, default=False)  # Flag to identify users who sign in with Google
    is_admin = Column(Boolean, default=False)  # Flag to identify admin users
    
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

class FixedCost(Base):
    __tablename__ = "fixed_costs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    cost_type = Column(String, index=True)  # e.g., "rent", "utilities", "insurance"
    amount = Column(Float)
    month = Column(Integer)  # 1-12
    year = Column(Integer)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to User
    user = relationship("User", backref="fixed_costs")

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    name = Column(String)
    pay_type = Column(String, index=True)  # "salary" or "hourly"
    salary = Column(Float, nullable=True)  # Annual salary if pay_type is "salary"
    hourly_rate = Column(Float, nullable=True)  # Hourly rate if pay_type is "hourly"
    weekly_hours = Column(Float, nullable=True)  # Expected weekly hours
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to User
    user = relationship("User", backref="employees")
