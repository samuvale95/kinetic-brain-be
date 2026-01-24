from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.config import settings
from loguru import logger
import redis
from typing import Optional


# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url if settings.redis_url and settings.redis_url != "redis://localhost:6379" else None,
    default_limits=["1000/hour"]  # Default limit: 1000 requests per hour per IP
)


def get_user_id_for_rate_limit(request: Request) -> Optional[str]:
    """Get user ID from request state for per-user rate limiting"""
    if hasattr(request.state, "user_id"):
        return str(request.state.user_id)
    return None


# Rate limit configuration per endpoint
RATE_LIMITS = {
    # Authentication endpoints - strict limits to prevent brute force
    "/auth/login": "10/hour",
    "/auth/register": "5/hour",
    "/auth/forgot-password": "5/hour",
    "/auth/reset-password": "5/hour",
    
    # AI endpoints - expensive operations, limit per user
    "/workouts/plans/generate-ai": "100/hour",
    "/workouts/plans/generate-progressive": "50/hour",
    "/ai/generate": "100/hour",
    "/ai/generate-plan": "100/hour",
    "/ai/analyze-workout": "100/hour",
    
    # Strava sync - limit to prevent abuse
    "/strava/sync": "10/hour",
    "/strava/sync-all": "5/hour",
    
    # Profile updates - moderate limits
    "/profile/update": "60/hour",
    
    # Default limit for all other endpoints
    "default": "1000/hour"
}


def get_rate_limit_for_path(path: str) -> str:
    """Get rate limit string for a given path"""
    # Check exact match first
    if path in RATE_LIMITS:
        return RATE_LIMITS[path]
    
    # Check prefix matches for nested paths
    for endpoint, limit in RATE_LIMITS.items():
        if endpoint != "default" and path.startswith(endpoint):
            return limit
    
    # Return default limit
    return RATE_LIMITS["default"]


def setup_rate_limiting(app):
    """Setup rate limiting middleware and exception handler"""
    
    # Add rate limit exception handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Add SlowAPI middleware
    app.add_middleware(SlowAPIMiddleware)
    
    logger.info("Rate limiting middleware configured")
    
    # Test Redis connection if configured
    if settings.redis_url and settings.redis_url != "redis://localhost:6379":
        try:
            r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
            r.ping()
            logger.info(f"Rate limiting using Redis: {settings.redis_url}")
        except Exception as e:
            logger.warning(f"Redis not available for rate limiting, using in-memory storage: {e}")
    else:
        logger.info("Rate limiting using in-memory storage (Redis not configured)")


def create_rate_limit_decorator(limit: str):
    """Create a rate limit decorator for specific endpoints"""
    def rate_limit_decorator(func):
        # For per-user rate limiting on authenticated endpoints
        def get_key_func(request: Request):
            user_id = get_user_id_for_rate_limit(request)
            if user_id:
                return f"user:{user_id}"
            return get_remote_address(request)
        
        return limiter.limit(limit, key_func=get_key_func)(func)
    return rate_limit_decorator
