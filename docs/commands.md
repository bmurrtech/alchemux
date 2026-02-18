# Alchemux Commands

Complete reference for all Alchemux commands and options.

**Install and run:** Use **uv** to try once (`uvx alchemux` / `uvx amx`) or install persistently (`uv tool install alchemux`). Prerequisites: uv and system FFmpeg. See [install.md](install.md).

**Running with uvx (try without installing):**
- **Tier 1:** `uvx alchemux "https://…"` — On first run, config is auto-created in your OS user config dir if missing; then the transmutation runs. `uvx alchemux --help` and `uvx alchemux --version` always work and never require config.
- **Tier 2 (ephemeral, no writes):** `uvx alchemux --no-config --download-dir . "https://…"` — No config files are read or written; downloads go to the given directory.

**Contributors:** Pre-commit hooks are run via [prek](https://github.com/j178/prek). See [contributors.md](contributors.md) for prek install, `prek run --all-files`, and the test suite.

---

## Basic Usage

The primary way to use Alchemux is to provide a URL for media transmutation.

```bash
alchemux [OPTIONS] ["URL"]
alchemux [OPTIONS] -- "URL"
alchemux              # Interactive: prompts for URL (paste, no quotes)
alchemux -p           # Use URL from clipboard (--clipboard)
```

To transmute a URL using current defaults (audio-only, FLAC 16 kHz mono):
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

### Beginner-safe ways to run (no quoting needed)

- **Option A:** Run `alchemux` with no arguments. When prompted, paste the URL (no quotes). Special characters are preserved.
- **Option B:** Copy the media link, then run `alchemux -p` or `alchemux --clipboard` to use the URL from the clipboard (with validation).
- **Option C (advanced):** Use a quoted URL or the `--` delimiter as above.

Tip: Run `alchemux` and paste the URL when prompted to avoid shell quoting issues.

---

## Command Reference Summary

### Flags (One-Time Overrides)
*These flags only apply to the current execution. For persistent configuration, use `alchemux config` wizard.*

| Option | Short | Description |
|--------|-------|-------------|
| `--flac` | | FLAC 16kHz mono conversion (one-time override) |
| `--video` | | Enable video download (one-time override) |
| `--gcp` | | Upload to GCP storage (one-time override) |
| `--s3` | | Upload to S3 storage (one-time override) |
| `--local` | | Save to local storage (one-time override) |
| `--no-config` | | Ephemeral mode: do not read or write config; use `--download-dir` for output. Ideal for `uvx` “no writes” runs. |
| `--download-dir` | | Directory for downloaded/converted files (can be used with or without `--no-config`) |
| `--debug` | | Enable debug mode with full tracebacks (one-time override) |
| `--verbose` | | Enable verbose logging (one-time override) |
| `--plain` | | Disable colors and animations (one-time override) |
| `--clipboard` | `-p` | Use URL from clipboard (paste) |
| `--version` | `-v` | Show version and exit |
| `--help` | `-h` | Show help and exit |

**Key principle:** Flags never persist. For persistent changes, use `alchemux config` wizard.

### Commands

| Command | Description |
|---------|-------------|
| `alchemux setup` | Run interactive setup wizard (first-time setup or reset) |
| `alchemux config` | Launch interactive config wizard (selective updates) |
| `alchemux doctor` | Run configuration diagnostics and guided repairs |
| `alchemux update` | Update yt-dlp to latest stable version |
| `alchemux batch` | Process multiple URLs from files (TXT/CSV), paste, or playlist |

**Note:** All configuration changes are handled through the `alchemux config` wizard.

---

## Main Command Options

### URL (Positional Argument)

The source URL to transmute. Can be from YouTube, Facebook, or any source supported by yt-dlp.

```bash
alchemux "https://youtube.com/watch?v=..."
```

### Format Configuration

**Audio and video formats are configured via `alchemux config` wizard, not command-line flags.**

To change default formats:
1. Run `alchemux config`
2. Select "Audio Settings" or "Video Settings" from the category menu
3. Choose your preferred format from the interactive list

Supported audio formats: `mp3`, `aac`, `alac`, `flac`, `m4a`, `opus`, `vorbis`, `wav`

Supported video formats: `mp4`, `webm`, `mkv`, `mov`

**One-time format override:** Use `--flac` flag for FLAC conversion on a single run.

### Ephemeral mode (`--no-config`)

When you want to run without reading or writing any config (e.g. “try it now” with uvx and no filesystem writes):

```bash
uvx alchemux --no-config --download-dir . "https://youtu.be/…"
```

- **`--no-config`** — Do not load or create config files. Use safe defaults for the run.
- **`--download-dir <path>`** — Where to save downloaded/converted files (required for a sensible no-config run; use `.` for current directory or any path you choose).

`--help` and `--version` never need config and always work, with or without `--no-config`.

---

## Configuration Commands

### `alchemux setup`

Run the interactive setup wizard for first-time setup or to reset configuration.

```bash
alchemux setup              # First-time setup or reset configuration
```

The setup wizard creates configuration files and guides you through initial configuration.
If configuration files already exist, the wizard will refresh them.

### `alchemux config`

Interactive configuration wizard for selective updates.

```bash
alchemux config              # Launch interactive wizard
```

The `alchemux config` wizard allows you to:
- **View current configuration**: Select "Show Configurations" from the menu
- **Modify specific settings**: Select one or more categories to update
- **Guided experience**: Current values shown as defaults, validation built-in

**Available options in the wizard:**
- Show Configurations
- Terminology Setting
- UI Settings
- Logging Settings
- Filesystem Paths
- Audio Media Settings
- Video Media Settings
- FLAC Preset Settings
- Network Settings
- Storage Settings
- S3 Storage Settings (if configured)
- GCP Storage Settings (if configured)

**No command-line options needed** — all configuration via guided UI.

### `alchemux doctor`

Run configuration diagnostics and guided repairs.

```bash
alchemux doctor              # Run diagnostics and offer guided repairs
```

Runs automatic diagnostics to check for common issues:
- Config directory and file existence
- TOML file validity
- Output directory writability
- Cloud storage credential configuration
- Pointer file validity

If issues are found, the doctor offers interactive repair options with automatic backup creation.
No command-line options needed — the doctor is designed to be simple and automatic.

### `alchemux update`

Update yt-dlp to the latest stable version.

```bash
alchemux update              # Check and update if needed (throttled to once per day)
alchemux update --force      # Force update check (bypass throttling)
```

**When to use:**
- If downloads fail with HTTP 403 or extraction errors
- To ensure you have the latest yt-dlp fixes and improvements
- After yt-dlp releases new versions

**How it works:**
- Checks current yt-dlp version
- Compares with latest stable from GitHub
- Uses yt-dlp's built-in `--update-to stable` mechanism
- Update checks are throttled to once per 24 hours (use `--force` to check immediately)

**Note**: This updates the yt-dlp Python package; no Alchemux reinstall is required.

### `alchemux batch`

Process multiple URLs from files (TXT/CSV), paste, or playlist expansion. Each URL runs through the same transmutation pipeline; a delay between items is applied automatically via yt-dlp to reduce 403 and rate-limit risk.

```bash
alchemux batch              # Interactive: choose source, then process
```

**Batch sources:**

- **Files from config dir**:  
  Place your `.txt` or `.csv` batch files in your Alchemux config folder—side by side with `config.toml` and `.env`. If you’re unsure where your config folder is, run:

```bash
amx config         # Select "Show Configurations" to display config directory location
```

  This will display the config directory path.

  Example:

  ```
  config_dir/
  ├── config.toml
  ├── .env
  ├── mylist.txt
  └── links.csv
  ```

  Alchemux scans this directory and lets you select one or more TXT/CSV files. URLs are extracted:
  - For TXT: one per line or comma-separated values.  
  - For CSV: any cell.  
  Comment lines starting with `#`, `;`, or `]` are ignored.

- **Paste URLs**:  
  Paste multiple links (one per line or comma-separated). Submit an empty line to finish.

- **Playlist URL**:  
  Enter a playlist URL; Alchemux expands it to individual entry URLs using yt-dlp. If expansion fails, you can process the playlist URL as a single job or cancel.

**After URLs are loaded:** You can optionally apply one-time overrides (same as single-URL: `--debug`, `--flac`, `--video`, `--local`, `--s3`, `--gcp`, `--verbose`, `--plain`) via a checkbox. Overrides apply to the entire batch run and do not persist.

**Examples:**

```bash
alchemux batch --flac                # Run all batch URLs with FLAC output
alchemux batch --video               # Process batch with video enabled
alchemux batch --debug --plain       # Apply debug and plain output modes to the batch
alchemux batch --local               # Force local output for all URLs in batch
```

You can select these overrides interactively after the URLs are loaded, or by passing them directly on the command line.

**Behavior:** URLs are processed in order. If one fails, the batch continues and a summary (successes/failures) is printed at the end. No batch report file is written by default.

**Note:** Batch mode requires an interactive terminal (TTY). Run `alchemux setup` first if you have not already.

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

### Basic Download (Default FLAC 16 kHz Mono)

```bash
alchemux "https://youtube.com/watch?v=abc123"
```

### Download as FLAC (16kHz Mono)

```bash
alchemux --flac "https://youtube.com/watch?v=abc123"
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
alchemux config  # Select "Storage Settings" → Choose S3
```

### Combined Options

```bash
alchemux --flac --gcp --debug "https://youtube.com/watch?v=abc123"
```

---

## Configuration Files

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

Run from the **repository root** (the directory that contains the `backend/` folder). Do **not** use `python -m app.main` from the repo root; use the path to `main.py`:

```bash
cd /path/to/alchemux
python backend/app/main.py --help
python backend/app/main.py "https://example.com/video"
```

---

## Troubleshooting

### EULA Acceptance

If the EULA has not been accepted, Alchemux will prompt for acceptance during setup or when running a transmutation. Use the setup wizard to accept interactively:

```bash
alchemux setup
```

To accept non-interactively (e.g., in CI for packaged builds), use:

```bash
alchemux --accept-eula          # Accept EULA only
alchemux --accept-eula setup    # Accept EULA, then run setup
```

### Missing Defaults

If `config.toml` is missing or corrupted, run:
```bash
alchemux setup
```
This will restore all default settings from the example template while preserving your secrets in `.env`.

### Update yt-dlp

If downloads fail with HTTP 403 or other extraction errors, try updating yt-dlp:

```bash
alchemux update
```

This command:
- Checks if yt-dlp is outdated
- Updates to the latest stable version automatically
- Throttles checks to once per day (use `--force` to bypass)

**Note**: Update checks are throttled to avoid GitHub API rate limits. The update uses yt-dlp's built-in update mechanism, which is the most reliable method across platforms.

### YouTube 403 / CDN blocking

Alchemux uses a **combined-format** default for audio extraction (`best`): it downloads a single combined stream then extracts audio. This reduces YouTube CDN 403 errors compared to requesting separate audio streams. To use best-audio-only instead (e.g. for non-YouTube sources), set in `config.toml` under `[ytdl]`: `audio_format_selector = "ba"`, or env `YTDL_AUDIO_FORMAT_SELECTOR=ba`. See [yt-dlp #14680](https://github.com/yt-dlp/yt-dlp/issues/14680) for upstream context.
