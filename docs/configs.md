# Alchemux Configuration Guide

## Configuration Files

Alchemux uses two main configuration files:

1. **`config.toml`** - Non-secret settings, UX preferences, and defaults
2. **`.env`** - Secret credentials and environment-specific settings

## Environment Variables

These can be set in your shell environment, `.env` file, or system-wide:

### UV and Development Settings

```bash
# Prevents "failed to hardlink files" warnings on cross-filesystem setups
# Common in WSL2, Docker containers, or when mixing Windows/Unix filesystems
# Values: 'hardlink' (default), 'symlink', 'copy'
UV_LINK_MODE=copy
```

### FFmpeg Path Override

```bash
# Override system FFmpeg/ffprobe detection
FFMPEG_PATH=/custom/path/to/ffmpeg
```

### yt-dlp Options

```bash
# Optional yt-dlp settings to reduce 403/Forbidden errors
YTDL_IMPERSONATE=chrome
YTDL_COOKIES_FROM_BROWSER=chrome
YTDL_FORCE_IPV4=true
YTDL_AUDIO_FORMAT_SELECTOR=ba
```

## config.toml Structure

See `config.toml.example` for the complete reference with all available options and their descriptions.

### Key Sections

- **[product]** - Product behavior and terminology preferences
- **[ui]** - User interface defaults (colors, animations, auto-open)
- **[paths]** - Output and temporary directory settings
- **[media.audio]** - Audio processing defaults
- **[media.video]** - Video processing settings
- **[storage]** - Cloud storage configuration
- **[network]** - Network retry and timeout settings

## Configuration Locations

### Run from Source
- Config files are created in the repository directory by default
- Can be overridden with `--config-dir` flag

### PyPI/uv Tool Install
- Config files use OS-standard locations (platformdirs)
- macOS: `~/Library/Application Support/Alchemux/`
- Linux: `~/.config/alchemux/`
- Windows: `%APPDATA%\Alchemux\`

## Troubleshooting

### Hardlink Warnings
If you see "failed to hardlink files; falling back to full copy" warnings:

1. Set `UV_LINK_MODE=copy` in your `.env` file or shell environment
2. This is common in WSL2 or mixed filesystem environments
3. The warning doesn't affect functionality, only suppresses the performance optimization

### Config Not Found
- Run `alchemux setup` to create initial configuration
- Use `--no-config` flag for ephemeral runs without configuration files
