# Custom application exceptions will be defined here.

class ApplicationException(Exception):
    """Base class for application-specific exceptions."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class NotFoundException(ApplicationException):
    """Raised when a resource is not found."""
    def __init__(self, resource_name: str, resource_id: any):
        message = f"{resource_name} with ID '{resource_id}' not found."
        super().__init__(message, status_code=404)

class ForbiddenException(ApplicationException):
    """Raised for forbidden actions."""
    def __init__(self, message="Forbidden", status_code=403):
        super().__init__(message, status_code=status_code)

class UnauthorizedException(ApplicationException):
    """Raised for authorization failures."""
    def __init__(self, message: str = "Not authorized to perform this action."):
        super().__init__(message, status_code=403) # 403 Forbidden is often more appropriate

class AuthenticationException(ApplicationException):
    """Raised for authentication failures."""
    def __init__(self, message: str = "Invalid authentication credentials."):
        super().__init__(message, status_code=401)

class ValidationException(ApplicationException):
    """Raised for data validation errors."""
    def __init__(self, message: str = "Input data validation failed.", errors: dict = None):
        self.errors = errors
        super().__init__(message, status_code=422) # Unprocessable Entity for validation

__all__ = ['ApplicationException', 'NotFoundException', 'ForbiddenException']
