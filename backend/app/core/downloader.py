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
from app.utils.file_utils import get_ffmpeg_location

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
        Get audio format from flag or config.toml default.

        Args:
            audio_format: Format from --audio-format flag (takes precedence)

        Returns:
            Audio format string
        """
        if audio_format:
            return audio_format
        return self.config.get("media.audio.format", "mp3") or "mp3"

    def _get_video_format(self, video_format: Optional[str] = None) -> str:
        """
        Get video format from flag or config.toml default.

        Args:
            video_format: Format from --video-format flag (takes precedence)

        Returns:
            Video format string
        """
        if video_format:
            return video_format
        return self.config.get("media.video.format", "mp4") or "mp4"

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
        # Use relative outtmpl + paths so yt-dlp doesn't warn "paths is ignored"
        home_dir = self.config.get("paths.output_dir") or self.config.get("DOWNLOAD_PATH", "./downloads")
        temp_dir = self.config.get("TEMP_PATH", "./temp")
        if os.path.isabs(output_path):
            p = Path(output_path)
            outtmpl_rel = f"{p.name}.%(ext)s"
            paths_home = str(p.parent)
        else:
            outtmpl_rel = f"{output_path}.%(ext)s"
            paths_home = home_dir
        opts = {
            'outtmpl': outtmpl_rel,
            'restrictfilenames': self.config.get("RESTRICT_FILENAMES", "true").lower() == "true",
            'paths': {'home': paths_home, 'temp': temp_dir},

            # Metadata
            'embedmetadata': True,
            'writeinfojson': (self.config.get("download.write_info_json", "false") or "false").lower() in ("1", "true", "yes"),

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
        # Check config for video enabled state: video is disabled if format is empty or enabled_formats is empty
        video_format_config = self.config.get("media.video.format", "")
        video_enabled_formats = self.config.get_list("media.video.enabled_formats") or []
        video_enabled_in_config = bool(video_format_config and video_format_config.strip()) or bool(video_enabled_formats)
        is_video = video_format is not None and video_enabled_in_config

        # Merge-oriented format selectors to avoid fragile progressive formats (e.g. YouTube
        # format 22) that often cause 403 from googlevideo.com. Prefer DASH merge + container.
        _VIDEO_FORMAT_SELECTORS = {
            'mp4': ('bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b', 'mp4'),
            'mkv': ('bv*+ba/b', 'mkv'),
            'webm': ('bv*[ext=webm]+ba[ext=webm]/b[ext=webm]/b', 'webm'),
        }

        if is_video:
            # Video conversion: use merge-oriented selector + merge_output_format
            video_fmt = (self._get_video_format(video_format) or 'mp4').lower().strip()
            fmt_selector, merge_fmt = _VIDEO_FORMAT_SELECTORS.get(
                video_fmt, _VIDEO_FORMAT_SELECTORS['mp4']
            )
            opts['format'] = fmt_selector
            opts['merge_output_format'] = merge_fmt
            logger.info(f"Video format: {video_fmt} (merge_output_format={merge_fmt})")
        else:
            # Audio extraction: --flac overrides config so effective format is flac
            audio_fmt = self._get_audio_format(audio_format)
            if flac_flag:
                audio_fmt = "flac"
            # Format selector for audio extraction. Default "best" reduces YouTube CDN 403s by requesting
            # a single combined stream then extracting audio; "ba" requests best audio-only (more 403-prone).
            # See: https://github.com/yt-dlp/yt-dlp/issues/14680
            audio_selector = (os.getenv("YTDL_AUDIO_FORMAT_SELECTOR") or
                             self.config.get("ytdl.audio_format_selector", "best") or "best")
            opts['format'] = "best" if audio_selector.strip().lower() == "best" else "ba"
            opts['extractaudio'] = True
            opts['audioformat'] = audio_fmt
            # Explicitly prevent video processing
            opts['writesubtitles'] = False
            opts['writeautomaticsub'] = False

            # Audio quality (only for MP3)
            if audio_fmt.lower() == "mp3":
                audio_quality = self.config.get("media.audio.quality", "5")
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
                    audio_quality = self.config.get("media.audio.quality", "5")
                    opts['postprocessors'][0]['preferredquality'] = audio_quality

            logger.info(f"Audio format: {audio_fmt}")

        # Overwrite behavior
        force_overwrites = self.config.get("FORCE_OVERWRITES", "false").lower() == "true"
        if not force_overwrites:
            opts['noverwrites'] = True

        # Add progress hook if provided
        if progress_hook:
            opts['progress_hooks'] = [progress_hook]

        # Set ffmpeg location if found (bundled, system, or custom from config)
        # Config values are already loaded into os.environ via load_dotenv in ConfigManager
        ffmpeg_location = get_ffmpeg_location()
        if ffmpeg_location:
            opts['ffmpeg_location'] = ffmpeg_location
            logger.debug(f"Using ffmpeg from: {ffmpeg_location}")
        else:
            logger.warning("ffmpeg/ffprobe not found. Audio/video conversion may fail.")

        # Batch context (PRD 009): human-like delay via yt-dlp sleep to reduce 403/rate-limit risk
        if os.getenv("ALCHEMUX_BATCH"):
            opts['sleep_interval'] = 5
            opts['max_sleep_interval'] = 6
            logger.debug("Batch mode: yt-dlp sleep_interval 5s, max_sleep_interval 6s")

        # Optional 403/workaround options: config or env (env overrides). Rely on yt-dlp upstream.
        impersonate = os.getenv("YTDL_IMPERSONATE") or self.config.get("ytdl.impersonate")
        if impersonate and isinstance(impersonate, str) and impersonate.strip():
            opts['impersonate'] = impersonate.strip()
            logger.debug("yt-dlp impersonate set (from config/env)")

        cookies_browser = os.getenv("YTDL_COOKIES_FROM_BROWSER") or self.config.get("ytdl.cookies_from_browser")
        if cookies_browser and isinstance(cookies_browser, str) and cookies_browser.strip():
            # yt-dlp expects (browser_name,) or (browser_name, profile); use tuple for API
            opts['cookiesfrombrowser'] = (cookies_browser.strip(),)
            logger.debug("yt-dlp cookiesfrombrowser set (from config/env)")

        force_ipv4 = os.getenv("YTDL_FORCE_IPV4") or self.config.get("ytdl.force_ipv4")
        if force_ipv4 and str(force_ipv4).lower() in ("1", "true", "yes"):
            opts['force_ipv4'] = True
            logger.debug("yt-dlp force_ipv4 set (from config/env)")

        # Debug: sanitized summary of effective opts for MP3 vs MP4 troubleshooting
        if log_level == "debug":
            summary = {
                "format": opts.get("format"),
                "merge_output_format": opts.get("merge_output_format"),
                "extractaudio": opts.get("extractaudio"),
                "impersonate": opts.get("impersonate"),
                "cookiesfrombrowser": opts.get("cookiesfrombrowser"),
                "force_ipv4": opts.get("force_ipv4"),
                "outtmpl": opts.get("outtmpl"),
                "paths_home": opts["paths"]["home"][:50] + "…" if len(opts["paths"]["home"]) > 50 else opts["paths"]["home"],
            }
            logger.debug(f"yt-dlp opts summary (sanitized): {summary}")

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

            # Find the downloaded file (prefer expected ext when FLAC/video so we don't pick .mp3)
            expected_ext = None
            if flac_flag:
                expected_ext = ".flac"
            elif video_format:
                vf = (self._get_video_format(video_format) or "mp4").lower()
                expected_ext = { "mp4": ".mp4", "mkv": ".mkv", "webm": ".webm" }.get(vf, ".mp4")
            elif audio_format:
                ext_map = { "aac": ".aac", "flac": ".flac", "m4a": ".m4a", "wav": ".wav", "opus": ".opus", "ogg": ".ogg" }
                expected_ext = ext_map.get((audio_format or "").lower()) or ".mp3"
            file_path = self._find_downloaded_file(output_path, downloaded_files, ydl_opts, expected_ext)

            if file_path and Path(file_path).exists():
                logger.info(f"Download complete: {file_path}")
                return True, file_path, None
            else:
                error_msg = "Download finished but output file not found"
                logger.error(error_msg)
                return False, None, error_msg

        except Exception as e:
            error_msg = str(e)
            # If 403 error on audio-only download, try alternative audio formats as fallback
            if not video_format and ("403" in error_msg.lower() or "forbidden" in error_msg.lower()):
                logger.warning(f"403 error on primary audio format, trying alternative audio formats...")
                # Try specific audio format IDs in order: m4a (140), lower quality m4a (139), webm opus (251)
                # These are common YouTube audio-only formats
                fallback_formats = ['140', '139', '251']
                for fmt_id in fallback_formats:
                    try:
                        ydl_opts_fallback = ydl_opts.copy()
                        ydl_opts_fallback['format'] = fmt_id
                        ydl_opts_fallback['extractaudio'] = True
                        ydl_opts_fallback['audioformat'] = audio_fmt
                        with yt_dlp.YoutubeDL(ydl_opts_fallback) as ydl_fallback:
                            ydl_fallback.download([url])
                        # If successful, find the file
                        file_path = self._find_downloaded_file(output_path, downloaded_files, ydl_opts_fallback, expected_ext)
                        if file_path and Path(file_path).exists():
                            logger.info(f"Fallback format {fmt_id} succeeded: {file_path}")
                            return True, file_path, None
                    except Exception as fallback_error:
                        logger.debug(f"Fallback format {fmt_id} failed: {fallback_error}")
                        continue
                # All fallbacks failed
                error_msg = f"Download failed: {error_msg} (tried fallback formats: {', '.join(fallback_formats)})"
            else:
                error_msg = f"Download failed: {error_msg}"
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
        ydl_opts: Dict[str, Any],
        expected_ext: Optional[str] = None,
    ) -> Optional[str]:
        """
        Find the actual downloaded file path.

        Args:
            output_path: Expected output path (without extension)
            downloaded_files: List of files captured by progress hooks
            ydl_opts: yt-dlp options used
            expected_ext: If set (e.g. .flac), try this extension first when scanning by path

        Returns:
            File path or None if not found
        """
        # Prefer files from progress hooks (actual paths yt-dlp reported)
        for filepath in reversed(downloaded_files):
            if filepath and Path(filepath).exists() and Path(filepath).stat().st_size > 0:
                logger.debug(f"Found file via progress hook: {filepath}")
                return filepath

        # Try expected output path: preferred extension first, then rest
        base_path = Path(output_path)
        all_extensions = ['.mp3', '.flac', '.aac', '.m4a', '.opus', '.wav', '.mp4', '.mkv', '.webm']
        if expected_ext and expected_ext in all_extensions:
            possible_extensions = [expected_ext] + [e for e in all_extensions if e != expected_ext]
        else:
            possible_extensions = all_extensions

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
