"""
Distill command - Downloads and converts media from URLs.
"""
import os
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import typer

from app.cli.output import ArcaneConsole
from app.core.config_manager import ConfigManager
from app.core.logger import setup_logger
from app.core.downloader import MediaDownloader
from app.services.gcp_upload import GCPUploader
from app.services.s3_upload import S3Uploader
from app.utils.file_utils import get_download_path, sanitize_filename, detect_source_type
from app.utils.metadata import write_source_url_to_metadata

# Logger will be re-initialized with console after console is created
logger = None

def is_valid_url(url: str) -> bool:
    """Validate URL format."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def _normalize_fracture_cause(msg: Optional[str]) -> str:
    """Map common error text to readable cause for FRACTURED box; else 'unknown'."""
    if not msg:
        return "unknown"
    m = (msg or "").lower()
    if "403" in m or "forbidden" in m:
        # Note: yt-dlp reports "video data" even for audio-only downloads (YouTube returns result_type='video')
        # The actual issue is CDN blocking (googlevideo.com) - can affect both audio and video streams
        if "video data" in m or "unable to download" in m:
            return "CDN blocked (HTTP 403) - try from residential IP"
        return "HTTP 403 Forbidden"
    if "429" in m or "too many requests" in m:
        return "rate limited (HTTP 429)"
    if "network" in m or "connection" in m or "timeout" in m or "unreachable" in m:
        return "network error"
    if "not found" in m or "404" in m:
        return "not found (HTTP 404)"
    if "download failed" in m:
        rest = m.replace("download failed:", "").replace("download failed", "").strip()
        if "403" in rest or "forbidden" in rest:
            return "HTTP 403 Forbidden"
        if rest:
            return rest[:80]
        return "download failed"
    return "unknown"


def distill(
    url: str = typer.Argument(..., help="Source URL to distill"),
    audio_format: Optional[str] = typer.Option(None, "--audio-format", "-a", help="Audio codec/format"),
    video_format: Optional[str] = typer.Option(None, "--video-format", help="Video container"),
    flac: bool = typer.Option(False, "--flac", help="FLAC 16kHz mono conversion"),
    save_path: Optional[str] = typer.Option(None, "--save-path", help="Custom output directory for this run (one-time override)"),
    local: bool = typer.Option(False, "--local", help="Save to local storage (one-time override)"),
    s3: bool = typer.Option(False, "--s3", help="Upload to S3 storage (one-time override)"),
    gcp: bool = typer.Option(False, "--gcp", help="Upload to GCP storage (one-time override)"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode with full tracebacks"),
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Distills the bound media into its purified vessel.
    
    This rite extracts and transmutes media from a source URL, converting it
    into a purified format suitable for further rites. Invoking this without
    a source will fail. The distillation process uses the arcane arts of
    yt-dlp to perform the transmutation.
    
    The rite performs validation, source detection, metadata extraction,
    download, and conversion in sequence. Optionally, it may also inscribe
    metadata and upload to cloud storage before completion.
    """
    # Initialize configuration (loads .env file and config.toml)
    config = ConfigManager()
    
    # Initialize console: arcane_terms from config.toml (product.arcane_terms) then env fallback
    arcane_terms_str = (config.get("product.arcane_terms") or config.get("ARCANE_TERMS") or "true").lower()
    arcane_terms = arcane_terms_str in ("1", "true", "yes")
    console = ArcaneConsole(plain=plain, arcane_terms=arcane_terms)
    
    # Set up logging with RichHandler (pass console for clean output)
    if debug:
        os.environ["LOG_LEVEL"] = "debug"
        os.environ["ALCHEMUX_DEBUG"] = "true"
    
    # Initialize logger with console for RichHandler (suppresses logs in default mode)
    global logger
    logger = setup_logger(__name__, console=console.console, verbose=debug)
    
    # Check EULA acceptance first (only enforced for packaged builds)
    # EULA must be accepted manually via setup wizard, not via flags
    from app.core.eula import is_packaged_build, EULAManager
    if is_packaged_build():
        eula = EULAManager(config)
        if not eula.is_accepted():
            # Run interactive EULA acceptance directly
            if not eula.interactive_acceptance():
                # User declined - exit gracefully
                raise typer.Exit(code=1)
    else:
        # Running from source - EULA not required (Apache 2.0 license applies)
        logger.debug("Running from source - EULA check skipped")
    
    # Ensure configuration files exist (auto-create from defaults if missing, now that EULA is handled)
    if not config.check_env_file_exists():
        try:
            config._create_env_from_example()
            # Reload env vars
            from dotenv import load_dotenv
            load_dotenv(config.env_path)
        except Exception as e:
            logger.warning(f"Could not create .env: {e}")
            
    if not config.check_toml_file_exists():
        try:
            config._create_toml_from_example()
        except Exception as e:
            logger.warning(f"Could not create config.toml: {e}")
    
    # Validate required variables
    # Check for paths.output_dir (preferred) or DOWNLOAD_PATH (legacy)
    required_vars = ["paths.output_dir"]
    is_valid, missing = config.validate_required(required_vars)
    if not is_valid:
        console.err_console.print(f"⚠️  Missing required configuration: {', '.join(missing)}")
        console.err_console.print("   Please run 'alchemux setup' to repair configuration.\n")
        raise typer.Exit(code=1)
    
    # Determine output directory (--save-path override or config default)
    if save_path:
        # One-run override: use provided path
        output_dir = save_path
        console.print_stage("vessel", "output path override", status=save_path)
    else:
        # Use config default
        output_dir = config.get("paths.output_dir", "./downloads")
    
    # Validate URL
    if not is_valid_url(url):
        console.print_fracture("scribe", "invalid URL format")
        raise typer.Exit(code=1)
    
    # Initial process divider
    console.print_phase_header("⟁ SCRYING")
    
    # Use status spinner for checking
    with console.stage_status("scribe", "checking URL..."):
        pass  # Validation already done above
    console.stage_ok("scribe", "accepted")
    
    # Detect source
    with console.stage_status("scry", "detecting source..."):
        source = detect_source_type(url)
    console.stage_ok("scry", f"source: {source}")
    
    # Initialize downloader
    downloader = MediaDownloader(config)
    
    # Extract metadata with status spinner
    with console.stage_status("profile", "extracting metadata..."):
        metadata = downloader.extract_metadata(url)
    
    if metadata:
        title = metadata.get("title", "untitled")
        duration = metadata.get("duration_string", "Unknown")
        console.stage_ok("profile", f'title="{title[:50]}"', duration=duration)
    else:
        title = f"{source}_{int(time.time())}"
        console.stage_ok("profile", "partial metadata recovered")
    
    # Formats to produce: --video-format → one video run; --flac → flac; --audio-format → that; else enabled_formats
    # Check config for video enabled state: video is disabled if format is empty or enabled_formats is empty
    video_format_config = config.get("media.video.format", "")
    video_enabled_formats = config.get_list("media.video.enabled_formats") or []
    video_enabled_in_config = bool(video_format_config and video_format_config.strip()) or bool(video_enabled_formats)
    if video_format and video_enabled_in_config:
        formats_to_produce = [video_format]  # one video run (only if enabled in config)
    elif flac:
        formats_to_produce = ["flac"]
    elif audio_format:
        formats_to_produce = [audio_format]
    else:
        # Check if video formats are enabled in config (for multi-format production)
        if video_enabled_in_config:
            video_formats = video_enabled_formats if video_enabled_formats else ([video_format_config] if video_format_config else [])
            enabled_audio = config.get_list("media.audio.enabled_formats")
            audio_formats = enabled_audio if enabled_audio else [config.get("media.audio.format", "mp3")]
            formats_to_produce = audio_formats + video_formats
        else:
            # Video disabled - only audio formats
            enabled = config.get_list("media.audio.enabled_formats")
            formats_to_produce = enabled if enabled else [config.get("media.audio.format", "mp3")]

    logger.debug(f"Formats to produce: {formats_to_produce}")

    # Determine storage destinations from flags (before loop so we know upload_to_* once)
    # If multiple flags are set AND all are configured, save to all indicated places
    # Otherwise, use priority: flags > config.toml storage.destination > fallback
    flags_set = [flag for flag, value in [("local", local), ("s3", s3), ("gcp", gcp)] if value]
    
    if len(flags_set) > 1:
        # Multiple flags set - check if all are configured
        all_configured = True
        if "s3" in flags_set and not config.is_s3_configured():
            all_configured = False
            console.console.print(f"[yellow]⚠[/yellow]  S3 not configured, skipping S3 upload")
        if "gcp" in flags_set and not config.is_gcp_configured():
            all_configured = False
            console.console.print(f"[yellow]⚠[/yellow]  GCP not configured, skipping GCP upload")
        
        if all_configured:
            # All flags set and all configured - save to all indicated places
            upload_to_local = "local" in flags_set
            upload_to_s3 = "s3" in flags_set
            upload_to_gcp = "gcp" in flags_set
            console.console.print(f"[dim]Saving to all specified destinations: {', '.join(flags_set)}[/dim]")
        else:
            # Some not configured - use only configured ones
            upload_to_local = "local" in flags_set  # Local is always available
            upload_to_s3 = "s3" in flags_set and config.is_s3_configured()
            upload_to_gcp = "gcp" in flags_set and config.is_gcp_configured()
    elif len(flags_set) == 1:
        # Single flag set - use that destination
        storage_dest = flags_set[0]
        if storage_dest == "s3" and not config.is_s3_configured():
            fallback = config.get("storage.fallback", "local")
            console.console.print(f"[yellow]⚠[/yellow]  S3 not configured, falling back to: {fallback}")
            storage_dest = fallback if fallback != "error" else "local"
        elif storage_dest == "gcp" and not config.is_gcp_configured():
            fallback = config.get("storage.fallback", "local")
            console.console.print(f"[yellow]⚠[/yellow]  GCP not configured, falling back to: {fallback}")
            storage_dest = fallback if fallback != "error" else "local"
        
        upload_to_local = (storage_dest == "local")
        upload_to_s3 = (storage_dest == "s3")
        upload_to_gcp = (storage_dest == "gcp")
    else:
        # No flags set - use config.toml storage.destination
        storage_dest = config.get_storage_destination()
        
        # Validate destination and check if configured
        if storage_dest == "s3" and not config.is_s3_configured():
            fallback = config.get("storage.fallback", "local")
            console.console.print(f"[yellow]⚠[/yellow]  S3 not configured, falling back to: {fallback}")
            storage_dest = fallback if fallback != "error" else "local"
        elif storage_dest == "gcp" and not config.is_gcp_configured():
            fallback = config.get("storage.fallback", "local")
            console.console.print(f"[yellow]⚠[/yellow]  GCP not configured, falling back to: {fallback}")
            storage_dest = fallback if fallback != "error" else "local"
        
        upload_to_local = (storage_dest == "local")
        upload_to_s3 = (storage_dest == "s3")
        upload_to_gcp = (storage_dest == "gcp")
    
    keep_local_copy = config.get("storage.keep_local_copy", "false").lower() == "true"

    # GCP/S3 setup once (so uploaders exist for the per-format loop)
    gcp_uploader = None
    if upload_to_gcp:
        console.print_phase_header("⇮ EVAPORATING")
        gcp_uploader = GCPUploader(config)
        if not gcp_uploader.is_configured():
            console.err_console.print("⚠️  GCP not configured. Running setup wizard...")
            from app.core.setup_wizard import interactive_gcp_setup
            if interactive_gcp_setup(config):
                console.print_success("setup", "GCP configuration complete")
                gcp_uploader = GCPUploader(config)
            else:
                console.print_fracture("setup", "GCP setup failed")
                raise typer.Exit(code=1)
    s3_uploader = None
    if upload_to_s3:
        if not upload_to_gcp:
            console.print_phase_header("⇮ EVAPORATING")
        s3_uploader = S3Uploader(config)
        if not s3_uploader.is_configured():
            console.err_console.print("⚠️  S3 not configured. Running setup wizard...")
            from app.core.setup_wizard import interactive_s3_setup
            if interactive_s3_setup(config):
                console.print_success("setup", "S3 configuration complete")
                s3_uploader = S3Uploader(config)
            else:
                console.print_fracture("setup", "S3 setup failed")
                raise typer.Exit(code=1)

    seal_items = []  # [(ext, path_or_url), ...] for successful saves only
    fractured_entries = []  # [(ext, cause), ...] for failed saves
    first_file_path = None
    title_display = os.path.splitext(sanitize_filename(f"{title}.mp3" if not title.endswith(".mp3") else title))[0]
    is_video_run = bool(video_format)
    video_ext_map = {"mp4": ".mp4", "mkv": ".mkv", "webm": ".webm", "mov": ".mov", "avi": ".avi", "flv": ".flv", "gif": ".gif"}
    audio_ext_map = {"aac": ".aac", "alac": ".m4a", "m4a": ".m4a", "opus": ".opus", "vorbis": ".ogg", "wav": ".wav"}

    for fmt in formats_to_produce:
        base = sanitize_filename(f"{title}.mp3" if not title.endswith(".mp3") else title)
        base = os.path.splitext(base)[0]
        if is_video_run:
            ext = video_ext_map.get((fmt or "").lower(), ".mp4")
        elif (fmt or "").lower() == "flac":
            ext = ".flac"
        else:
            ext = audio_ext_map.get((fmt or "").lower(), ".mp3")
        filename = base + ext
        output_path = get_download_path(output_dir, source, filename)

        with console.stage_status("vessel", f"preparing {filename}..."):
            pass
        console.stage_ok("vessel", "ready")

        console.print_phase_header("⚗ DISTILLING")
        with console.stage_status("distill", "distilling..."):
            success, file_path, error_msg = downloader.download(
                url,
                str(output_path.with_suffix("")),
                audio_format=None if is_video_run else fmt,
                video_format=fmt if is_video_run else None,
                flac_flag=(fmt == "flac" and flac),
                progress_callback=None,
            )
        if not success:
            # If video download failed, try audio-only fallback
            if is_video_run and ("403" in (error_msg or "").lower() or "video data" in (error_msg or "").lower() or "forbidden" in (error_msg or "").lower()):
                logger.warning(f"Video download failed ({error_msg}), attempting audio-only fallback...")
                console.console.print(f"[yellow]⚠[/yellow]  Video download failed, attempting audio-only extraction...")
                # Try audio-only extraction
                audio_fmt = config.get("media.audio.format", "mp3")
                success, file_path, error_msg = downloader.download(
                    url,
                    str(output_path.with_suffix("")),
                    audio_format=audio_fmt,
                    video_format=None,  # Explicitly disable video
                    flac_flag=False,
                    progress_callback=None,
                )
                if success:
                    # Update extension for audio file
                    ext = audio_ext_map.get(audio_fmt.lower(), ".mp3")
                    filename = base + ext
                    output_path = get_download_path(output_dir, source, filename)
                    # Update is_video_run for this iteration
                    is_video_run = False
                    console.console.print(f"[green]✓[/green]  Audio extraction succeeded")
                else:
                    cause = _normalize_fracture_cause(error_msg)
                    fractured_entries.append((ext.lstrip(".") or fmt or "file", cause))
                    console.print_fracture("distill", error_msg or "download failed (video and audio fallback)")
                    continue
            else:
                cause = _normalize_fracture_cause(error_msg)
                fractured_entries.append((ext.lstrip(".") or fmt or "file", cause))
                console.print_fracture("distill", error_msg or "download failed")
                continue

        with console.stage_status("attune", "locating output..."):
            pass
        console.stage_ok("attune", "attunement complete")
        if not first_file_path and file_path:
            first_file_path = file_path

        if file_path:
            console.print_phase_header("⌘ MUXING")
            with console.stage_status("mux", "inscribing metadata..."):
                metadata_success = write_source_url_to_metadata(file_path, url)
            if metadata_success:
                console.stage_ok("mux", "inscription complete")
                logger.debug("Source URL written to metadata")
            else:
                logger.debug("Failed to write source URL to metadata (continuing anyway)")

        this_display = None
        if upload_to_gcp and gcp_uploader and file_path:
            with console.stage_status("evaporate", "evaporating artifact..."):
                up_ok, up_res = gcp_uploader.upload(file_path, Path(file_path).name, source)
            if up_ok:
                console.stage_ok("evaporate", "transfer complete")
                this_display = up_res
            else:
                console.print_fracture("evaporate", up_res or "upload failed")
                this_display = file_path
        if upload_to_s3 and s3_uploader and file_path:
            with console.stage_status("evaporate", "evaporating artifact..."):
                up_ok, up_res = s3_uploader.upload(file_path, Path(file_path).name, source)
            if up_ok:
                console.stage_ok("evaporate", "transfer complete")
                if this_display is None:
                    this_display = up_res
            else:
                console.print_fracture("evaporate", up_res or "upload failed")
                if this_display is None:
                    this_display = file_path
        if this_display is None and file_path:
            this_display = file_path
        if this_display:
            seal_items.append((ext.lstrip(".") or fmt or "file", this_display))

    with console.stage_status("purge", "purging residues..."):
        pass
    console.stage_ok("purge", "chamber clear")

    # Seal: title (no ext) + items; FRACTURED box for failed saves
    if seal_items:
        console.print_seal(title_base=title_display, items=seal_items)
    if fractured_entries:
        console.print_fractured_box(fractured_entries)
    if fractured_entries and not seal_items:
        raise typer.Exit(code=1)

    # Auto-open folder if enabled
    auto_open_str = config.get("ui.auto_open") or config.get("AUTO_OPEN", "false")
    auto_open = auto_open_str.lower() == "true" if isinstance(auto_open_str, str) else bool(auto_open_str)
    path_for_open = first_file_path or (seal_items[0][1] if seal_items else None)
    if auto_open and path_for_open and os.path.exists(path_for_open):
        try:
            import subprocess
            import platform
            
            folder_path = Path(path_for_open).parent
            
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(folder_path)], check=False)
            elif platform.system() == "Windows":
                subprocess.run(["explorer", str(folder_path)], check=False)
            else:  # Linux
                subprocess.run(["xdg-open", str(folder_path)], check=False)
            
            logger.debug(f"Opened folder: {folder_path}")
        except Exception as e:
            logger.warning(f"Could not open folder: {e}")

