from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
from loguru import logger
import sys
import os

from app.config import settings
from app.database import engine, Base
from app.api import auth, profile, workouts, calendar, ai, dashboard, strava, weather, statistics
from app.middleware.auth_middleware import AuthMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Kinetic Brain API...")
    
    # Create database tables (disabled due to permission issues)
    # Base.metadata.create_all(bind=engine)
    # logger.info("Database tables created")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Kinetic Brain API...")


# Configure logging
logger.remove()

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Get log level from settings (default to INFO)
log_level = settings.log_level.upper()

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

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend API for Kinetic Brain - Sports Training Management",
    lifespan=lifespan
)

# Add authentication middleware (before CORS)
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    return await AuthMiddleware.authenticate_request(request, call_next)

# Configure CORS (after auth middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version
    }


# Include API routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(workouts.router)
app.include_router(calendar.router)
app.include_router(ai.router)
app.include_router(dashboard.router)
app.include_router(strava.router)
app.include_router(weather.router)
app.include_router(statistics.router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Kinetic Brain API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )
