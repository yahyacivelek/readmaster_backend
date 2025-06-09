"""
Defines the interface for file storage services.
This allows the application to interact with different file storage backends
(e.g., local, Google Cloud Storage, AWS S3) through a consistent interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple

class FileStorageInterface(ABC):
    """
    Abstract Base Class for file storage operations.
    Implementations of this interface will handle the specifics of interacting
    with the chosen storage backend.
    """
    @abstractmethod
    async def get_presigned_upload_url(
        self,
        blob_name: str,
        content_type: str = "audio/wav",
        expiration_seconds: int = 3600
    ) -> Tuple[str, Dict[str, str]]:
        """
        Generates a presigned URL that allows a client to upload a file directly
        to the storage backend.

        Args:
            blob_name: The desired name (path) of the object in the storage bucket.
                       This should be unique, e.g., "assessments_audio/<assessment_id>.<extension>".
            content_type: The MIME type of the file to be uploaded (e.g., "audio/wav", "audio/mpeg").
            expiration_seconds: The duration (in seconds) for which the presigned URL is valid.

        Returns:
            A tuple containing:
                - upload_url (str): The presigned URL for the PUT request.
                - required_fields (Dict[str, str]): Any additional fields or headers required by the
                                                    storage provider for the upload (e.g., for S3 presigned POSTs).
                                                    For GCS presigned PUT, this is often empty or just Content-Type.
        """
        pass

    @abstractmethod
    async def get_presigned_download_url(
        self,
        blob_name: str,
        expiration_seconds: int = 3600
    ) -> str:
        """
        Generates a presigned URL that allows a client to download a file directly
        from the storage backend.

        Args:
            blob_name: The name (path) of the object in the storage bucket.
            expiration_seconds: The duration (in seconds) for which the presigned URL is valid.

        Returns:
            The presigned URL for the GET request.
        """
        pass

    # Future methods could include:
    # @abstractmethod
    # async def delete_file(self, blob_name: str) -> bool:
    #     """Deletes a file from the storage."""
    #     pass
    #
    # @abstractmethod
    # async def get_file_metadata(self, blob_name: str) -> Dict[str, Any]:
    #     """Retrieves metadata for a file."""
    #     pass
