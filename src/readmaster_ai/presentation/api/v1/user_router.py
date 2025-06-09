"""
API Router for User related operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

# Application Layer
from readmaster_ai.application.use_cases.user_use_cases import CreateUserUseCase, GetUserProfileUseCase, UpdateUserProfileUseCase

# Presentation Layer
from readmaster_ai.presentation.schemas.user_schemas import UserCreateRequest, UserResponse, UserUpdateRequest

# Infrastructure Layer (for DI)
from readmaster_ai.infrastructure.database.config import get_db
from readmaster_ai.domain.repositories.user_repository import UserRepository # Abstract
from readmaster_ai.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl # Concrete

# Shared Layer
from readmaster_ai.shared.exceptions import ApplicationException

# For get_current_user dependency and DomainUser type hint
from readmaster_ai.domain.entities.user import User as DomainUser
from readmaster_ai.presentation.dependencies.auth_deps import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

# Dependency Injection for UserRepository
def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    """Provides a UserRepository implementation."""
    return UserRepositoryImpl(session)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: UserCreateRequest,
    # db: AsyncSession = Depends(get_db), # Session is now encapsulated within get_user_repository
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Registers a new user in the system.
    """
    create_user_use_case = CreateUserUseCase(user_repo=user_repo)
    try:
        created_user_domain = await create_user_use_case.execute(request)

        # Convert domain entity to response model.
        # This relies on UserResponse.Config.from_attributes = True (Pydantic v2)
        # or UserResponse.Config.orm_mode = True (Pydantic v1)
        # and that the field names match between DomainUser and UserResponse.
        return UserResponse.model_validate(created_user_domain)
    except ApplicationException as e:
        if e.status_code == 409: # Specific case for duplicate email
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
        # Handle other application-specific errors that might be raised
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        # Log the exception e here for debugging purposes
        # import logging
        # logging.exception("Unexpected error during user registration:")
        print(f"Unexpected error: {e}") # Basic print for now
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration."
        )

# Example of a protected endpoint
@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: DomainUser = Depends(get_current_user)):
    """
    Get current authenticated user's details.
    """
    # The get_current_user dependency already returns the DomainUser.
    # For now, directly validating the current_user from token is sufficient.
    # If more complex logic or data fetching for the profile is needed,
    # a GetUserProfileUseCase could be instantiated and used here.
    # Example:
    # get_profile_use_case = GetUserProfileUseCase(user_repo=Depends(get_user_repository)) # Pass repo via Depends
    # user_profile = await get_profile_use_case.execute(current_user)
    # return UserResponse.model_validate(user_profile)
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_users_me(
    update_data: UserUpdateRequest,
    current_user: DomainUser = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository) # For UpdateUserProfileUseCase
):
    """
    Update current authenticated user's profile.
    """
    update_user_profile_use_case = UpdateUserProfileUseCase(user_repo=user_repo)
    try:
        updated_user = await update_user_profile_use_case.execute(current_user, update_data)
        return UserResponse.model_validate(updated_user)
    except ApplicationException as e:
        if e.status_code == 409: # Specific case for duplicate email during update
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
        # Handle other application-specific errors (e.g., validation from use case if any)
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        # Log the error e for debugging purposes
        # import logging
        # logging.exception("Unexpected error updating user profile:")
        print(f"Unexpected error updating profile: {e}") # Basic print for now
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating profile."
        )
