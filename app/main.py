from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
from loguru import logger
import sys
import os


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
    
    # Centralized request/response logging
    app.add_middleware(RequestResponseLoggingMiddleware)
    
    # Add authentication middleware (before CORS)
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        return await AuthMiddleware.authenticate_request(request, call_next)
    
    # Configure CORS (after auth middleware)
    from app.config import settings as _settings_for_cors
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_settings_for_cors.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if minimal_startup:
        return {
            "status": "healthy",
            "app_name": app_title,
            "version": app_version
        }
    else:
        from app.config import settings
        return {
            "status": "healthy",
            "app_name": settings.app_name,
            "version": settings.app_version
        }


if not minimal_startup:
    # Include API routers
    from app.api import auth, profile, workouts, calendar, ai, dashboard, strava, weather, statistics, metrics, plan_versions, exercises, healthkit, feedback, notifications
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
