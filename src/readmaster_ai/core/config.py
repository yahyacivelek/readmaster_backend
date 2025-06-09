"""
Core configuration settings for the Readmaster.ai application.
Includes settings for JWT, database, etc.
"""
import os
from datetime import timedelta

class JWTSettings:
    """
    Configuration settings for JSON Web Tokens (JWT).
    It's crucial to manage SECRET_KEY securely, ideally from environment variables
    or a secrets management system, not hardcoded in production.
    """
    # IMPORTANT: In a real application, get this from environment variables or a secrets manager!
    # For local development, this default is provided as an example.
    # Consider using libraries like Pydantic Settings for more robust config management.
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "a_very_secret_key_that_should_be_long_and_random_for_dev_only")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    @property
    def ACCESS_TOKEN_EXPIRE_DELTA(self) -> timedelta:
        """Timedelta for access token expiry."""
        return timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)

    @property
    def REFRESH_TOKEN_EXPIRE_DELTA(self) -> timedelta:
        """Timedelta for refresh token expiry."""
        return timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)

# Global instance of JWT settings
jwt_settings = JWTSettings()

# Future: You might add other configurations here, e.g., DatabaseSettings, EmailSettings, etc.
# from pydantic_settings import BaseSettings
# class Settings(BaseSettings):
#     jwt: JWTSettings = JWTSettings()
#     # db_url: str = Field(default=..., env="DATABASE_URL")
#     # ...
# settings = Settings()
