from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse, HTMLResponse
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
    import json
    import os
    log_path = "/Volumes/ExtremeSSD/repositories/kinetic-brain-be/.cursor/debug.log"
    logger = logging.getLogger(__name__)
    
    # #region agent log
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "H",
                "location": "auth.py:19",
                "message": "get_current_user entry",
                "data": {
                    "has_credentials": credentials is not None,
                    "has_credentials_attr": hasattr(credentials, "credentials") if credentials else False
                },
                "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
    except Exception:
        pass
    # #endregion
    
    try:
        token = credentials.credentials
        
        # #region agent log
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "I",
                    "location": "auth.py:26",
                    "message": "Token extracted from credentials",
                    "data": {
                        "token_length": len(token) if token else 0,
                        "token_preview": token[:30] + "..." if token and len(token) > 30 else token
                    },
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
        except Exception:
            pass
        # #endregion
        
        logger.debug(f"[AUTH] Validating token (length: {len(token) if token else 0})")
        
        payload = verify_token(token, "access")
        
        # #region agent log
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "J",
                    "location": "auth.py:29",
                    "message": "Token verification in get_current_user",
                    "data": {
                        "payload_valid": payload is not None,
                        "user_id": payload.get("sub") if payload else None
                    },
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
        except Exception:
            pass
        # #endregion
        
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
        
        # #region agent log
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "K",
                    "location": "auth.py:42",
                    "message": "User lookup in get_current_user",
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
        
        # #region agent log
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "L",
                    "location": "auth.py:58",
                    "message": "get_current_user success",
                    "data": {
                        "user_id": user.id,
                        "user_email": user.email
                    },
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
        except Exception:
            pass
        # #endregion
        
        return {"user_id": user.id, "email": user.email}
    except HTTPException:
        raise
    except Exception as e:
        # #region agent log
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "M",
                    "location": "auth.py:65",
                    "message": "get_current_user exception",
                    "data": {
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
        except Exception:
            pass
        # #endregion
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
    mobile: bool = Query(False, description="If True, indicates this is a mobile app request. The callback will redirect to kineticbrain://oauth"),
    mobile_redirect_uri: Optional[str] = Query(None, description="Mobile app deep link (e.g., kineticbrain://oauth/callback). If provided, uses web callback endpoint that redirects to this. Takes precedence over mobile parameter.")
):
    """Get Google OAuth authorization URL
    
    For web frontend: call without mobile or mobile_redirect_uri (uses default web callback)
    For React Native: 
      - Option 1: call with mobile=True (uses kineticbrain://oauth as deep link)
      - Option 2: call with mobile_redirect_uri=kineticbrain://oauth/callback (custom deep link)
      - Both use a web endpoint as intermediate redirect (registered in Google Console)
      - The web endpoint then redirects to your mobile deep link with tokens
    """
    import logging
    import base64
    import json
    import time
    import secrets
    from urllib.parse import urlencode
    from fastapi import Request
    logger = logging.getLogger(__name__)
    
    print(f"\n{'='*80}")
    print(f"[GOOGLE AUTH URL] ===== REQUEST RECEIVED =====")
    print(f"[GOOGLE AUTH URL] Endpoint: GET /auth/google/url")
    print(f"[GOOGLE AUTH URL] Query Parameters:")
    print(f"[GOOGLE AUTH URL]   - mobile: {mobile} (type: {type(mobile).__name__})")
    print(f"[GOOGLE AUTH URL]   - mobile_redirect_uri: {mobile_redirect_uri}")
    print(f"[GOOGLE AUTH URL] Settings:")
    print(f"[GOOGLE AUTH URL]   - google_redirect_uri: {settings.google_redirect_uri}")
    print(f"[GOOGLE AUTH URL]   - google_client_id: {settings.google_client_id[:30] if settings.google_client_id else 'None'}...")
    print(f"{'='*80}\n")
    
    google_service = GoogleAuthService(next(get_db()))
    
    # Determine if this is a mobile request
    is_mobile = mobile or mobile_redirect_uri is not None
    print(f"[GOOGLE AUTH URL] Determined request type: {'MOBILE' if is_mobile else 'WEB'}")
    
    if is_mobile:
        # For mobile: use web callback endpoint, encode mobile flag/redirect_uri in state
        # The web callback will redirect to mobile deep link after authentication
        web_callback_uri = settings.google_redirect_uri  # Use normal callback endpoint
        
        # Determine the mobile redirect URI
        if mobile_redirect_uri:
            # Use provided mobile_redirect_uri (takes precedence)
            final_mobile_redirect_uri = mobile_redirect_uri
        elif mobile:
            # Use default deep link for mobile=True
            final_mobile_redirect_uri = "kineticbrain://oauth"
        else:
            final_mobile_redirect_uri = None
        
        # Encode mobile flag and redirect URI in state parameter for later use
        state_data = {
            "mobile": True,
            "mobile_redirect_uri": final_mobile_redirect_uri,
            "token": secrets.token_urlsafe(32),  # Random token for CSRF protection
            "timestamp": time.time()
        }
        state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode().rstrip('=')
        
        print(f"[GOOGLE AUTH URL] Mobile flow configuration:")
        print(f"[GOOGLE AUTH URL]   - mobile parameter: {mobile}")
        print(f"[GOOGLE AUTH URL]   - mobile_redirect_uri (query param): {mobile_redirect_uri}")
        print(f"[GOOGLE AUTH URL]   - final_mobile_redirect_uri: {final_mobile_redirect_uri}")
        print(f"[GOOGLE AUTH URL]   - web_callback_uri: {web_callback_uri}")
        print(f"[GOOGLE AUTH URL] State data (before encoding):")
        print(f"[GOOGLE AUTH URL]   {json.dumps(state_data, indent=2)}")
        print(f"[GOOGLE AUTH URL] State (encoded, length {len(state)}): {state[:100]}...")
        
        auth_url = google_service.get_google_auth_url(redirect_uri=web_callback_uri, state=state)
    else:
        # For web: use default redirect URI without state
        print(f"[GOOGLE AUTH URL] Web flow configuration:")
        print(f"[GOOGLE AUTH URL]   - Using default redirect_uri: {settings.google_redirect_uri}")
        
        auth_url = google_service.get_google_auth_url(redirect_uri=settings.google_redirect_uri)
    
    print(f"[GOOGLE AUTH URL] Generated auth URL (length {len(auth_url)}):")
    print(f"[GOOGLE AUTH URL]   {auth_url}")
    print(f"[GOOGLE AUTH URL] ===== RESPONSE =====")
    print(f"[GOOGLE AUTH URL] Returning: {{'auth_url': '...'}}")
    print(f"{'='*80}\n")
    
    return {"auth_url": auth_url}


