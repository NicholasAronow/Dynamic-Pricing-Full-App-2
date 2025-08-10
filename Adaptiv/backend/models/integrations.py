from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base

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
    pos_id = Column(String, nullable=True, index=True)  # Store primary location ID
    location_ids = Column(String, nullable=True)  # Store all location IDs as JSON string
    
    # Persistent sync progress/state (JSON)
    # Use a non-reserved name (not "metadata") to avoid SQLAlchemy conflicts
    sync_metadata = Column(JSON, nullable=True)
    
    # Relationship to User
    user = relationship("User", backref="pos_integrations")
