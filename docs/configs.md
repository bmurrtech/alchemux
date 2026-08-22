# Alchemux Configuration Guide

## Configuration Files

Alchemux uses two main configuration files:

1. **`config.toml`** - Non-secret settings, UX preferences, and defaults
2. **`.env`** - Secret credentials and environment-specific settings

## Environment Variables

These can be set in your shell environment, `.env` file, or system-wide:

### UV and Development Settings

```bash
# Prevents "failed to hardlink files" warnings on cross-filesystem setups
# Common in WSL2, Docker containers, or when mixing Windows/Unix filesystems
# Values: 'hardlink' (default), 'symlink', 'copy'
UV_LINK_MODE=copy
```

### FFmpeg Path Override

```bash
# Override system FFmpeg/ffprobe detection
FFMPEG_PATH=/custom/path/to/ffmpeg
```

### yt-dlp Options

```bash
# Optional yt-dlp settings (use with caution — see Cookies below)
YTDL_IMPERSONATE=chrome
YTDL_COOKIES_FROM_BROWSER=chrome
YTDL_FORCE_IPV4=true
YTDL_AUDIO_FORMAT_SELECTOR=ba
# YouTube player clients (default android,web). Use "default" for yt-dlp stock.
YTDL_PLAYER_CLIENT=android,web
```

## Cookies from browser (optional, at your own risk)

> **Caution:** Passing browser cookies to yt-dlp can associate downloads with your logged-in account. Abuse or automation that violates a site’s terms can lead to **temporary or permanent account suspension**. Enable only if you accept that risk. Alchemux does **not** export or write a `cookies.txt` file; it only stores a **browser name** and lets yt-dlp read the browser cookie database in-process.

### Prefer config / setup (recommended)

- **`alchemux config` → Download Reliability Settings** — enable or disable cookies at any time (independent of video).
- **`alchemux setup`** — cookie prompt appears **only if** you enable video in that setup pass. If you leave video disabled, an existing `ytdl.cookies_from_browser` value is **preserved**.

```text
Pass cookies for YouTube downloads?
(Caution: Abuse can lead to temporary or permanent account suspension. Enable at your own risk.)
[N/y]
```

- Default is **N** (cookies disabled / cleared when answering N after the prompt).
- If you choose **Y**, Alchemux **auto-detects** installed browser profiles and **auto-picks** one (prints the chosen name). No free-text browser entry in the wizards.
- If no supported profile is found, cookies stay off; set `ytdl.cookies_from_browser` or `YTDL_COOKIES_FROM_BROWSER` manually (see below).

### Config / env equivalents

In `config.toml`:

```toml
[ytdl]
# At your own risk. Browser name only — Alchemux never writes cookies.txt.
# cookies_from_browser = "chrome"
# Advanced override (Flatpak / custom profile path — docs/env only, not wizard UX):
# cookies_from_browser = "chrome:~/.var/app/com.google.Chrome"
```

Or via environment:

```bash
YTDL_COOKIES_FROM_BROWSER=chrome
```

### Security notes

- Do **not** commit cookie files, browser profile paths with secrets, or dumps to git.
- Alchemux must not log cookie values.
- Manual Netscape `--cookies` files are an advanced yt-dlp escape hatch; prefer cookies-from-browser so Alchemux never materializes an all-sites cookie export on disk.
- `YTDL_IMPERSONATE` / `ytdl.impersonate` is separate TLS fingerprint tooling—not the same as cookies—and remains optional/advanced.

## Output paths and filenames

Alchemux uses yt-dlp’s path (`-P` / `paths`) and output template (`-o` / `outtmpl`) concepts under the hood.

### Defaults (MVP)

| Setting | Default behavior |
|---------|------------------|
| Destination directory | `paths.output_dir` (typically `~/Downloads/Alchemux`) or `--download-dir` |
| Layout | Per-title folder: `<title>/<title>.<ext>` (reuse folder on collision; playlists are flat per-entry) |
| Embedded metadata (Layer-2) | Artist = channel/uploader; compact description → comment (≤2048 UTF-8 bytes + `Source:` footer); date when known; **SOURCE_URL** from the distill input URL |
| Companion info file | On by default. `download.info_file = true` writes `<stem>.info.md` (or `.txt` via `info_file_format`) with source URL, optional **Cloud Object URL** after successful S3/GCP evaporate, description, chapters, and other details |
| yt-dlp machine sidecars | Off by default. Set `download.ytdlp_sidecars = true` for `.info.json` + `.description` |
| `restrictfilenames` | On — safer across OSes and shells |

There is **no** custom `-o` template editor in the CLI/TUI MVP. Change destination via config, setup, `--download-dir`, or the TUI destination field (when available). Companion info files are offered in `alchemux setup` (default Yes) and under **Download Settings** in `alchemux config`.

