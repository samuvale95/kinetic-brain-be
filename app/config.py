from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # AWS Secrets Manager
    aws_secret_name: Optional[str] = None
    aws_region: str = "eu-north-1"
    # AWS Credentials (optional - can also use ~/.aws/credentials or IAM role)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    # Database connection details (optional - can be in secret or here)
    db_host: Optional[str] = None
    db_name: Optional[str] = None
    db_port: Optional[int] = None
    
    # Database
    database_url: str = "postgresql://user:password@localhost/kinetic_brain"
    database_url_async: str = "postgresql+asyncpg://user:password@localhost/kinetic_brain"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 2000
    openai_timeout_seconds: int = 120  # Timeout in seconds for OpenAI API calls
    
    # Anthropic/Claude
    enable_claude_review: bool = False
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5"
    claude_review_percentage: int = 20
    anthropic_timeout_seconds: int = 120  # Timeout in seconds for Anthropic API calls
    
    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    frontend_callback_uri: str = "http://localhost:8080/auth/callback"
    # Additional Google Client IDs (comma-separated) for React Native Android/iOS
    # These are used when verifying ID tokens from mobile apps
    google_additional_client_ids: str = ""
    
    # Apple OAuth
    apple_client_id: str = ""  # Service ID from Apple Developer
    apple_team_id: str = ""  # Team ID from Apple Developer
    apple_key_id: str = ""  # Key ID for JWT client secret
    apple_private_key: str = ""  # Private key for generating JWT client secret (PEM format)
    apple_redirect_uri: str = "http://localhost:8080/auth/apple/callback"
    
    # CORS
    cors_origins: List[str] = ["http://localhost:8080", "http://127.0.0.1:8080"]
    
    # Redis (optional)
    redis_url: str = "redis://localhost:6379"
    
    # App
    app_name: str = "Kinetic Brain API"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    disable_openapi: bool = False  # OpenAPI is enabled by default
    minimal_startup: bool = False
    
    # File uploads
    max_file_size: int = 5 * 1024 * 1024  # 5MB
    upload_folder: str = "uploads"
    
    # Mock LLM for testing
    mock_llm: bool = False
    
    # Mock progressive plan - always allow next week generation (for testing)
    mock_progressive_always_allow_generation: bool = False

    # Plan generation limits
    max_plan_duration_weeks: int = 24
    
    # Strava OAuth
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_redirect_uri: str = "http://localhost:8000/auth/strava/callback"
    strava_webhook_verify_token: str = ""
    
    # Email Configuration
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = "noreply@kineticbrain.com"
    mail_from_name: str = "Kinetic Brain"
    mail_port: int = 587
    mail_server: str = "smtp.gmail.com"
    mail_starttls: bool = True
    mail_ssl_tls: bool = False
    
    # Internal API Secret (for cron jobs and internal endpoints)
    internal_api_secret: str = ""
    
    # Scheduled Tasks Configuration
    # Options: "render_cron" (endpoint HTTP chiamato da Render Cron Jobs) or "apscheduler" (APScheduler nel processo)
    scheduled_tasks_provider: str = "render_cron"  # "render_cron" or "apscheduler"
    
    # APScheduler Configuration (only used if scheduled_tasks_provider == "apscheduler")
    # Workout reminder schedules (cron format: minute hour day month day_of_week)
    # Default: 8:00 AM and 6:00 PM UTC every day
    workout_reminder_morning_cron: str = "0 8 * * *"  # Every day at 8:00 AM UTC
    workout_reminder_evening_cron: str = "0 18 * * *"  # Every day at 6:00 PM UTC (optional, set to "" to disable)
    
    # Application URLs
    frontend_url: str = "http://localhost:8080"
    admin_email: str = "admin@kineticbrain.com"
    
    # Firebase Cloud Messaging (FCM) for push notifications (API V1)
    # FCM API V1 requires a service account JSON instead of Server Key
    fcm_project_id: str = ""  # FCM Project ID (required for V1 API)
    fcm_service_account_json: str = ""  # Service Account JSON as string (required for V1 API)
    # Legacy FCM Server Key (deprecated - kept for backward compatibility but not used)
    fcm_server_key: str = ""  # DEPRECATED: Use FCM_SERVICE_ACCOUNT_JSON instead
    
    # Development/Testing flags
    skip_secret_validation: bool = False  # Allow default SECRET_KEY in development (set to true in .env for local dev)
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Validate secret key - CRITICAL for production security
        self._validate_secret_key()
        
        # If AWS secret name is provided, use it to get database credentials
        # Import here to avoid circular import issues
        # Import directly from file to avoid loading utils/__init__.py which imports security
        if self.aws_secret_name:
            try:
                import importlib.util
                import sys
                # Get the path to aws_secrets.py
                current_dir = os.path.dirname(os.path.abspath(__file__))
                aws_secrets_path = os.path.join(current_dir, "utils", "aws_secrets.py")
                # Load the module directly without going through __init__.py
                spec = importlib.util.spec_from_file_location("aws_secrets", aws_secrets_path)
                aws_secrets_module = importlib.util.module_from_spec(spec)
                # Add to sys.modules with a unique name to avoid conflicts
                module_name = f"app_config_aws_secrets_{id(self)}"
                sys.modules[module_name] = aws_secrets_module
                spec.loader.exec_module(aws_secrets_module)
                self.database_url, self.database_url_async = aws_secrets_module.get_database_url_from_secret(
                    secret_name=self.aws_secret_name,
                    region_name=self.aws_region,
                    access_key_id=self.aws_access_key_id,
                    secret_access_key=self.aws_secret_access_key,
                    db_host=self.db_host,
                    db_name=self.db_name,
                    db_port=self.db_port
                )
            except Exception as e:
                # Log error but don't fail - allow fallback to env vars
                from loguru import logger
                from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
                
                # Check if it's an AWS authentication error (common in local development)
                error_msg = str(e)
                error_type = type(e).__name__
                
                # Check for various AWS credential errors
                is_no_credentials = (
                    isinstance(e, NoCredentialsError) or
                    isinstance(e, PartialCredentialsError) or
                    "NoCredentialsError" in error_msg or
                    "CredentialsError" in error_msg
                )
                
                is_invalid_credentials = (
                    "UnrecognizedClientException" in error_msg or
                    "InvalidClientTokenId" in error_msg or
                    "The security token included in the request is invalid" in error_msg
                )
                
                if is_no_credentials:
                    # Use INFO level when credentials are not configured (normal in local dev)
                    logger.info(
                        "AWS Secrets Manager not available (AWS credentials not configured). "
                        "Using database credentials from environment variables (DATABASE_URL)"
                    )
                elif is_invalid_credentials:
                    # Use WARNING when credentials are configured but invalid
                    logger.warning(
                        f"AWS Secrets Manager authentication failed (invalid credentials): {error_msg}. "
                        "Please check your AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY. "
                        "Falling back to environment variables (DATABASE_URL)"
                    )
                elif isinstance(e, ClientError):
                    # ClientError from boto3 - log the full error code
                    error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', 'Unknown')
                    logger.warning(
                        f"Failed to get database credentials from AWS Secrets Manager "
                        f"(Error: {error_code}): {error_msg}"
                    )
                    logger.warning("Falling back to environment variables or defaults")
                else:
                    # Use WARNING for other errors
                    logger.warning(f"Failed to get database credentials from AWS Secrets Manager: {e}")
                    logger.warning("Falling back to environment variables or defaults")
    
    def _validate_secret_key(self):
        """Validate that secret key is not using default value in production"""
        from loguru import logger
        
        default_secret_key = "your-secret-key-change-in-production"
        
        # Check if using default secret key
        if self.secret_key == default_secret_key:
            if self.skip_secret_validation:
                logger.warning(
                    "⚠️  SECURITY WARNING: Using default SECRET_KEY value. "
                    "This is INSECURE and should only be used in development. "
                    "Set SKIP_SECRET_VALIDATION=true only for local development."
                )
            else:
                error_msg = (
                    "❌ SECURITY ERROR: SECRET_KEY is using default value. "
                    "This is INSECURE and not allowed in production. "
                    "Please set a strong SECRET_KEY in your environment variables or .env file. "
                    "For local development only, you can set SKIP_SECRET_VALIDATION=true to bypass this check."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
        
        # Check if secret key is too short or weak
        if len(self.secret_key) < 32:
            logger.warning(
                f"⚠️  SECURITY WARNING: SECRET_KEY is too short ({len(self.secret_key)} characters). "
                "Recommendation: Use at least 32 characters for production."
            )
        
        # Check if secret key contains only common/default patterns
        weak_patterns = ["secret", "password", "key", "123", "default", "test", "demo"]
        secret_lower = self.secret_key.lower()
        if any(pattern in secret_lower for pattern in weak_patterns) and len(self.secret_key) < 40:
            logger.warning(
                "⚠️  SECURITY WARNING: SECRET_KEY appears to be weak (contains common words). "
                "Recommendation: Use a strong, randomly generated secret key."
            )


settings = Settings()
