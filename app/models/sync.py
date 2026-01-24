from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime, timezone


class SyncConflict(Base):
    """Model for tracking sync conflicts between web and mobile"""
    __tablename__ = "sync_conflicts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)  # "workout", "session", "plan"
    entity_id = Column(Integer, nullable=False)
    server_version = Column(String(255))  # Server timestamp
    client_version = Column(String(255))  # Client timestamp
    server_data = Column(JSON)  # Server version of the data
    client_data = Column(JSON)  # Client version of the data
    resolution = Column(String(50))  # "server", "client", "merge"
    resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sync_conflicts")


class SyncHistory(Base):
    """Model for tracking sync history"""
    __tablename__ = "sync_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    synced_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    changes_count = Column(Integer, default=0)
    conflicts_count = Column(Integer, default=0)
    client_timestamp = Column(DateTime(timezone=True))  # Client's timestamp when sync started
    sync_type = Column(String(50), default="full")  # "full", "incremental"
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="sync_history")
