"""
GCP Cloud Storage upload service.
Handles credential management and file uploads.
"""
import os
import base64
import tempfile
import time
from pathlib import Path
from typing import Tuple, Optional

try:
    from google.cloud import storage
except ImportError:
    raise ImportError("google-cloud-storage is required. Install with: pip install google-cloud-storage")

from app.core.logger import setup_logger
from app.core.config_manager import ConfigManager
from app.utils.file_utils import get_media_folder

logger = setup_logger(__name__)


class GCPUploader:
    """Handles GCP Cloud Storage uploads."""
    
    def __init__(self, config: ConfigManager):
        """
        Initialize GCP Uploader.
        
        Args:
            config: ConfigManager instance
        """
        self.config = config
        self.bucket_name = config.get("GCP_STORAGE_BUCKET")
        self.sa_key_base64 = config.get("GCP_SA_KEY_BASE64")
        self._creds_file: Optional[str] = None
    
    def _get_credentials_file(self) -> str:
        """
        Create temporary credentials file from base64-encoded service account key.
        
        Returns:
            Path to temporary credentials file
        """
        if not self.sa_key_base64:
            raise ValueError("GCP_SA_KEY_BASE64 environment variable is not set")
        
        try:
            # Strip whitespace and handle padding issues
            key_b64 = self.sa_key_base64.strip().replace('\n', '').replace(' ', '')
            # Add padding if needed (base64 strings should be multiples of 4)
            missing_padding = len(key_b64) % 4
            if missing_padding:
                key_b64 += '=' * (4 - missing_padding)
            
            sa_key_json = base64.b64decode(key_b64).decode("utf-8")
            tmp = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".json")
            tmp.write(sa_key_json)
            tmp.close()
            self._creds_file = tmp.name
            logger.debug(f"Created temporary GCP credentials file: {self._creds_file}")
            return self._creds_file
        
        except Exception as e:
            logger.error(f"Error decoding GCP credentials: {e}")
            raise ValueError(f"Failed to decode GCP_SA_KEY_BASE64: {str(e)}. Please check that the base64 string is valid.")
    
    def _cleanup_credentials(self) -> None:
        """Clean up temporary credentials file."""
        if self._creds_file and os.path.exists(self._creds_file):
            try:
                os.remove(self._creds_file)
                logger.debug(f"Cleaned up temporary credentials file: {self._creds_file}")
            except Exception as e:
                logger.warning(f"Could not remove temporary credentials file: {e}")
    
    def is_configured(self) -> bool:
        """
        Check if GCP upload is configured.
        
        Returns:
            True if both bucket and credentials are configured
        """
        return bool(self.bucket_name and self.sa_key_base64)
    
    def upload(
        self,
        file_path: str,
        filename: str,
        source_type: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Upload file to GCP Cloud Storage.
        
        Args:
            file_path: Local file path to upload
            filename: Filename to use in bucket
            source_type: Source type (youtube, facebook, etc.)
            
        Returns:
            Tuple of (success, public_url or error_message)
        """
        if not self.is_configured():
            error_msg = "GCP upload not configured. Set GCP_STORAGE_BUCKET and GCP_SA_KEY_BASE64 in .env"
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
        
        creds_file = None
        try:
            # Get credentials
            creds_file = self._get_credentials_file()
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_file
            
            # Initialize client
            client = storage.Client()
            bucket = client.bucket(self.bucket_name)
            
            # Determine blob path
            media_folder = get_media_folder(source_type)
            blob_name = f"{media_folder}/{filename}"
            blob = bucket.blob(blob_name)
            
            # Check if already exists and marked complete
            if blob.exists():
                metadata = blob.metadata or {}
                if metadata.get("upload_complete") == "true":
                    public_url = f"https://storage.googleapis.com/{self.bucket_name}/{blob_name}"
                    logger.info(f"File already exists: {public_url}")
                    return True, public_url
            
            # Upload file
            blob.upload_from_filename(file_path)
            
            # Set metadata
            blob.metadata = {
                "upload_complete": "true",
                "upload_timestamp": str(int(time.time())),
                "content_type": self._guess_content_type(file_path),
            }
            blob.patch()
            
            # Make public (if bucket allows)
            try:
                blob.make_public()
                logger.debug("File made public via ACL")
            except Exception as e:
                logger.debug(f"Could not set ACL (bucket may use uniform access): {e}")
            
            public_url = f"https://storage.googleapis.com/{self.bucket_name}/{blob_name}"
            logger.info(f"Uploaded to {public_url}")
            return True, public_url
        
        except Exception as e:
            error_msg = f"GCP upload error: {str(e)}"
            logger.exception(error_msg)
            
            # Provide helpful error message for common issues
            if "Incorrect padding" in str(e) or "base64" in str(e).lower():
                error_msg += "\nThis usually means GCP_SA_KEY_BASE64 is malformed. Please check that it's a valid base64-encoded JSON key."
            
            return False, error_msg
        
        finally:
            # Clean up credentials
            if creds_file:
                try:
                    os.remove(creds_file)
                except Exception:
                    pass
            if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
                del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    
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

