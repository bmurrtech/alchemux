# Alchemux Commands

Complete reference for all Alchemux commands and options.

---

## Basic Usage

The primary way to use Alchemux is to provide a URL.

```bash
amx [url]
```

Or with the full command name:

```bash
alchemux [url]
```

This automatically performs the full transmutation pipeline: scribe → scry → profile → distill → mux → seal.

**Note**: The binary supports both `alchemux` and `amx` as command names. If you prefer the shorter `amx` command, you can create an alias:
- **Unix/macOS/Linux**: `ln -s alchemux amx` (creates a symlink)
- **Windows**: Copy `alchemux.exe` to `amx.exe` (or create a batch file)

**Optional**: Create a symlink or alias for easier access:
   ```bash
   ln -s $(pwd)/backend/app/main.py /usr/local/bin/alchemux
   # or add to your shell profile:
   alias alchemux='python /path/to/alchemux/backend/app/main.py'
   alias amx='python /path/to/alchemux/backend/app/main.py'  # shorter alias
   ```

---

## Main Command Options

### URL (Positional Argument)

The source URL to transmute. Can be from YouTube, Facebook, or any source supported by yt-dlp.

```bash
amx https://youtube.com/watch?v=...
```

### Format Options

#### `--format`, `-f` (Audio Format)

Specify the audio codec/format. Default: `mp3`

```bash
amx --format aac [url]
amx -f opus [url]
```

Supported formats: `mp3`, `aac`, `alac`, `flac`, `m4a`, `opus`, `vorbis`, `wav`

#### `--audio-format` (Audio Format Alias)

Alias for `--format`. Use whichever you prefer.

```bash
amx --audio-format flac [url]
```

#### `--video-format` (Video Container)

Specify the video container format. Requires ffmpeg.

```bash
amx --video-format mkv [url]
amx --video-format webm [url]
```

Supported formats: `mp4`, `mkv`, `webm`, `mov`, `avi`, `flv`, `gif`

#### `--flac` (FLAC 16kHz Mono)

Shortcut for FLAC format with 16kHz mono conversion. Equivalent to `--audio-format flac` with optimized settings.

```bash
amx --flac [url]
```

---

## Path & Storage Options

### `--save-path`

Set a custom download location. This updates your `.env` file automatically.

```bash
amx --save-path ~/Music [url]
amx --save-path /path/to/downloads [url]
```

### `--gcp` (Google Cloud Storage Upload)

Enable automatic upload to Google Cloud Storage after successful download.

```bash
alchemux --gcp [url]
```

**Prerequisites:**
- GCP storage bucket configured (see `setup gcp`)
- `GCP_STORAGE_BUCKET` and `GCP_SA_KEY_BASE64` set in `.env`

**Note:** If GCP is not configured, the setup wizard will automatically run when this flag is used.

### `--s3` (S3-Compatible Storage Upload)

Enable automatic upload to S3-compatible storage after successful download.

```bash
alchemux --s3 [url]
```

