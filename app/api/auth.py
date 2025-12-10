from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.schemas.auth import Token, RefreshTokenRequest
from app.schemas.user import UserCreate, UserLogin, UserResponse, GoogleAuthRequest, GoogleIdTokenRequest, AppleAuthRequest, AppleIdTokenRequest
from app.services.auth_service import AuthService
from app.services.google_auth_service import GoogleAuthService
from app.services.apple_auth_service import AppleAuthService
from app.utils.security import verify_token
from app.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), 
                    db: Session = Depends(get_db)) -> dict:
    """Get current user from JWT token"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        token = credentials.credentials
        logger.debug(f"[AUTH] Validating token (length: {len(token) if token else 0})")
        
        payload = verify_token(token, "access")
        
        if payload is None:
            logger.warning(f"[AUTH] Token validation failed - invalid or expired token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials. Token may be invalid, expired, or missing.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = int(payload["sub"])
        logger.debug(f"[AUTH] Token validated, user_id: {user_id}")
        
        auth_service = AuthService(db)
        user = auth_service.get_user_by_id(user_id)
        
        if user is None:
            logger.warning(f"[AUTH] User not found for user_id: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            logger.warning(f"[AUTH] User {user_id} is inactive")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.debug(f"[AUTH] User authenticated: {user.email} (id: {user.id})")
        return {"user_id": user.id, "email": user.email}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] Unexpected error in get_current_user: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication error",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    auth_service = AuthService(db)
    
    try:
        user = auth_service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user and return tokens"""
    auth_service = AuthService(db)
    
    user = auth_service.authenticate_user(
        user_credentials.email, 
        user_credentials.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Update last login
    auth_service.update_last_login(user)
    
    # Create tokens
    tokens = auth_service.create_tokens(user)
    return tokens


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    payload = verify_token(request.refresh_token, "refresh")
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    auth_service = AuthService(db)
    user = auth_service.get_user_by_id(int(payload["sub"]))
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    tokens = auth_service.create_tokens(user)
    return tokens


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user), 
                               db: Session = Depends(get_db)):
    """Get current user information"""
    auth_service = AuthService(db)
    user = auth_service.get_user_by_id(current_user["user_id"])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.post("/logout")
async def logout():
    """Logout user (client should discard tokens)"""
    return {"message": "Successfully logged out"}


@router.get("/google/url")
async def get_google_auth_url(
    mobile_redirect_uri: Optional[str] = Query(None, description="Mobile app deep link (e.g., kineticbrain://oauth/callback). If provided, uses web callback endpoint that redirects to this.")
):
    """Get Google OAuth authorization URL
    
    For web frontend: call without mobile_redirect_uri (uses default web callback)
    For React Native: call with mobile_redirect_uri=kineticbrain://oauth/callback
      - This uses a web endpoint as intermediate redirect (registered in Google Console)
      - The web endpoint then redirects to your mobile deep link with tokens
    """
    import logging
    import base64
    import json
    from urllib.parse import urlencode
    logger = logging.getLogger(__name__)
    
    google_service = GoogleAuthService(next(get_db()))
    
    if mobile_redirect_uri:
        # For mobile: use web callback endpoint, encode mobile_redirect_uri in state
        # The web callback will redirect to mobile_redirect_uri after authentication
        web_callback_uri = f"{settings.google_redirect_uri.rstrip('/callback')}/mobile-callback"
        
        # Encode mobile_redirect_uri in state parameter for later use
        state_data = {"mobile_redirect_uri": mobile_redirect_uri}
        state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode().rstrip('=')
        
        logger.info(f"[Google OAuth URL] Mobile request received")
        logger.info(f"[Google OAuth URL]   - mobile_redirect_uri: {mobile_redirect_uri}")
        logger.info(f"[Google OAuth URL]   - web_callback_uri: {web_callback_uri}")
        logger.info(f"[Google OAuth URL]   - state (encoded): {state[:50]}...")
        
        auth_url = google_service.get_google_auth_url(redirect_uri=web_callback_uri, state=state)
    else:
        # For web: use default redirect URI
        logger.info(f"[Google OAuth URL] Web request received")
        logger.info(f"[Google OAuth URL]   - Using default redirect_uri: {settings.google_redirect_uri}")
        
        auth_url = google_service.get_google_auth_url(redirect_uri=settings.google_redirect_uri)
    
    return {"auth_url": auth_url}


