from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class NotificationPreferences(Base):
    __tablename__ = "notification_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Email preferences
    email_enabled = Column(Boolean, default=True, nullable=False)
    email_workout_reminders = Column(Boolean, default=True, nullable=False)
    email_new_workout = Column(Boolean, default=True, nullable=False)
    email_workout_completed = Column(Boolean, default=True, nullable=False)
    email_plan_updates = Column(Boolean, default=True, nullable=False)
    email_weekly_generation = Column(Boolean, default=True, nullable=False)
    
    # Push preferences
    push_enabled = Column(Boolean, default=True, nullable=False)
    push_workout_reminders = Column(Boolean, default=True, nullable=False)
    push_new_workout = Column(Boolean, default=True, nullable=False)
    push_workout_completed = Column(Boolean, default=True, nullable=False)
    push_plan_updates = Column(Boolean, default=True, nullable=False)
    push_weekly_generation = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="notification_preferences")


class DeviceToken(Base):
    __tablename__ = "device_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_token = Column(Text, nullable=False)
    platform = Column(String(20), nullable=False)  # ios, android, web
    device_id = Column(String(255), nullable=True)
    app_version = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="device_tokens")
    
    # Unique constraint on user_id + device_token + platform
    __table_args__ = (
        {"extend_existing": True}
    )


class NotificationLog(Base):
    """Log table for tracking all sent notifications"""
    __tablename__ = "notification_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Notification details
    notification_type = Column(String(50), nullable=False)  # workout_reminder, new_workout, etc.
    channel = Column(String(20), nullable=False)  # email, push
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)  # Additional data payload
    
    # Status
    status = Column(String(20), nullable=False)  # sent, failed, skipped
    error_message = Column(Text, nullable=True)  # Error details if failed
    
    # Timestamps
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="notification_logs")
    
    __table_args__ = (
        {"extend_existing": True}
    )

