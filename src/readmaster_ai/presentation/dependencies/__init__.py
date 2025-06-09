"""
FastAPI dependencies for the Readmaster.ai application.

This package contains reusable functions that can be injected into
FastAPI path operation functions to handle common tasks such as:
- Authenticating users and extracting current user information.
- Managing database sessions.
- Enforcing permissions or role-based access control.
- Handling pagination parameters.

These dependencies help keep the API endpoint logic clean and focused
on the specific task of the endpoint by abstracting away these
cross-cutting concerns.
"""

from .auth_deps import get_current_user, oauth2_scheme, require_role # Added require_role

__all__ = [
    "get_current_user",
    "oauth2_scheme",
    "require_role", # Export require_role
]
