"""
Storage Service Interface
Abstract base class for different storage providers.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO, Dict, Any, Optional, List  # Added List


class StorageProvider(ABC):
    """Abstract base class for file storage providers."""

    @abstractmethod
    def upload_file(
        self,
        file_path: str,
        file_obj: BinaryIO,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Uploads a file.
        Args:
            file_path: The desired path/key for the file in storage.
            file_obj: A file-like object (e.g., BytesIO, file handle) to upload.
            metadata: Optional dictionary of metadata to associate with the file.
        Returns:
            A unique identifier or URL for the stored file.
        """
        pass

    @abstractmethod
    def download_file(self, file_path: str, output_file_obj: BinaryIO) -> None:
        """
        Downloads a file to a given file-like object.
        Args:
            file_path: The path/key of the file in storage.
            output_file_obj: A file-like object (e.g., BytesIO, file handle) to write to.
        """
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> None:
        """
        Deletes a file from storage.
        Args:
            file_path: The path/key of the file to delete.
        """
        pass

    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        """
        Checks if a file exists in storage.
        Args:
            file_path: The path/key of the file to check.
        Returns:
            True if the file exists, False otherwise.
        """
        pass

    @abstractmethod
    def get_presigned_url(
        self, file_path: str, expiration: int = 3600, http_method: str = "GET"
    ) -> str:
        """
        Generates a presigned URL for direct access to a file.
        Args:
            file_path: The path/key of the file in storage.
            expiration: URL expiration time in seconds.
            http_method: HTTP method (e.g., 'GET', 'PUT').
        Returns:
            The presigned URL.
        """
        pass

    # For multipart uploads (large files)
    @abstractmethod
    def create_multipart_upload(
        self, file_path: str, metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Initiates a multipart upload for a large file.
        Returns:
            A dictionary containing UploadId and other multipart specific info.
        """
        pass

    @abstractmethod
    def get_presigned_multipart_upload_url(
        self, file_path: str, upload_id: str, part_number: int, expiration: int = 3600
    ) -> str:
        """
        Generates a presigned URL for uploading a specific part of a multipart upload.
        """
        pass

    @abstractmethod
    def complete_multipart_upload(
        self, file_path: str, upload_id: str, parts: List[Dict[str, Any]]
    ) -> str:
        """
        Completes a multipart upload.
        Args:
            file_path: The path/key of the file.
            upload_id: The UploadId received from create_multipart_upload.
            parts: A list of dicts, each containing 'PartNumber' and 'ETag' for completed parts.
        Returns:
            A unique identifier or URL for the stored file.
        """
        pass

    def get_local_path(self, file_path: str) -> Optional[str]:
        """
        Returns local filesystem path if applicable.
        Returns None if storage is not local (e.g. S3).
        """
        return None
