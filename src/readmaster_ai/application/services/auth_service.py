"""
AuthenticationService provides methods for user authentication and token management.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from uuid import UUID

from readmaster_ai.domain.entities.user import User as DomainUser
from readmaster_ai.domain.repositories.user_repository import UserRepository
from readmaster_ai.core.config import jwt_settings # Import JWT configuration
from readmaster_ai.shared.exceptions import AuthenticationException # ApplicationException could also be used

# Re-initialize pwd_context here as it's used by this service.
# Ensure this context is consistent with the one used during user registration (in CreateUserUseCase).
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthenticationService:
    """
    Handles user authentication, password verification, and JWT token generation/decoding.
    """
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifies a plain password against a hashed password."""
        return pwd_context.verify(plain_password, hashed_password)

    async def authenticate_user(self, email: str, password: str) -> Optional[DomainUser]:
        """
        Authenticates a user by email and password.

        Args:
            email: User's email.
            password: User's plain text password.

        Returns:
            The authenticated DomainUser if credentials are valid, otherwise None.
            (Consider raising specific exceptions for 'user not found' vs 'invalid password'
             for security reasons, or a generic AuthenticationException).
        """
        user = await self.user_repo.get_by_email(email)
        if not user:
            # Security consideration: Avoid confirming if email exists or not.
            # raise AuthenticationException("Invalid credentials.")
            return None
        if not self._verify_password(password, user.password_hash):
            # raise AuthenticationException("Invalid credentials.")
            return None
        return user

    def _create_token(self, data: Dict[str, Any], expires_delta: timedelta) -> str:
        """
        Creates a JWT token with the given data and expiry.
        Ensures all data is JSON serializable (e.g., UUID to str).
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})

        # Sanitize data for JWT encoding (e.g., UUID to str)
        for key, value in to_encode.items():
            if isinstance(value, UUID):
                to_encode[key] = str(value)
            elif hasattr(value, 'value') and not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                 # Attempt to get .value for enums or similar objects, if not already a primitive
                to_encode[key] = value.value


        encoded_jwt = jwt.encode(to_encode, jwt_settings.SECRET_KEY, algorithm=jwt_settings.ALGORITHM)
        return encoded_jwt

    def create_access_token(self, user: DomainUser) -> str:
        """Creates an access token for the given user."""
        access_token_data = {
            "sub": user.user_id, # 'sub' (subject) is standard for user identifier
            "email": user.email,
            "role": user.role, # user.role is already an enum, .value will be taken by _create_token if needed
            "type": "access", # Custom claim to differentiate token types
            # Add other claims as needed, e.g., "permissions": [...]
        }
        return self._create_token(access_token_data, jwt_settings.ACCESS_TOKEN_EXPIRE_DELTA)

    def create_refresh_token(self, user: DomainUser) -> str:
        """Creates a refresh token for the given user."""
        refresh_token_data = {
            "sub": user.user_id, # Subject is user_id
            "type": "refresh" # Custom claim
        }
        return self._create_token(refresh_token_data, jwt_settings.REFRESH_TOKEN_EXPIRE_DELTA)

    async def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decodes a JWT token.

        Args:
            token: The JWT token string.

        Returns:
            The token payload as a dictionary if valid and not expired, otherwise None.
        """
        try:
            payload = jwt.decode(token, jwt_settings.SECRET_KEY, algorithms=[jwt_settings.ALGORITHM])
            return payload
        except JWTError:
            # Catches various JWT errors: ExpiredSignatureError, InvalidTokenError, etc.
            # Log the error for debugging if necessary
            return None
