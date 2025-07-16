from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_date = Column(DateTime(timezone=True))
    total_amount = Column(Float)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Add user_id for account-specific data
    pos_id = Column(String, nullable=True, index=True)  # Store external POS system order ID (Square order ID)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    total_cost = Column(Float, nullable=True)
    gross_margin = Column(Float, nullable=True)
    net_margin = Column(Float, nullable=True)
    
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
    unit_cost = Column(Float, nullable=True)
    subtotal_cost = Column(Float, nullable=True)
    
    # Relationships
    order = relationship("Order", back_populates="items")
    item = relationship("Item", back_populates="order_items")
    
    @property
    def subtotal(self):
        return self.quantity * self.unit_price
