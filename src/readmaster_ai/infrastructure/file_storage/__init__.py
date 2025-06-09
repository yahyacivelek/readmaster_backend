"""
Infrastructure package for File Storage services.

This package contains concrete implementations of the FileStorageInterface
defined in the application layer. These implementations interact with
specific file storage backends like local disk (for development/testing),
Google Cloud Storage, AWS S3, etc.

The choice of which implementation to use can be determined by
configuration settings.
"""

# Export concrete implementations if needed for direct instantiation elsewhere,
# though typically they are resolved via a factory or DI based on configuration.
from .local_storage import LocalFileStorageService

__all__ = [
    "LocalFileStorageService",
    # Add other storage service implementations here (e.g., "GCSFileStorageService")
]
