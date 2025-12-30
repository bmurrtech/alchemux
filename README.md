# Alchemux
```
  ___                                             
 -   -_  ,,      ,,                               
(  ~/||  ||      ||                         ,     
(  / ||  ||  _-_ ||/\\  _-_  \/\/\/\ \\ \\ \\ /` 
 \/==||  || ||   || || || \\ || || || || ||  \\   
 /_ _||  || ||   || || ||/   || || || || ||  /\\  
(  - \\, \\ \\,/ \\ |/  \\,/ \\ \\ \\ \\/\\ /  \; 
                   _/                             
```                   
**An arcane-styled yt-dlp CLI wrapper. Download + convert YouTube videos + 1K more -- it's alchemy media magic!**

Alchemux transmutes URLs into purified media vessels through distillation, muxing, and sealing.

## What It Can Do

- **Download & Convert Media**: Extract audio or video from YouTube, Facebook, and other [yt-dlp supported sources](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- **Multiple Formats**: Support for audio formats (MP3, AAC, FLAC, Opus, WAV, etc.) and video containers (MP4, MKV, WebM, etc.)
- **Metadata Embedding**: Automatically embeds source URLs and metadata into media files
- **Cloud Storage**: Optional Google Cloud Storage upload support (see [docs/commands.md](docs/commands.md) for details)
- **Arcane Interface**: Stylized terminal output with unique sigils and progress indicators (can be disabled for technical terms)

## Quick Start

### Installation

#### Option 1: Portable Executable (Recommended)

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

5. **Transmute a URL**:
   - **macOS/Linux**:
     ```bash
     ./alchemux https://youtube.com/watch?v=...
     ```
   - **Windows (CMD)**:
     ```cmd
     alchemux.exe https://youtube.com/watch?v=...
     ```

6. **Get help**:
   - **macOS/Linux**:
     ```bash
     ./alchemux -h
     ```
   - **Windows (CMD)**:
     ```cmd
     alchemux.exe -h
     ```

**Note**: The portable binary includes all dependencies (including ffmpeg/ffprobe) and doesn't require Python or any additional setup beyond the initial configuration wizard.

#### Option 2: Run from Source

For running from source (requires Python 3.8+), see [docs/install.md](docs/install.md) for detailed installation instructions.

---

**See [docs/commands.md](docs/commands.md) for full CLI usage, formats, and options.**

## Arcane Terms

For fun, Alchemux uses arcane-themed terminology (distill, mux, seal, etc.), but if you want to be _boring_ and use technical terms instead, set `ARCANE_TERMS=false` in your `.env` file or as an environment variable.

For a complete legend of arcane terminology and their technical equivalents, see [docs/legend.md](docs/legend.md).

## Configuration

Alchemux uses a `.env` file for configuration. The location depends on how you're running it:

- **Portable binary**: Config is stored next to the binary (if writable) or in your user config directory
- **Source**: Config is stored in the project root

You can specify a custom config location using the `--config` flag:
```bash
amx --config /path/to/custom/.env [url]
```

## Cloud Storage

Alchemux supports optional cloud storage uploads. See [docs/commands.md](docs/commands.md) for configuration details and all available commands.

### Troubleshooting

**Problem**: "Configuration file (.env) not found" after moving the binary

**Solution**: 
1. Find where your config was created (check the setup completion message)
2. Use `--config` to point to that location, or
3. Run `setup` again to create a new config in the new location

**Problem**: Permission errors when creating config

**Solution**: The binary will automatically use your user config directory if the binary location isn't writable. You can also use `--config` to specify a writable location.

## Contributing

Feature requests, bug reports, and contributions are welcome!

## Acknowledgements

Alchemux relies on these excellent projects:

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - Media downloader and converter (core functionality)
- **[FFmpeg](https://ffmpeg.org/)** - Audio and video conversion (included in portable binaries)
- **[Typer](https://typer.tiangolo.com/)** - Modern CLI framework
- **[Rich](https://github.com/Textualize/rich)** - Beautiful terminal output and progress bars
- **[mutagen](https://github.com/quodlibet/mutagen)** - Audio metadata handling
- **[python-dotenv](https://github.com/theskumar/python-dotenv)** - Environment variable management
- **[PyInstaller](https://www.pyinstaller.org/)** - Binary packaging
- **[termcolor](https://github.com/termcolor/termcolor)** - Terminal color support

Special thanks to the yt-dlp community for their incredible work on media extraction and conversion.

## EULA

Prebuilt releases distributed by the project maintainer may require acceptance of additional Release Terms (`EULA.md`) before enabling functionality. These Release Terms apply only to official releases.

---
Made with ❤️ for open-source.
