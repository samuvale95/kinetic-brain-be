from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class EmailConfig(Base):
    __tablename__ = "email_config"

    id = Column(Integer, primary_key=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # SMTP Configuration
    mail_username = Column(String(255), nullable=False)
    mail_password = Column(String(255), nullable=False)
    mail_from = Column(String(255), nullable=False)
    mail_from_name = Column(String(255), nullable=False)
    mail_port = Column(Integer, nullable=False)
    mail_server = Column(String(255), nullable=False)
    mail_starttls = Column(Boolean, default=True, nullable=False)
    mail_ssl_tls = Column(Boolean, default=False, nullable=False)
    
    # Application URLs
    frontend_url = Column(String(500), nullable=True)
    admin_email = Column(String(255), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
