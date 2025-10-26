from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.utils.security import verify_token
from app.database import get_db
from app.services.auth_service import AuthService
from sqlalchemy.orm import Session


class AuthMiddleware:
    """Middleware to protect API endpoints"""
    
    # List of public endpoints that don't require authentication
    PUBLIC_ENDPOINTS = {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/auth/register",
        "/auth/login",
        "/auth/google/url",
        "/auth/google/callback",
        "/auth/google/login",
        "/profile/calculate-zones",  # Public endpoint for zone calculations
        "/strava/webhook",  # Strava webhook endpoint
        "/strava/auth/callback"  # Strava OAuth callback
    }
    
    @staticmethod
    def is_public_endpoint(path: str) -> bool:
        """Check if endpoint is public"""
        # Remove query parameters
        clean_path = path.split('?')[0]
        
        # Check exact match
        if clean_path in AuthMiddleware.PUBLIC_ENDPOINTS:
            return True
        
        # Check if it's a public auth endpoint
        if clean_path.startswith("/auth/") and any(
            clean_path.startswith(public) for public in AuthMiddleware.PUBLIC_ENDPOINTS
        ):
            return True
        
        return False
    
    @staticmethod
    async def authenticate_request(request: Request, call_next):
        """Authenticate the request"""
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Skip authentication for public endpoints
        if AuthMiddleware.is_public_endpoint(request.url.path):
            return await call_next(request)
        
        # Get authorization header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid authorization header"}
            )
        
        # Extract token
        token = authorization.split(" ")[1]
        
        # Verify token
        payload = verify_token(token, "access")
        if not payload:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"}
            )
        
        # Get user from database
        db = next(get_db())
        try:
            auth_service = AuthService(db)
            user = auth_service.get_user_by_id(int(payload["sub"]))
            
            if not user or not user.is_active:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "User not found or inactive"}
                )
            
            # Add user info to request state
            request.state.user_id = user.id
            request.state.user_email = user.email
            request.state.user = user
            
            return await call_next(request)
        finally:
            # Ensure database session is closed
            db.close()
