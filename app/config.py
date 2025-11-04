from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
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
    
    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    frontend_callback_uri: str = "http://localhost:8080/auth/callback"
    
    # CORS
    cors_origins: List[str] = ["http://localhost:8080", "http://127.0.0.1:8080"]
    
    # Redis (optional)
    redis_url: str = "redis://localhost:6379"
    
    # App
    app_name: str = "Kinetic Brain API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # File uploads
    max_file_size: int = 5 * 1024 * 1024  # 5MB
    upload_folder: str = "uploads"
    
    # Mock LLM for testing
    mock_llm: bool = False
    
    # Mock progressive plan - always allow next week generation (for testing)
    mock_progressive_always_allow_generation: bool = False
    
    # Strava OAuth
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_redirect_uri: str = "http://localhost:8000/auth/strava/callback"
    strava_webhook_verify_token: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
