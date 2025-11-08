from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.sql import func

from app.database import Base


class AIResponseLog(Base):
    __tablename__ = "ai_response_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    request_type = Column(String(100), nullable=False)
    model = Column(String(100), nullable=True)
    prompt = Column(Text, nullable=True)
    request_payload = Column(JSON, nullable=True)
    response = Column(Text, nullable=True)
    parse_success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())



