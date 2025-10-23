import httpx
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.config import settings
from app.models.user import User, OAuthAccount
from app.schemas.user import GoogleUserInfo
from app.utils.security import create_access_token, create_refresh_token
from datetime import datetime, timedelta


class GoogleAuthService:
    def __init__(self, db: Session):
        self.db = db
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_redirect_uri
    
    async def get_google_user_info(self, access_token: str) -> Optional[GoogleUserInfo]:
        """Get user information from Google using access token"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                data = response.json()
                
                return GoogleUserInfo(
                    id=data["id"],
                    email=data["email"],
                    name=data["name"],
                    picture=data.get("picture"),
                    verified_email=data.get("verified_email", True)
                )
        except Exception as e:
            print(f"Error getting Google user info: {e}")
            return None
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str = None) -> Optional[str]:
        """Exchange authorization code for access token"""
        try:
            redirect_uri = redirect_uri or self.redirect_uri
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data.get("access_token")
        except Exception as e:
            print(f"Error exchanging code for token: {e}")
            return None
    
    async def authenticate_google_user(self, code: str, redirect_uri: str = None) -> Optional[Dict[str, Any]]:
        """Authenticate user with Google OAuth"""
        # Exchange code for access token
        access_token = await self.exchange_code_for_token(code, redirect_uri)
        if not access_token:
            return None
        
        # Get user info from Google
        google_user = await self.get_google_user_info(access_token)
        if not google_user or not google_user.verified_email:
            return None
        
        # Check if user exists
        user = self.db.execute(
            select(User).where(User.email == google_user.email)
        ).scalar_one_or_none()
        
        if not user:
            # Create new user
            user = User(
                email=google_user.email,
                name=google_user.name,
                avatar_url=google_user.picture,
                auth_provider="google",
                is_verified=True,
                is_active=True
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        
        # Create or update OAuth account
        oauth_account = self.db.execute(
            select(OAuthAccount).where(
                OAuthAccount.user_id == user.id,
                OAuthAccount.provider == "google"
            )
        ).scalar_one_or_none()
        
        if not oauth_account:
            oauth_account = OAuthAccount(
                user_id=user.id,
                provider="google",
                provider_account_id=google_user.id,
                access_token=access_token,
                token_expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            self.db.add(oauth_account)
        else:
            oauth_account.access_token = access_token
            oauth_account.token_expires_at = datetime.utcnow() + timedelta(hours=1)
        
        self.db.commit()
        
        # Update last login
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        # Create JWT tokens
        tokens = {
            "access_token": create_access_token(
                data={"sub": str(user.id), "email": user.email}
            ),
            "refresh_token": create_refresh_token(
                data={"sub": str(user.id), "email": user.email}
            ),
            "token_type": "bearer"
        }
        
        return {
            "user": user,
            "tokens": tokens
        }
    
    def get_google_auth_url(self, state: str = None) -> str:
        """Generate Google OAuth authorization URL"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "openid email profile",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent"
        }
        
        if state:
            params["state"] = state
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"
