# Alchemux Commands

Complete reference for all Alchemux commands and options.

---

## Basic Usage

The primary way to use Alchemux is to provide a URL:

```bash
amx [url]
```

Or with the full command name:

```bash
alchemux [url]
```

This automatically performs the full transmutation pipeline: scribe → scry → profile → distill → mux → seal.

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
amx --gcp [url]
```

**Prerequisites:**
- GCP storage bucket configured (see `setup gcp`)
- `GCP_STORAGE_BUCKET` and `GCP_SA_KEY_BASE64` set in `.env`

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

### `--accept-eula`

Accept the EULA non-interactively (useful for scripts).

```bash
amx --accept-eula [url]
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
amx --gcp https://youtube.com/watch?v=abc123
```

### Combined Options

```bash
amx --format aac --save-path ~/Music --gcp --verbose https://youtube.com/watch?v=abc123
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

See `env.example` for all available options.

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
   amx --gcp [url]
   ```

### S3-Compatible Storage

1. **Run Setup Wizard:**
   ```bash
   amx setup s3
   ```

2. **Manual Configuration:**
   - Set `S3_ENDPOINT` in `.env`
   - Set `S3_ACCESS_KEY` in `.env`
   - Set `S3_SECRET_KEY` in `.env`
   - Set `S3_BUCKET` in `.env`

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
| `--gcp` | | Enable GCP upload |
| `--setup` | | Run setup wizard |
| `--accept-eula` | | Accept EULA non-interactively |
| `--verbose` | | Enable debug logging |
| `--debug` | | Enable debug mode |
| `--plain` | | Disable colors/animations |
| `--version` | `-v` | Show version |
| `--help` | `-h` | Show help |

---

For more information about arcane terminology, see [docs/legend.md](docs/legend.md).

