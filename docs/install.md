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

**Note**: If you plan to use cloud storage uploads, the `google-cloud-storage` and `boto3` packages will be installed automatically. If you only need local downloads, you can skip GCP-related dependencies.

### 3. Install FFmpeg (Required for Audio/Video Conversion)

**Important:** Alchemux requires `ffmpeg` and `ffprobe` for media conversion. These must be installed on your system and accessible via PATH when running from source.

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

**Option 1: Using Chocolatey (Recommended)**

First, install Chocolatey if you don't have it:
```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

Then install ffmpeg:
```powershell
choco install ffmpeg
```

**Option 2: Manual Installation**

1. Download from [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/) (recommended) or [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Extract the ZIP file
3. Add the `bin` folder to your system PATH:
   - Open System Properties → Environment Variables
   - Add the full path to the `bin` folder (e.g., `C:\ffmpeg\bin`) to the PATH variable
   - Restart your terminal/PowerShell

**Verify Installation (All Platforms):**
```bash
ffmpeg -version
ffprobe -version
```

Both commands should display version information. If you get "command not found" errors, ensure ffmpeg is in your PATH.

### 4. Verify Installation

Test that everything is working:

**Unix/macOS/Linux:**
```bash
# From the project root
python backend/app/main.py --version
```

**Windows (PowerShell):**
```powershell
# From the project root
python backend\app\main.py --version
```

You should see the version number displayed.

## Usage

### Run Setup (First Time Only)

**Unix/macOS/Linux:**
```bash
python backend/app/main.py setup
```

**Windows (PowerShell):**
```powershell
python backend\app\main.py setup
```

This will:
- Create a `.env` configuration file
- Prompt you to accept the EULA
- Set up download paths
- Optionally configure cloud storage (GCP or S3)

### Transmute a URL

**Unix/macOS/Linux:**
```bash
python backend/app/main.py https://youtube.com/watch?v=...
```

**Windows (PowerShell):**
```powershell
python backend\app\main.py https://youtube.com/watch?v=...
```

### Get Help

**Unix/macOS/Linux:**
```bash
python backend/app/main.py --help
```

**Windows (PowerShell):**
```powershell
python backend\app\main.py --help
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
# Option 1: If you're always running from the project root
function alchemux { python backend\app\main.py $args }
function amx { python backend\app\main.py $args }

# Option 2: Auto-detect project root (works from any directory)
function alchemux {
    $projectRoot = if ($PSScriptRoot) { 
        $PSScriptRoot 
    } else { 
        $PWD 
    }
    # Navigate to project root (look for backend/app/main.py)
    while (-not (Test-Path (Join-Path $projectRoot "backend\app\main.py"))) {
        $parent = Split-Path -Parent $projectRoot
        if ($parent -eq $projectRoot) {
            Write-Error "Could not find alchemux project root. Please run from the project directory."
            return
        }
        $projectRoot = $parent
    }
    python (Join-Path $projectRoot "backend\app\main.py") $args
}
function amx { alchemux $args }
```

**Note:** Option 1 assumes you're running commands from the project root (matching the bash examples above). Option 2 automatically finds the project root from any directory.

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
   
   **Unix/macOS/Linux:**
   ```bash
   export FFMPEG_CUSTOM_PATH=true
   export FFMPEG_PATH=/path/to/ffmpeg
   ```
   
   **Windows (PowerShell):**
   ```powershell
   $env:FFMPEG_CUSTOM_PATH="true"
   $env:FFMPEG_PATH="C:\path\to\ffmpeg"
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

**Unix/macOS/Linux:**
```bash
cd backend
pip install -r requirements.txt --upgrade
```

**Windows (PowerShell):**
```powershell
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

