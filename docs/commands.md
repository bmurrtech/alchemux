# Alchemux Commands

Complete reference for all Alchemux commands and options.

---

## Basic Usage

The primary way to use Alchemux is to provide a URL for media transmutation.

```bash
alchemux [OPTIONS] ["URL"]
alchemux [OPTIONS] -- "URL"
```

To transmute a URL using current defaults:
```bash
alchemux "https://example.com/video"
```

This automatically performs the full transmutation pipeline: scribe → scry → profile → distill → mux → seal.

### URL quoting (critical)

Always **quote URLs**, especially those containing shell-special characters such as `?`, `&`, `*`, `[`, `]`.

If you suspect argument parsing ambiguity, use the explicit delimiter form:

```bash
alchemux -- "https://example.com/video?a=1&b=2"
```

---

## Command Reference Summary

### Flags (One-Run Overrides)
*Requires a URL. These flags only apply to the current execution.*

| Option | Short | Description |
|--------|-------|-------------|
| `--audio-format` | `-a` | Audio format (mp3, aac, flac, etc.) |
| `--video-format` | | Video container (mp4, mkv, etc.) |
| `--flac` | | FLAC 16kHz mono conversion |
| `--save-path` | | Custom download location |
| `--gcp` | | Enable GCP upload |
| `--s3` | | Enable S3 upload |
| `--local` | | Force local storage |
| `--debug` | | Enable debug mode |
| `--verbose` | | Enable verbose logging |
| `--plain` | | Disable colors/animations |
| `--version` | `-v` | Show version |
| `--help` | `-h` | Show help |

### Commands (Persistent Configuration)
*Standalone commands that modify `config.toml` or provide interactive wizards.*

| Command | Description |
|---------|-------------|
| `alchemux setup [target]` | Run setup wizard (target: gcp, s3, or default) |
| `alchemux setup --reset` | Reset configuration to defaults |
| `alchemux config` | Launch interactive config wizard |
| `alchemux config show` | Show current configuration paths and values |
| `alchemux config doctor` | Run diagnostics on configuration |
| `alchemux config mv <path>` | Move/copy configuration to new directory |
| `alchemux audio-format` | Set default audio format via selector |
| `alchemux video-format` | Set default video format via selector |
| `alchemux storage ...` | Manage storage settings and paths |
| `alchemux debug` | Toggle persistent debug mode |
| `alchemux verbose` | Toggle persistent verbose logging |
| `alchemux plain` | Toggle persistent plain mode |

---

## Main Command Options

### URL (Positional Argument)

The source URL to transmute. Can be from YouTube, Facebook, or any source supported by yt-dlp.

```bash
alchemux "https://youtube.com/watch?v=..."
```

### Format Options (Overrides)

#### `--audio-format`, `-a`

Specify the audio codec/format for this run. Default is read from `config.toml`.

```bash
alchemux --audio-format flac "https://example.com/video"
alchemux -a opus "https://example.com/video"
```

Supported formats: `mp3`, `aac`, `alac`, `flac`, `m4a`, `opus`, `vorbis`, `wav`

#### `--video-format`

Specify the video container format for this run. Requires ffmpeg.

```bash
alchemux --video-format mkv "https://example.com/video"
alchemux --video-format webm "https://example.com/video"
```

---

## Configuration Commands

### `alchemux setup [ARGS]`

Run the interactive setup wizard.

```bash
alchemux setup              # Full setup refresh
alchemux setup gcp          # Configure GCP Cloud Storage
alchemux setup s3           # Configure S3-compatible storage
alchemux setup --reset      # Reset all configuration to defaults
```

The `--reset` flag deletes existing config files and recreates them from templates.
This is useful when configuration becomes corrupted or you want a fresh start.

### `alchemux audio-format` / `alchemux video-format`

Interactive selection of supported codecs. Saves your selection as the new default in `config.toml`.

```bash
alchemux audio-format
alchemux video-format
```

### `alchemux config`

Configuration management with subcommands and interactive wizard.

```bash
alchemux config              # Launch interactive wizard (category-based multi-select)
alchemux config show         # Show configuration paths and values
alchemux config doctor       # Run diagnostics and guided repair
alchemux config mv <path>    # Relocate configuration
```

The `alchemux config` wizard is the **preferred** way to modify persistent settings. It supports **category-based selective updates**:

- **Multi-select interface**: Choose multiple configuration categories to modify in one session
- **Selective updates**: Only selected categories are changed; other settings remain unchanged
- **Guided experience**: Current values shown as defaults, validation built-in
- **Available categories**: Product Settings, UI Settings, Logging, Filesystem Paths, Audio/Video Media, FLAC Presets, Network, Storage, S3/GCP (if configured)

#### `alchemux config show`

Displays current configuration including:
- Config directory and file paths
- Output and temp directories
- Storage destination and fallback
- UI settings (arcane mode, plain mode)

#### `alchemux config doctor`

Runs diagnostics to check for common issues:
- Config directory and file existence
- TOML file validity
- Output directory writability
- Cloud storage credential configuration
- Pointer file validity

**PRD7 behavior (config management MVP):**
- After printing the diagnostic report, `config doctor` offers a **guided repair** flow for issues found.
- Repairs are **interactive by default** and create a **single latest backup** before making changes.
- If a repair fails, Alchemux attempts to **restore from the latest backup** and reports what happened.

