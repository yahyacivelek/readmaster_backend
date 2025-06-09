"""
API Router for Authentication related operations (login, token refresh, etc.).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

# Application Layer
from readmaster_ai.application.services.auth_service import AuthenticationService

# Presentation Layer
from readmaster_ai.presentation.schemas.auth_schemas import LoginRequest, TokenResponse

# Infrastructure Layer (for DI)
from readmaster_ai.infrastructure.database.config import get_db
from readmaster_ai.domain.repositories.user_repository import UserRepository # Abstract
from readmaster_ai.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl # Concrete

# Shared Layer
# from readmaster_ai.shared.exceptions import AuthenticationException # Handled by HTTPExceptions directly for now

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Dependency Injection for UserRepository (consistent with user_router)
def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    """Provides a UserRepository implementation."""
    return UserRepositoryImpl(session)

# Dependency Injection for AuthenticationService
def get_auth_service(user_repo: UserRepository = Depends(get_user_repository)) -> AuthenticationService:
    """Provides an AuthenticationService instance."""
    return AuthenticationService(user_repo)

@router.post("/login", response_model=TokenResponse)
async def login_for_access_token(
    form_data: LoginRequest,
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """
    Handles user login and issues access and refresh tokens upon successful authentication.
    """
    user = await auth_service.authenticate_user(email=form_data.email, password=form_data.password)
    if not user:
        # It's good practice to use a generic message for invalid credentials
        # to avoid confirming whether an email address is registered.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"}, # Standard for token-based authentication challenges
        )

    access_token = auth_service.create_access_token(user)
    refresh_token = auth_service.create_refresh_token(user)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

# Future endpoints:
# @router.post("/refresh", response_model=TokenResponse)
# async def refresh_access_token(refresh_request: RefreshTokenRequest, auth_service: AuthenticationService = Depends(get_auth_service)):
#     # Logic to validate refresh token and issue new access token
#     pass
#
# @router.post("/request-password-reset")
# async def request_password_reset( ... ):
#     pass
#
# @router.post("/reset-password")
# async def reset_password( ... ):
#     pass
