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
    print(f"[Google OAuth Mobile]   - params keys: {list(params.keys())}")
    print(f"[Google OAuth Mobile] ===== MOBILE CALLBACK END =====")
    
    # Return HTML page that opens the deep link using JavaScript
    # This works better than HTTP redirect for custom URL schemes in WebViews
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Redirecting to App...</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }}
            .container {{
                text-align: center;
                padding: 2rem;
            }}
            .spinner {{
                border: 4px solid rgba(255, 255, 255, 0.3);
                border-top: 4px solid white;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 1rem;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            h1 {{
                margin: 0 0 1rem 0;
                font-size: 1.5rem;
            }}
            p {{
                margin: 0.5rem 0;
                opacity: 0.9;
            }}
            .button {{
                margin-top: 1.5rem;
                padding: 0.75rem 1.5rem;
                background: white;
                color: #667eea;
                border: none;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
            }}
            .button:hover {{
                background: #f0f0f0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="spinner"></div>
            <h1>Redirecting to App...</h1>
            <p>Please wait while we open the app.</p>
            <p>If the app doesn't open automatically, click the button below.</p>
            <a href="{redirect_url}" class="button">Open App</a>
        </div>
        <script>
            // Try to open the deep link immediately
            window.location.href = "{redirect_url}";
            
            // Fallback: try after a short delay (some browsers need this)
            setTimeout(function() {{
                window.location.href = "{redirect_url}";
            }}, 500);
            
            // Fallback: try with window.open (for some WebViews)
            setTimeout(function() {{
                window.open("{redirect_url}", "_self");
            }}, 1000);
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


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
    It doesn't require redirect URIs and works without custom URL schemes.
    
    Usage in React Native:
    1. Use @react-native-google-signin/google-signin to get ID token
    2. Send ID token to this endpoint
    3. Receive JWT tokens (access_token, refresh_token)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    print(f"[Google ID Token API] ===== REQUEST RECEIVED =====")
    print(f"[Google ID Token API] Token length: {len(request.id_token) if request.id_token else 0}")
    
    google_service = GoogleAuthService(db)
    
    try:
        result = await google_service.verify_google_id_token(request.id_token)
        
        if not result:
            print(f"[Google ID Token API] ✗ Verification failed - invalid or expired token")
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
        user_email = user.email if user else "unknown"
        user_id = user.id if user else "unknown"
        
        print(f"[Google ID Token API] ✓ Verification successful for user: {user_email} (id: {user_id})")
        print(f"[Google ID Token API] ===== REQUEST SUCCESS =====")
        
        return result["tokens"]
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Google ID Token API] ✗ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        print(f"[Google ID Token API] Traceback: {traceback.format_exc()}")
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
