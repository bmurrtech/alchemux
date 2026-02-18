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

**Option 1: Chocolatey (recommended for most users)**

If you don't already have Chocolatey installed, open PowerShell **as Administrator** and run:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; `
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; `
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

Once installed, close and reopen your PowerShell window, then install FFmpeg:

```powershell
choco install ffmpeg
```

You may need to restart your shell for the `ffmpeg` command to be available.


**Option 2: Manual**

1. Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract and add the `bin` folder to your system PATH

### Verify (all platforms)

```bash
ffmpeg -version
ffprobe -version
```

### Optional: xdg-utils (Linux only, for auto-open folder feature)

On Linux systems, the `xdg-utils` package is required for the auto-open folder feature to work. Without it, folder opening will gracefully fail with a warning message.

**Install xdg-utils:**

```bash
# Ubuntu/Debian
sudo apt install xdg-utils

# Fedora/RHEL
sudo dnf install xdg-utils

# Arch Linux
sudo pacman -S xdg-utils
```

**Note:** WSL2 users don't need `xdg-utils`; Alchemux automatically uses Windows Explorer when running in WSL2.

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

## 4. Run from source

If you prefer to run from source, developing Alchemux, or need to run from a git checkout:

### Prerequisites

- Python 3.12+ and **uv** (see above)
- FFmpeg on PATH (see above)

### Source run steps

**Clone the repository:**

```bash
git clone https://github.com/bmurrtech/alchemux.git
cd alchemux
```

From the repository root (same as `pyproject.toml`), run:

```bash
uv venv
uv pip install -e .
```
> **Note:** No virtual environment activation is required when using `pyproject.toml` and `uv`; dependency isolation is handled automatically.

#### Option A: Run from source (using `uv` with no venv required)

```bash
uv run alchemux --help
uv run alchemux --version
uv run alchemux setup
uv run alchemux "https://…"
```
> **Note:** No virtual environment activation is required when using `uv` in this way—`uv` automatically creates and manages an isolated environment under the hood during these commands, so you don't need to manually run `source .venv/bin/activate` or similar.

**Done!**

#### Option B: Run from source (using traditional virtual environment)

Alternatively, you can use a typical virtual environment instead of relying on `uv`'s built-in isolation. See below:

**Create and activate a virtual environment:**

```bash
uv venv
source .venv/bin/activate   # On Windows: .venv\Scripts\Activate.ps1
```

**Install dependencies:**

```bash
uv pip install -e .
```

You can now run Alchemux commands directly:

```bash
alchemux --help
alchemux setup
alchemux "https://…"
```

Or, if you want to run the main module directly:

```bash
python backend/app/main.py --help
```

This approach lets you use typical Python tooling and shell (venv, python, pip).


### Run tests

From repo root: `uv run python -m pytest backend/app/tests -q`. See [backend/app/tests/README.md](../backend/app/tests/README.md) for details and config isolation.

### Contributors (prek, tests, references)

If you are contributing code, see **[docs/contributors.md](contributors.md)** for: installing [prek](https://github.com/j178/prek) (pre-commit replacement), recommended local checks before push, running the test suite, and references.

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
- Contributors: see [contributors.md](contributors.md) for prek, test suite, and references.
