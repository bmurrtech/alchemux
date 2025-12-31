# Alchemux Commands

Complete reference for all Alchemux commands and options.

---

## Basic Usage

The primary way to use Alchemux is to provide a URL.

```bash
alchemux [url]
```

This automatically performs the full transmutation pipeline: scribe → scry → profile → distill → mux → seal.

---

## Command Reference Summary

### Flags (One-Run Overrides)

| Option | Short | Description |
|--------|-------|-------------|
| `--format` | `-f` | Audio format (mp3, aac, flac, etc.) |
| `--audio-format` | | Audio format (alias for --format) |
| `--video-format` | | Video container (mp4, mkv, etc.) |
| `--flac` | | FLAC 16kHz mono conversion |
| `--save-path` | | Custom download location (one-time) |
| `--gcp` | | Enable GCP upload (one-time) |
| `--s3` | | Enable S3 upload (one-time) |
| `--local` | | Force local storage (override defaults) |
| `--accept-eula` | | Accept EULA non-interactively |
| `--debug` | | Enable debug mode |
| `--plain` | | Disable colors/animations |
| `--version` | `-v` | Show version |
| `--help` | `-h` | Show help |

### Commands (Persistent Configuration)

| Command | Description |
|---------|-------------|
| `alchemux setup` | Run setup wizard |
| `alchemux setup gcp` | Configure GCP storage |
| `alchemux setup s3` | Configure S3 storage |
| `alchemux config` | Launch interactive config wizard |
| `alchemux storage use <target>` | Set default storage (local/s3/gcp) |
| `alchemux storage set <path>` | Set output directory path |
| `alchemux storage status` | Show storage configuration status |

---

## Main Command Options

### URL (Positional Argument)

The source URL to transmute. Can be from YouTube, Facebook, or any source supported by yt-dlp.

```bash
alchemux https://youtube.com/watch?v=...
```

### Format Options

#### `--format`, `-f` (Audio Format)

Specify the audio codec/format. Default: `mp3`

```bash
alchemux --format aac [url]
alchemux -f opus [url]
```

Supported formats: `mp3`, `aac`, `alac`, `flac`, `m4a`, `opus`, `vorbis`, `wav`

#### `--audio-format` (Audio Format Alias)

Alias for `--format`. Use whichever you prefer.

```bash
alchemux --audio-format flac [url]
```

#### `--video-format` (Video Container)

Specify the video container format. Requires ffmpeg.

```bash
alchemux --video-format mkv [url]
alchemux --video-format webm [url]
```

Supported formats: `mp4`, `mkv`, `webm`, `mov`, `avi`, `flv`, `gif`

#### `--flac` (FLAC 16kHz Mono)

Shortcut for FLAC format with 16kHz mono conversion. Equivalent to `--audio-format flac` with optimized settings.

```bash
alchemux --flac [url]
```

---

## Path & Storage Options

### `--save-path`

Set a custom download location for this run only (does not persist).

```bash
alchemux --save-path ~/Music [url]
alchemux --save-path /path/to/downloads [url]
```

### `--gcp` (Google Cloud Storage Upload)

Enable automatic upload to Google Cloud Storage after successful download.

```bash
alchemux --gcp [url]
```

**Prerequisites:**
- GCP storage bucket configured (see `alchemux setup gcp`)
- `storage.gcp.bucket` set in `config.toml`
- `GCP_SA_KEY_BASE64` set in `.env`

**Note:** If GCP is not configured, the setup wizard will automatically run when this flag is used.

### `--s3` (S3-Compatible Storage Upload)

Enable automatic upload to S3-compatible storage after successful download.

```bash
alchemux --s3 [url]
```

**Prerequisites:**
- S3-compatible storage configured (see `alchemux setup s3`)
- `storage.s3.endpoint` and `storage.s3.bucket` set in `config.toml`
- `S3_ACCESS_KEY` and `S3_SECRET_KEY` set in `.env`

**Note:** If S3 is not configured, the setup wizard will automatically run when this flag is used.

### `--local` (Force Local Storage)

Force local storage only, overriding any default cloud upload settings.

```bash
alchemux --local [url]
```

This flag ensures files are saved locally only, regardless of `storage.destination` setting in `config.toml`.

---

## Configuration Commands

### `alchemux setup`

Run the interactive setup wizard.

```bash
alchemux setup              # Full setup refresh (configures all preferences, creates files if missing)
alchemux setup gcp          # Configure GCP Cloud Storage
alchemux setup s3           # Configure S3-compatible storage
```

When run without arguments, the setup wizard guides you through:
- Arcane terminology preference
- Auto-open folder preference
- Output directory configuration
- Cloud storage setup (optional)

The wizard only updates settings you choose to change, preserving existing configuration.

### `alchemux config`

Interactive configuration wizard for config.toml.

```bash
alchemux config    # Launch interactive configuration wizard
```

This command launches an interactive wizard that guides you through reconfiguring existing settings in config.toml. For direct editing, modify `config.toml` manually.

### `alchemux storage`

Manage storage settings and paths.

```bash
alchemux storage use <target>        # Set default storage destination
alchemux storage set <path>          # Set output directory path
alchemux storage status              # Show storage configuration status
```

Where `<target>` is one of: `local`, `s3`, or `gcp`.

Examples:
```bash
alchemux storage use local            # Set default to local storage
alchemux storage use s3              # Set default to S3 storage
alchemux storage use gcp              # Set default to GCP storage
alchemux storage set ~/Downloads     # Set output directory
alchemux storage status              # Show current storage configuration
```

