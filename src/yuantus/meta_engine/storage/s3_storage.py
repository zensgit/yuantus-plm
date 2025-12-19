"""
S3 Storage Provider
Implements StorageProvider for AWS S3 compatible storage (e.g., MinIO).
"""

import logging
from typing import BinaryIO, Dict, Any, Optional, List

# Optional boto3 dependency for S3 storage
try:
    import boto3
    from botocore.exceptions import ClientError

    _BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None  # type: ignore
    ClientError = Exception  # type: ignore
    _BOTO3_AVAILABLE = False

from yuantus.meta_engine.storage.storage_interface import StorageProvider
from yuantus.config.settings import Settings  # Import Settings

logger = logging.getLogger(__name__)  # Initialize logger


class S3StorageProvider(StorageProvider):
    def __init__(self, settings: Settings):  # No default get_settings()
        if not _BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for S3 storage. Install with: pip install boto3"
            )
        self.bucket_name = settings.S3_BUCKET_NAME
        self._endpoint_url = settings.S3_ENDPOINT_URL
        self._public_endpoint_url = (
            settings.S3_PUBLIC_ENDPOINT_URL.strip() or self._endpoint_url
        )

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self._endpoint_url,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION_NAME,  # Optional, but good practice
        )
        self._presign_client = (
            self.s3_client
            if self._public_endpoint_url == self._endpoint_url
            else boto3.client(
                "s3",
                endpoint_url=self._public_endpoint_url,
                aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
                region_name=settings.S3_REGION_NAME,
            )
        )

    def upload_file(
        self,
        file_path: str,
        file_obj: BinaryIO,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        try:
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                file_path,
                ExtraArgs={"Metadata": metadata} if metadata else {},
            )
            logger.info(f"File {file_path} uploaded to S3 bucket {self.bucket_name}")
            return file_path
        except ClientError as e:
            logger.error(f"Failed to upload {file_path} to S3: {e}")
            raise

    def download_file(self, file_path: str, output_file_obj: BinaryIO) -> None:
        try:
            self.s3_client.download_fileobj(
                self.bucket_name, file_path, output_file_obj
            )
            logger.info(
                f"File {file_path} downloaded from S3 bucket {self.bucket_name}"
            )
        except ClientError as e:
            logger.error(f"Failed to download {file_path} from S3: {e}")
            raise

    def delete_file(self, file_path: str) -> None:
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_path)
            logger.info(f"File {file_path} deleted from S3 bucket {self.bucket_name}")
        except ClientError as e:
            logger.error(f"Failed to delete {file_path} from S3: {e}")
            raise

    def file_exists(self, file_path: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.error(f"Error checking existence of {file_path} in S3: {e}")
            raise

    def get_presigned_url(
        self, file_path: str, expiration: int = 3600, http_method: str = "GET"
    ) -> str:
        try:
            return self._presign_client.generate_presigned_url(
                ClientMethod="get_object" if http_method == "GET" else "put_object",
                Params={"Bucket": self.bucket_name, "Key": file_path},
                ExpiresIn=expiration,
                HttpMethod=http_method,
            )
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {file_path}: {e}")
            raise

    def create_multipart_upload(
        self, file_path: str, metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        try:
            response = self.s3_client.create_multipart_upload(
                Bucket=self.bucket_name,
                Key=file_path,
                Metadata=metadata if metadata else {},
            )
            return {"UploadId": response["UploadId"], "FilePath": file_path}
        except ClientError as e:
            logger.error(f"Failed to initiate multipart upload for {file_path}: {e}")
            raise

    def get_presigned_multipart_upload_url(
        self, file_path: str, upload_id: str, part_number: int, expiration: int = 3600
    ) -> str:
        try:
            return self._presign_client.generate_presigned_url(
                ClientMethod="upload_part",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": file_path,
                    "UploadId": upload_id,
                    "PartNumber": part_number,
                },
                ExpiresIn=expiration,
            )
        except ClientError as e:
            logger.error(
                f"Failed to generate presigned URL for part {part_number} of {file_path}: {e}"
            )
            raise

    def complete_multipart_upload(
        self, file_path: str, upload_id: str, parts: List[Dict[str, Any]]
    ) -> str:
        # 'parts' should be a list of dictionaries, each with 'PartNumber' and 'ETag'
        try:
            self.s3_client.complete_multipart_upload(
                Bucket=self.bucket_name,
                Key=file_path,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
            logger.info(f"Multipart upload for {file_path} completed successfully.")
            return file_path
        except ClientError as e:
            logger.error(f"Failed to complete multipart upload for {file_path}: {e}")
            raise
