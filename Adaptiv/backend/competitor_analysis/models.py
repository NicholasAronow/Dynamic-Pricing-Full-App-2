#!/usr/bin/env python3
"""
SQLAlchemy models for competitor analysis system
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """User model - placeholder for future user management"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CompetitorEntity(Base):
    __tablename__ = "competitor_entities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    address = Column(String, nullable=True)
    category = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    distance_km = Column(Float, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    menu_url = Column(String, nullable=True)
    score = Column(Float, nullable=True)  # Overall competitor similarity/relevance score
    is_selected = Column(Boolean, default=False)  # Flag to track if competitor is selected for tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to User
    user = relationship("User", backref="competitor_entities")
    
    # Relationship to CompetitorItems
    items = relationship(
            "CompetitorItem", 
            cascade="all, delete-orphan",
            lazy="select"  # This prevents automatic loading
        )    
    # Index for efficient user-specific queries
    __table_args__ = (Index('idx_user_competitor', 'user_id', 'name'),)


class CompetitorItem(Base):
    __tablename__ = "competitor_items"
    
    id = Column(Integer, primary_key=True, index=True)
    competitor_id = Column(Integer, ForeignKey("competitor_entities.id"), nullable=False, index=True)
    competitor_name = Column(String, index=True)  # Keep for backward compatibility during migration
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
    
    # Relationship to CompetitorEntity
    # Foreign key reference to competitor (no back_populates to avoid circular reference)
    # Use competitor_id to access the parent competitor    
    # Index for efficient batch queries
    __table_args__ = (
        Index('idx_competitor_batch', 'competitor_name', 'batch_id'),
        Index('idx_competitor_entity_batch', 'competitor_id', 'batch_id'),
    )
