from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Text, Index
from sqlalchemy.sql import func

from app.database import Base


class MetricsPendingJob(Base):
    __tablename__ = "metrics_pending_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(String(50), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    payload = Column(JSON)

    status = Column(String(20), nullable=False, default="pending")  # pending, processing, completed, failed
    priority = Column(Integer, default=0)
    attempts = Column(Integer, default=0)

    available_at = Column(DateTime(timezone=True), server_default=func.now())
    last_error = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


Index("ix_metrics_pending_jobs_status_priority", MetricsPendingJob.status, MetricsPendingJob.priority, MetricsPendingJob.available_at)

