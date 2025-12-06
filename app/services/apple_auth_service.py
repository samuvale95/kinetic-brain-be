import httpx
import jwt
import time
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.config import settings
from app.models.user import User, OAuthAccount
from app.schemas.user import AppleUserInfo
from app.utils.security import create_access_token, create_refresh_token
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization


class AppleAuthService:
    def __init__(self, db: Session):
        self.db = db
        self.client_id = settings.apple_client_id
        self.team_id = settings.apple_team_id
        self.key_id = settings.apple_key_id
        self.private_key = settings.apple_private_key
        self.redirect_uri = settings.apple_redirect_uri
        
        # Log configuration (masked for security)
        if self.client_id:
            masked_id = f"{self.client_id[:20]}..." if len(self.client_id) > 20 else self.client_id
            print(f"[Apple OAuth] Service initialized with client_id: {masked_id}")
        else:
            print("[Apple OAuth] WARNING: No client_id configured!")
    
    def _generate_client_secret(self) -> Optional[str]:
        """Generate JWT client secret for Apple OAuth"""
        try:
            if not all([self.team_id, self.client_id, self.key_id, self.private_key]):
                print("[Apple OAuth] Missing required configuration for client secret generation")
                return None
            
            # Load private key
            # Handle both literal \n and actual newlines
            private_key_str = self.private_key
            if '\\n' in private_key_str:
                # Replace literal \n with actual newlines
                private_key_str = private_key_str.replace('\\n', '\n')
            
            try:
                # Load as PEM format
                private_key_obj = serialization.load_pem_private_key(
                    private_key_str.encode('utf-8'),
                    password=None
                )
            except Exception as e:
                print(f"[Apple OAuth] Error loading private key: {e}")
                return None
            
            # Create JWT headers
            headers = {
                "alg": "ES256",
                "kid": self.key_id
            }
            
            # Create JWT payload
            now = int(time.time())
            payload = {
                "iss": self.team_id,
                "iat": now,
                "exp": now + 3600,  # 1 hour expiration
                "aud": "https://appleid.apple.com",
                "sub": self.client_id
            }
            
            # Generate JWT
            client_secret = jwt.encode(
                payload,
                private_key_obj,
                algorithm="ES256",
                headers=headers
            )
            
            return client_secret
        except Exception as e:
            print(f"[Apple OAuth] Error generating client secret: {e}")
            return None
    
    async def get_apple_user_info(self, id_token: str) -> Optional[AppleUserInfo]:
        """Get user information from Apple Identity Token"""
        try:
            # Decode token without verification first to get claims
            unverified = jwt.decode(id_token, options={"verify_signature": False})
            
            # Extract user information
            apple_user_id = unverified.get("sub")
            email = unverified.get("email")
            email_verified = unverified.get("email_verified", False)
            
            # Name is only available on first login
            name = None
            if "name" in unverified:
                name_data = unverified.get("name", {})
                if isinstance(name_data, dict):
                    first_name = name_data.get("firstName", "")
                    last_name = name_data.get("lastName", "")
                    name = f"{first_name} {last_name}".strip() or None
            
            return AppleUserInfo(
                id=apple_user_id,
                email=email or "",  # Email might be empty if using private relay
                name=name,
                email_verified=email_verified
            )
        except Exception as e:
            print(f"[Apple OAuth] Error getting user info from token: {e}")
            return None
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str = None) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token and ID token"""
        try:
            redirect_uri = redirect_uri or self.redirect_uri
            client_secret = self._generate_client_secret()
            
            if not client_secret:
                print("[Apple OAuth] Failed to generate client secret")
                return None
            
            masked_client_id = f"{self.client_id[:20]}..." if self.client_id and len(self.client_id) > 20 else self.client_id
            print(f"[Apple OAuth] Exchanging code for token")
            print(f"[Apple OAuth]   - redirect_uri: {redirect_uri}")
            print(f"[Apple OAuth]   - client_id: {masked_client_id}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://appleid.apple.com/auth/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code != 200:
                    error_data = response.text
                    print(f"[Apple OAuth] Token exchange failed: {response.status_code} - {error_data}")
                    return None
                
                response.raise_for_status()
                data = response.json()
                
                id_token = data.get("id_token")
                access_token = data.get("access_token")
                refresh_token = data.get("refresh_token")
                
                if not id_token:
                    print(f"[Apple OAuth] No id_token in response: {data}")
                    return None
                
                print(f"[Apple OAuth] Token exchange successful")
                return {
                    "id_token": id_token,
                    "access_token": access_token,
                    "refresh_token": refresh_token
                }
        except httpx.HTTPStatusError as e:
            error_data = e.response.text if e.response else "No response"
            print(f"[Apple OAuth] HTTP error exchanging code for token: {e.response.status_code} - {error_data}")
            return None
        except Exception as e:
            print(f"[Apple OAuth] Error exchanging code for token: {type(e).__name__}: {e}")
            return None
    
    async def verify_apple_identity_token(self, id_token_string: str) -> Optional[Dict[str, Any]]:
        """Verify Apple Identity Token and authenticate user (for React Native and web)"""
        try:
            # First, decode without verification to get the key ID
            unverified = jwt.decode(id_token_string, options={"verify_signature": False})
            kid = unverified.get("kid")
            
            if not kid:
                print("[Apple OAuth] No 'kid' in token header")
                return None
            
            # Get Apple's public keys
            async with httpx.AsyncClient() as client:
                jwks_response = await client.get("https://appleid.apple.com/auth/keys")
                jwks_response.raise_for_status()
                jwks = jwks_response.json()
            
            # Find the matching key and verify the token
            decoded_token = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    try:
                        # Convert JWK to cryptography public key
                        from cryptography.hazmat.primitives.asymmetric import ec
                        from cryptography.hazmat.backends import default_backend
                        import base64
                        
                        x = base64.urlsafe_b64decode(key["x"] + "==")
                        y = base64.urlsafe_b64decode(key["y"] + "==")
                        
                        public_numbers = ec.EllipticCurvePublicNumbers(
                            int.from_bytes(x, "big"),
                            int.from_bytes(y, "big"),
                            ec.SECP256R1()
                        )
                        public_key = public_numbers.public_key(default_backend())
                        
                        # Verify token using the public key object directly
                        # PyJWT with ES256 accepts cryptography key objects
                        decoded_token = jwt.decode(
                            id_token_string,
                            public_key,
                            algorithms=["ES256"],
                            audience=self.client_id,
                            issuer="https://appleid.apple.com"
                        )
                        break
                    except jwt.ExpiredSignatureError:
                        print("[Apple OAuth] Token has expired")
                        return None
                    except jwt.InvalidTokenError as e:
                        # Try next key if this one doesn't work
                        print(f"[Apple OAuth] Token verification failed with this key: {e}")
                        continue
            
            if not decoded_token:
                print(f"[Apple OAuth] No matching public key found or token verification failed for kid: {kid}")
                return None
            
            # Extract user information
            apple_user_id = decoded_token.get("sub")
            email = decoded_token.get("email")
            email_verified = decoded_token.get("email_verified", False)
            
            # Name is only available on first login (in user object, not token)
            name = None
            if "name" in decoded_token:
                name_data = decoded_token.get("name", {})
                if isinstance(name_data, dict):
                    first_name = name_data.get("firstName", "")
                    last_name = name_data.get("lastName", "")
                    name = f"{first_name} {last_name}".strip() or None
            
            # Handle private relay email
            is_private_email = email and "privaterelay.appleid.com" in email if email else False
            
            # Check if user exists by email or by OAuth account
            user = None
            if email and not is_private_email:
                user = self.db.execute(
                    select(User).where(User.email == email)
                ).scalar_one_or_none()
            
            # If not found by email, check by OAuth account
            if not user:
                oauth_account = self.db.execute(
                    select(OAuthAccount).where(
                        OAuthAccount.provider == "apple",
                        OAuthAccount.provider_account_id == apple_user_id
                    )
                ).scalar_one_or_none()
                
                if oauth_account:
                    user = self.db.execute(
                        select(User).where(User.id == oauth_account.user_id)
                    ).scalar_one_or_none()
            
            if not user:
                # Create new user
                # Use email if available, otherwise use a placeholder
                user_email = email if email and not is_private_email else f"apple_{apple_user_id}@privaterelay.appleid.com"
                user = User(
                    email=user_email,
                    name=name or user_email.split("@")[0],
                    avatar_url=None,  # Apple doesn't provide avatar URL
                    auth_provider="apple",
                    is_verified=True,
                    is_active=True
                )
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
            else:
                # Update user info if needed
                if name and not user.name:
                    user.name = name
                # Update auth provider if needed
                if user.auth_provider != "apple":
                    user.auth_provider = "apple"
            
            # Create or update OAuth account
            oauth_account = self.db.execute(
                select(OAuthAccount).where(
                    OAuthAccount.user_id == user.id,
                    OAuthAccount.provider == "apple"
                )
            ).scalar_one_or_none()
            
            if not oauth_account:
                oauth_account = OAuthAccount(
                    user_id=user.id,
                    provider="apple",
                    provider_account_id=apple_user_id,
                    access_token=None,  # ID token doesn't provide access token
                    token_expires_at=None
                )
                self.db.add(oauth_account)
            else:
                # Update provider account ID if changed
                if oauth_account.provider_account_id != apple_user_id:
                    oauth_account.provider_account_id = apple_user_id
            
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
        except Exception as e:
            print(f"[Apple OAuth] Unexpected error verifying Identity token: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def authenticate_apple_user(self, code: str, redirect_uri: str = None) -> Optional[Dict[str, Any]]:
        """Authenticate user with Apple OAuth (web flow)"""
        # Exchange code for tokens
        token_data = await self.exchange_code_for_token(code, redirect_uri)
        if not token_data or not token_data.get("id_token"):
            return None
        
        # Verify Identity Token and get user info
        return await self.verify_apple_identity_token(token_data["id_token"])
    
    def get_apple_auth_url(self, state: str = None) -> str:
        """Generate Apple OAuth authorization URL"""
        masked_client_id = f"{self.client_id[:20]}..." if self.client_id and len(self.client_id) > 20 else self.client_id
        print(f"[Apple OAuth] Generating auth URL with client_id: {masked_client_id}")
        print(f"[Apple OAuth] Using redirect_uri: {self.redirect_uri}")
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "name email",
            "response_mode": "form_post"  # Apple recommends form_post for web
        }
        
        if state:
            params["state"] = state
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://appleid.apple.com/auth/authorize?{query_string}"
