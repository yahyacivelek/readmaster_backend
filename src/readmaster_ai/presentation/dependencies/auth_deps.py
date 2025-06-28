"""
Authentication dependencies for FastAPI.
Provides a way to protect endpoints and get the current authenticated user.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError # Though auth_service.decode_token handles it, good for context
from uuid import UUID
from builtins import ValueError as InvalidUUIDError

# Application Layer
from readmaster_ai.application.services.auth_service import AuthenticationService

# Domain Layer
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.repositories.user_repository import UserRepository
from readmaster_ai.domain.value_objects.common_enums import UserRole # For role-based access if added

# Infrastructure Layer
from readmaster_ai.infrastructure.database.config import get_db
from readmaster_ai.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl

# Core (not directly used here but auth_service uses it)
# from readmaster_ai.core.config import jwt_settings

# OAuth2PasswordBearer scheme:
# - tokenUrl: The URL where the client (e.g., frontend) can send username and password to get a token.
#   This should match the login endpoint.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Dependency to get UserRepository (same as in routers)
def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    """Provides a UserRepository implementation."""
    return UserRepositoryImpl(session)

# Dependency to get AuthenticationService (same as in auth_router)
def get_auth_service(user_repo: UserRepository = Depends(get_user_repository)) -> AuthenticationService:
    """Provides an AuthenticationService instance."""
    return AuthenticationService(user_repo)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthenticationService = Depends(get_auth_service),
    # user_repo is needed to fetch the user details from DB after validating token.
    # Alternatively, if all necessary user info is in the token (not recommended for sensitive data),
    # user_repo might not be needed here, but fetching fresh user data is generally safer.
    user_repo: UserRepository = Depends(get_user_repository)
) -> DomainUser:
    """
    FastAPI dependency to get the current authenticated user from a JWT token.
    Validates the token, extracts user ID, and fetches the user from the database.

    Raises:
        HTTPException (401): If authentication fails (e.g., invalid token, user not found).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"}, # Standard challenge header
    )

    token_data = await auth_service.decode_token(token)
    if token_data is None:
        # This means token was invalid (expired, bad signature, etc.)
        raise credentials_exception

    user_id_str = token_data.get("sub")
    token_type = token_data.get("type")

    if user_id_str is None:
        # 'sub' claim is missing
        raise credentials_exception

    if token_type != "access":
        # Ensure the token is an access token, not a refresh token or other type
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Access token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(user_id_str)
    except (InvalidUUIDError, ValueError): # Catch if 'sub' is not a valid UUID string
        raise credentials_exception

    user = await user_repo.get_by_id(user_id)
    if user is None:
        # User ID from token does not correspond to an existing user (e.g., user deleted after token issuance)
        raise credentials_exception

    return user

# Example of a role-based access control dependency (optional, can be expanded)
# def require_role(required_role: UserRole):
#     """
#     Factory for a dependency that checks if the current user has the required role.
#     """
#     async def role_checker(current_user: DomainUser = Depends(get_current_user)) -> DomainUser:
#         if current_user.role != required_role:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN, # 403 Forbidden for authorization issues
#                 detail=f"Operation not permitted. User role '{current_user.role.value}' does not have required role '{required_role.value}'."
#             )
#         return current_user
#     return role_checker

# Example usage in a router:
    # from readmaster_ai.domain.value_objects.common_enums import UserRole # Already imported UserRole above
# @router.get("/admin-only", dependencies=[Depends(require_role(UserRole.ADMIN))])
# async def get_admin_info(current_user: DomainUser = Depends(get_current_user)):
#     return {"message": f"Hello Admin {current_user.email}"}

def require_role(required_role: UserRole):
    """
    Factory for a dependency that checks if the current user has the required role.
    """
    async def role_checker(current_user: DomainUser = Depends(get_current_user)) -> DomainUser:
        if current_user.role != required_role:
            # You might also want to check for a hierarchy, e.g., if admin can do everything a teacher can.
            # For now, direct role match.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, # 403 Forbidden for authorization issues
                detail=f"User role '{current_user.role.value}' is not authorized for this operation. Requires '{required_role.value}'."
            )
        return current_user
    return role_checker

async def get_current_active_student(current_user: DomainUser = Depends(get_current_user)) -> DomainUser:
    """
    Dependency to get the current authenticated user and ensure they are a student.
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. User must be a student."
        )
    if not current_user.is_active: # Assuming DomainUser has an 'is_active' field
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive."
        )
    return current_user
