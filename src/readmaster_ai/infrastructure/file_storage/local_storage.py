"""
Mock/Local implementation of the FileStorageInterface for development purposes.
This service simulates presigned URL generation but does not actually handle
file uploads or serve files over HTTP itself. It provides paths and conceptual URLs.
"""
import os
import uuid
from typing import Dict, Any, Tuple
from readmaster_ai.application.interfaces.file_storage_interface import FileStorageInterface

# Base path for storing "uploaded" files locally during development.
# Ensure this directory is created or writable by the application.
LOCAL_STORAGE_BASE_PATH = os.path.abspath(os.path.join(os.getcwd(), "local_audio_uploads"))

# Example base URL for constructing mock presigned URLs.
# This URL implies that there's a local server or mechanism that could potentially
# handle uploads/downloads at these paths, though this service doesn't set that up.
# For testing, one might need a separate local server or adjust client behavior.
LOCAL_STORAGE_BASE_URL = os.getenv("LOCAL_STORAGE_BASE_URL", "http://localhost:8000/dev-local-audio")


class LocalFileStorageService(FileStorageInterface):
    """
    A mock file storage service that simulates generating presigned URLs for local development.
    It creates paths where files would be stored but doesn't handle actual HTTP uploads/downloads.
    """
    def __init__(self):
        os.makedirs(LOCAL_STORAGE_BASE_PATH, exist_ok=True)
        print(f"LocalFileStorageService initialized. Uploads will be referenced under: {LOCAL_STORAGE_BASE_PATH}")
        print(f"Mock URLs will be generated using base: {LOCAL_STORAGE_BASE_URL}")


    async def get_presigned_upload_url(
        self,
        blob_name: str,
        content_type: str = "audio/wav",
        expiration_seconds: int = 3600 # Not used in this mock
    ) -> Tuple[str, Dict[str, str]]:
        """
        Generates a mock presigned URL for uploading a file.
        In this local mock, it essentially constructs a URL that implies a target path.
        No actual "signing" or security token generation occurs.
        """
        # The 'blob_name' should be unique, e.g., "assessments_audio/{assessment_id}.wav"
        # The actual file path where it would be "stored" if this mock service handled uploads.
        # This service itself doesn't handle the upload, just gives the URL.
        # Example: local_file_path = os.path.join(LOCAL_STORAGE_BASE_PATH, blob_name)

        # Simulate a URL that a client might use to PUT/POST a file.
        # This mock doesn't set up an endpoint at this URL.
        # A dummy token is added to make it look more like a presigned URL.
        upload_token = str(uuid.uuid4())
        mock_upload_url = f"{LOCAL_STORAGE_BASE_URL}/upload/{blob_name}?token={upload_token}&contentType={content_type}"

        # For some cloud services (like S3 presigned POST), specific form fields are returned.
        # For GCS presigned PUT, typically only headers like 'Content-Type' are needed by the client.
        # This mock returns a common header.
        required_fields_or_headers = {"Content-Type": content_type}

        print(f"Generated mock presigned upload URL for '{blob_name}': {mock_upload_url}")
        print(f"Mock required headers for upload: {required_fields_or_headers}")

        return mock_upload_url, required_fields_or_headers

    async def get_presigned_download_url(
        self,
        blob_name: str,
        expiration_seconds: int = 3600 # Not used in this mock
    ) -> str:
        """
        Generates a mock presigned URL for downloading a file.
        This URL would point to where the file is conceptually stored locally.
        """
        # Illustrative check: In a real system, you'd ensure the file exists before generating a download URL.
        # local_file_path = os.path.join(LOCAL_STORAGE_BASE_PATH, blob_name)
        # if not os.path.exists(local_file_path):
        #     # This check is more for a real file server; here we just form the URL.
        #     print(f"Warning: File at {local_file_path} does not actually exist for download URL generation.")
        #     # Depending on requirements, could raise FileNotFoundError.

        mock_download_url = f"{LOCAL_STORAGE_BASE_URL}/{blob_name}" # Assumes files are served from this base
        print(f"Generated mock presigned download URL for '{blob_name}': {mock_download_url}")
        return mock_download_url

    # Example of how a file path would be constructed if this service also saved files:
    def get_local_file_path(self, blob_name: str) -> str:
        """Helper to get the full local path for a given blob name."""
        return os.path.join(LOCAL_STORAGE_BASE_PATH, blob_name)
