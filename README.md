<div align="center">

# Alchemux

**Magically intuitive CLI for yt-dlp & FFmpeg** — download, convert, and optionally upload to **S3** or **GCP**.

*Interactive terminal alchemy for YouTube and 1,000+ media sources.*

[![Star on GitHub](https://img.shields.io/badge/Star-on_GitHub-blue?logo=github)](https://github.com/bmurrtech/alchemux)
[![PyPI version](https://img.shields.io/pypi/v/alchemux?label=pypi)](https://pypi.org/project/alchemux/)
[![PyPI downloads](https://img.shields.io/pypi/dm/alchemux?label=downloads&color=success)](https://pypi.org/project/alchemux/)
[![CI](https://img.shields.io/github/actions/workflow/status/bmurrtech/alchemux/ci.yml?branch=main&logo=github&label=CI)](https://github.com/bmurrtech/alchemux/actions/workflows/ci.yml?query=branch%3Amain)
[![Latest Release](https://img.shields.io/github/v/release/bmurrtech/alchemux?include_prereleases&label=release&logo=github)](https://github.com/bmurrtech/alchemux/releases)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-blue.svg)](https://docs.astral.sh/uv/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![uv](https://img.shields.io/badge/distributed_with-uv-DE5FE9.svg)](https://docs.astral.sh/uv/)
[![License: AGPL v3](https://img.shields.io/badge/license-GNU%20AGPLv3-blue.svg)](LICENSE)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support-FF5E5B?logo=ko-fi)](https://ko-fi.com/bmurrtech)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Support-FFDD00?logo=buymeacoffee&logoColor=black)](https://www.buymeacoffee.com/bmurrtech)

<p align="center">
  <img src="https://i.imgur.com/coG2REg.png" width="700" alt="Alchemux CLI transmuting media">
  <br><br>
  <img src="https://i.imgur.com/iDFjVCw.png" width="700" alt="Alchemux usage example">
</p>

</div>

## About

Alchemux is a **terminal-first** media CLI built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) and **system FFmpeg**. It wraps complex download and conversion workflows in an interactive wizard, batch mode, optional cloud upload, and arcane (or plain) terminal output.

- **Distribution**: [PyPI](https://pypi.org/project/alchemux/) — install with [uv](https://docs.astral.sh/uv/) (`uv tool install` / `uvx`)
- **Platforms**: macOS, Linux, Windows (shell + Python 3.12+)
- **Config**: Per-user TOML via `alchemux setup` — no manual file editing required
- **Status**: Pre-release — bugs and limitations are expected; see [docs/known-issues.md](docs/known-issues.md)

## Features

- 🎵 **Download & Convert Media**: Extract audio or video from YouTube, Facebook, and other [yt-dlp supported sources](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- 🧙‍♂️ **Interactive Simplicity**: Delightfully easy terminal UI—just run and follow prompts; configure everything in seconds (including cloud storage and presets) interactively
- 📋 **Batch Processing**: Process many URLs from a YouTube playlist, TXT/CSV files, or pasted lists of URLs with automatic rate-limit mitigation logic built-in. See [commands.md](docs/commands.md) for batch mode details
- 🏷️ **Metadata Embedding**: Automatically embeds source URLs and metadata into media files
- ☁️ **Cloud Storage**: Upload media to **S3** and **GCP buckets** after interactive setup ([commands.md](docs/commands.md))
- 🎚️ **Multiple Formats**: Audio (MP3, AAC, FLAC, Opus, WAV, etc.) and video (MP4, MKV, WebM, etc.)
- 🤖 **AI Agent Support**: CLI guidance for agents like [OpenClaw](https://openclaw.ai), [Agent Zero](https://github.com/agent0ai/agent-zero), and Claude Skills — see [backend/AGENTS.md](backend/AGENTS.md)
- 🛠️ **`config` Command**: Interactive wizard for formats, cloud credentials, download folder, batch defaults, and more
- 🩺 **`doctor` Command**: Diagnose cloud misconfigurations, missing FFmpeg, permissions, and common failures
- ✨ **Arcane Interface**: Optional stylized output (disable with `arcane_terms = "false"` or during setup)
- 🔄 **`update` Command**: Refresh the bundled yt-dlp dependency from the community release channel

Full command reference: [docs/commands.md](docs/commands.md).

## Quick Start

### Prerequisites

- **Shell**: Terminal (macOS/Linux) or PowerShell (Windows)
- **uv**: [Astral’s uv](https://docs.astral.sh/uv/) — one-time install below
- **FFmpeg**: Required for conversion — [docs/install.md](docs/install.md)

### Install from PyPI (recommended)

Installing with **uv** avoids macOS Gatekeeper and Windows SmartScreen prompts that often affect downloaded executables.

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
uvx alchemux --help
uvx alchemux "https://youtu.be/…"
uvx --from alchemux amx --help
uvx --from alchemux amx "https://youtu.be/…"
```

`uvx amx ...` is not recommended: `uvx` resolves package names first, and PyPI has an unrelated `amx` package. Use `uvx alchemux ...` or `uvx --from alchemux amx ...`.

#### 3) Install as a persistent CLI tool

```bash
uv tool install alchemux
alchemux setup
alchemux "https://youtu.be/…"
amx "https://…"
```

#### 4) Upgrade / uninstall

```bash
uv tool upgrade alchemux
uv tool uninstall alchemux
```

### Run from source (development)

For unreleased or experimental features:

```bash
git clone https://github.com/bmurrtech/alchemux.git
cd alchemux
uv pip install -e .
uv run alchemux --help
uv run alchemux setup
```

See [docs/install.md](docs/install.md) for platform-specific FFmpeg and config paths.

## Arcane terms

Alchemux can use arcane-themed wording (transmute, distill, seal, etc.). Prefer plain terms? Set `arcane_terms = "false"` in `config.toml` or choose technical mode during `alchemux setup`. Legend: [docs/legend.md](docs/legend.md).

## Known issues

Alchemux is pre-release. Documented limitations, workarounds, and what to check before filing a report: **[docs/known-issues.md](docs/known-issues.md)**.

## Troubleshooting

```bash
alchemux -h
amx -h         # available after `uv tool install alchemux`
alchemux doctor
```

| Problem | Solution |
|---------|----------|
| Config not found | Run `alchemux setup` or `alchemux doctor` — paths in [docs/install.md](docs/install.md) |
| Downloads fail | Try audio-only or `--flac`; run `alchemux update`; see [known-issues.md](docs/known-issues.md) (KI-002, KI-003) |
| `ffmpeg not found` | Install system FFmpeg (`brew install ffmpeg`, `apt install ffmpeg`, etc.) — [docs/install.md](docs/install.md) |

## Contributing

Bug reports, feature requests, and feedback are welcome via **[GitHub Issues](https://github.com/bmurrtech/alchemux/issues/new/choose)**. Please read **[docs/known-issues.md](docs/known-issues.md)** first.

Maintainers: local tooling, tests, and CI — **[docs/contributors.md](docs/contributors.md)**. Release process — **[docs/release.md](docs/release.md)**.

## Support open source

If Alchemux saves you time, consider:

- ⭐ **Starring the repo** — [![Star on GitHub](https://img.shields.io/badge/Star-on_GitHub-blue?logo=github)](https://github.com/bmurrtech/alchemux)
- 🐛 **[Open a GitHub Issue](https://github.com/bmurrtech/alchemux/issues/new/choose)** — bugs, ideas, and feedback
- 📣 **Sharing** with others who download or archive media from the terminal
- ☕ **[Buy Me a Coffee](https://www.buymeacoffee.com/bmurrtech)** or **[Ko-fi](https://ko-fi.com/bmurrtech)**

<p align="center">
  <a href="https://www.buymeacoffee.com/bmurrtech" target="_blank" rel="noopener">
    <img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Support%20the%20project-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black" alt="Buy Me a Coffee">
  </a>
  <a href="https://ko-fi.com/bmurrtech" target="_blank" rel="noopener">
    <img src="https://img.shields.io/badge/Ko--fi-Support%20the%20project-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white" alt="Ko-fi">
  </a>
</p>

## Acknowledgements

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** — core downloader
- **[FFmpeg](https://ffmpeg.org/)** — audio/video conversion (system install)
- **[uv](https://docs.astral.sh/uv/)** — install and run via `uv tool install` / `uvx`
- **[prek](https://github.com/j178/prek)** — pre-commit hooks in CI and locally
- **[PyPI](https://pypi.org/)** — package distribution
- **[Typer](https://typer.tiangolo.com/)**, **[Rich](https://github.com/Textualize/rich)**, **[InquirerPy](https://github.com/kazhala/InquirerPy)** — CLI UX
- **[pyperclip](https://github.com/pyperclip/pyperclip)**, **[mutagen](https://github.com/quodlibet/mutagen)**, **[python-dotenv](https://github.com/theskumar/python-dotenv)** — clipboard, metadata, env helpers

## License

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)

This repository is licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE). The badge links to the official license text; the [`LICENSE`](LICENSE) file in this repo is the binding copy.

### License permissions and restrictions

*Keeping open-source open.*

| Use case | Permitted | Notes / conditions |
|----------|-----------|-------------------|
| Private / internal use | ✅ | No obligation to publish changes if you do not distribute or offer the software as a network service to others. |
| Modify for own private use | ✅ | Obligations attach when you distribute or run modified code as a networked service for users. |
| Share / distribute (unmodified) | ✅ | Include AGPL license and corresponding source (or compliant written offer). |
| Distribute with modifications | ✅ | Modified source must be available under AGPL-3.0 to recipients. |
| Provide as SaaS / network service | ✅ | Users interacting with your modified version over a network must be able to obtain complete corresponding source. |
| Closed / proprietary redistribution | ❌ | Public distribution or SaaS without corresponding source under AGPL is not allowed. |
| Restricting source access for users you serve | ❌ | Network users must be able to get complete corresponding source as AGPL defines. |
| Sublicensing under more restrictive terms | ❌ | AGPL terms must flow through. |

### Commercial / proprietary licensing

Need use **without** AGPL copyleft (closed-source distribution, SaaS without source-offer obligations, etc.)? **Commercial licenses may be available.** Open a [GitHub Issue](https://github.com/bmurrtech/alchemux/issues/new/choose) to discuss licensing and pricing.

---

## Disclaimer

This software is provided **as-is**, without warranty of any kind. The author(s) are **not liable** for damages or losses from use of this project, including data loss, failed downloads, or cloud storage misconfiguration.

By using Alchemux you accept responsibility for:

- Complying with this license and the **terms of service** of sites you download from (e.g. YouTube)
- Ensuring **yt-dlp**, **FFmpeg**, and cloud provider usage comply with their respective licenses and policies
- Securing your own credentials for S3/GCP and local config files
