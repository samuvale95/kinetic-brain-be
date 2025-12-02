from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserLogin, UserResponse, GoogleAuthRequest, GoogleIdTokenRequest
from app.services.auth_service import AuthService
from app.services.google_auth_service import GoogleAuthService
from app.utils.security import verify_token
from app.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), 
                    db: Session = Depends(get_db)) -> dict:
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token, "access")
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    auth_service = AuthService(db)
    user = auth_service.get_user_by_id(int(payload["sub"]))
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {"user_id": user.id, "email": user.email}


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
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    payload = verify_token(refresh_token, "refresh")
    
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
async def get_google_auth_url():
    """Get Google OAuth authorization URL"""
    google_service = GoogleAuthService(next(get_db()))
    auth_url = google_service.get_google_auth_url()
    return {"auth_url": auth_url}


@router.get("/google/callback")
async def google_auth_callback_get(code: str, db: Session = Depends(get_db)):
    """Handle Google OAuth callback from browser redirect (GET)"""
    google_service = GoogleAuthService(db)
    
    # Use configured redirect URI (env-configurable) instead of hardcoded localhost
    result = await google_service.authenticate_google_user(
        code=code,
        redirect_uri=settings.google_redirect_uri
    )
    
    if not result:
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


@router.post("/google/callback", response_model=Token)
async def google_auth_callback_post(request: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Handle Google OAuth callback from API calls (POST)"""
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
    """Verify Google ID token from React Native and return JWT tokens"""
    google_service = GoogleAuthService(db)
    
    result = await google_service.verify_google_id_token(request.id_token)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Google ID token"
        )
    
    return result["tokens"]


@router.get("/test")
async def test_auth():
    """Test endpoint to verify authentication is working"""
    return {"message": "Authentication test successful", "status": "ok"}
