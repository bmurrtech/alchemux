# Installation Guide

This guide covers installing and running Alchemux using **uv** (recommended) or from source.

## Prerequisites

- **Shell**: Terminal (macOS/Linux) or PowerShell (Windows)
- **uv**: [Astral’s uv](https://docs.astral.sh/uv/) — install once (see below)
- **FFmpeg**: **Required.** Alchemux needs `ffmpeg` and `ffprobe` on your system PATH for media conversion. There is no bundled FFmpeg; you must install it for your OS.

---

## 1. Install uv (one-time)

### macOS / Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart your shell or run `source $HOME/.local/bin/env` (or add uv’s bin to your PATH if the installer directed you to).

### Windows (PowerShell)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Verify

```bash
uv --version
```

---

## 2. Install FFmpeg (required)

Alchemux does **not** bundle FFmpeg. Install it on your system and ensure `ffmpeg` and `ffprobe` are on your PATH.

### macOS

```bash
brew install ffmpeg
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install ffmpeg
```

### Linux (Fedora/RHEL)

```bash
sudo dnf install ffmpeg
```

### Windows

**Option 1: Chocolatey**

```powershell
choco install ffmpeg
```

**Option 2: Manual**

1. Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract and add the `bin` folder to your system PATH

### Verify (all platforms)

```bash
ffmpeg -version
ffprobe -version
```

---

## 3. Run Alchemux

### Try without installing (uvx)

You can run Alchemux once without installing it using **uvx**. Two ways are supported:

**Tier 1 — Easiest “try it now” (recommended)**  
On first run, if you don’t have config yet, Alchemux will create it automatically in your OS user config directory and then proceed. In an interactive terminal you’ll get a few short prompts (e.g. download folder, terminology); in non-interactive use it uses safe defaults and prints where config was written.

```bash
uvx alchemux --help                    # Always works; no config needed
uvx alchemux "https://youtu.be/…"      # First run: auto-creates config, then runs
uvx amx "https://…"                    # Same with short name
```

**Tier 2 — Ephemeral (no filesystem writes)**  
If you want to try Alchemux without writing any config or state to disk, use `--no-config` and set a download directory. No config files are read or created.

```bash
uvx alchemux --no-config --download-dir . "https://youtu.be/…"
```

Downloads go to the directory you pass to `--download-dir` (or a temporary directory). Cloud upload and other config-dependent features are not available in this mode unless overridden via environment variables. See [commands.md](commands.md) for full option reference.

### Install as a persistent CLI tool (recommended)

```bash
uv tool install alchemux
```

Then use `alchemux` or `amx` from any directory:

```bash
alchemux --help
amx --help
alchemux setup          # first-time setup
alchemux "https://…"    # transmute a URL
amx "https://…"         # same, shorter name
```

### Upgrade

```bash
uv tool upgrade alchemux
```

### Uninstall

```bash
uv tool uninstall alchemux
```

---

## 4. Run from source (development)

If you are developing Alchemux or need to run from a git checkout:

### Prerequisites

- Python 3.8+ and **uv** (see above)
- FFmpeg on PATH (see above)

### Clone and install dependencies

From the repository root:

```bash
git clone https://github.com/bmurrtech/alchemux.git
cd alchemux
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
uv pip install -r backend/requirements.txt
```

If the project has a root `pyproject.toml`, you can instead use:

```bash
uv pip install -e .
```

### Run via Python

From the repository root (with venv activated):

```bash
python backend/app/main.py --help
python backend/app/main.py setup
python backend/app/main.py "https://…"
```

### Run tests

See [backend/app/tests/README.md](../backend/app/tests/README.md) for using **uv** to install dependencies and run the test suite (e.g. `uv pip install -r backend/requirements.txt pytest` then `pytest backend/app/tests`).

---

## 5. Optional: Pin Python version

For consistent behavior, you can pin the Python version used by uv:

```bash
uv python install 3.12
uv python pin 3.12
```

Then `uv tool install alchemux` (or `uvx alchemux`) uses that version.

---

## Troubleshooting

### "ffmpeg not found"

- Install FFmpeg for your OS (see section 2) and ensure it is on your PATH.
- You can override the location with environment variables:
  - `FFMPEG_CUSTOM_PATH=true`
  - `FFMPEG_PATH=/path/to/ffmpeg` (or the directory containing `ffmpeg` and `ffprobe`)

  **Note:** Alchemux uses **system FFmpeg only** (PATH and optional `FFMPEG_PATH`). There is no bundled FFmpeg.

### "Configuration file (.env) not found"

- **With uvx / installed tool:** On first run of a URL, Alchemux can auto-create config in your OS user config directory (see Tier 1 above). You can also run `alchemux setup` for full interactive setup.
- Use `alchemux doctor` to see where Alchemux looks for config and to repair paths.
- Config is stored in OS-standard per-user directories (e.g. `~/Library/Application Support/Alchemux/` on macOS, `~/.config/alchemux/` on Linux, `%APPDATA%\Alchemux\` on Windows).
- To run without any config: use `--no-config` and `--download-dir` (Tier 2).

### Import or dependency errors (source install)

Ensure the virtual environment is activated and dependencies are installed:

```bash
uv pip install -r backend/requirements.txt --upgrade
# or from repo root with editable install:
uv pip install -e .
```

---

## Next steps

- [commands.md](commands.md) — full CLI reference
- [legend.md](legend.md) — arcane terminology
- [README.md](../README.md) — quick start and features