@router.get("/google/callback")
async def google_auth_callback_get(code: str, db: Session = Depends(get_db)):
    """Handle Google OAuth callback from browser redirect (GET) - Web frontend"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[Google OAuth] Web callback received with code (length: {len(code) if code else 0})")
    logger.info(f"[Google OAuth] Using redirect_uri: {settings.google_redirect_uri}")
    logger.info(f"[Google OAuth] Using client_id: {settings.google_client_id[:20]}...")
    
    google_service = GoogleAuthService(db)
    
    # Use configured redirect URI (env-configurable) instead of hardcoded localhost
    result = await google_service.authenticate_google_user(
        code=code,
        redirect_uri=settings.google_redirect_uri
    )
    
    if not result:
        logger.error(f"[Google OAuth] Authentication failed - redirecting to frontend with error")
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"{settings.frontend_callback_uri}?error=authentication_failed",
            status_code=302
        )
    
    # Get tokens and user info
    tokens = result["tokens"]
    user = result["user"]
    
    # Redirect to frontend with tokens as URL parameters
    from urllib.parse import urlencode
    
    # Encode tokens for URL
    params = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": tokens["token_type"],
        "user_id": str(user.id),
        "user_email": user.email,
        "user_name": user.name
    }
    
    # Redirect to frontend callback page using config
    frontend_callback_url = f"{settings.frontend_callback_uri}?{urlencode(params)}"
    return RedirectResponse(url=frontend_callback_url, status_code=302)


@router.get("/google/mobile-callback")
async def google_auth_mobile_callback_get(
    code: str,
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback for mobile apps (GET)
    
    This endpoint:
    1. Receives callback from Google (web URL registered in Google Console)
    2. Authenticates the user
    3. Redirects to mobile deep link (from state parameter) with tokens
    """
    import logging
    import base64
    import json
    from urllib.parse import urlencode
    logger = logging.getLogger(__name__)
    
    logger.info(f"[Google OAuth Mobile] Callback received with code (length: {len(code) if code else 0})")
    logger.info(f"[Google OAuth Mobile] State: {state[:50] if state else 'None'}...")
    
    # Decode mobile_redirect_uri from state
    mobile_redirect_uri = None
    if state:
        try:
            # Add padding if needed
            state_padded = state + '=' * (4 - len(state) % 4)
            state_data = json.loads(base64.urlsafe_b64decode(state_padded).decode())
            mobile_redirect_uri = state_data.get("mobile_redirect_uri")
            logger.info(f"[Google OAuth Mobile] Decoded mobile_redirect_uri: {mobile_redirect_uri}")
        except Exception as e:
            logger.error(f"[Google OAuth Mobile] Failed to decode state: {e}")
    
    if not mobile_redirect_uri:
        logger.error(f"[Google OAuth Mobile] No mobile_redirect_uri in state - redirecting to web callback")
        # Fallback to web callback
        return RedirectResponse(
            url=f"{settings.frontend_callback_uri}?error=invalid_state",
            status_code=302
        )
    
    # Use the web callback URI (this is what Google redirected to)
    web_callback_uri = f"{settings.google_redirect_uri.rstrip('/callback')}/mobile-callback"
    
    google_service = GoogleAuthService(db)
    
    result = await google_service.authenticate_google_user(
        code=code,
        redirect_uri=web_callback_uri
    )
    
    if not result:
        logger.error(f"[Google OAuth Mobile] Authentication failed")
        # Redirect to mobile app with error
        error_params = {
            "error": "authentication_failed"
        }
        redirect_url = f"{mobile_redirect_uri}?{urlencode(error_params)}"
        return RedirectResponse(url=redirect_url, status_code=302)
    
    # Get tokens and user info
    tokens = result["tokens"]
    user = result["user"]
    
    # Redirect to mobile app with tokens as URL parameters
    params = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": tokens["token_type"],
        "user_id": str(user.id),
        "user_email": user.email,
        "user_name": user.name or "",
        "success": "true"
    }
    
    redirect_url = f"{mobile_redirect_uri}?{urlencode(params)}"
    logger.info(f"[Google OAuth Mobile] Redirecting to mobile app: {mobile_redirect_uri}")
    
    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/google/callback", response_model=Token)
