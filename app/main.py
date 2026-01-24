from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
from loguru import logger
import sys
import os
import traceback


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Kinetic Brain API...")
    
    # Create database tables (disabled due to permission issues)
    # Base.metadata.create_all(bind=engine)
    # logger.info("Database tables created")
    
    # Initialize scheduled tasks (if using APScheduler)
    if not minimal_startup:
        try:
            from app.services.scheduler_service import SchedulerService
            SchedulerService.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize scheduler service: {e}")
            # Don't fail startup if scheduler fails - app can still work with Render Cron Jobs
    
    yield
    
    # Shutdown
    logger.info("Shutting down Kinetic Brain API...")
    
    # Shutdown scheduled tasks (if using APScheduler)
    if not minimal_startup:
        try:
            from app.services.scheduler_service import SchedulerService
            SchedulerService.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down scheduler service: {e}")


# Read minimal flags early from env to avoid importing pydantic Settings at startup if requested
minimal_startup = os.getenv("MINIMAL_STARTUP", "false").lower() == "true"
disable_openapi_env = os.getenv("DISABLE_OPENAPI", "false").lower() == "true"

# Configure logging
logger.remove()

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Get log level from env or settings (default to INFO)
if not minimal_startup:
    from app.config import settings
    log_level = settings.log_level.upper()
else:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Log format for console (with colors)
console_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

# Log format for file (without colors, more detailed)
file_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"

# Add console handler
logger.add(
    sys.stdout,
    format=console_format,
    level=log_level,
    colorize=True
)

# Add file handler for logs
logger.add(
    "logs/app.log",
    format=file_format,
    level=log_level,
    rotation="10 MB",      # Rotate when file reaches 10MB
    retention="30 days",   # Keep logs for 30 days
    compression="zip",     # Compress old log files
    encoding="utf-8"
)

# If not in minimal mode, load full settings
if not minimal_startup:
    from app.config import settings
    from app.database import engine, Base  # import DB only in non-minimal mode
    app_title = settings.app_name
    app_version = settings.app_version
    disable_openapi = settings.disable_openapi
else:
    app_title = "Kinetic Brain API"
    app_version = "1.0.0"
    disable_openapi = disable_openapi_env

# Create FastAPI app
app = FastAPI(
    title=app_title,
    version=app_version,
    description="Backend API for Kinetic Brain - Sports Training Management",
    lifespan=lifespan,
    openapi_url=None if disable_openapi else "/openapi.json",
    docs_url=None if disable_openapi else "/docs",
    redoc_url=None if disable_openapi else "/redoc",
)

if not minimal_startup:
    # Import middleware only when not in minimal mode
    from app.middleware.auth_middleware import AuthMiddleware
    from app.middleware.logging_middleware import RequestResponseLoggingMiddleware
    from app.middleware.rate_limit_middleware import setup_rate_limiting
    
    # Setup rate limiting (before other middleware)
    setup_rate_limiting(app)
    
    # Centralized request/response logging
    app.add_middleware(RequestResponseLoggingMiddleware)
    
    # Add authentication middleware (before CORS)
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        return await AuthMiddleware.authenticate_request(request, call_next)
    
    # Configure CORS (after auth middleware)
    from app.config import settings as _settings_for_cors
    
    # Validate CORS configuration for production
    if not _settings_for_cors.debug:
        # Production: validate CORS origins don't contain wildcard
        if "*" in _settings_for_cors.cors_origins:
            logger.error(
                "❌ SECURITY ERROR: CORS_ORIGINS contains '*' which is not allowed in production. "
                "Please specify explicit origins in your environment variables."
            )
            raise ValueError("CORS_ORIGINS cannot contain '*' in production")
    
    # Explicit allowed methods (more secure than "*")
    allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    
    # Explicit allowed headers (more secure than "*")
    allowed_headers = [
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Accept",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_settings_for_cors.cors_origins,
        allow_credentials=True,
        allow_methods=allowed_methods,
        allow_headers=allowed_headers,
    )