The `storage use` command is a human-friendly alias for `alchemux config set storage.destination <target>`.

### `--accept-eula`

Accept the EULA non-interactively (useful for scripts).

```bash
alchemux --accept-eula [url]
```

Alternatively, set `eula.accepted = true` in `config.toml` to accept non-interactively.

---

## Output Options

### `--plain`

Disable colors and animations (useful for CI/logs).

```bash
alchemux --plain [url]
```

### `--debug`

Enable debug mode with full tracebacks.

```bash
alchemux --debug [url]
```

---

## Information Options

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
alchemux https://youtube.com/watch?v=abc123
```

### Download as FLAC (16kHz Mono)

```bash
alchemux --flac https://youtube.com/watch?v=abc123
```

### Download as Opus

```bash
alchemux --format opus https://youtube.com/watch?v=abc123
```

### Download Video as MKV

```bash
alchemux --video-format mkv https://youtube.com/watch?v=abc123
```

### Download with Custom Path

```bash
alchemux --save-path ~/Music https://youtube.com/watch?v=abc123
```

### Download and Upload to GCP

```bash
alchemux --gcp https://youtube.com/watch?v=abc123
```

### Download and Upload to S3

```bash
alchemux --s3 https://youtube.com/watch?v=abc123
```

### Force Local Storage (Override Defaults)

```bash
alchemux --local https://youtube.com/watch?v=abc123
```

### Set Default Storage Destination

```bash
alchemux storage use s3
```

### Combined Options

```bash
alchemux --format aac --save-path ~/Music --gcp --debug https://youtube.com/watch?v=abc123
```

---

## Configuration Files

Alchemux uses two configuration files:

### `.env` (Secrets Only)

The `.env` file contains **only secrets and sensitive data**:
- `GCP_SA_KEY_BASE64` - GCP service account key
- `S3_ACCESS_KEY` - S3 access key
- `S3_SECRET_KEY` - S3 secret key
- `OAUTH_CLIENT_ID` - OAuth client ID
- `OAUTH_CLIENT_SECRET` - OAuth client secret
- `FACEBOOK_COOKIES_BASE64` - Facebook cookies (if using base64)

See `env.example` for all secret variables.

### `config.toml` (Non-Secret Configuration)

The `config.toml` file contains **user preferences and non-sensitive defaults**:
- `paths.output_dir` - Default download location
- `media.audio.format` - Default audio format
- `storage.destination` - Default storage destination (local/s3/gcp)
- `product.arcane_terms` - Use arcane terminology
- `ui.auto_open` - Auto-open folder after download
- `eula.accepted` - EULA acceptance state

See `config.toml.example` for all available options.

### Managing Configuration

**Edit directly:**
- Edit `config.toml` for non-secret settings
- Edit `.env` for secrets (use `chmod 600 .env` for security)

**Use commands:**
```bash
alchemux config              # Interactive configuration wizard
alchemux storage use <target>    # Set default storage
alchemux storage set <path>      # Set output directory
```

### Default Storage Behavior

By default, files are saved locally only. You can set the default storage destination using:
```bash
alchemux storage use s3    # or 'gcp' or 'local'
```

Or directly:
```bash
alchemux config set storage.destination s3
```

These defaults can be overridden per-run using the `--gcp`, `--s3`, or `--local` flags.

---

## Cloud Storage Configuration

### Google Cloud Storage (GCP)

1. **Run Setup Wizard:**
   ```bash
   alchemux setup gcp
   ```

2. **Manual Configuration:**
   - Set `storage.gcp.bucket` in `config.toml`
   - Set `GCP_SA_KEY_BASE64` in `.env` (base64-encoded service account JSON)

3. **Use:**
   ```bash
   alchemux --gcp [url]
   ```

### S3-Compatible Storage

1. **Run Setup Wizard:**
   ```bash
   alchemux setup s3
   ```

2. **Manual Configuration:**
   - Set `storage.s3.endpoint` and `storage.s3.bucket` in `config.toml`
   - Set `storage.s3.ssl` in `config.toml` (default: `true`)
   - Set `S3_ACCESS_KEY` and `S3_SECRET_KEY` in `.env`

3. **Use:**
   ```bash
   alchemux --s3 [url]
   ```

---

## Troubleshooting

### Missing Configuration Files

If you see a configuration error, run:

```bash
alchemux setup
```

This creates `.env` and `config.toml` files with default settings.

### EULA Not Accepted

On first run, you'll be prompted to accept the EULA. To accept non-interactively:

```bash
alchemux --accept-eula [url]
```

Or set in `config.toml`:
```toml
[eula]
accepted = true
```

### Format Conversion Fails

Some formats require `ffmpeg`. Ensure it's installed:

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### GCP Upload Fails

Verify your configuration:

```bash
alchemux setup gcp
```

Check that `storage.gcp.bucket` is set in `config.toml` and `GCP_SA_KEY_BASE64` is set in `.env`.

---

## Advanced Usage

### Using Technical Terms

To use technical terminology instead of arcane terms, set in `config.toml`:

```toml
[product]
arcane_terms = false
```

Or use the config command:

```bash
alchemux config set product.arcane_terms false
```

See [docs/legend.md](docs/legend.md) for terminology mappings.

### Scripting

For non-interactive use:

```bash
alchemux --accept-eula --plain --format mp3 [url]
```

The `--plain` flag ensures clean output for parsing.

---

For more information about arcane terminology, see [docs/legend.md](docs/legend.md).