async def google_auth_callback_post(request: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Handle Google OAuth callback from API calls (POST)"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[Google OAuth POST] Callback received with code (length: {len(request.code) if request.code else 0})")
    logger.info(f"[Google OAuth POST] Request redirect_uri: {request.redirect_uri}")
    logger.info(f"[Google OAuth POST] Settings redirect_uri: {settings.google_redirect_uri}")
    
    # Warn if redirect_uri doesn't match settings (common cause of 401 errors)
    if request.redirect_uri and request.redirect_uri != settings.google_redirect_uri:
        logger.warning(f"[Google OAuth POST] WARNING: redirect_uri mismatch!")
        logger.warning(f"[Google OAuth POST]   Request: {request.redirect_uri}")
        logger.warning(f"[Google OAuth POST]   Settings: {settings.google_redirect_uri}")
        logger.warning(f"[Google OAuth POST]   This will likely cause authentication to fail!")
        
        # Check if it's a custom URL scheme (React Native)
        if request.redirect_uri.startswith(("kineticbrain://", "com.", "io.")):
            logger.warning(f"[Google OAuth POST]   Detected custom URL scheme - this requires:")
            logger.warning(f"[Google OAuth POST]   1. Register '{request.redirect_uri}' in Google Cloud Console")
            logger.warning(f"[Google OAuth POST]   2. OR use /auth/google/verify-id-token endpoint (recommended for React Native)")
    
    google_service = GoogleAuthService(db)
    
    try:
        result = await google_service.authenticate_google_user(
            code=request.code,
            redirect_uri=request.redirect_uri
        )
        
        if not result:
            logger.error(f"[Google OAuth POST] Authentication failed - result is None")
            logger.error(f"[Google OAuth POST] Check server logs for detailed error information")
            logger.error(f"[Google OAuth POST] Common issues:")
            logger.error(f"[Google OAuth POST]   - redirect_uri mismatch (must match exactly)")
            logger.error(f"[Google OAuth POST]   - Code already used or expired")
            logger.error(f"[Google OAuth POST]   - Invalid client_id or client_secret")
            logger.error(f"[Google OAuth POST]   - User email not verified")
            logger.error(f"[Google OAuth POST]   - App doesn't comply with Google OAuth 2.0 policy")
            
            # Check if it's a custom URL scheme issue
            if request.redirect_uri and request.redirect_uri.startswith(("kineticbrain://", "com.", "io.")):
                error_detail = (
                    "Google authentication failed: Custom URL scheme detected. "
                    "For React Native apps, use /auth/google/verify-id-token endpoint instead "
                    "(uses Google Sign-In SDK, no redirect URI needed). "
                    "Alternatively, register the custom URL scheme in Google Cloud Console."
                )
            else:
                error_detail = (
                    "Google authentication failed: Unable to exchange code for token or retrieve user info. "
                    "Check server logs for details. Common causes: redirect_uri mismatch, "
                    "code already used/expired, invalid credentials, or unverified email."
                )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_detail
            )
        
        logger.info(f"[Google OAuth POST] Authentication successful for user: {result.get('user', {}).get('email', 'unknown')}")
        return result["tokens"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Google OAuth POST] Unexpected error: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error during Google authentication: {str(e)}"
        )


@router.post("/google/login", response_model=Token)
async def google_login(request: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Login with Google OAuth (same as callback but with different endpoint name)"""
    google_service = GoogleAuthService(db)
    
    result = await google_service.authenticate_google_user(
        code=request.code,
        redirect_uri=request.redirect_uri
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google authentication failed"
        )
    
    return result["tokens"]


@router.post("/google/verify-id-token", response_model=Token)
async def verify_google_id_token(request: GoogleIdTokenRequest, db: Session = Depends(get_db)):
    """Verify Google ID token from React Native and return JWT tokens
    
    This endpoint is RECOMMENDED for React Native apps using Google Sign-In SDK.
    It doesn't require redirect URIs and works with custom URL schemes.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[Google ID Token] Verification request received (token length: {len(request.id_token) if request.id_token else 0})")
    
    google_service = GoogleAuthService(db)
    
    try:
        result = await google_service.verify_google_id_token(request.id_token)
        
        if not result:
            logger.error(f"[Google ID Token] Verification failed - invalid or expired token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired Google ID token. Make sure you're using Google Sign-In SDK correctly."
            )
        
        user_email = result.get("user", {}).get("email", "unknown")
        logger.info(f"[Google ID Token] Verification successful for user: {user_email}")
        return result["tokens"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Google ID Token] Unexpected error: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error during Google ID token verification: {str(e)}"
        )


@router.get("/apple/url")
async def get_apple_auth_url():
    """Get Apple OAuth authorization URL"""
    apple_service = AppleAuthService(next(get_db()))
    auth_url = apple_service.get_apple_auth_url()
    return {"auth_url": auth_url}


@router.post("/apple/callback", response_model=Token)
async def apple_auth_callback_post(request: AppleAuthRequest, db: Session = Depends(get_db)):
    """Handle Apple OAuth callback from API calls (POST)"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[Apple OAuth] Callback received with code (length: {len(request.code) if request.code else 0})")
    logger.info(f"[Apple OAuth] Using redirect_uri: {request.redirect_uri or settings.apple_redirect_uri}")
    
    apple_service = AppleAuthService(db)
    
    result = await apple_service.authenticate_apple_user(
        code=request.code,
        redirect_uri=request.redirect_uri
    )
    
    if not result:
        logger.error(f"[Apple OAuth] Authentication failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Apple authentication failed"
        )
    
    return result["tokens"]


@router.post("/apple/login", response_model=Token)
async def apple_login(request: AppleAuthRequest, db: Session = Depends(get_db)):
    """Login with Apple OAuth (same as callback but with different endpoint name)"""
    apple_service = AppleAuthService(db)
    
    result = await apple_service.authenticate_apple_user(
        code=request.code,
        redirect_uri=request.redirect_uri
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Apple authentication failed"
        )
    
    return result["tokens"]


@router.post("/apple/verify-identity-token", response_model=Token)
async def verify_apple_identity_token(request: AppleIdTokenRequest, db: Session = Depends(get_db)):
    """Verify Apple Identity Token from React Native or web and return JWT tokens"""
    apple_service = AppleAuthService(db)
    
    result = await apple_service.verify_apple_identity_token(request.id_token)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Apple Identity Token"
        )
    
    return result["tokens"]


@router.get("/test")
async def test_auth():
    """Test endpoint to verify authentication is working"""
    return {"message": "Authentication test successful", "status": "ok"}
