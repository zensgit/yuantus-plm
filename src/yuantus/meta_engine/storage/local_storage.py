"""
Local Storage Provider
Implements StorageProvider for local filesystem storage.
"""

import os
import shutil
from pathlib import Path
from typing import BinaryIO, Dict, Any, Optional, List
import uuid  # Import uuid

from yuantus.meta_engine.storage.storage_interface import StorageProvider
from yuantus.config.settings import Settings  # Import Settings


class LocalStorageProvider(StorageProvider):
    def __init__(self, settings: Settings):  # No default get_settings()
        self.base_path = Path(settings.LOCAL_STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.public_url_prefix = (
            settings.LOCAL_STORAGE_PUBLIC_URL_PREFIX
        )  # For presigned URLs in local dev

    def _full_path(self, file_path: str) -> Path:
        """Returns the full absolute path for a given file_path/key."""
        # Sanitize file_path to prevent directory traversal attacks
        # Ensure file_path is relative to base_path, not absolute
        sanitized_path = (
            Path(file_path).relative_to("/")
            if str(file_path).startswith("/")
            else Path(file_path)
        )
        return self.base_path / sanitized_path

    def upload_file(
        self,
        file_path: str,
        file_obj: BinaryIO,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        full_path = self._full_path(file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "wb") as f:
            shutil.copyfileobj(file_obj, f)
        # For local storage, the identifier can just be the file_path itself
        return file_path

    def download_file(self, file_path: str, output_file_obj: BinaryIO) -> None:
        full_path = self._full_path(file_path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {full_path}")
        with open(full_path, "rb") as f:
            shutil.copyfileobj(f, output_file_obj)

    def delete_file(self, file_path: str) -> None:
        full_path = self._full_path(file_path)
        if full_path.exists():
            os.remove(full_path)

    def file_exists(self, file_path: str) -> bool:
        return self._full_path(file_path).exists()

    def get_presigned_url(
        self, file_path: str, expiration: int = 3600, http_method: str = "GET"
    ) -> str:
        # For local storage, we return a direct URL if a public prefix is configured
        if self.public_url_prefix:
            return f"{self.public_url_prefix}/{file_path}"
        # If no public_url_prefix, for presigned URL context, we raise an error.
        # Direct file path is not a "presigned URL".
        raise NotImplementedError(
            "Public URL prefix not configured for local storage, cannot generate presigned URL."
        )

    def get_local_path(self, file_path: str) -> Optional[str]:
        return str(self._full_path(file_path))

    # Multipart upload methods are simplified for local storage, not truly "multipart"
    def create_multipart_upload(
        self, file_path: str, metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        # For local, we don't really do multipart. Just simulate an UploadId.
        # The client will then call get_presigned_multipart_upload_url for each part.
        # We can simulate by creating a temp directory for parts.
        upload_id = str(uuid.uuid4())
        temp_dir = self.base_path / "temp_uploads" / upload_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        return {"UploadId": upload_id, "FilePath": file_path, "TempDir": str(temp_dir)}

    def get_presigned_multipart_upload_url(
        self, file_path: str, upload_id: str, part_number: int, expiration: int = 3600
    ) -> str:
        # Return a path to a temporary part file
        temp_dir = self.base_path / "temp_uploads" / upload_id
        part_file = temp_dir / f"part_{part_number}"
        return str(part_file)  # This is where the client would PUT to

    def complete_multipart_upload(
        self, file_path: str, upload_id: str, parts: List[Dict[str, Any]]
    ) -> str:
        # Reconstruct the file from parts
        full_path = self._full_path(file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = self.base_path / "temp_uploads" / upload_id

        with open(full_path, "wb") as dest_file:
            for part in sorted(parts, key=lambda p: p["PartNumber"]):
                part_file = temp_dir / f"part_{part['PartNumber']}"
                if not part_file.exists():
                    raise FileNotFoundError(f"Missing part file: {part_file}")
                with open(part_file, "rb") as src_file:
                    shutil.copyfileobj(src_file, dest_file)

        shutil.rmtree(temp_dir)  # Clean up temp parts
        return file_path
