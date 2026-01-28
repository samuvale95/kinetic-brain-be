from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base

class MemoryCategory(str, enum.Enum):
    PHYSIOLOGICAL = "physiological"
    PSYCHOLOGICAL = "psychological"
    PREFERENCE = "preference"
    INJURY = "injury"

class CoachMemory(Base):
    """
    Persistent memory for the Agentic Coach.
    Stores facts/feedback about the athlete that shouldn't be lost.
    """
    __tablename__ = "coach_memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    key = Column(String(100), nullable=False, index=True) # e.g., 'knee_pain_left'
    value = Column(Text, nullable=False) # e.g., 'Pain flares up after 10km run'
    category = Column(Enum(MemoryCategory), nullable=False)
    confidence = Column(Float, default=1.0) # 0.0 to 1.0
    
    source_event_id = Column(String(100), nullable=True) # e.g., 'workout_123'
    
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="coach_memories")
