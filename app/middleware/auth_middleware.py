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
        "/auth/google/verify-id-token",  # iOS/React Native ID token verification
        "/auth/apple/url",
        "/auth/apple/callback",
        "/auth/apple/login",
        "/auth/apple/verify-identity-token",  # iOS/React Native Identity token verification
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
        import json
        import os
        log_path = "/Volumes/ExtremeSSD/repositories/kinetic-brain-be/.cursor/debug.log"
        
        # #region agent log
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A",
                    "location": "auth_middleware.py:53",
                    "message": "Middleware entry",
                    "data": {
                        "path": request.url.path,
                        "method": request.method,
                        "has_auth_header": "Authorization" in request.headers
                    },
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
        except Exception:
            pass
        # #endregion
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Skip authentication for public endpoints
        if AuthMiddleware.is_public_endpoint(request.url.path):
            # #region agent log
            try:
                with open(log_path, "a") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "B",
                        "location": "auth_middleware.py:61",
                        "message": "Public endpoint - skipping auth",
                        "data": {"path": request.url.path},
                        "timestamp": int(__import__("time").time() * 1000)
                    }) + "\n")
            except Exception:
                pass
            # #endregion
            return await call_next(request)
        
        # Get authorization header
        authorization = request.headers.get("Authorization")
        
        # #region agent log
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "C",
                    "location": "auth_middleware.py:64",
                    "message": "Authorization header check",
                    "data": {
                        "has_header": authorization is not None,
                        "header_preview": authorization[:50] + "..." if authorization and len(authorization) > 50 else authorization,
                        "starts_with_bearer": authorization.startswith("Bearer ") if authorization else False
                    },
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
        except Exception:
            pass
        # #endregion
        
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid authorization header"}
            )
        
        # Extract token
        token = authorization.split(" ")[1]
        
        # #region agent log
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "D",
                    "location": "auth_middleware.py:72",
                    "message": "Token extracted",
                    "data": {
                        "token_length": len(token),
                        "token_preview": token[:30] + "..." if len(token) > 30 else token
                    },
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
        except Exception:
            pass
        # #endregion
        
        # Verify token
        payload = verify_token(token, "access")
        
        # #region agent log
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "E",
                    "location": "auth_middleware.py:75",
                    "message": "Token verification result",
                    "data": {
                        "payload_valid": payload is not None,
                        "user_id": payload.get("sub") if payload else None
                    },
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
        except Exception:
            pass
        # #endregion
        
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
            
            # #region agent log
            try:
                with open(log_path, "a") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "F",
                        "location": "auth_middleware.py:86",
                        "message": "User lookup result",
                        "data": {
                            "user_found": user is not None,
                            "user_id": user.id if user else None,
                            "user_active": user.is_active if user else None
                        },
                        "timestamp": int(__import__("time").time() * 1000)
                    }) + "\n")
            except Exception:
                pass
            # #endregion
            
            if not user or not user.is_active:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "User not found or inactive"}
                )
            
            # Add user info to request state
            request.state.user_id = user.id
            request.state.user_email = user.email
            request.state.user = user
            
            # #region agent log
            try:
                with open(log_path, "a") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "G",
                        "location": "auth_middleware.py:97",
                        "message": "Middleware auth success - passing to next",
                        "data": {
                            "user_id": user.id,
                            "user_email": user.email
                        },
                        "timestamp": int(__import__("time").time() * 1000)
                    }) + "\n")
            except Exception:
                pass
            # #endregion
            
            return await call_next(request)
        finally:
            # Ensure database session is closed
            db.close()