# Global exception handler
from app.exceptions import AppException
from app.config import settings
import traceback

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle custom application exceptions"""
    from uuid import uuid4
    
    # Generate request ID for tracking
    request_id = str(uuid4())
    
    # Log error with context
    logger.error(
        f"Application error [{request_id}]: {exc.error_code} - {exc.message}",
        extra={
            "request_id": request_id,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details
        }
    )
    
    # Build response
    response_data = {
        "error": {
            "message": exc.message,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "request_id": request_id
        }
    }
    
    # Add details if present
    if exc.details:
        response_data["error"]["details"] = exc.details
    
    # Include stack trace only in debug mode
    if settings.debug:
        response_data["error"]["traceback"] = traceback.format_exc()
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    from uuid import uuid4
    from fastapi import HTTPException
    from slowapi.errors import RateLimitExceeded
    
    # Handle FastAPI HTTPException
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.detail,
                    "error_code": "HTTP_EXCEPTION",
                    "status_code": exc.status_code
                }
            }
        )
    
    # Handle RateLimitExceeded
    if isinstance(exc, RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "message": "Rate limit exceeded",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "status_code": 429,
                    "detail": str(exc)
                }
            }
        )
    
    # Generate request ID for tracking
    request_id = str(uuid4())
    
    # Log full error with traceback
    logger.error(
        f"Unhandled exception [{request_id}]: {str(exc)}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__
        },
        exc_info=True
    )
    
    # Build response
    response_data = {
        "error": {
            "message": "Internal server error",
            "error_code": "INTERNAL_ERROR",
            "status_code": 500,
            "request_id": request_id
        }
    }
    
    # Include stack trace only in debug mode
    if settings.debug:
        response_data["error"]["traceback"] = traceback.format_exc()
        response_data["error"]["exception"] = str(exc)
    
    return JSONResponse(
        status_code=500,
        content=response_data
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint with service verification"""
    if minimal_startup:
        return {
            "status": "healthy",
            "app_name": app_title,
            "version": app_version
        }
    
    from app.config import settings
    from app.database import engine
    
    services_status = {}
    overall_status = "healthy"
    
    # Check database
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        services_status["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        services_status["database"] = "unhealthy"
        overall_status = "unhealthy"
    
    # Check Redis (if configured)
    if settings.redis_url and settings.redis_url != "redis://localhost:6379":
        try:
            import redis
            r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
            r.ping()
            services_status["redis"] = "healthy"
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            services_status["redis"] = "unhealthy"
            if overall_status == "healthy":
                overall_status = "degraded"
    else:
        services_status["redis"] = "not_configured"
    
    # Check OpenAI (if configured)
    if settings.openai_api_key:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"}
                )
                if response.status_code == 200:
                    services_status["openai"] = "healthy"
                else:
                    services_status["openai"] = "unhealthy"
                    if overall_status == "healthy":
                        overall_status = "degraded"
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            services_status["openai"] = "unhealthy"
            if overall_status == "healthy":
                overall_status = "degraded"
    else:
        services_status["openai"] = "not_configured"
    
    # Check Strava (if configured)
    if settings.strava_client_id and settings.strava_client_secret:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Simple check - just verify we can reach Strava API
                response = await client.get("https://www.strava.com/api/v3/", timeout=5.0)
                # Any response (even 401) means API is reachable
                services_status["strava"] = "healthy"
        except Exception as e:
            logger.warning(f"Strava health check failed: {e}")
            services_status["strava"] = "unhealthy"
            if overall_status == "healthy":
                overall_status = "degraded"
    else:
        services_status["strava"] = "not_configured"
    
    return {
        "status": overall_status,
        "app_name": settings.app_name,
        "version": settings.app_version,
        "services": services_status
    }


if not minimal_startup:
    # Setup Prometheus metrics
    from app.api.metrics import setup_metrics
    setup_metrics(app)
    
    # Include API routers
    from app.api import auth, profile, workouts, calendar, ai, dashboard, strava, weather, statistics, metrics, plan_versions, exercises, healthkit, feedback, notifications, sync, garmin
    app.include_router(auth.router)
    app.include_router(profile.router)
    app.include_router(workouts.router)
    app.include_router(calendar.router)
    app.include_router(ai.router)
    app.include_router(dashboard.router)
    app.include_router(strava.router)
    app.include_router(healthkit.router)
    app.include_router(weather.router)
    app.include_router(statistics.router)
    app.include_router(metrics.router)
    app.include_router(plan_versions.router)
    app.include_router(exercises.router)
    app.include_router(feedback.router)
    app.include_router(notifications.router)
    app.include_router(sync.router)
    app.include_router(garmin.router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Kinetic Brain API",
        "version": app_version,
        "docs": "/docs" if not disable_openapi else None,
        "health": "/health"
    }


if __name__ == "__main__":
    reload_mode = False
    if not minimal_startup:
        from app.config import settings
        reload_mode = settings.debug
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=reload_mode,
        log_level="info"
    )
