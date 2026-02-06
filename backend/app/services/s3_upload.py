"""
S3-compatible storage upload service.
Handles credential management and file uploads.
"""

import os
import time
from pathlib import Path
from typing import Tuple, Optional
from urllib.parse import urlparse

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    raise ImportError("boto3 is required. Install with: pip install boto3")

from app.core.logger import setup_logger
from app.core.config_manager import ConfigManager
from app.utils.file_utils import get_media_folder

logger = setup_logger(__name__)


class S3Uploader:
    """Handles S3-compatible storage uploads."""

    def __init__(self, config: ConfigManager):
        """
        Initialize S3 Uploader.

        Args:
            config: ConfigManager instance
        """
        self.config = config
        # Non-secrets from config.toml (with .env fallback for legacy)
        self.endpoint = config.get("storage.s3.endpoint") or config.get("S3_ENDPOINT")
        self.bucket_name = config.get("storage.s3.bucket") or config.get("S3_BUCKET")
        s3_ssl_str = config.get("storage.s3.ssl") or config.get("S3_SSL", "true")
        self.use_ssl = (
            s3_ssl_str.lower() == "true"
            if isinstance(s3_ssl_str, str)
            else bool(s3_ssl_str)
        )
        # Secrets from .env
        self.access_key = config.get("S3_ACCESS_KEY")
        self.secret_key = config.get("S3_SECRET_KEY")
        self._client = None

    def _get_client(self):
        """
        Get or create S3 client.

        Returns:
            boto3 S3 client
        """
        if self._client is None:
            # Parse endpoint URL
            endpoint_url = self.endpoint
            if endpoint_url and not endpoint_url.startswith(("http://", "https://")):
                # Add protocol if missing
                endpoint_url = f"{'https' if self.use_ssl else 'http'}://{endpoint_url}"

            # Create S3 client
            self._client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                use_ssl=self.use_ssl,
                verify=self.use_ssl,  # Verify SSL certificates
            )

        return self._client

    def is_configured(self) -> bool:
        """
        Check if S3 upload is configured.

        Returns:
            True if all required credentials are configured
        """
        return bool(
            self.endpoint and self.access_key and self.secret_key and self.bucket_name
        )

    def upload(
        self, file_path: str, filename: str, source_type: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Upload file to S3-compatible storage.

        Args:
            file_path: Local file path to upload
            filename: Filename to use in bucket
            source_type: Source type (youtube, facebook, etc.)

        Returns:
            Tuple of (success, public_url or error_message)
        """
        if not self.is_configured():
            error_msg = "S3 upload not configured. Run 'alchemux setup s3' to configure S3 storage"
            logger.error(error_msg)
            return False, error_msg

        # Verify file exists
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            return False, error_msg

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            error_msg = f"File is empty: {file_path}"
            logger.error(error_msg)
            return False, error_msg

        logger.info(f"Uploading file: {file_path} ({file_size} bytes)")

        try:
            client = self._get_client()

            # Determine object key (path in bucket)
            media_folder = get_media_folder(source_type)
            object_key = f"{media_folder}/{filename}"

            # Check if object already exists
            try:
                client.head_object(Bucket=self.bucket_name, Key=object_key)
                # Object exists - construct public URL
                if self.endpoint:
                    endpoint_parsed = urlparse(
                        self.endpoint
                        if self.endpoint.startswith(("http://", "https://"))
                        else f"{'https' if self.use_ssl else 'http'}://{self.endpoint}"
                    )
                    public_url = f"{endpoint_parsed.scheme}://{endpoint_parsed.netloc}/{self.bucket_name}/{object_key}"
                else:
                    public_url = f"s3://{self.bucket_name}/{object_key}"
                logger.info(f"File already exists: {public_url}")
                return True, public_url
            except ClientError as e:
                if e.response["Error"]["Code"] != "404":
                    # Some other error occurred
                    raise

            # Upload file
            content_type = self._guess_content_type(file_path)

            client.upload_file(
                file_path,
                self.bucket_name,
                object_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "Metadata": {
                        "upload_complete": "true",
                        "upload_timestamp": str(int(time.time())),
                        "source_type": source_type,
                    },
                },
            )

            # Construct public URL
            if self.endpoint:
                endpoint_parsed = urlparse(
                    self.endpoint
                    if self.endpoint.startswith(("http://", "https://"))
                    else f"{'https' if self.use_ssl else 'http'}://{self.endpoint}"
                )
                public_url = f"{endpoint_parsed.scheme}://{endpoint_parsed.netloc}/{self.bucket_name}/{object_key}"
            else:
                public_url = f"s3://{self.bucket_name}/{object_key}"

            logger.info(f"Uploaded to {public_url}")
            return True, public_url

        except NoCredentialsError:
            error_msg = "S3 credentials not found or invalid"
            logger.error(error_msg)
            return False, error_msg
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = f"S3 upload error ({error_code}): {str(e)}"
            logger.exception(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"S3 upload error: {str(e)}"
            logger.exception(error_msg)
            return False, error_msg

    def _guess_content_type(self, file_path: str) -> str:
        """
        Guess content type from file extension.

        Args:
            file_path: File path

        Returns:
            Content type string
        """
        ext = Path(file_path).suffix.lower()
        content_types = {
            ".mp3": "audio/mpeg",
            ".flac": "audio/flac",
            ".aac": "audio/aac",
            ".m4a": "audio/mp4",
            ".opus": "audio/opus",
            ".ogg": "audio/ogg",
            ".wav": "audio/wav",
            ".mp4": "video/mp4",
            ".mkv": "video/x-matroska",
            ".webm": "video/webm",
            ".mov": "video/quicktime",
        }
        return content_types.get(ext, "application/octet-stream")
