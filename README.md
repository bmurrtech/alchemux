# Alchemux
  ___                                             
 -   -_  ,,      ,,                               
(  ~/||  ||      ||                         ,     
(  / ||  ||  _-_ ||/\\  _-_  \/\/\/\ \\ \\ \\ /` 
 \/==||  || ||   || || || \\ || || || || ||  \\   
 /_ _||  || ||   || || ||/   || || || || ||  /\  
(  - \\, \\ \\,/ \\ |/  \\,/ \\ \\ \\ \\/\\ /  \; 
                   _/                             
**An arcane-styled yt-dlp CLI wrapper. Download YouTube videos + 1K more -- it's alchemy media magic!**

Alchemux transmutes URLs into purified media vessels through distillation, muxing, and sealing. Built on yt-dlp, it provides a stylized command-line interface for downloading and converting media from various sources.

## What It Can Do

- **Download & Convert Media**: Extract audio or video from YouTube, Facebook, and other [yt-dlp supported sources](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- **Multiple Formats**: Support for audio formats (MP3, AAC, FLAC, Opus, WAV, etc.) and video containers (MP4, MKV, WebM, etc.)
- **Metadata Embedding**: Automatically embeds source URLs and metadata into media files
- **Cloud Storage**: Optional Google Cloud Storage upload support (see [docs/commands.md](docs/commands.md) for details)
- **Arcane Interface**: Stylized terminal output with unique sigils and progress indicators (can be disabled for technical terms)

## Quick Start

1. **Run Setup**:
   ```bash
   amx setup
   ```
   Or use the full command: `alchemux setup`

2. **Transmute a URL**:
   ```bash
   amx [url]
   ```
   Example: `amx https://youtube.com/watch?v=...`

3. **Get Help**:
   ```bash
   amx --help
   ```

## Arcane Terms

For fun, Alchemux uses arcane-themed terminology (distill, mux, seal, etc.), but if you want to be _boring_ and use technical terms instead, set `ARCANE_TERMS=false` in your `.env` file or as an environment variable.

For a complete legend of arcane terminology and their technical equivalents, see [docs/legend.md](docs/legend.md).

## Cloud Storage

Alchemux supports optional cloud storage uploads. See [docs/commands.md](docs/commands.md) for configuration details and all available commands.

## Contributing

Feature requests, bug reports, and contributions are welcome!

## Acknowledgements

Alchemux relies on these excellent projects:

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - Media downloader and converter (core functionality)
- **[Typer](https://typer.tiangolo.com/)** - Modern CLI framework
- **[Rich](https://github.com/Textualize/rich)** - Beautiful terminal output and progress bars
- **[mutagen](https://github.com/quodlibet/mutagen)** - Audio metadata handling
- **[python-dotenv](https://github.com/theskumar/python-dotenv)** - Environment variable management
- **[PyInstaller](https://www.pyinstaller.org/)** - Binary packaging
- **[termcolor](https://github.com/termcolor/termcolor)** - Terminal color support

Special thanks to the yt-dlp community for their incredible work on media extraction and conversion.

## License

Source code is licensed under the Apache License 2.0 (see `LICENSE`).

## EULA

Official prebuilt releases distributed by the project maintainer may require acceptance of additional Release Terms (`EULA.md`) before enabling functionality. These Release Terms apply only to official releases and do not modify the Apache 2.0 license for the source code.

---
Made with ❤️ for open-source.
