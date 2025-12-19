from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.email_config import EmailConfig
from app.config import settings
from loguru import logger


class EmailConfigService:
    """
    Service to manage email configuration from database with fallback to environment variables.
    Allows runtime configuration changes without application restart.
    """
    
    _cache: Optional[Dict[str, Any]] = None
    _cache_timestamp: Optional[float] = None
    _cache_ttl: float = 300.0  # Cache for 5 minutes
    
    @classmethod
    def get_email_config(cls, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Get email configuration from database (if available) or fallback to settings.
        
        Args:
            db: Optional database session. If None, only uses settings.
            
        Returns:
            Dictionary with email configuration
        """
        import time
        
        # Check cache first
        if cls._cache is not None and cls._cache_timestamp is not None:
            if time.time() - cls._cache_timestamp < cls._cache_ttl:
                return cls._cache.copy()
        
        # Try to get from database
        if db is not None:
            try:
                email_config = db.query(EmailConfig).filter(
                    EmailConfig.is_active == True
                ).first()
                
                if email_config:
                    config = {
                        "mail_username": email_config.mail_username,
                        "mail_password": email_config.mail_password,
                        "mail_from": email_config.mail_from,
                        "mail_from_name": email_config.mail_from_name,
                        "mail_port": email_config.mail_port,
                        "mail_server": email_config.mail_server,
                        "mail_starttls": email_config.mail_starttls,
                        "mail_ssl_tls": email_config.mail_ssl_tls,
                        "frontend_url": email_config.frontend_url or settings.frontend_url,
                        "admin_email": email_config.admin_email or settings.admin_email,
                    }
                    # Update cache
                    cls._cache = config.copy()
                    cls._cache_timestamp = time.time()
                    logger.debug("Email configuration loaded from database")
                    return config
            except Exception as e:
                logger.warning(f"Failed to load email config from database: {e}. Using environment variables.")
        
        # Fallback to settings from environment variables
        config = {
            "mail_username": settings.mail_username,
            "mail_password": settings.mail_password,
            "mail_from": settings.mail_from,
            "mail_from_name": settings.mail_from_name,
            "mail_port": settings.mail_port,
            "mail_server": settings.mail_server,
            "mail_starttls": settings.mail_starttls,
            "mail_ssl_tls": settings.mail_ssl_tls,
            "frontend_url": settings.frontend_url,
            "admin_email": settings.admin_email,
        }
        
        # Update cache
        cls._cache = config.copy()
        cls._cache_timestamp = time.time()
        logger.debug("Email configuration loaded from environment variables")
        return config
    
    @classmethod
    def clear_cache(cls):
        """Clear the configuration cache to force reload on next request"""
        cls._cache = None
        cls._cache_timestamp = None
        logger.debug("Email configuration cache cleared")