@router.get("/google/callback")
async def google_auth_callback_get(
    code: str,
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback from browser redirect (GET)
    
    Supports both web and mobile flows:
    - Web: No state parameter, redirects to frontend web app
    - Mobile: State parameter contains mobile flag, redirects to deep link (kineticbrain://oauth)
    """
    import logging
    import base64
    import json
    from urllib.parse import urlencode, parse_qs
    from fastapi import Request
    logger = logging.getLogger(__name__)
    
    print(f"\n{'='*80}")
    print(f"[GOOGLE CALLBACK GET] ===== REQUEST RECEIVED =====")
    print(f"[GOOGLE CALLBACK GET] Endpoint: GET /auth/google/callback")
    print(f"[GOOGLE CALLBACK GET] Query Parameters:")
    print(f"[GOOGLE CALLBACK GET]   - code: {code[:50] if code else 'None'}... (length: {len(code) if code else 0})")
    print(f"[GOOGLE CALLBACK GET]   - state: {state[:100] if state else 'None'}... (length: {len(state) if state else 0})")
    print(f"[GOOGLE CALLBACK GET] Settings:")
    print(f"[GOOGLE CALLBACK GET]   - google_redirect_uri: {settings.google_redirect_uri}")
    print(f"[GOOGLE CALLBACK GET]   - google_client_id: {settings.google_client_id[:30] if settings.google_client_id else 'None'}...")
    print(f"[GOOGLE CALLBACK GET]   - frontend_callback_uri: {settings.frontend_callback_uri}")
    print(f"{'='*80}\n")
    
    # Decode mobile flag from state if present
    is_mobile = False
    mobile_redirect_uri = None
    if state:
        print(f"[GOOGLE CALLBACK GET] Decoding state parameter...")
        try:
            # Add padding if needed
            state_padded = state + '=' * (4 - len(state) % 4)
            print(f"[GOOGLE CALLBACK GET]   - State padded length: {len(state_padded)}")
            decoded_bytes = base64.urlsafe_b64decode(state_padded)
            decoded_str = decoded_bytes.decode('utf-8')
            print(f"[GOOGLE CALLBACK GET]   - Decoded string: {decoded_str}")
            state_data = json.loads(decoded_str)
            print(f"[GOOGLE CALLBACK GET]   - State data: {json.dumps(state_data, indent=2)}")
            is_mobile = state_data.get("mobile", False)
            mobile_redirect_uri = state_data.get("mobile_redirect_uri")
            print(f"[GOOGLE CALLBACK GET] ✓ State decoded successfully")
            print(f"[GOOGLE CALLBACK GET]   - is_mobile: {is_mobile}")
            print(f"[GOOGLE CALLBACK GET]   - mobile_redirect_uri: {mobile_redirect_uri}")
        except Exception as e:
            print(f"[GOOGLE CALLBACK GET] ✗ Failed to decode state: {type(e).__name__}: {e}")
            import traceback
            print(f"[GOOGLE CALLBACK GET] Traceback: {traceback.format_exc()}")
            # Continue with web flow if state decoding fails
    else:
        print(f"[GOOGLE CALLBACK GET] No state parameter - using web flow")
    
    google_service = GoogleAuthService(db)
    
    print(f"[GOOGLE CALLBACK GET] Calling authenticate_google_user...")
    print(f"[GOOGLE CALLBACK GET]   - code: {code[:30]}...")
    print(f"[GOOGLE CALLBACK GET]   - redirect_uri: {settings.google_redirect_uri}")
    
    # Use configured redirect URI (env-configurable) instead of hardcoded localhost
    result = await google_service.authenticate_google_user(
        code=code,
        redirect_uri=settings.google_redirect_uri
    )
    
    if not result:
        print(f"[GOOGLE CALLBACK GET] ✗ Authentication failed - result is None")
        print(f"[GOOGLE CALLBACK GET] Preparing error redirect...")
        if is_mobile:
            # Redirect to mobile app with error
            redirect_uri = mobile_redirect_uri or "kineticbrain://oauth"
            error_params = {"error": "authentication_failed"}
            redirect_url = f"{redirect_uri}?{urlencode(error_params)}"
            print(f"[GOOGLE CALLBACK GET] Redirecting to mobile app with error:")
            print(f"[GOOGLE CALLBACK GET]   - redirect_url: {redirect_url}")
            return RedirectResponse(url=redirect_url, status_code=302)
        else:
            # Redirect to frontend with error
            error_url = f"{settings.frontend_callback_uri}?error=authentication_failed"
            print(f"[GOOGLE CALLBACK GET] Redirecting to web app with error:")
            print(f"[GOOGLE CALLBACK GET]   - error_url: {error_url}")
            return RedirectResponse(url=error_url, status_code=302)
    
    # Get tokens and user info
    tokens = result["tokens"]
    user = result["user"]
    
    print(f"[GOOGLE CALLBACK GET] ✓ Authentication successful!")
    print(f"[GOOGLE CALLBACK GET] User info:")
    print(f"[GOOGLE CALLBACK GET]   - user_id: {user.id}")
    print(f"[GOOGLE CALLBACK GET]   - email: {user.email}")
    print(f"[GOOGLE CALLBACK GET]   - name: {user.name}")
    print(f"[GOOGLE CALLBACK GET] Tokens:")
    print(f"[GOOGLE CALLBACK GET]   - access_token length: {len(tokens['access_token'])}")
    print(f"[GOOGLE CALLBACK GET]   - refresh_token length: {len(tokens['refresh_token'])}")
    print(f"[GOOGLE CALLBACK GET]   - token_type: {tokens['token_type']}")
    
    # Encode tokens for URL
    params = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": tokens["token_type"],
        "user_id": str(user.id),
        "user_email": user.email,
        "user_name": user.name or ""
    }
    
    print(f"[GOOGLE CALLBACK GET] URL parameters (keys only): {list(params.keys())}")
    
    if is_mobile:
        # Mobile flow: redirect to deep link with HTTP 302 redirect
        redirect_uri = mobile_redirect_uri or "kineticbrain://oauth"
        params["success"] = "true"
        redirect_url = f"{redirect_uri}?{urlencode(params)}"
        print(f"[GOOGLE CALLBACK GET] Mobile flow - redirecting to deep link with HTTP 302:")
        print(f"[GOOGLE CALLBACK GET]   - redirect_uri: {redirect_uri}")
        print(f"[GOOGLE CALLBACK GET]   - redirect_url (first 200 chars): {redirect_url[:200]}...")
        print(f"[GOOGLE CALLBACK GET]   - redirect_url (full length): {len(redirect_url)} chars")
        print(f"[GOOGLE CALLBACK GET]   - redirect_url (FULL): {redirect_url}")
        print(f"[GOOGLE CALLBACK GET]   - Using HTTP 302 redirect (RedirectResponse)")
        print(f"[GOOGLE CALLBACK GET] ===== RESPONSE (302 Redirect to deeplink) =====")
        return RedirectResponse(url=redirect_url, status_code=302)
    else:
        # Web flow: redirect to frontend callback page
        frontend_callback_url = f"{settings.frontend_callback_uri}?{urlencode(params)}"
        print(f"[GOOGLE CALLBACK GET] Web flow - redirecting to frontend:")
        print(f"[GOOGLE CALLBACK GET]   - frontend_callback_uri: {settings.frontend_callback_uri}")
        print(f"[GOOGLE CALLBACK GET]   - frontend_callback_url (first 200 chars): {frontend_callback_url[:200]}...")
        print(f"[GOOGLE CALLBACK GET] ===== RESPONSE (302 Redirect) =====")
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
    import base64
    import json
    from urllib.parse import urlencode
    
    print(f"[Google OAuth Mobile] ===== MOBILE CALLBACK START =====")
    print(f"[Google OAuth Mobile] Callback received with code (length: {len(code) if code else 0})")
    print(f"[Google OAuth Mobile] State: {state[:100] if state else 'None'}...")
    print(f"[Google OAuth Mobile] Full state: {state}")
    
    # Decode mobile_redirect_uri from state
    mobile_redirect_uri = None
    if state:
        try:
            # Add padding if needed
            state_padded = state + '=' * (4 - len(state) % 4)
            print(f"[Google OAuth Mobile] Decoding state (padded length: {len(state_padded)})")
            decoded_bytes = base64.urlsafe_b64decode(state_padded)
            decoded_str = decoded_bytes.decode('utf-8')
            print(f"[Google OAuth Mobile] Decoded string: {decoded_str}")
            state_data = json.loads(decoded_str)
            mobile_redirect_uri = state_data.get("mobile_redirect_uri")
            print(f"[Google OAuth Mobile] ✓ Successfully decoded mobile_redirect_uri: {mobile_redirect_uri}")
        except Exception as e:
            print(f"[Google OAuth Mobile] ✗ Failed to decode state: {type(e).__name__}: {e}")
            import traceback
            print(f"[Google OAuth Mobile] Traceback: {traceback.format_exc()}")
    
    if not mobile_redirect_uri:
        print(f"[Google OAuth Mobile] No mobile_redirect_uri in state - redirecting to web callback")
        # Fallback to web callback
        return RedirectResponse(
            url=f"{settings.frontend_callback_uri}?error=invalid_state",
            status_code=302
        )
    
    # Use the web callback URI (this is what Google redirected to)
    web_callback_uri = f"{settings.google_redirect_uri.rstrip('/callback')}/mobile-callback"
    
    google_service = GoogleAuthService(db)
    
    print(f"[Google OAuth Mobile] Using web_callback_uri for token exchange: {web_callback_uri}")
    
    result = await google_service.authenticate_google_user(
        code=code,
        redirect_uri=web_callback_uri
    )
    
    if not result:
        print(f"[Google OAuth Mobile] ✗ Authentication failed")
        # Redirect to mobile app with error
        error_params = {
            "error": "authentication_failed"
        }
        redirect_url = f"{mobile_redirect_uri}?{urlencode(error_params)}"
        print(f"[Google OAuth Mobile] Redirecting to mobile app with error: {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=302)
    
    # Get tokens and user info
    tokens = result["tokens"]
    user = result["user"]
    
    print(f"[Google OAuth Mobile] ✓ Authentication successful for user: {user.email} (id: {user.id})")
    print(f"[Google OAuth Mobile] Tokens generated - access_token length: {len(tokens['access_token'])}, refresh_token length: {len(tokens['refresh_token'])}")
    
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
    print(f"[Google OAuth Mobile] ===== REDIRECTING TO MOBILE APP =====")
    print(f"[Google OAuth Mobile]   - mobile_redirect_uri: {mobile_redirect_uri}")
    print(f"[Google OAuth Mobile]   - redirect_url (first 150 chars): {redirect_url[:150]}...")
    print(f"[Google OAuth Mobile]   - redirect_url (full length): {len(redirect_url)} chars")
    print(f"[Google OAuth Mobile]   - redirect_url (FULL): {redirect_url}")
    print(f"[Google OAuth Mobile]   - params keys: {list(params.keys())}")
    print(f"[Google OAuth Mobile]   - Using HTTP 302 redirect (RedirectResponse)")
    print(f"[Google OAuth Mobile] ===== MOBILE CALLBACK END =====")
    
    # Return HTTP 302 redirect to deep link (instead of HTML with JavaScript)
    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/google/callback", response_model=Token)
async def google_auth_callback_post(request: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Handle Google OAuth callback from API calls (POST)"""
    import logging
    import json
    logger = logging.getLogger(__name__)
    
    print(f"\n{'='*80}")
    print(f"[GOOGLE CALLBACK POST] ===== REQUEST RECEIVED =====")
    print(f"[GOOGLE CALLBACK POST] Endpoint: POST /auth/google/callback")
    print(f"[GOOGLE CALLBACK POST] Request Body:")
    print(f"[GOOGLE CALLBACK POST]   - code: {request.code[:50] if request.code else 'None'}... (length: {len(request.code) if request.code else 0})")
    print(f"[GOOGLE CALLBACK POST]   - redirect_uri: {request.redirect_uri}")
    print(f"[GOOGLE CALLBACK POST] Settings:")
    print(f"[GOOGLE CALLBACK POST]   - google_redirect_uri: {settings.google_redirect_uri}")
    print(f"[GOOGLE CALLBACK POST]   - google_client_id: {settings.google_client_id[:30] if settings.google_client_id else 'None'}...")
    print(f"{'='*80}\n")
    
    # Warn if redirect_uri doesn't match settings (common cause of 401 errors)
    if request.redirect_uri and request.redirect_uri != settings.google_redirect_uri:
        print(f"[GOOGLE CALLBACK POST] ⚠️  WARNING: redirect_uri mismatch!")
        print(f"[GOOGLE CALLBACK POST]   Request redirect_uri: {request.redirect_uri}")
        print(f"[GOOGLE CALLBACK POST]   Settings redirect_uri: {settings.google_redirect_uri}")
        print(f"[GOOGLE CALLBACK POST]   Match: {request.redirect_uri == settings.google_redirect_uri}")
        print(f"[GOOGLE CALLBACK POST]   This will likely cause authentication to fail!")
        
        # Check if it's a custom URL scheme (React Native)
        if request.redirect_uri.startswith(("kineticbrain://", "com.", "io.")):
            print(f"[GOOGLE CALLBACK POST]   Detected custom URL scheme - this requires:")
            print(f"[GOOGLE CALLBACK POST]   1. Register '{request.redirect_uri}' in Google Cloud Console")
            print(f"[GOOGLE CALLBACK POST]   2. OR use /auth/google/verify-id-token endpoint (recommended for React Native)")
    else:
        print(f"[GOOGLE CALLBACK POST] ✓ redirect_uri matches settings")
    
    google_service = GoogleAuthService(db)
    
    print(f"[GOOGLE CALLBACK POST] Calling authenticate_google_user...")
    print(f"[GOOGLE CALLBACK POST]   - code: {request.code[:30]}...")
    print(f"[GOOGLE CALLBACK POST]   - redirect_uri: {request.redirect_uri}")
    
    try:
        result = await google_service.authenticate_google_user(
            code=request.code,
            redirect_uri=request.redirect_uri
        )
        
        if not result:
            print(f"[GOOGLE CALLBACK POST] ✗ Authentication failed - result is None")
            print(f"[GOOGLE CALLBACK POST] Common issues:")
            print(f"[GOOGLE CALLBACK POST]   - redirect_uri mismatch (must match exactly)")
            print(f"[GOOGLE CALLBACK POST]   - Code already used or expired")
            print(f"[GOOGLE CALLBACK POST]   - Invalid client_id or client_secret")
            print(f"[GOOGLE CALLBACK POST]   - User email not verified")
            print(f"[GOOGLE CALLBACK POST]   - App doesn't comply with Google OAuth 2.0 policy")
            
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
            
            print(f"[GOOGLE CALLBACK POST] Raising HTTPException with detail: {error_detail}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_detail
            )
        
        user = result.get("user")
        tokens = result.get("tokens")
        
        print(f"[GOOGLE CALLBACK POST] ✓ Authentication successful!")
        print(f"[GOOGLE CALLBACK POST] User info:")
        print(f"[GOOGLE CALLBACK POST]   - user_id: {user.id if user else 'None'}")
        print(f"[GOOGLE CALLBACK POST]   - email: {user.email if user else 'None'}")
        print(f"[GOOGLE CALLBACK POST]   - name: {user.name if user else 'None'}")
        print(f"[GOOGLE CALLBACK POST] Tokens:")
        print(f"[GOOGLE CALLBACK POST]   - access_token length: {len(tokens['access_token']) if tokens else 'None'}")
        print(f"[GOOGLE CALLBACK POST]   - refresh_token length: {len(tokens['refresh_token']) if tokens else 'None'}")
        print(f"[GOOGLE CALLBACK POST]   - token_type: {tokens.get('token_type') if tokens else 'None'}")
        print(f"[GOOGLE CALLBACK POST] ===== RESPONSE =====")
        print(f"[GOOGLE CALLBACK POST] Returning tokens (access_token and refresh_token)")
        print(f"{'='*80}\n")
        
        return result["tokens"]
    except HTTPException:
        raise
    except Exception as e:
        print(f"[GOOGLE CALLBACK POST] ✗ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        print(f"[GOOGLE CALLBACK POST] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error during Google authentication: {str(e)}"
        )


@router.post("/google/login", response_model=Token)
async def google_login(request: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Login with Google OAuth (same as callback but with different endpoint name)"""
    print(f"\n{'='*80}")
    print(f"[GOOGLE LOGIN] ===== REQUEST RECEIVED =====")
    print(f"[GOOGLE LOGIN] Endpoint: POST /auth/google/login")
    print(f"[GOOGLE LOGIN] Request Body:")
    print(f"[GOOGLE LOGIN]   - code: {request.code[:50] if request.code else 'None'}... (length: {len(request.code) if request.code else 0})")
    print(f"[GOOGLE LOGIN]   - redirect_uri: {request.redirect_uri}")
    print(f"{'='*80}\n")
    
    google_service = GoogleAuthService(db)
    
    print(f"[GOOGLE LOGIN] Calling authenticate_google_user...")
    result = await google_service.authenticate_google_user(
        code=request.code,
        redirect_uri=request.redirect_uri
    )
    
    if not result:
        print(f"[GOOGLE LOGIN] ✗ Authentication failed - result is None")
        print(f"[GOOGLE LOGIN] ===== RESPONSE (401) =====")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google authentication failed"
        )
    
    user = result.get("user")
    tokens = result.get("tokens")
    
    print(f"[GOOGLE LOGIN] ✓ Authentication successful!")
    print(f"[GOOGLE LOGIN] User: {user.email if user else 'None'} (id: {user.id if user else 'None'})")
    print(f"[GOOGLE LOGIN] Tokens generated (access_token length: {len(tokens['access_token']) if tokens else 'None'})")
    print(f"[GOOGLE LOGIN] ===== RESPONSE =====")
    print(f"{'='*80}\n")
    
    return result["tokens"]


@router.post("/google/verify-id-token", response_model=Token)
async def verify_google_id_token(request: GoogleIdTokenRequest, db: Session = Depends(get_db)):
    """Verify Google ID token from React Native and return JWT tokens
    
    This endpoint is RECOMMENDED for React Native apps using Google Sign-In SDK.
    It doesn't require redirect URIs and works without custom URL schemes.
    
    Usage in React Native:
    1. Use @react-native-google-signin/google-signin to get ID token
    2. Send ID token to this endpoint
    3. Receive JWT tokens (access_token, refresh_token)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    print(f"\n{'='*80}")
    print(f"[GOOGLE VERIFY ID TOKEN] ===== REQUEST RECEIVED =====")
    print(f"[GOOGLE VERIFY ID TOKEN] Endpoint: POST /auth/google/verify-id-token")
    print(f"[GOOGLE VERIFY ID TOKEN] Request Body:")
    print(f"[GOOGLE VERIFY ID TOKEN]   - id_token: {request.id_token[:100] if request.id_token else 'None'}... (length: {len(request.id_token) if request.id_token else 0})")
    print(f"[GOOGLE VERIFY ID TOKEN] Settings:")
    print(f"[GOOGLE VERIFY ID TOKEN]   - google_client_id: {settings.google_client_id[:30] if settings.google_client_id else 'None'}...")
    print(f"[GOOGLE VERIFY ID TOKEN]   - google_additional_client_ids: {settings.google_additional_client_ids if hasattr(settings, 'google_additional_client_ids') else 'Not configured'}")
    print(f"{'='*80}\n")
    
    google_service = GoogleAuthService(db)
    
    print(f"[GOOGLE VERIFY ID TOKEN] Calling verify_google_id_token...")
    try:
        result = await google_service.verify_google_id_token(request.id_token)
        
        if not result:
            print(f"[GOOGLE VERIFY ID TOKEN] ✗ Verification failed - invalid or expired token")
            print(f"[GOOGLE VERIFY ID TOKEN] ===== RESPONSE (401) =====")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(
                    "Invalid or expired Google ID token. "
                    "Common causes: "
                    "1) Wrong Client ID - Use the WEB Client ID (not Android/iOS Client ID) in GoogleSignin.configure() "
                    "2) Token expired - Request a new token "
                    "3) Client ID mismatch - Add your Android/iOS Client ID to GOOGLE_ADDITIONAL_CLIENT_IDS in backend .env"
                )
            )
        
        user = result.get("user")
        tokens = result.get("tokens")
        user_email = user.email if user else "unknown"
        user_id = user.id if user else "unknown"
        
        print(f"[GOOGLE VERIFY ID TOKEN] ✓ Verification successful!")
        print(f"[GOOGLE VERIFY ID TOKEN] User info:")
        print(f"[GOOGLE VERIFY ID TOKEN]   - user_id: {user_id}")
        print(f"[GOOGLE VERIFY ID TOKEN]   - email: {user_email}")
        print(f"[GOOGLE VERIFY ID TOKEN]   - name: {user.name if user else 'None'}")
        print(f"[GOOGLE VERIFY ID TOKEN] Tokens:")
        print(f"[GOOGLE VERIFY ID TOKEN]   - access_token length: {len(tokens['access_token']) if tokens else 'None'}")
        print(f"[GOOGLE VERIFY ID TOKEN]   - refresh_token length: {len(tokens['refresh_token']) if tokens else 'None'}")
        print(f"[GOOGLE VERIFY ID TOKEN]   - token_type: {tokens.get('token_type') if tokens else 'None'}")
        print(f"[GOOGLE VERIFY ID TOKEN] ===== RESPONSE =====")
        print(f"[GOOGLE VERIFY ID TOKEN] Returning tokens")
        print(f"{'='*80}\n")
        
        return result["tokens"]
    except HTTPException:
        raise
    except Exception as e:
        print(f"[GOOGLE VERIFY ID TOKEN] ✗ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        print(f"[GOOGLE VERIFY ID TOKEN] Traceback: {traceback.format_exc()}")
        print(f"[GOOGLE VERIFY ID TOKEN] ===== RESPONSE (500) =====")
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