Backups are stored under your active config directory (example):
- `<config_dir>/.backups/latest/`

Security note: diagnostics and repairs must **never print secret values** from `.env`.

#### `alchemux config mv <path>`

Copies configuration files to a new directory and updates the pointer file.
Use `--move` to move files instead of copying.

```bash
alchemux config mv ~/my-config              # Copy config to new location
alchemux config mv ~/my-config --move       # Move config to new location
```

The pointer file allows you to relocate configuration without breaking the app.
Alchemux will use the new location on subsequent runs.

### `alchemux debug` / `alchemux verbose` / `alchemux plain`

Toggle persistent settings. These commands echo the new state and the path to `config.toml`.

```bash
alchemux debug      # Toggles debug mode on/off
alchemux verbose    # Toggles verbose logging on/off
alchemux plain      # Toggles plain mode on/off
```

### `alchemux storage`

Manage storage settings and paths.

```bash
alchemux storage use <target>        # Set default storage destination (local, s3, gcp)
alchemux storage set <path>          # Set default output directory
alchemux storage status              # Show current configuration status
```

---

## Path & Storage Options (Overrides)

### `--save-path`

Set a custom download location for this run only.

```bash
alchemux --save-path ~/Music "https://example.com/video"
```

### `--gcp` / `--s3` / `--local`

One-time storage destination overrides. Requires a URL.

```bash
alchemux --gcp "https://example.com/video"    # Upload this transmutation to GCP
alchemux --local "https://example.com/video"  # Save this transmutation locally only
```

---

## Output & Information

### `--plain` / `--debug` / `--verbose` (Overrides)

Apply these modes to the current transmutation run.

```bash
alchemux --plain "https://example.com/video"
```

### `--version`, `-v`

Display version information and exit.

```bash
alchemux --version
alchemux -v
```

### `--help`, `-h`

Display help information.

```bash
alchemux --help
alchemux -h
```

---

## Examples

### Basic Download (MP3)

```bash
alchemux "https://youtube.com/watch?v=abc123"
```

### Download as FLAC (16kHz Mono)

```bash
alchemux --flac "https://youtube.com/watch?v=abc123"
```

### Download as Opus

```bash
alchemux --audio-format opus "https://youtube.com/watch?v=abc123"
```

### Download Video as MKV

```bash
alchemux --video-format mkv "https://youtube.com/watch?v=abc123"
```

### Download with Custom Path

```bash
alchemux --save-path ~/Music "https://youtube.com/watch?v=abc123"
```

### Download and Upload to GCP

```bash
alchemux --gcp "https://youtube.com/watch?v=abc123"
```

### Download and Upload to S3

```bash
alchemux --s3 "https://youtube.com/watch?v=abc123"
```

### Force Local Storage (Override Defaults)

```bash
alchemux --local "https://youtube.com/watch?v=abc123"
```

### Set Default Storage Destination

```bash
alchemux storage use s3
```

### Combined Options

```bash
alchemux --audio-format aac --save-path ~/Music --gcp --debug "https://youtube.com/watch?v=abc123"
```

---

## Configuration Files

### Configuration Location

Alchemux uses platform-specific directories for configuration:

| Platform | Config Directory |
|----------|------------------|
| macOS | `~/Library/Application Support/Alchemux/` |
| Linux | `~/.config/alchemux/` or `$XDG_CONFIG_HOME/alchemux/` |
| Windows | `%APPDATA%\Alchemux\` |

Use `alchemux config show` to see your current configuration paths.

#### Config Location Priority

1. `ALCHEMUX_CONFIG_DIR` environment variable
2. Pointer file (`config_path.txt` in default location)
3. Portable mode: next to binary (if `.env` already exists there)
4. Default OS config directory

Use `alchemux config mv <path>` to relocate configuration.

### `.env` (Secrets Only)

Contains **only secrets and sensitive data**:
- `GCP_SA_KEY_BASE64`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `OAUTH_CLIENT_ID`
- `OAUTH_CLIENT_SECRET`

### `config.toml` (User Preferences)

Contains **non-secret configuration and defaults**:
- `paths.output_dir`
- `media.audio.format`
- `product.arcane_terms`
- `ui.auto_open`
- `eula.accepted`

All default configurations from `config.toml.example` are copied to `config.toml` during setup, with placeholders replaced by actual values dynamically.

### Running from source (Linux/macOS/Windows)

If you are running from source (without a packaged binary), use:

```bash
python backend/app/main.py --help
python backend/app/main.py config show
python backend/app/main.py "https://example.com/video"
```

---

## Troubleshooting

### EULA Acceptance

If the EULA has not been accepted (packaged builds only), Alchemux will prompt for acceptance during setup or when running a transmutation. Use the setup wizard to accept interactively:

```bash
alchemux setup
```

To accept non-interactively when transmuting a URL (e.g., in CI):
```bash
alchemux --accept-eula "https://example.com/video"
```

Note: Source code builds (running from Python source) do not require EULA acceptance - they are covered by the Apache 2.0 license.

### Missing Defaults

If `config.toml` is missing or corrupted, run:
```bash
alchemux setup
```
This will restore all default settings from the example template while preserving your secrets in `.env`.
