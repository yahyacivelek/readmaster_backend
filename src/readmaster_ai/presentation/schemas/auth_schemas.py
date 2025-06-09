"""
Pydantic schemas for authentication-related request and response models.
"""
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    """
    Schema for user login request. Requires email and password.
    """
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """
    Schema for the response when tokens are issued (e.g., after login).
    Includes access token, refresh token, and token type.
    """
    access_token: str
    refresh_token: str # Note: In some flows, refresh token might be sent via HttpOnly cookie for security.
    token_type: str = "bearer"

# Future schemas might include:
# class RefreshTokenRequest(BaseModel):
#     refresh_token: str
#
# class PasswordResetRequest(BaseModel):
# email: EmailStr
#
# class SetNewPasswordRequest(BaseModel):
# token: str # Password reset token
# new_password: str
