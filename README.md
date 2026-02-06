# Alchemux

**Magically intuitive and interactive CLI wrapper for yt-dlp & FFmpeg** with **cloud upload** optionality (S3-compatible, GCP Buckets). Download & convert YouTube videos + 1K more sources — it's alchemy media magic!

## CLI Showcase

![transmuting](https://i.imgur.com/coG2REg.png)
![usage](https://i.imgur.com/iDFjVCw.png)

## Features

- 🎵 **Download & Convert Media**: Extract audio or video from YouTube, Facebook, and other [yt-dlp supported sources](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- 🧙‍♂️ **Interactive Simplicity**: Delightfully easy terminal UI—just run and follow prompts; configure everything in seconds (including cloud storage and presets) interactively
- 📋 **Batch Processing**: Process many URLs from a YouTube playlist, or TXT/CSV files, or paste a list of URLs with automatic rate-limit mitigation logic built-in
- 🏷️ **Metadata Embedding**: Automatically embeds source URLs and metadata into media files so you don't have to
- ☁️ **Cloud Storage**: Upload media to **S3** and **GCP buckets** by configuring your cloud storage settings; to enable cloud media storage (see [docs/commands.md](docs/commands.md) for more details)
- 🎚️ **Multiple Formats**: Support for audio formats (MP3, AAC, FLAC, Opus, WAV, etc.) and video containers (MP4, MKV, WebM, etc.)
- ✨ **Arcane Interface**: Stylized terminal output with unique sigils and progress indicators (can be disabled for technical terms)

For a fuller list of features, commands, and options, see [docs/commands.md](docs/commands.md).

## Quick Start

### Prerequisites

- **Shell**: Terminal (macOS/Linux) or PowerShell (Windows)
- **uv**: [Astral’s uv](https://docs.astral.sh/uv/) — fast Python package and project manager (one-time install below)
- **FFmpeg**: Required for audio/video conversion. Install via your system package manager — see [docs/install.md](docs/install.md) for platform-specific steps.

### Installation (recommended): uv + PyPI

Alchemux is distributed as a Python CLI from PyPI. Installing with **uv** avoids macOS Gatekeeper and Windows SmartScreen prompts that often affect downloaded executables.

#### 1) Install uv (one-time)

**macOS/Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify: `uv --version`

#### 2) Try without installing

```bash
uvx alchemux --help                              # always works (no config needed)
uvx amx -h
uvx amx "https://youtu.be/…"                # first run: auto-creates config, then runs
uvx amx --no-config --download-dir . "…"    # ephemeral: no config read/write
```

#### 3) Install as a persistent CLI tool

```bash
uv tool install alchemux
```

Then run from any directory:

```bash
alchemux setup    # first-time setup
alchemux "https://youtu.be/…"
amx "https://…"   # same CLI, shorter name
```

#### 4) Upgrade / Uninstall

```bash
uv tool upgrade alchemux
uv tool uninstall alchemux
```

For running from **source** (development), see [docs/install.md](docs/install.md).

## Arcane Terms

For fun, Alchemux uses arcane-themed terminology (transmute, distill, seal, etc.), but if you want technical terms instead, set `arcane_terms = "false"` in your `config.toml` or select technical terms during `alchemux setup` runtime.

For a complete legend of arcane terminology and their technical equivalents, see [docs/legend.md](docs/legend.md).

## Known Issues & Limitations

**Pre-Release Status**: Alchemux is currently in pre-release. Bugs and limitations are expected. Please report issues via GitHub Issues.

### YouTube HTTP 403 Errors (Video Downloads)

**Symptom**: Downloads fail with "HTTP 403 Forbidden" errors, especially for video formats.

**Root Cause**: YouTube's anti-bot detection measures. This affects video downloads.

## Contributors welcome

Feature requests, bug reports, and contributions are welcome. We use **[prek](https://github.com/j178/prek)** for pre-commit hooks so CI and local checks stay in sync.

**Before you start:** See **[docs/contributors.md](docs/contributors.md)** for:

- Installing prek and running the test suite
- Pre-commit best practice (`prek install --install-hooks`, `prek run --all-files`)
- [Tests README](backend/app/tests/README.md)

**Submitting a PR (best practice):**

1. **Run hooks locally** so CI passes: `prek run --all-files` (from repo root).
2. **Run the test suite**: `pytest backend/app/tests -q` (see [backend/app/tests/README.md](backend/app/tests/README.md)).
3. **Keep PRs focused** — one logical change per PR; reference any related issue.
4. **No secrets** — never commit credentials, API keys, or tokens; use `env.example` as a template.
5. **Branch from `main`** and ensure your branch is up to date before opening the PR.

## Troubleshooting

**Get help:**

```bash
alchemux -h
# or
amx -h
```

**Problem**: "Configuration file (.env) not found"

**Solution**: Run `alchemux setup` to create config, or use `alchemux doctor` to diagnose. Config is stored in OS-standard per-user directories (see [docs/install.md](docs/install.md)).

**Problem**: Downloads fail

**Solution**:

1. Try audio extraction instead: `alchemux --audio-format mp3 "URL"`
2. Update yt-dlp: `alchemux update`
3. If issues persist, this may be YouTube anti-bot detection (see Known Issues above)

**Problem**: "ffmpeg not found"

**Solution**: Alchemux requires **system FFmpeg**. Install it for your OS (e.g. `brew install ffmpeg`, `apt install ffmpeg`, or `choco install ffmpeg`) — see [docs/install.md](docs/install.md).

## Acknowledgements

Alchemux relies on these excellent projects:

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - Media downloader and converter (core functionality)
- **[FFmpeg](https://ffmpeg.org/)** - Audio and video conversion (system install required)
- **[uv](https://docs.astral.sh/uv/)** (Astral) - Python package and project manager; install and run Alchemux via `uv tool install` / `uvx`
- **[prek](https://github.com/j178/prek)** - Pre-commit replacement (Rust); runs format, lint, and repo-hygiene hooks in CI and locally ([docs/contributors.md](docs/contributors.md))
- **[PyPI](https://pypi.org/)** - Python package index for distribution
- **[Typer](https://typer.tiangolo.com/)** - Modern CLI framework
- **[Rich](https://github.com/Textualize/rich)** - Terminal output, progress bars, and styling
- **[InquirerPy](https://github.com/kazhala/InquirerPy)** - Interactive CLI wizards
- **[pyperclip](https://github.com/pyperclip/pyperclip)** - Clipboard URL input for `-p`/`--clipboard`
- **[mutagen](https://github.com/quodlibet/mutagen)** - Audio metadata handling
- **[python-dotenv](https://github.com/theskumar/python-dotenv)** - Environment variable management

## License

Open source under the **GNU AGPLv3**—see `[LICENSE](LICENSE)` for terms.
Commercial licensing available—contact maintainers for details.
