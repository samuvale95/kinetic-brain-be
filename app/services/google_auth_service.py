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
        print(f"\n[GOOGLE USER INFO] ===== REQUEST START =====")
        print(f"[GOOGLE USER INFO] Endpoint: GET https://www.googleapis.com/oauth2/v2/userinfo")
        print(f"[GOOGLE USER INFO] Headers:")
        print(f"[GOOGLE USER INFO]   - Authorization: Bearer {access_token[:30]}... (length: {len(access_token)})")
        print(f"[GOOGLE USER INFO] Making HTTP request...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                print(f"[GOOGLE USER INFO] ===== RESPONSE RECEIVED =====")
                print(f"[GOOGLE USER INFO] Status Code: {response.status_code}")
                print(f"[GOOGLE USER INFO] Response Headers:")
                for key, value in response.headers.items():
                    print(f"[GOOGLE USER INFO]   - {key}: {value}")
                
                if response.status_code != 200:
                    error_data = response.text
                    print(f"[GOOGLE USER INFO] ✗ Failed to get user info")
                    print(f"[GOOGLE USER INFO] Error Response Body: {error_data}")
                    print(f"[GOOGLE USER INFO] ===== REQUEST FAILED =====")
                    return None
                
                response.raise_for_status()
                data = response.json()
                
                print(f"[GOOGLE USER INFO] Response Body (JSON):")
                print(f"[GOOGLE USER INFO]   - id: {data.get('id')}")
                print(f"[GOOGLE USER INFO]   - email: {data.get('email')}")
                print(f"[GOOGLE USER INFO]   - name: {data.get('name')}")
                print(f"[GOOGLE USER INFO]   - picture: {data.get('picture', 'None')[:50]}...")
                print(f"[GOOGLE USER INFO]   - verified_email: {data.get('verified_email', True)}")
                print(f"[GOOGLE USER INFO] ✓ Successfully retrieved user info")
                print(f"[GOOGLE USER INFO] ===== REQUEST SUCCESS =====")
                
                return GoogleUserInfo(
                    id=data["id"],
                    email=data["email"],
                    name=data["name"],
                    picture=data.get("picture"),
                    verified_email=data.get("verified_email", True)
                )
        except httpx.HTTPStatusError as e:
            error_data = e.response.text if e.response else "No response"
            print(f"[GOOGLE USER INFO] ✗ HTTP error getting user info")
            print(f"[GOOGLE USER INFO] Status Code: {e.response.status_code if e.response else 'None'}")
            print(f"[GOOGLE USER INFO] Error Response: {error_data}")
            print(f"[GOOGLE USER INFO] ===== REQUEST FAILED =====")
            return None
        except Exception as e:
            print(f"[GOOGLE USER INFO] ✗ Error getting Google user info: {type(e).__name__}: {e}")
            import traceback
            print(f"[GOOGLE USER INFO] Traceback: {traceback.format_exc()}")
            print(f"[GOOGLE USER INFO] ===== REQUEST FAILED =====")
            return None
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str = None) -> Optional[str]:
        """Exchange authorization code for access token"""
        print(f"\n[TOKEN EXCHANGE] ===== REQUEST START =====")
        redirect_uri = redirect_uri or self.redirect_uri
        masked_client_id = f"{self.client_id[:20]}..." if self.client_id and len(self.client_id) > 20 else self.client_id
        masked_client_secret = "***" if self.client_secret else "None"
        
        print(f"[TOKEN EXCHANGE] Endpoint: POST https://oauth2.googleapis.com/token")
        print(f"[TOKEN EXCHANGE] Request Parameters:")
        print(f"[TOKEN EXCHANGE]   - client_id: {masked_client_id} (full length: {len(self.client_id) if self.client_id else 0})")
        print(f"[TOKEN EXCHANGE]   - client_secret: {masked_client_secret} (configured: {'Yes' if self.client_secret else 'No'})")
        print(f"[TOKEN EXCHANGE]   - code: {code[:30]}... (length: {len(code) if code else 0})")
        print(f"[TOKEN EXCHANGE]   - grant_type: authorization_code")
        print(f"[TOKEN EXCHANGE]   - redirect_uri: {redirect_uri}")
        print(f"[TOKEN EXCHANGE]   - default redirect_uri: {self.redirect_uri}")
        print(f"[TOKEN EXCHANGE]   - redirect_uri match: {redirect_uri == self.redirect_uri}")
        
        if not self.client_id:
            print(f"[TOKEN EXCHANGE] ✗ ERROR: client_id is not configured!")
            print(f"[TOKEN EXCHANGE] ===== REQUEST FAILED =====")
            return None
        
        if not self.client_secret:
            print(f"[TOKEN EXCHANGE] ✗ ERROR: client_secret is not configured!")
            print(f"[TOKEN EXCHANGE] ===== REQUEST FAILED =====")
            return None
        
        print(f"[TOKEN EXCHANGE] Making HTTP POST request...")
        
        try:
            async with httpx.AsyncClient() as client:
                request_data = {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri
                }
                
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data=request_data
                )
                
                print(f"[TOKEN EXCHANGE] ===== RESPONSE RECEIVED =====")
                print(f"[TOKEN EXCHANGE] Status Code: {response.status_code}")
                print(f"[TOKEN EXCHANGE] Response Headers:")
                for key, value in response.headers.items():
                    print(f"[TOKEN EXCHANGE]   - {key}: {value}")
                
                if response.status_code != 200:
                    error_data = response.text
                    print(f"[TOKEN EXCHANGE] ✗ Token exchange failed")
                    print(f"[TOKEN EXCHANGE] Error Response Body: {error_data}")
                    try:
                        error_json = response.json()
                        print(f"[TOKEN EXCHANGE] Error JSON:")
                        for key, value in error_json.items():
                            print(f"[TOKEN EXCHANGE]   - {key}: {value}")
                        
                        error_type = error_json.get("error", "unknown")
                        error_description = error_json.get("error_description", "No description")
                        print(f"[TOKEN EXCHANGE] Error Analysis:")
                        print(f"[TOKEN EXCHANGE]   - error_type: {error_type}")
                        print(f"[TOKEN EXCHANGE]   - error_description: {error_description}")
                        
                        # Common errors:
                        if error_type == "invalid_grant":
                            print(f"[TOKEN EXCHANGE] This usually means:")
                            print(f"[TOKEN EXCHANGE]   - Code already used or expired")
                            print(f"[TOKEN EXCHANGE]   - redirect_uri mismatch")
                            print(f"[TOKEN EXCHANGE]   - client_id/client_secret mismatch")
                        elif error_type == "redirect_uri_mismatch":
                            print(f"[TOKEN EXCHANGE] redirect_uri mismatch! Expected: {redirect_uri}")
                        elif error_type == "invalid_request":
                            if "OAuth 2.0 policy" in error_description or "doesn't comply" in error_description:
                                print(f"[TOKEN EXCHANGE] ⚠️  CRITICAL: App doesn't comply with Google OAuth 2.0 policy!")
                                print(f"[TOKEN EXCHANGE] This usually means:")
                                print(f"[TOKEN EXCHANGE]   1. Custom URL scheme '{redirect_uri}' not registered in Google Cloud Console")
                                print(f"[TOKEN EXCHANGE]   2. App is in testing mode and needs test users added")
                                print(f"[TOKEN EXCHANGE]   3. App needs to be verified/published")
                                print(f"[TOKEN EXCHANGE] SOLUTIONS:")
                                print(f"[TOKEN EXCHANGE]   → Register '{redirect_uri}' in Google Cloud Console → Credenziali → OAuth 2.0 Client ID")
                                print(f"[TOKEN EXCHANGE]   → Add test users in OAuth consent screen (if in testing mode)")
                                print(f"[TOKEN EXCHANGE]   → See docs/GOOGLE_OAUTH_REACT_NATIVE.md for detailed instructions")
                                print(f"[TOKEN EXCHANGE]   → Alternative: Use /auth/google/verify-id-token endpoint (Google Sign-In SDK)")
                    except:
                        print(f"[TOKEN EXCHANGE] Could not parse error as JSON, raw response: {error_data}")
                    print(f"[TOKEN EXCHANGE] ===== REQUEST FAILED =====")
                    return None
                
                response.raise_for_status()
                data = response.json()
                
                print(f"[TOKEN EXCHANGE] Response Body (JSON):")
                access_token = data.get("access_token")
                refresh_token = data.get("refresh_token")
                expires_in = data.get("expires_in")
                token_type = data.get("token_type")
                print(f"[TOKEN EXCHANGE]   - access_token: {'Present' if access_token else 'Missing'} (length: {len(access_token) if access_token else 0})")
                print(f"[TOKEN EXCHANGE]   - refresh_token: {'Present' if refresh_token else 'Missing'}")
                print(f"[TOKEN EXCHANGE]   - expires_in: {expires_in}")
                print(f"[TOKEN EXCHANGE]   - token_type: {token_type}")
                
                if access_token:
                    print(f"[TOKEN EXCHANGE] ✓ Token exchange successful")
                    print(f"[TOKEN EXCHANGE] ===== REQUEST SUCCESS =====")
                else:
                    print(f"[TOKEN EXCHANGE] ✗ No access_token in response")
                    print(f"[TOKEN EXCHANGE] Full response data: {data}")
                    print(f"[TOKEN EXCHANGE] ===== REQUEST FAILED =====")
                
                return access_token
        except httpx.HTTPStatusError as e:
            error_data = e.response.text if e.response else "No response"
            print(f"[TOKEN EXCHANGE] ✗ HTTP error exchanging code for token")
            print(f"[TOKEN EXCHANGE] Status Code: {e.response.status_code if e.response else 'None'}")
            print(f"[TOKEN EXCHANGE] Error Response: {error_data}")
            try:
                error_json = e.response.json()
                print(f"[TOKEN EXCHANGE] Error JSON: {error_json}")
            except:
                pass
            print(f"[TOKEN EXCHANGE] ===== REQUEST FAILED =====")
            return None
        except Exception as e:
            print(f"[TOKEN EXCHANGE] ✗ Error exchanging code for token: {type(e).__name__}: {e}")
            import traceback
            print(f"[TOKEN EXCHANGE] Traceback: {traceback.format_exc()}")
            print(f"[TOKEN EXCHANGE] ===== REQUEST FAILED =====")
            return None
    
    async def authenticate_google_user(self, code: str, redirect_uri: str = None) -> Optional[Dict[str, Any]]:
        """Authenticate user with Google OAuth"""
        print(f"\n{'='*80}")
        print(f"[AUTHENTICATE GOOGLE USER] ===== PROCESS START =====")
        print(f"[AUTHENTICATE GOOGLE USER] Step 1: Exchange code for access token")
        print(f"{'='*80}\n")
        
        # Exchange code for access token
        access_token = await self.exchange_code_for_token(code, redirect_uri)
        if not access_token:
            print(f"[AUTHENTICATE GOOGLE USER] ✗ Failed to exchange code for token - aborting")
            print(f"[AUTHENTICATE GOOGLE USER] ===== PROCESS FAILED =====")
            return None
        
        print(f"\n[AUTHENTICATE GOOGLE USER] Step 2: Get user info from Google")
        print(f"{'='*80}\n")
        
        # Get user info from Google
        google_user = await self.get_google_user_info(access_token)
        if not google_user:
            print(f"[AUTHENTICATE GOOGLE USER] ✗ Failed to get user info from Google - aborting")
            print(f"[AUTHENTICATE GOOGLE USER] ===== PROCESS FAILED =====")
            return None
        
        if not google_user.verified_email:
            print(f"[AUTHENTICATE GOOGLE USER] ✗ User email not verified: {google_user.email}")
            print(f"[AUTHENTICATE GOOGLE USER] ===== PROCESS FAILED =====")
            return None
        
        print(f"\n[AUTHENTICATE GOOGLE USER] Step 3: Check if user exists in database")
        print(f"[AUTHENTICATE GOOGLE USER]   - Searching for email: {google_user.email}")
        
        # Check if user exists
        user = self.db.execute(
            select(User).where(User.email == google_user.email)
        ).scalar_one_or_none()
        
        if not user:
            print(f"[AUTHENTICATE GOOGLE USER]   - User not found, creating new user...")
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
            print(f"[AUTHENTICATE GOOGLE USER]   - ✓ New user created: {user.email} (id: {user.id})")
        else:
            print(f"[AUTHENTICATE GOOGLE USER]   - ✓ User exists: {user.email} (id: {user.id})")
        
        print(f"\n[AUTHENTICATE GOOGLE USER] Step 4: Create or update OAuth account")
        
        # Create or update OAuth account
        oauth_account = self.db.execute(
            select(OAuthAccount).where(
                OAuthAccount.user_id == user.id,
                OAuthAccount.provider == "google"
            )
        ).scalar_one_or_none()
        
        if not oauth_account:
            print(f"[AUTHENTICATE GOOGLE USER]   - OAuth account not found, creating new one...")
            oauth_account = OAuthAccount(
                user_id=user.id,
                provider="google",
                provider_account_id=google_user.id,
                access_token=access_token,
                token_expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            self.db.add(oauth_account)
            print(f"[AUTHENTICATE GOOGLE USER]   - ✓ New OAuth account created")
        else:
            print(f"[AUTHENTICATE GOOGLE USER]   - OAuth account exists, updating access token...")
            oauth_account.access_token = access_token
            oauth_account.token_expires_at = datetime.utcnow() + timedelta(hours=1)
            print(f"[AUTHENTICATE GOOGLE USER]   - ✓ OAuth account updated")
        
        self.db.commit()
        
        print(f"\n[AUTHENTICATE GOOGLE USER] Step 5: Update last login")
        # Update last login
        user.last_login = datetime.utcnow()
        self.db.commit()
        print(f"[AUTHENTICATE GOOGLE USER]   - ✓ Last login updated: {user.last_login}")
        
        print(f"\n[AUTHENTICATE GOOGLE USER] Step 6: Create JWT tokens")
        # Create JWT tokens
        token_data = {"sub": str(user.id), "email": user.email}
        print(f"[AUTHENTICATE GOOGLE USER]   - Token payload: {token_data}")
        
        access_token_jwt = create_access_token(data=token_data)
        refresh_token_jwt = create_refresh_token(data=token_data)
        
        tokens = {
            "access_token": access_token_jwt,
            "refresh_token": refresh_token_jwt,
            "token_type": "bearer"
        }
        
        print(f"[AUTHENTICATE GOOGLE USER]   - ✓ JWT tokens created")
        print(f"[AUTHENTICATE GOOGLE USER]     - access_token length: {len(access_token_jwt)}")
        print(f"[AUTHENTICATE GOOGLE USER]     - refresh_token length: {len(refresh_token_jwt)}")
        
        print(f"\n[AUTHENTICATE GOOGLE USER] ===== PROCESS SUCCESS =====")
        print(f"[AUTHENTICATE GOOGLE USER] Final result:")
        print(f"[AUTHENTICATE GOOGLE USER]   - user_id: {user.id}")
        print(f"[AUTHENTICATE GOOGLE USER]   - email: {user.email}")
        print(f"[AUTHENTICATE GOOGLE USER]   - tokens: access_token + refresh_token")
        print(f"{'='*80}\n")
        
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
        print(f"\n[GENERATE AUTH URL] ===== PROCESS START =====")
        
        # Use provided redirect_uri or default from settings
        use_redirect_uri = redirect_uri or self.redirect_uri
        
        masked_client_id = f"{self.client_id[:20]}..." if self.client_id and len(self.client_id) > 20 else self.client_id
        print(f"[GENERATE AUTH URL] Configuration:")
        print(f"[GENERATE AUTH URL]   - client_id: {masked_client_id} (full length: {len(self.client_id) if self.client_id else 0})")
        print(f"[GENERATE AUTH URL]   - redirect_uri (provided): {redirect_uri}")
        print(f"[GENERATE AUTH URL]   - redirect_uri (default): {self.redirect_uri}")
        print(f"[GENERATE AUTH URL]   - redirect_uri (using): {use_redirect_uri}")
        print(f"[GENERATE AUTH URL]   - state: {state[:50] if state else 'None'}... (length: {len(state) if state else 0})")
        if redirect_uri:
            print(f"[GENERATE AUTH URL]   - Custom redirect_uri provided (for React Native)")
        
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
        
        print(f"[GENERATE AUTH URL] URL Parameters:")
        for key, value in params.items():
            if key == "client_id":
                print(f"[GENERATE AUTH URL]   - {key}: {masked_client_id}...")
            elif key == "state":
                print(f"[GENERATE AUTH URL]   - {key}: {value[:50]}... (length: {len(value)})")
            else:
                print(f"[GENERATE AUTH URL]   - {key}: {value}")
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"
        
        print(f"[GENERATE AUTH URL] Generated URL (length: {len(auth_url)}):")
        print(f"[GENERATE AUTH URL]   {auth_url[:200]}...")
        print(f"[GENERATE AUTH URL] ===== PROCESS SUCCESS =====")
        
        return auth_url
    
    async def verify_google_id_token(self, id_token_string: str) -> Optional[Dict[str, Any]]:
        """Verify Google ID token and authenticate user (for React Native)"""
        print(f"[Google ID Token] ===== VERIFICATION START =====")
        print(f"[Google ID Token] Token length: {len(id_token_string) if id_token_string else 0}")
        print(f"[Google ID Token] Using client_id: {self.client_id[:20] if self.client_id else 'None'}...")
        
        # Get list of allowed client IDs
        allowed_client_ids = [self.client_id] if self.client_id else []
        
        # Add additional client IDs from settings (for Android/iOS apps)
        if settings.google_additional_client_ids:
            additional_ids = [cid.strip() for cid in settings.google_additional_client_ids.split(",") if cid.strip()]
            allowed_client_ids.extend(additional_ids)
            print(f"[Google ID Token] Additional client IDs configured: {len(additional_ids)}")
        
        print(f"[Google ID Token] Allowed client IDs: {len(allowed_client_ids)}")
        
        try:
            # Verify the ID token - try each allowed client ID
            request = requests.Request()
            print(f"[Google ID Token] Verifying token with Google...")
            
            id_info = None
            last_error = None
            
            for client_id in allowed_client_ids:
                try:
                    print(f"[Google ID Token] Trying client_id: {client_id[:30]}...")
                    id_info = id_token.verify_oauth2_token(
                        id_token_string, 
                        request, 
                        client_id
                    )
                    print(f"[Google ID Token] ✓ Token verified successfully with client_id: {client_id[:30]}...")
                    break
                except Exception as e:
                    last_error = e
                    print(f"[Google ID Token] ✗ Failed with client_id {client_id[:30]}...: {type(e).__name__}")
                    continue
            
            if not id_info:
                # Extract audience from error if possible
                error_msg = str(last_error) if last_error else "Unknown error"
                print(f"[Google ID Token] ✗ All client IDs failed. Last error: {error_msg}")
                
                # Try to extract audience from token to help debugging
                try:
                    import jwt as pyjwt
                    decoded = pyjwt.decode(id_token_string, options={"verify_signature": False})
                    token_audience = decoded.get("aud")
                    print(f"[Google ID Token] Token audience: {token_audience}")
                    print(f"[Google ID Token] Expected audiences: {[cid[:50] + '...' if len(cid) > 50 else cid for cid in allowed_client_ids]}")
                except Exception as decode_error:
                    print(f"[Google ID Token] Could not decode token for debugging: {decode_error}")
                
                raise ValueError(f"Token verification failed. {error_msg}")
            
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
