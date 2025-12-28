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


def distill(
    url: str = typer.Argument(..., help="Source URL to distill"),
    format: str = typer.Option("mp3", "--format", "-f", help="Audio codec/format"),
    video_format: Optional[str] = typer.Option(None, "--video-format", help="Video container"),
    flac: bool = typer.Option(False, "--flac", help="FLAC 16kHz mono conversion"),
    save_path: Optional[str] = typer.Option(None, "--save-path", help="Custom save location"),
    gcp: bool = typer.Option(False, "--gcp", help="Enable GCP Cloud Storage upload"),
    accept_eula: bool = typer.Option(False, "--accept-eula", help="Accept EULA non-interactively"),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging"),
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
    # Initialize configuration first (loads .env file)
    config = ConfigManager()
    
    # Initialize console (needed for logger) - read arcane_terms after .env is loaded
    arcane_terms_str = config.get("ARCANE_TERMS", "true").lower()
    arcane_terms = arcane_terms_str in ("1", "true", "yes")
    console = ArcaneConsole(plain=plain, arcane_terms=arcane_terms)
    
    # Set up logging with RichHandler (pass console for clean output)
    if verbose:
        os.environ["LOG_LEVEL"] = "debug"
        os.environ["VERBOSE"] = "true"
    
    # Initialize logger with console for RichHandler (suppresses logs in default mode)
    global logger
    logger = setup_logger(__name__, console=console.console, verbose=verbose)
    
    # Check .env file - auto-run setup if missing
    if not config.check_env_file_exists():
        console.err_console.print("⚠️  Configuration file (.env) not found.")
        console.err_console.print("   Running setup wizard...\n")
        from app.core.setup_wizard import interactive_setup_minimal
        if interactive_setup_minimal(config):
            console.console.print()  # Add spacing
        else:
            console.err_console.print("\n❌ Setup failed. Please run 'alchemux setup' manually.")
            raise typer.Exit(code=1)
    
    # Validate required variables
    required_vars = ["DOWNLOAD_PATH"]
    is_valid, missing = config.validate_required(required_vars)
    if not is_valid:
        console.err_console.print(f"⚠️  Missing required configuration: {', '.join(missing)}")
        console.err_console.print("   Running setup wizard...\n")
        from app.core.setup_wizard import interactive_setup_minimal
        if interactive_setup_minimal(config):
            console.console.print()  # Add spacing
        else:
            console.err_console.print("\n❌ Setup failed. Please run 'alchemux setup' manually.")
            raise typer.Exit(code=1)
    
    # Check EULA acceptance (only enforced for packaged builds)
    from app.core.eula import is_packaged_build, EULAManager
    if is_packaged_build():
        eula = EULAManager(config)
        if not eula.check_and_require_acceptance(
            accept_flag=accept_eula,
            env_var=os.getenv("EULA_ACCEPTED", "").lower() == "true"
        ):
            raise typer.Exit(code=1)
    else:
        # Running from source - EULA not required (Apache 2.0 license applies)
        logger.debug("Running from source - EULA check skipped")
    
    # Handle --save-path flag
    if save_path:
        config.update_download_path(save_path)
        console.print_stage("vessel", "download path updated", status=save_path)
        console.print_success("vessel", "ready")
    
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
    
    # Prepare output path
    download_path = config.get("DOWNLOAD_PATH", "./downloads")
    filename = sanitize_filename(f"{title}.mp3" if not title.endswith(".mp3") else title)
    
    # Determine actual format
    audio_format = format
    if video_format:
        # Video conversion - adjust filename extension
        ext_map = {
            "mp4": ".mp4", "mkv": ".mkv", "webm": ".webm",
            "mov": ".mov", "avi": ".avi", "flv": ".flv", "gif": ".gif"
        }
        ext = ext_map.get(video_format, ".mp4")
        filename = os.path.splitext(filename)[0] + ext
    elif flac or (audio_format and audio_format.lower() == "flac"):
        filename = os.path.splitext(filename)[0] + ".flac"
    elif audio_format:
        ext_map = {
            "aac": ".aac", "alac": ".m4a", "m4a": ".m4a",
            "opus": ".opus", "vorbis": ".ogg", "wav": ".wav"
        }
        ext = ext_map.get(audio_format.lower(), ".mp3")
        filename = os.path.splitext(filename)[0] + ext
    
    output_path = get_download_path(download_path, source, filename)
    with console.stage_status("vessel", f"preparing {filename}..."):
        pass  # Path already prepared
    console.stage_ok("vessel", "ready")
    
    # Download phase header (includes divider pattern)
    console.print_phase_header("⚗ DISTILLING")
    # Note: "initializing..." message is handled by progress bar, no need for separate print_stage
    
    # Progress tracking for Rich Progress
    pulse_index = 0
    last_percent = -1
    progress_state = {"progress": None, "task_id": None, "total_bytes": 0}
    
    def progress_callback(d: dict) -> None:
        nonlocal pulse_index, last_percent
        status = d.get('status', '')
        if status == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            
            if total > 0:
                progress_state["total_bytes"] = total
                percent = int((downloaded / total) * 100)
                
                # Rotate pulse mark
                if percent != last_percent:
                    pulse_index = (pulse_index + 1) % len(console.PULSE_MARKS)
                    last_percent = percent
                
                pulse = console.rotate_pulse(pulse_index)
                
                # Determine stage description (translate if needed)
                if percent < 50:
                    stage_desc = console.translate_message("charging vessel")
                elif percent < 90:
                    stage_desc = console.translate_message("distilling stream")
                else:
                    stage_desc = console.translate_message("distillation complete") if percent == 100 else "finalizing"
                
                # Update progress if available
                if progress_state["progress"] and progress_state["task_id"] is not None:
                    progress_state["progress"].update(
                        progress_state["task_id"],
                        completed=percent,
                        total=100,
                        status=stage_desc,
                        description="downloading" if percent < 100 else "complete"
                    )
        elif status == 'finished':
            if progress_state["progress"] and progress_state["task_id"] is not None:
                progress_state["progress"].update(
                    progress_state["task_id"],
                    completed=100,
                    total=100,
                    status=console.translate_message("distillation complete"),
                    description="[green]complete[/green]"
                )
    
    # Create progress context
    with console.create_progress_context("distill", total=100) as progress:
        progress_state["progress"] = progress
        task_id = console.add_progress_task(progress, "distill", total=100, status="initializing")
        progress_state["task_id"] = task_id
        
        success, file_path, error_msg = downloader.download(
            url,
            str(output_path.with_suffix('')),  # Remove extension, yt-dlp will add it
            audio_format=audio_format,
            video_format=video_format,
            flac_flag=flac,
            progress_callback=progress_callback
        )
    
    if not success:
        console.print_fracture("distill", error_msg or "download failed")
        raise typer.Exit(code=1)
    
    with console.stage_status("attune", "locating output..."):
        pass  # File already located
    console.stage_ok("attune", "attunement complete")
    
    # Write source URL to metadata (MUX stage)
    if file_path:
        console.print_phase_header("⌘ MUXING")
        with console.stage_status("mux", "inscribing metadata..."):
            metadata_success = write_source_url_to_metadata(file_path, url)
        if metadata_success:
            console.stage_ok("mux", "inscription complete")
            logger.debug("Source URL written to metadata")
        else:
            console.print_fracture("mux", "metadata write failed (continuing)")
            logger.warning("Failed to write source URL to metadata (continuing anyway)")
    
    # GCP upload
    if gcp:
        console.print_divider()
        uploader = GCPUploader(config)
        if not uploader.is_configured():
            console.err_console.print("❌ GCP upload not configured. Run: alchemux setup gcp")
            raise typer.Exit(code=1)
        
        with console.stage_status("evaporate", "evaporating artifact..."):
            upload_success, upload_result = uploader.upload(
                file_path,
                Path(file_path).name,
                source
            )
        
        if upload_success:
            console.stage_ok("evaporate", "transfer complete")
            console.console.print(f"☁️  Uploaded to: {upload_result}")
        else:
            console.print_fracture("evaporate", upload_result or "upload failed")
            # Continue anyway - local file is still available
    
    with console.stage_status("purge", "purging residues..."):
        pass  # Cleanup is automatic
    console.stage_ok("purge", "chamber clear")
    
    # Elevated completion state
    console.print_seal(file_path)
    
    # Auto-open folder if enabled
    auto_open = config.get("AUTO_OPEN", "false").lower() == "true"
    if auto_open and file_path:
        try:
            import subprocess
            import platform
            
            folder_path = Path(file_path).parent
            
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(folder_path)], check=False)
            elif platform.system() == "Windows":
                subprocess.run(["explorer", str(folder_path)], check=False)
            else:  # Linux
                subprocess.run(["xdg-open", str(folder_path)], check=False)
            
            logger.debug(f"Opened folder: {folder_path}")
        except Exception as e:
            logger.warning(f"Could not open folder: {e}")