**Prerequisites:**
- S3-compatible storage configured (see `setup s3`)
- `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, and `S3_BUCKET` set in `.env`

**Note:** If S3 is not configured, the setup wizard will automatically run when this flag is used.

### `--local` (Force Local Storage)

Force local storage only, overriding any default cloud upload settings.

```bash
alchemux --local [url]
```

This flag ensures files are saved locally only, regardless of `GCP_UPLOAD_ENABLED` or `S3_UPLOAD_ENABLED` settings.

---

## Configuration Options

### `--setup` (Setup Wizard)

Run the interactive setup wizard.

```bash
amx setup              # Minimal setup (creates .env, handles EULA)
amx setup gcp          # Configure GCP Cloud Storage
amx setup s3           # Configure S3-compatible storage
```

Or use the flag:

```bash
amx --setup
amx --setup gcp
```

### `--save-default` (Set Default Storage)

Interactively set the default storage destination for all future transmutations.

```bash
alchemux --save-default
```

This command displays an interactive menu where you can select:
- **Local**: Save files locally only (no cloud upload)
- **GCP**: Upload to Google Cloud Platform by default
- **S3**: Upload to S3-compatible storage by default

The selected default is saved to your `.env` file and can be overridden per-run using `--gcp`, `--s3`, or `--local` flags.

### `--accept-eula`

Accept the EULA non-interactively (useful for scripts).

```bash
alchemux --accept-eula [url]
```

---

## Output Options

### `--plain`

Disable colors and animations (useful for CI/logs).

```bash
amx --plain [url]
```

### `--verbose`

Enable debug logging with detailed output.

```bash
amx --verbose [url]
```

### `--debug`

Enable debug mode with full tracebacks.

```bash
amx --debug [url]
```

---

## Information Options

### `--version`, `-v`

Display version information and exit.

```bash
amx --version
amx -v
```

### `--help`, `-h`

Display help information.

```bash
amx --help
amx -h
```

---

## Examples

### Basic Download (MP3)

```bash
amx https://youtube.com/watch?v=abc123
```

### Download as FLAC (16kHz Mono)

```bash
amx --flac https://youtube.com/watch?v=abc123
```

### Download as Opus

```bash
amx --format opus https://youtube.com/watch?v=abc123
```

### Download Video as MKV

```bash
amx --video-format mkv https://youtube.com/watch?v=abc123
```

### Download with Custom Path

```bash
amx --save-path ~/Music https://youtube.com/watch?v=abc123
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
alchemux --save-default
```

### Combined Options

```bash
alchemux --format aac --save-path ~/Music --gcp --verbose https://youtube.com/watch?v=abc123
```

---

## Environment Variables

Alchemux reads configuration from your `.env` file. Key variables:

- `DOWNLOAD_PATH` - Default download location
- `AUDIO_FORMAT` - Default audio format
- `VIDEO_FORMAT` - Default video format
- `ARCANE_TERMS` - Use arcane terminology (default: `true`)
- `AUTO_OPEN` - Auto-open folder after download (default: `false`)
- `GCP_STORAGE_BUCKET` - GCP bucket name (for `--gcp`)
- `GCP_SA_KEY_BASE64` - GCP service account key (for `--gcp`)
- `GCP_UPLOAD_ENABLED` - Enable GCP upload by default (default: `false`)
- `S3_ENDPOINT` - S3-compatible storage endpoint (for `--s3`)
- `S3_ACCESS_KEY` - S3 access key (for `--s3`)
- `S3_SECRET_KEY` - S3 secret key (for `--s3`)
- `S3_BUCKET` - S3 bucket name (for `--s3`)
- `S3_UPLOAD_ENABLED` - Enable S3 upload by default (default: `false`)

See `env.example` for all available options.

### Default Storage Behavior

By default, files are saved locally only. You can set `GCP_UPLOAD_ENABLED=true` or `S3_UPLOAD_ENABLED=true` in your `.env` file to enable automatic cloud uploads for all transmutations. These defaults can be overridden per-run using the `--gcp`, `--s3`, or `--local` flags.

Use `alchemux --save-default` to interactively set your default storage destination.

---

## Cloud Storage Configuration

### Google Cloud Storage (GCP)

1. **Run Setup Wizard:**
   ```bash
   amx setup gcp
   ```

2. **Manual Configuration:**
   - Set `GCP_STORAGE_BUCKET` in `.env`
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
   - Set `S3_ENDPOINT` in `.env`
   - Set `S3_ACCESS_KEY` in `.env`
   - Set `S3_SECRET_KEY` in `.env`
   - Set `S3_BUCKET` in `.env`
   - Set `S3_SSL` in `.env` (default: `true`)

3. **Use:**
   ```bash
   alchemux --s3 [url]
   ```

---

## Troubleshooting

### Missing .env File

If you see a configuration error, run:

```bash
amx setup
```

This creates a `.env` file with default settings.

### EULA Not Accepted

On first run, you'll be prompted to accept the EULA. To accept non-interactively:

```bash
amx --accept-eula [url]
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
amx setup gcp
```

Check that `GCP_STORAGE_BUCKET` and `GCP_SA_KEY_BASE64` are set correctly in `.env`.

---

## Advanced Usage

### Using Technical Terms

To use technical terminology instead of arcane terms, set in `.env`:

```
ARCANE_TERMS=false
```

Or as an environment variable:

```bash
ARCANE_TERMS=false amx [url]
```

See [docs/legend.md](docs/legend.md) for terminology mappings.

### Scripting

For non-interactive use:

```bash
amx --accept-eula --plain --format mp3 [url]
```

The `--plain` flag ensures clean output for parsing.

---

## Command Reference Summary

| Option | Short | Description |
|--------|-------|-------------|
| `--format` | `-f` | Audio format (mp3, aac, flac, etc.) |
| `--audio-format` | | Audio format (alias for --format) |
| `--video-format` | | Video container (mp4, mkv, etc.) |
| `--flac` | | FLAC 16kHz mono conversion |
| `--save-path` | | Custom download location |
| `--gcp` | | Enable GCP upload (one-time) |
| `--s3` | | Enable S3 upload (one-time) |
| `--local` | | Force local storage (override defaults) |
| `--save-default` | | Set default storage destination interactively |
| `--setup` | | Run setup wizard |
| `--accept-eula` | | Accept EULA non-interactively |
| `--verbose` | | Enable debug logging |
| `--debug` | | Enable debug mode |
| `--plain` | | Disable colors/animations |
| `--version` | `-v` | Show version |
| `--help` | `-h` | Show help |

---

For more information about arcane terminology, see [docs/legend.md](docs/legend.md).

