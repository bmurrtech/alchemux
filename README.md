# Alchemux

**Magically intuitive and interactive CLI wrapper for yt-dlp** with **cloud upload** support. Download & convert YouTube videos + 1K more sources — it's alchemy media magic!

## CLI Showcase
![transmuting](https://i.imgur.com/coG2REg.png)
![usage](https://i.imgur.com/iDFjVCw.png)

## Features

- **Download & Convert Media**: Extract audio or video from YouTube, Facebook, and other [yt-dlp supported sources](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- **Interactive Simplictity**: Delightfully easy terminal UI—just run and follow prompts; configure everything in seconds (including cloud storage and presets) interactively
- **Batch Processing**: Process many URLs from a YouTube playlist, or TXT/CSV files, or paste a list of URLs with automatic rate-limit mitigation logic built-in
- **Metadata Embedding**: Automatically embeds source URLs and metadata into media files so you don't have to
- **Cloud Storage**: Upload media to **S3** and **GCP buckets** by configuring your cloud storage settings; to enable cloud media storage (see [docs/commands.md](docs/commands.md) for more details)
- **Multiple Formats**: Support for audio formats (MP3, AAC, FLAC, Opus, WAV, etc.) and video containers (MP4, MKV, WebM, etc.)
- **Arcane Interface**: Stylized terminal output with unique sigils and progress indicators (can be disabled for technical terms)

For a fuller list of features, commands, and options, see [docs/commands.md](docs/commands.md).

## Quick Start

### Installation

#### Option 1: Portable Executable (Not Latest)

1. **Download the binary** for your platform from the [releases page](https://github.com/bmurrtech/alchemux/releases).
   - **macOS**: `alchemux`
   - **Linux**: `alchemux`
   - **Windows**: `alchemux.exe`

2. **Make it executable** (macOS/Linux only):
   ```bash
   chmod +x alchemux
   ```

3. **Open your terminal** and navigate to where you downloaded the binary.

4. **Run setup** (first time only):
   - **macOS/Linux**:
     ```bash
     ./alchemux setup
     ```
   - **Windows (CMD)**:
     ```cmd
     alchemux.exe setup
     ```

5. **Transmute/Convert a URL**:
   - **macOS/Linux**:
     ```bash
     ./alchemux
     ```
   - **Windows (CMD)**:
     ```cmd
     alchemux.exe
     ```

#### Option 2: Run from Source (Latest, Experimental Builds)

For running from source (requires Python 3.8+), see [docs/install.md](docs/install.md) for detailed installation instructions.

## Arcane Terms

For fun, Alchemux uses arcane-themed terminology (transmute, distill, seal, etc.), but if you want technical terms instead, set `arcane_terms = "false"` in your `config.toml` or select technical terms during `alchemux setup` runtime.

For a complete legend of arcane terminology and their technical equivalents, see [docs/legend.md](docs/legend.md).

## Known Issues & Limitations

**⚠️ Pre-Release Status**: Alchemux is currently in pre-release. Bugs and limitations are expected. Please report issues via GitHub Issues.

### YouTube HTTP 403 Errors (Video Downloads)

**Symptom**: Downloads fail with "HTTP 403 Forbidden" errors, especially for video formats.

**Root Cause**: YouTube's anti-bot detection measures. This affects video downloads.

## Contributing

Feature requests, bug reports, and contributions are welcome!

## Troubleshooting

**Get help**:
   - **macOS/Linux**:
     ```bash
     ./alchemux -h
     ```
   - **Windows (CMD)**:
     ```cmd
     alchemux.exe -h
     ```
**Problem**: "Configuration file (.env) not found" after moving the binary

**Solution**: 
1. Find where your config was created (check the setup completion message)
2. Use `alchemux doctor`, or
3. Run `alchemux setup` again to create a new config

**Problem**: Downloads fail

**Solution**: 
1. Try audio extraction instead: `alchemux --audio-format mp3 "URL"`
2. Update yt-dlp: `alchemux update`
3. If issues persist, this may be YouTube anti-bot detection (see Known Issues above)

## Acknowledgements

Alchemux relies on these excellent projects:

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - Media downloader and converter (core functionality)
- **[FFmpeg](https://ffmpeg.org/)** - Audio and video conversion (included in portable binaries)
- **[Typer](https://typer.tiangolo.com/)** - Modern CLI framework
- **[Rich](https://github.com/Textualize/rich)** - Terminal output, progress bars, and styling
- **[InquirerPy](https://github.com/kazhala/InquirerPy)** - Interactive CLI wizards.
- **[pyperclip](https://github.com/pyperclip/pyperclip)** - Clipboard URL input for `-p`/`--clipboard`.
- **[mutagen](https://github.com/quodlibet/mutagen)** - Audio metadata handling
- **[python-dotenv](https://github.com/theskumar/python-dotenv)** - Environment variable management
- **[PyInstaller](https://www.pyinstaller.org/)** - Binary packaging
Special thanks to the yt-dlp and FFmpeg communities for their incredible work on media extraction and conversion.

## EULA

Prebuilt releases distributed by the project maintainer may require acceptance of additional Release Terms (`EULA.md`) before enabling functionality.

---
Made with ❤️ for open-source.