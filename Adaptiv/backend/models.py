from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text, Float, Table, Enum
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
