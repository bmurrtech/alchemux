# Alchemux

**Magically intuitive and interactive CLI wrapper for yt-dlp & FFmpeg** with **cloud upload** optionality (S3-compatible, GCP Buckets). Download & convert YouTube videos + 1K more sources — it's alchemy media magic!

## CLI Showcase

![transmuting](https://i.imgur.com/coG2REg.png)
![usage](https://i.imgur.com/iDFjVCw.png)

## Features

- 🎵 **Download & Convert Media**: Extract audio or video from YouTube, Facebook, and other [yt-dlp supported sources](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- 🧙‍♂️ **Interactive Simplicity**: Delightfully easy terminal UI—just run and follow prompts; configure everything in seconds (including cloud storage and presets) interactively
- 📋 **Batch Processing**: Process many URLs from a YouTube playlist, TXT/CSV files, or pasted lists of URLs with automatic rate-limit mitigation logic built-in. See [commands.md](docs/commands.md) for more details about batch mode and usage
- 🏷️ **Metadata Embedding**: Automatically embeds source URLs and metadata into media files so you don't have to
- ☁️ **Cloud Storage**: Upload media to **S3** and **GCP buckets** by configuring your cloud storage settings; to enable cloud media storage (see [docs/commands.md](docs/commands.md) for more details)
- 🎚️ **Multiple Formats**: Support for audio formats (MP3, AAC, FLAC, Opus, WAV, etc.) and video containers (MP4, MKV, WebM, etc.)
- 🤖 **AI Agent Support**: Give your AI assistant media downloading power! Supports AI agents like [OpenClaw](https://openclaw.ai) (formerly Clawdbot/Moltbot), [Agent Zero](https://github.com/agent0ai/agent-zero), and **Claude Skills**. AI agents, see [backend/AGENTS.md](backend/AGENTS.md).
- 🛠️ **No-Edit Configuration (`config` Command)**: Configure every aspect of Alchemux—media formats, cloud credentials, download folder, batch defaults, and more—**directly in an interactive wizard**. No need to open or edit any files.
- 🩺 **Troubleshooting Assistant (`doctor` Command)**: Having trouble? Instantly diagnose and resolve common issues, from cloud misconfigurations to missing dependencies, file permission errors, and more. Get clear, actionable help.
- ✨ **Arcane Interface**: Stylized terminal output with unique sigils and progress indicators (can be disabled for technical terms)
- 🔄 **Easy Updater (`update` Command)**: Quickly update the underlying downloader to always have the latest and greatest from the yt-dlp community

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

### Nightly / Experimental: Run from source (latest development version)

This method is recommended only if you want to use the **latest (unreleased, experimental, or nightly)** Alchemux features direct from the GitHub source.

First, clone the repository:

```bash
git clone https://github.com/bmurrtech/alchemux.git
cd alchemux
```

Then, from the repository root (no venv activation required):

```bash
uv pip install -e .
uv run alchemux --help
uv run amx -v
uv run amx setup
uv run amx "https://…"
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

**Default behavior**: Video is disabled by default for reliability. Audio-only transmutation remains the stable path. To include video for one run, pass `--video`.

## Contributors welcome

**For human contributors:** Feature requests, bug reports, and contributions are welcome. We use **[prek](https://github.com/j178/prek)** for pre-commit hooks so CI and local checks stay in sync.

**Before you start:** See **[docs/contributors.md](docs/contributors.md)** for:

- Installing prek and running the test suite
- Pre-commit best practice (`prek install --install-hooks`, `prek run --all-files`)
- [Tests README](backend/app/tests/README.md)

**Submitting a PR (best practice):**

Before submitting a pull request, please **read [docs/contributors.md](docs/contributors.md)** for detailed contributor guidance, workflow, and required developer setup.

1. **Run pre-commit hooks locally** to ensure your changes pass quality gates:  
   `prek run --all-files` (from the repo root).
2. **Run the test suite**:  
   `uv run python -m pytest backend/app/tests -q`  
   (No venv activation needed; see [backend/app/tests/README.md](backend/app/tests/README.md). With an activated venv, you can also use `pytest backend/app/tests -q`.)
3. **Keep pull requests focused** — make one logical change per PR, and reference any related issues.
4. **Do not commit secrets** — never check in credentials, API keys, tokens, or sensitive data. Use `env.example` as a model for any environment settings.
5. **Branch from `main`** and ensure your branch is up to date before opening a PR.

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

1. Try the default audio-only run (or force FLAC): `alchemux "URL"` or `alchemux --flac "URL"`
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

Open source under the **GNU AGPLv3**—see [LICENSE](LICENSE) for terms.

### License Philosophy (Plain English)

This project is licensed under GNU AGPLv3.

That means:

- **You may use it commercially.**
- **You may build a paid SaaS product with it.**
- **You may modify it.**

However:

- **Hosted Service or SaaS:** If you run this software as part of a hosted service or SaaS product, you must provide your users access to the corresponding source code, including any modifications you have made.
- **Distribution:** If you distribute this software (or a derivative), you must include the same license and provide source code.
- **Openness:** This ensures improvements remain **open** and the community benefits from derivative work.

If you want to use this project in a proprietary or closed-source product without AGPL obligations, a commercial license is available.

---

#### Commercial / Proprietary Licensing

Need any of the following?
- Commercial use **without** copyleft obligations
- Proprietary or closed-source usage
- SaaS or hosted deployment without source disclosure
- Embedded or internal distribution without attribution

**Commercial licenses are available.**

These licenses waive AGPL-3.0 copyleft requirements, including:
- No obligation to publish source code
- No public attribution requirements
- SaaS, hosted, and embedded use allowed

**How to obtain a commercial license:**  
_Open a GitHub Issue in this project’s repository to contact the maintainers for licensing and pricing details._
