from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import secrets
from app.database import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    user = relationship("User", back_populates="password_reset_tokens")

    @staticmethod
    def generate_token() -> str:
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def create_token(user_id: int, expiration_hours: int = 24) -> "PasswordResetToken":
        """Create a new password reset token"""
        token = PasswordResetToken.generate_token()
        expires_at = datetime.utcnow() + timedelta(hours=expiration_hours)
        
        return PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            used=False
        )

    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)"""
        return not self.used and datetime.utcnow() < self.expires_at

    def mark_as_used(self):
        """Mark token as used"""
        self.used = True
