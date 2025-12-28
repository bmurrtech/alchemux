"""
yt-dlp integration for media download and conversion.
Supports audio/video formats, FLAC override, and progress hooks.
"""
import os
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Callable

try:
    import yt_dlp
except ImportError:
    raise ImportError("yt-dlp is required. Install with: pip install yt-dlp")

from app.core.logger import setup_logger, get_ytdl_logger
from app.core.config_manager import ConfigManager

logger = setup_logger(__name__)


class MediaDownloader:
    """Handles media download and conversion using yt-dlp."""
    
    def __init__(self, config: ConfigManager):
        """
        Initialize MediaDownloader.
        
        Args:
            config: ConfigManager instance
        """
        self.config = config
        self.ytdl_logger = get_ytdl_logger(logger)
    
    def _get_audio_format(self, audio_format: Optional[str] = None) -> str:
        """
        Get audio format from flag, .env, or default.
        
        Args:
            audio_format: Format from --audio-format flag (takes precedence)
            
        Returns:
            Audio format string
        """
        if audio_format:
            return audio_format
        return self.config.get("AUDIO_FORMAT", "mp3")
    
    def _get_video_format(self, video_format: Optional[str] = None) -> str:
        """
        Get video format from flag, .env, or default.
        
        Args:
            video_format: Format from --video-format flag (takes precedence)
            
        Returns:
            Video format string
        """
        if video_format:
            return video_format
        return self.config.get("VIDEO_FORMAT", "mp4")
    
    def _should_apply_flac_override(self, audio_format: str, flac_flag: bool) -> bool:
        """
        Determine if FLAC 16kHz mono override should be applied.
        
        Precedence: --flac flag > FLAC_OVERRIDE=true > default
        
        Args:
            audio_format: Selected audio format
            flac_flag: True if --flac flag was used
            
        Returns:
            True if 16kHz mono should be applied
        """
        if flac_flag:
            return True
        
        if audio_format.lower() == "flac":
            flac_override = self.config.get("FLAC_OVERRIDE", "false").lower() == "true"
            return flac_override
        
        return False
    
    def _build_ydl_opts(
        self,
        output_path: str,
        audio_format: Optional[str] = None,
        video_format: Optional[str] = None,
        flac_flag: bool = False,
        progress_hook: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Build yt-dlp options dictionary.
        
        Args:
            output_path: Output file path (without extension)
            audio_format: Audio format (optional, for audio extraction)
            video_format: Video format (optional, for video conversion)
            flac_flag: True if --flac flag was used
            progress_hook: Optional progress hook function
            
        Returns:
            yt-dlp options dictionary
        """
        opts = {
            # Output template
            'outtmpl': f"{output_path}.%(ext)s",
            'restrictfilenames': self.config.get("RESTRICT_FILENAMES", "true").lower() == "true",
            
            # Paths
            'paths': {
                'home': self.config.get("DOWNLOAD_PATH", "./downloads"),
                'temp': self.config.get("TEMP_PATH", "./temp")
            },
            
            # Metadata
            'embedmetadata': True,
            'writeinfojson': True,
            
            # Error handling
            'ignoreerrors': False,
            'retries': int(self.config.get("RETRIES", "10")),
            
            # Progress (will be set based on log level below)
            'quiet': False,
            'noprogress': False,
        }
        
        # Suppress warnings and quiet output in INFO mode, show in DEBUG mode
        log_level = os.getenv("LOG_LEVEL", "info").lower()
        if log_level == "debug":
            opts['no_warnings'] = False  # Show warnings in debug mode
            opts['quiet'] = False
        else:
            opts['no_warnings'] = True  # Suppress yt-dlp warnings in INFO mode
            opts['quiet'] = True  # Suppress all yt-dlp output in INFO mode
            opts['noprogress'] = True  # Suppress progress output (we handle it)
        
        # Add logger only if debug mode (prevents warnings from showing in INFO mode)
        if log_level == "debug" and self.ytdl_logger:
            opts['logger'] = self.ytdl_logger
        
        # Determine if we're doing audio or video
        is_video = video_format is not None
        
        if is_video:
            # Video conversion
            video_fmt = self._get_video_format(video_format)
            opts['format'] = 'bestvideo+bestaudio/best'
            opts['remuxvideo'] = video_fmt  # yt-dlp will use remuxing when possible
            logger.info(f"Video format: {video_fmt}")
        else:
            # Audio extraction
            audio_fmt = self._get_audio_format(audio_format)
            opts['format'] = 'bestaudio/best'
            opts['extractaudio'] = True
            opts['audioformat'] = audio_fmt
            
            # Audio quality (only for MP3)
            if audio_fmt.lower() == "mp3":
                audio_quality = self.config.get("AUDIO_QUALITY", "5")
                opts['audioquality'] = audio_quality
            
            # FLAC override handling
            if self._should_apply_flac_override(audio_fmt, flac_flag):
                # Apply 16kHz mono via postprocessor args
                opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'flac',
                    'preferredquality': '0',  # Lossless
                }]
                opts['postprocessor_args'] = {
                    'ffmpeg': ['-ar', '16000', '-ac', '1']  # 16kHz mono
                }
                logger.info("FLAC 16kHz mono conversion enabled")
            else:
                # Standard audio extraction
                opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': audio_fmt,
                }]
                if audio_fmt.lower() == "mp3":
                    audio_quality = self.config.get("AUDIO_QUALITY", "5")
                    opts['postprocessors'][0]['preferredquality'] = audio_quality
            
            logger.info(f"Audio format: {audio_fmt}")
        
        # Overwrite behavior
        force_overwrites = self.config.get("FORCE_OVERWRITES", "false").lower() == "true"
        if not force_overwrites:
            opts['noverwrites'] = True
        
        # Add progress hook if provided
        if progress_hook:
            opts['progress_hooks'] = [progress_hook]
        
        return opts
    
    def extract_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from URL without downloading.
        
        Args:
            url: Media URL
            
        Returns:
            Metadata dictionary or None if extraction fails
        """
        opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        
        if self.ytdl_logger:
            opts['logger'] = self.ytdl_logger
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                logger.debug(f"Extracted metadata: title={info.get('title', 'Unknown')}")
                return info
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return None
    
    def download(
        self,
        url: str,
        output_path: str,
        audio_format: Optional[str] = None,
        video_format: Optional[str] = None,
        flac_flag: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Download and convert media.
        
        Args:
            url: Media URL
            output_path: Output file path (without extension)
            audio_format: Audio format (optional)
            video_format: Video format (optional)
            flac_flag: True if --flac flag was used
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (success, file_path, error_message)
        """
        # Build yt-dlp options
        ydl_opts = self._build_ydl_opts(
            output_path,
            audio_format=audio_format,
            video_format=video_format,
            flac_flag=flac_flag,
            progress_hook=self._create_progress_hook(progress_callback)
        )
        
        downloaded_files = []
        
        def progress_hook(d: Dict[str, Any]) -> None:
            """Internal progress hook to capture file paths."""
            if d.get('status') == 'finished':
                filepath = d.get('filename')
                if filepath:
                    downloaded_files.append(filepath)
                    logger.debug(f"Progress hook captured file: {filepath}")
            
            # Call external progress callback if provided
            if progress_callback:
                progress_callback(d)
        
        ydl_opts['progress_hooks'] = [progress_hook]
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Starting download: {url}")
                ydl.download([url])
            
            # Find the downloaded file
            file_path = self._find_downloaded_file(output_path, downloaded_files, ydl_opts)
            
            if file_path and Path(file_path).exists():
                logger.info(f"Download complete: {file_path}")
                return True, file_path, None
            else:
                error_msg = "Download finished but output file not found"
                logger.error(error_msg)
                return False, None, error_msg
        
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            logger.exception(error_msg)
            return False, None, error_msg
    
    def _create_progress_hook(self, callback: Optional[Callable] = None) -> Callable:
        """
        Create progress hook function.
        
        Args:
            callback: Optional external callback
            
        Returns:
            Progress hook function
        """
        def hook(d: Dict[str, Any]) -> None:
            status = d.get('status', '')
            if status == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total > 0:
                    percent = (downloaded / total) * 100
                    logger.debug(f"Download progress: {percent:.1f}%")
            elif status == 'finished':
                logger.debug("Download finished, processing...")
            
            if callback:
                callback(d)
        
        return hook
    
    def _find_downloaded_file(
        self,
        output_path: str,
        downloaded_files: list,
        ydl_opts: Dict[str, Any]
    ) -> Optional[str]:
        """
        Find the actual downloaded file path.
        
        Args:
            output_path: Expected output path (without extension)
            downloaded_files: List of files captured by progress hooks
            ydl_opts: yt-dlp options used
            
        Returns:
            File path or None if not found
        """
        # Prefer files from progress hooks
        for filepath in reversed(downloaded_files):
            if filepath and Path(filepath).exists() and Path(filepath).stat().st_size > 0:
                logger.debug(f"Found file via progress hook: {filepath}")
                return filepath
        
        # Try expected output path with various extensions
        base_path = Path(output_path)
        possible_extensions = ['.mp3', '.flac', '.aac', '.m4a', '.opus', '.wav', '.mp4', '.mkv', '.webm']
        
        for ext in possible_extensions:
            candidate = base_path.with_suffix(ext)
            if candidate.exists() and candidate.stat().st_size > 0:
                logger.debug(f"Found file at expected path: {candidate}")
                return str(candidate)
        
        # Search in output directory
        output_dir = Path(ydl_opts['paths']['home'])
        if output_dir.exists():
            # Find most recently modified file in output directory
            now = time.time()
            candidates = []
            for file_path in output_dir.rglob('*'):
                if file_path.is_file():
                    try:
                        mtime = file_path.stat().st_mtime
                        size = file_path.stat().st_size
                        if size > 1024:  # At least 1KB
                            age = now - mtime
                            if age < 300:  # Modified in last 5 minutes
                                candidates.append((str(file_path), mtime))
                    except Exception:
                        continue
            
            if candidates:
                candidates.sort(key=lambda x: x[1], reverse=True)
                logger.debug(f"Found file via directory search: {candidates[0][0]}")
                return candidates[0][0]
        
        return None

