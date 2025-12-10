import httpx
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from google.auth.transport import requests
from google.oauth2 import id_token
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
        
        # Log configuration (masked for security)
        if self.client_id:
            masked_id = f"{self.client_id[:20]}..." if len(self.client_id) > 20 else self.client_id
            print(f"[Google OAuth] Service initialized with client_id: {masked_id}")
        else:
            print("[Google OAuth] WARNING: No client_id configured!")
    
    async def get_google_user_info(self, access_token: str) -> Optional[GoogleUserInfo]:
        """Get user information from Google using access token"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if response.status_code != 200:
                    error_data = response.text
                    print(f"[Google OAuth] Failed to get user info: {response.status_code} - {error_data}")
                    return None
                
                response.raise_for_status()
                data = response.json()
                
                print(f"[Google OAuth] Successfully retrieved user info for: {data.get('email', 'unknown')}")
                return GoogleUserInfo(
                    id=data["id"],
                    email=data["email"],
                    name=data["name"],
                    picture=data.get("picture"),
                    verified_email=data.get("verified_email", True)
                )
        except httpx.HTTPStatusError as e:
            error_data = e.response.text if e.response else "No response"
            print(f"[Google OAuth] HTTP error getting user info: {e.response.status_code} - {error_data}")
            return None
        except Exception as e:
            print(f"[Google OAuth] Error getting Google user info: {type(e).__name__}: {e}")
            return None
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str = None) -> Optional[str]:
        """Exchange authorization code for access token"""
        try:
            redirect_uri = redirect_uri or self.redirect_uri
            masked_client_id = f"{self.client_id[:20]}..." if self.client_id and len(self.client_id) > 20 else self.client_id
            print(f"[Google OAuth] Exchanging code for token")
            print(f"[Google OAuth]   - redirect_uri: {redirect_uri}")
            print(f"[Google OAuth]   - default redirect_uri: {self.redirect_uri}")
            print(f"[Google OAuth]   - redirect_uri match: {redirect_uri == self.redirect_uri}")
            print(f"[Google OAuth]   - client_id: {masked_client_id}")
            print(f"[Google OAuth]   - client_secret configured: {'Yes' if self.client_secret else 'No'}")
            print(f"[Google OAuth]   - code length: {len(code) if code else 0}")
            
            if not self.client_id:
                print(f"[Google OAuth] ERROR: client_id is not configured!")
                return None
            
            if not self.client_secret:
                print(f"[Google OAuth] ERROR: client_secret is not configured!")
                return None
            
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
                
                if response.status_code != 200:
                    error_data = response.text
                    print(f"[Google OAuth] Token exchange failed: {response.status_code}")
                    try:
                        error_json = response.json()
                        print(f"[Google OAuth] Error details: {error_json}")
                        error_type = error_json.get("error", "unknown")
                        error_description = error_json.get("error_description", "No description")
                        print(f"[Google OAuth] Error type: {error_type}")
                        print(f"[Google OAuth] Error description: {error_description}")
                        
                        # Common errors:
                        if error_type == "invalid_grant":
                            print(f"[Google OAuth] This usually means:")
                            print(f"[Google OAuth]   - Code already used or expired")
                            print(f"[Google OAuth]   - redirect_uri mismatch")
                            print(f"[Google OAuth]   - client_id/client_secret mismatch")
                        elif error_type == "redirect_uri_mismatch":
                            print(f"[Google OAuth] redirect_uri mismatch! Expected: {redirect_uri}")
                        elif error_type == "invalid_request":
                            if "OAuth 2.0 policy" in error_description or "doesn't comply" in error_description:
                                print(f"[Google OAuth] ⚠️  CRITICAL: App doesn't comply with Google OAuth 2.0 policy!")
                                print(f"[Google OAuth] This usually means:")
                                print(f"[Google OAuth]   1. Custom URL scheme '{redirect_uri}' not registered in Google Cloud Console")
                                print(f"[Google OAuth]   2. App is in testing mode and needs test users added")
                                print(f"[Google OAuth]   3. App needs to be verified/published")
                                print(f"[Google OAuth] SOLUTIONS:")
                                print(f"[Google OAuth]   → Register '{redirect_uri}' in Google Cloud Console → Credenziali → OAuth 2.0 Client ID")
                                print(f"[Google OAuth]   → Add test users in OAuth consent screen (if in testing mode)")
                                print(f"[Google OAuth]   → See docs/GOOGLE_OAUTH_REACT_NATIVE.md for detailed instructions")
                                print(f"[Google OAuth]   → Alternative: Use /auth/google/verify-id-token endpoint (Google Sign-In SDK)")
                    except:
                        print(f"[Google OAuth] Raw error response: {error_data}")
                    return None
                
                response.raise_for_status()
                data = response.json()
                access_token = data.get("access_token")
                if access_token:
                    print(f"[Google OAuth] Token exchange successful")
                else:
                    print(f"[Google OAuth] No access_token in response: {data}")
                return access_token
        except httpx.HTTPStatusError as e:
            error_data = e.response.text if e.response else "No response"
            print(f"[Google OAuth] HTTP error exchanging code for token: {e.response.status_code} - {error_data}")
            try:
                error_json = e.response.json()
                print(f"[Google OAuth] Error JSON: {error_json}")
            except:
                pass
            return None
        except Exception as e:
            print(f"[Google OAuth] Error exchanging code for token: {type(e).__name__}: {e}")
            import traceback
            print(f"[Google OAuth] Traceback: {traceback.format_exc()}")
            return None
    
    async def authenticate_google_user(self, code: str, redirect_uri: str = None) -> Optional[Dict[str, Any]]:
        """Authenticate user with Google OAuth"""
        # Exchange code for access token
        access_token = await self.exchange_code_for_token(code, redirect_uri)
        if not access_token:
            print(f"[Google OAuth] Failed to exchange code for token")
            return None
        
        # Get user info from Google
        google_user = await self.get_google_user_info(access_token)
        if not google_user:
            print(f"[Google OAuth] Failed to get user info from Google")
            return None
        
        if not google_user.verified_email:
            print(f"[Google OAuth] User email not verified: {google_user.email}")
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
    
    def get_google_auth_url(self, redirect_uri: str = None, state: str = None) -> str:
        """Generate Google OAuth authorization URL
        
        Args:
            redirect_uri: Optional custom redirect URI (for React Native custom URL schemes)
            state: Optional state parameter for CSRF protection
        """
        # Use provided redirect_uri or default from settings
        use_redirect_uri = redirect_uri or self.redirect_uri
        
        masked_client_id = f"{self.client_id[:20]}..." if self.client_id and len(self.client_id) > 20 else self.client_id
        print(f"[Google OAuth] Generating auth URL with client_id: {masked_client_id}")
        print(f"[Google OAuth] Using redirect_uri: {use_redirect_uri}")
        if redirect_uri:
            print(f"[Google OAuth]   - Custom redirect_uri provided (for React Native)")
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": use_redirect_uri,
            "scope": "openid email profile",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent"
        }
        
        if state:
            params["state"] = state
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"
    
    async def verify_google_id_token(self, id_token_string: str) -> Optional[Dict[str, Any]]:
        """Verify Google ID token and authenticate user (for React Native)"""
        print(f"[Google ID Token] ===== VERIFICATION START =====")
        print(f"[Google ID Token] Token length: {len(id_token_string) if id_token_string else 0}")
        print(f"[Google ID Token] Using client_id: {self.client_id[:20] if self.client_id else 'None'}...")
        
        try:
            # Verify the ID token
            request = requests.Request()
            print(f"[Google ID Token] Verifying token with Google...")
            id_info = id_token.verify_oauth2_token(
                id_token_string, 
                request, 
                self.client_id
            )
            print(f"[Google ID Token] ✓ Token verified successfully")
            
            # Extract user information from ID token
            google_user_id = id_info.get("sub")
            email = id_info.get("email")
            name = id_info.get("name")
            picture = id_info.get("picture")
            email_verified = id_info.get("email_verified", False)
            
            print(f"[Google ID Token] Extracted info:")
            print(f"[Google ID Token]   - google_user_id: {google_user_id}")
            print(f"[Google ID Token]   - email: {email}")
            print(f"[Google ID Token]   - name: {name}")
            print(f"[Google ID Token]   - email_verified: {email_verified}")
            
            if not email or not email_verified:
                print(f"[Google ID Token] ✗ Email not verified or missing in ID token")
                return None
            
            # Check if user exists
            print(f"[Google ID Token] Checking if user exists in database...")
            user = self.db.execute(
                select(User).where(User.email == email)
            ).scalar_one_or_none()
            
            if not user:
                # Create new user
                print(f"[Google ID Token] Creating new user...")
                user = User(
                    email=email,
                    name=name or email.split("@")[0],
                    avatar_url=picture,
                    auth_provider="google",
                    is_verified=True,
                    is_active=True
                )
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
                print(f"[Google ID Token] ✓ New user created: {user.email} (id: {user.id})")
            else:
                print(f"[Google ID Token] User exists: {user.email} (id: {user.id})")
                # Update user info if needed
                if name and user.name != name:
                    user.name = name
                if picture and user.avatar_url != picture:
                    user.avatar_url = picture
            
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
                    provider_account_id=google_user_id,
                    access_token=None,  # ID token doesn't provide access token
                    token_expires_at=None
                )
                self.db.add(oauth_account)
            else:
                # Update provider account ID if changed
                if oauth_account.provider_account_id != google_user_id:
                    oauth_account.provider_account_id = google_user_id
            
            self.db.commit()
            
            # Update last login
            user.last_login = datetime.utcnow()
            self.db.commit()
            
            # Create JWT tokens
            print(f"[Google ID Token] Creating JWT tokens...")
            tokens = {
                "access_token": create_access_token(
                    data={"sub": str(user.id), "email": user.email}
                ),
                "refresh_token": create_refresh_token(
                    data={"sub": str(user.id), "email": user.email}
                ),
                "token_type": "bearer"
            }
            
            print(f"[Google ID Token] ✓ Tokens created successfully")
            print(f"[Google ID Token]   - access_token length: {len(tokens['access_token'])}")
            print(f"[Google ID Token]   - refresh_token length: {len(tokens['refresh_token'])}")
            print(f"[Google ID Token] ===== VERIFICATION SUCCESS =====")
            
            return {
                "user": user,
                "tokens": tokens
            }
        except ValueError as e:
            # Invalid token
            print(f"[Google ID Token] ✗ Invalid token error: {type(e).__name__}: {e}")
            import traceback
            print(f"[Google ID Token] Traceback: {traceback.format_exc()}")
            return None
        except Exception as e:
            print(f"[Google ID Token] ✗ Unexpected error: {type(e).__name__}: {e}")
            import traceback
            print(f"[Google ID Token] Traceback: {traceback.format_exc()}")
            return None
