# Installation Guide

This guide covers installing and running Alchemux from source.

## Prerequisites

- **Python 3.8+** installed and accessible from your terminal
- **pip** (Python package manager, usually included with Python)

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/bmurrtech/alchemux.git
cd alchemux
```

### 2. Install Dependencies

Navigate to the backend directory and install required packages:

```bash
cd backend
pip install -r requirements.txt
```

**Note**: If you plan to use GCP Cloud Storage uploads, the `google-cloud-storage` package will be installed automatically. If you only need local downloads, you can skip GCP-related dependencies.

### 3. Install FFmpeg (Required for Audio/Video Conversion)

Alchemux requires `ffmpeg` and `ffprobe` for media conversion. Install them based on your platform:

#### macOS
```bash
brew install ffmpeg
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install ffmpeg
```

#### Linux (Fedora/RHEL)
```bash
sudo dnf install ffmpeg
```

#### Windows
1. Download from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Extract and add to your system PATH, or
3. Use a package manager like [Chocolatey](https://chocolatey.org/):
   ```powershell
   choco install ffmpeg
   ```

### 4. Verify Installation

Test that everything is working:

```bash
# From the project root
python backend/app/main.py --version
```

You should see the version number displayed.

## Usage

### Run Setup (First Time Only)

```bash
python backend/app/main.py setup
```

This will:
- Create a `.env` configuration file
- Prompt you to accept the EULA
- Set up download paths
- Optionally configure cloud storage (GCP or S3)

### Transmute a URL

```bash
python backend/app/main.py https://youtube.com/watch?v=...
```

### Get Help

```bash
python backend/app/main.py --help
```

## Optional: Create Command Aliases

### For Portable Binaries

The portable binary supports both `alchemux` and `amx` as command names. To use the shorter `amx` command:

**Unix/macOS/Linux:**
```bash
# Create a symlink
ln -s /path/to/alchemux /usr/local/bin/amx
# Or in the same directory
ln -s alchemux amx
```

**Windows:**
```cmd
# Copy the binary
copy alchemux.exe amx.exe
# Or create a batch file: amx.bat
@echo off
alchemux.exe %*
```

### For Source Installations

To avoid typing the full path each time, you can create aliases:

**Unix/macOS/Linux:**

Add to your `~/.bashrc`, `~/.zshrc`, or equivalent:

```bash
alias alchemux='python /path/to/alchemux/backend/app/main.py'
alias amx='python /path/to/alchemux/backend/app/main.py'
```

Then reload your shell:
```bash
source ~/.bashrc  # or ~/.zshrc
```

**Windows (PowerShell):**

Add to your PowerShell profile (`$PROFILE`):

```powershell
function alchemux { python C:\path\to\alchemux\backend\app\main.py $args }
function amx { python C:\path\to\alchemux\backend\app\main.py $args }
```

## Troubleshooting

### "ffmpeg not found" Error

If you see an error about ffmpeg not being found:

1. **Verify ffmpeg is installed**:
   ```bash
   ffmpeg -version
   ```

2. **Check your PATH**: Ensure ffmpeg is in your system PATH

3. **Specify ffmpeg location manually**: You can configure a custom FFmpeg path in your `.env` file:
   ```bash
   # In your .env file:
   FFMPEG_CUSTOM_PATH=true
   FFMPEG_PATH=/path/to/ffmpeg
   ```
   
   Or set as environment variables:
   ```bash
   export FFMPEG_CUSTOM_PATH=true
   export FFMPEG_PATH=/path/to/ffmpeg
   ```
   
   **Note**: 
   - Set `FFMPEG_CUSTOM_PATH=false` (default) to use system PATH or bundled binaries
   - Set `FFMPEG_CUSTOM_PATH=true` and `FFMPEG_PATH=/path/to/ffmpeg` to use a custom location
   - `FFMPEG_PATH` can be either a directory containing ffmpeg/ffprobe or the ffmpeg binary itself

### Python Version Issues

Ensure you're using Python 3.8 or higher:

```bash
python --version
```

If you need to use a different Python version, use `python3` instead:

```bash
python3 backend/app/main.py --help
```

### Import Errors

If you see import errors, ensure all dependencies are installed:

```bash
cd backend
pip install -r requirements.txt --upgrade
```

### Permission Errors

On Unix systems, if you get permission errors, you may need to use `pip3` with `--user`:

```bash
pip3 install -r requirements.txt --user
```

## Next Steps

- See [commands.md](commands.md) for full CLI usage and options
- See [legend.md](legend.md) for arcane terminology reference
- Check the main [README.md](../README.md) for quick start examples

