from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
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

