"""
File Storage Service
Abstraction for file operations, supporting Local and S3 (MinIO).
"""

import io
from typing import BinaryIO, Dict, Any, Optional, List

from yuantus.config import get_settings
from yuantus.config.settings import Settings  # Import Settings
from yuantus.meta_engine.storage.storage_interface import StorageProvider
from yuantus.meta_engine.storage.local_storage import LocalStorageProvider
from yuantus.meta_engine.storage.s3_storage import S3StorageProvider
from yuantus.exceptions.handlers import ConfigurationError
from yuantus.meta_engine.events.event_bus import event_bus
from yuantus.meta_engine.events.domain_events import FileUploadedEvent


def get_storage_provider(settings: Optional[Settings] = None) -> StorageProvider:
    """Factory function to get the configured StorageProvider."""
    settings = settings or get_settings()
    if settings.STORAGE_TYPE == "local":
        return LocalStorageProvider(settings)
    elif settings.STORAGE_TYPE == "s3":
        return S3StorageProvider(settings)
    else:
        raise ConfigurationError(f"Unsupported STORAGE_TYPE: {settings.STORAGE_TYPE}")


class FileService:
    def __init__(self, storage_provider: Optional[StorageProvider] = None):
        self.storage_provider = storage_provider or get_storage_provider()

    @staticmethod
    def _safe_size(file_obj: BinaryIO) -> int:
        """
        Best-effort file size detection that won't break if the underlying library
        closes the stream after upload (e.g. boto3.upload_fileobj()).
        """
        try:
            # Prefer seek/tell for generic streams.
            if hasattr(file_obj, "tell") and hasattr(file_obj, "seek"):
                pos = file_obj.tell()
                file_obj.seek(0, io.SEEK_END)
                size = int(file_obj.tell())
                file_obj.seek(pos, io.SEEK_SET)
                return size
        except Exception:
            pass

        # Fallbacks for in-memory buffers
        try:
            if isinstance(file_obj, io.BytesIO):
                return len(file_obj.getbuffer())
        except Exception:
            pass

        return 0

    def upload_file(
        self,
        file_obj: BinaryIO,
        file_path: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Uploads a file and returns its stored path/key."""
        file_size = self._safe_size(file_obj)
        stored_key = self.storage_provider.upload_file(file_path, file_obj, metadata)

        # Publish event
        event_bus.publish(
            FileUploadedEvent(
                file_id=stored_key,  # Using storage_key as file_id for now
                file_name=file_path.split("/")[-1],  # Extract filename
                file_size=file_size,
                storage_key=stored_key,
                actor_id=None,  # FileService doesn't know actor, caller adds to metadata or event
            )
        )
        return stored_key

    def download_file(self, file_path: str, output_file_obj: BinaryIO) -> None:
        """Downloads a file."""
        self.storage_provider.download_file(file_path, output_file_obj)

    def delete_file(self, file_path: str) -> None:
        """Deletes a file."""
        self.storage_provider.delete_file(file_path)

    def file_exists(self, file_path: str) -> bool:
        """Checks if a file exists."""
        return self.storage_provider.file_exists(file_path)

    def get_presigned_url(
        self, file_path: str, expiration: int = 3600, http_method: str = "GET"
    ) -> str:
        """Generates a presigned URL for direct access."""
        return self.storage_provider.get_presigned_url(
            file_path, expiration, http_method
        )

    def create_multipart_upload(
        self, file_path: str, metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Initiates a multipart upload."""
        return self.storage_provider.create_multipart_upload(file_path, metadata)

    def get_presigned_multipart_upload_url(
        self, file_path: str, upload_id: str, part_number: int, expiration: int = 3600
    ) -> str:
        """Generates a presigned URL for a multipart upload part."""
        return self.storage_provider.get_presigned_multipart_upload_url(
            file_path, upload_id, part_number, expiration
        )

    def complete_multipart_upload(
        self, file_path: str, upload_id: str, parts: List[Dict[str, Any]]
    ) -> str:
        """Completes a multipart upload."""
        return self.storage_provider.complete_multipart_upload(
            file_path, upload_id, parts
        )

    def get_local_path(self, file_path: str) -> Optional[str]:
        """Returns local filesystem path if applicable."""
        return self.storage_provider.get_local_path(file_path)