### Companion information file

By default Alchemux writes a human-readable companion beside the seal:

```toml
[download]
info_file = true
info_file_format = "md"   # md | txt
```

Creates `<title>.info.md` (or `.info.txt`) containing the source URL, description, chapters (when present), and other media details. When S3 or GCP evaporate succeeds, a **Cloud Object URL** line is included immediately after Source URL (exact uploader return value: `https://…` or `s3://…`). The field is omitted for local-only runs or when upload fails — Alchemux never invents cloud URLs. Companion write happens after the evaporate attempt so the URL can be included in a single write. This is separate from yt-dlp’s optional machine-readable `.info.json` files. Set `info_file = false` to skip. Invalid `info_file_format` values fall back to `md`.

### Optional yt-dlp machine sidecars

Machine-readable yt-dlp sidecars (`.info.json` + `.description`) stay off by default. The human-readable companion info file is separate and on by default. To also keep yt-dlp machine sidecars in the title folder:

```toml
[download]
ytdlp_sidecars = true
```

When enabled, Alchemux asks yt-dlp to write both `.info.json` and `.description` next to the seal (no extra network requests beyond the distill itself).

### Examples (curated)

These illustrate yt-dlp patterns for power users who run yt-dlp directly or extend config later. Alchemux itself keeps the title-folder defaults above.

**Title folder (product default shape):**

```bash
yt-dlp -o "%(title)s/%(title)s.%(ext)s" --restrict-filenames "URL"
```

**Literal stem, correct extension:**

```bash
yt-dlp --print filename -o "test video.%(ext)s" VIDEO_ID
```

**Restricted filenames (recommended for transfer/Windows):**

```bash
yt-dlp -o "%(title)s/%(title)s.%(ext)s" --restrict-filenames "URL"
```

**Playlist into a parent folder, indexed (curated power-user pattern — not Alchemux default):**

```bash
yt-dlp -o "%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s" "PLAYLIST_URL"
```

**Upload-year folders:**

```bash
yt-dlp -o "%(upload_date>%Y)s/%(title)s.%(ext)s" "URL"
```

**Avoid “filename too long”** by truncating fields (bytes):

```bash
yt-dlp -o "%(uploader).30B - %(title).180B.%(ext)s" "URL"
```

**Separate home path and template** (conceptually what Alchemux splits as destination vs name):

```bash
yt-dlp -P "~/Downloads/Alchemux" -o "%(title)s/%(title)s.%(ext)s" "URL"
```

For the full field reference, see [yt-dlp output template docs](https://github.com/yt-dlp/yt-dlp#output-template).

## config.toml Structure

See `config.toml.example` for the complete reference with all available options and their descriptions.

### Key Sections

- **[product]** - Product behavior and terminology preferences
- **[ui]** - User interface defaults (colors, animations, auto-open)
- **[paths]** - Output and temporary directory settings
- **[media.audio]** - Audio processing defaults
- **[media.video]** - Video processing settings
- **[ytdl]** - Optional yt-dlp extras (cookies-from-browser, impersonate, etc.)
- **[storage]** - Cloud storage configuration
- **[network]** - Network retry and timeout settings

## Configuration Locations

### Run from Source
- Config files are created in the repository directory by default
- Can be overridden with `--config-dir` flag

### PyPI/uv Tool Install
- Config files use OS-standard locations (platformdirs)
- macOS: `~/Library/Application Support/Alchemux/`
- Linux: `~/.config/alchemux/`
- Windows: `%APPDATA%\Alchemux\`

## Troubleshooting

### Rate limited (HTTP 429 / 402)

If Alchemux reports rate limiting (HTTP **429** Too Many Requests or **402** Payment Required), the site is often soft-blocking your IP for overuse.

1. Open the same URL in a browser and solve any CAPTCHA the site presents.
2. Optionally enable cookies via `alchemux config` (Download Reliability), or via `alchemux setup` after enabling video (**at your own risk** — see [Cookies from browser](#cookies-from-browser-optional-at-your-own-risk)).
3. If your machine has multiple external IPs, the CAPTCHA solve and download path need to use the **same** IP (yt-dlp `--source-address` is an advanced manual option outside Alchemux MVP).
4. Matching your browser’s User-Agent is also an advanced yt-dlp option; prefer cookies-from-browser first.

### Hardlink Warnings
If you see "failed to hardlink files; falling back to full copy" warnings:

1. Set `UV_LINK_MODE=copy` in your `.env` file or shell environment
2. This is common in WSL2 or mixed filesystem environments
3. The warning doesn't affect functionality, only suppresses the performance optimization

### Config Not Found
- Run `alchemux setup` to create initial configuration
- Use `--no-config` flag for ephemeral runs without configuration files
