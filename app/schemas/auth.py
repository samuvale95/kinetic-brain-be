from pydantic import BaseModel, Field, EmailStr
from typing import Optional


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token to exchange for new access token")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address to send password reset link")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Password reset token from email")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")
