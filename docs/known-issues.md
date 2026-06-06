# Known issues

Curated list of **documented, recurring limitations** in Alchemux. This page helps you self-diagnose before opening a GitHub issue — it does **not** replace the [issue tracker](https://github.com/bmurrtech/alchemux/issues).

**Before opening an issue:** skim the table below, try the workaround, run `alchemux doctor`, and check [commands.md](commands.md) / [install.md](install.md). If your report is already listed here, only open an issue if the workaround fails or you have new reproduction details.

---

## Status legend

| Status | Meaning |
|--------|---------|
| **Active** | Ongoing in current releases; no full fix yet |
| **Mitigated** | Default behavior or docs reduce impact; may still occur |
| **Upstream** | Root cause in yt-dlp, FFmpeg, or the source site — track upstream |
| **By design** | Intentional product choice, not a bug |

---

## Known issues

| ID | Area | Symptom | Workaround / mitigation | Status |
|----|------|---------|-------------------------|--------|
| **KI-001** | Release | Pre-release software; rough edges and behavior changes between versions | Expect instability; pin a version with `uv tool install alchemux==…` if you need consistency | **Active** |
| **KI-002** | YouTube | HTTP **403** or failed **video** download | Video is **off by default**. Try audio-only first. For one run: `--video`. Failures may still occur (anti-bot). Run `alchemux update` | **Upstream** |
| **KI-003** | YouTube | HTTP **403** on **audio** extraction | Run `alchemux update`. Default uses combined stream (`best`) to reduce CDN blocks — see [commands.md — YouTube 403](commands.md#youtube-403--cdn-blocking). Optional env: `YTDL_IMPERSONATE`, `YTDL_COOKIES_FROM_BROWSER`, `YTDL_FORCE_IPV4` ([configs.md](configs.md)) | **Mitigated** |
| **KI-004** | Dependencies | `ffmpeg not found` / conversion fails | Install **system** FFmpeg (`ffmpeg` + `ffprobe` on PATH). Not bundled. See [install.md § FFmpeg](install.md#2-install-ffmpeg-required). Optional: `FFMPEG_PATH` in `.env` | **By design** |
| **KI-005** | yt-dlp | Extraction errors after a site or yt-dlp change | `alchemux update` (or `--force`). Throttled to once per day by default | **Upstream** |
| **KI-006** | Media defaults | Output has audio but no video | Expected: video disabled in defaults. Use `--video` for one run or enable in `config.toml` / `alchemux config` | **By design** |
| **KI-007** | Batch | Some URLs in a batch fail; rate limits | Built-in delay between items; reduce batch size; retry failed URLs. See [commands.md — batch](commands.md) | **Mitigated** |
| **KI-008** | CLI / TTY | Interactive prompts hang or exit in CI, SSH, or pipes | Pass URL on the command line; use flags instead of wizards; batch needs a TTY for interactive source selection | **Active** |
| **KI-009** | Clipboard | `-p` / `--clipboard` fails or empty | Paste URL as an argument: `alchemux "https://…"`. Clipboard often unavailable over SSH or headless sessions | **Active** |
| **KI-010** | Linux UI | Download folder does not auto-open | Install `xdg-utils` on Linux, or open the folder path shown in output manually ([install.md](install.md)) | **Active** |
| **KI-011** | Paths (WSL) | Permission or path errors on config/output | Common with mixed Windows/WSL paths — see [configs.md — WSL](configs.md) | **Active** |
| **KI-012** | Cloud | S3/GCP upload fails after download | Run `alchemux doctor`; verify credentials and bucket settings in `alchemux config` ([commands.md](commands.md)) | **Active** |
| **KI-013** | Legal / ToS | Site blocks download or account action | Ensure you have rights to the content and comply with the **source site’s terms**. Alchemux does not bypass DRM or access controls | **By design** |

---

## Quick checks

```bash
alchemux doctor          # config, FFmpeg, paths
alchemux update          # refresh yt-dlp
alchemux update --force  # bypass daily throttle
alchemux -h              # flags and non-interactive usage
```

---

## Reporting something new

1. Confirm it is **not** already covered in the table above.
2. Note **ID** if related (e.g. “KI-003, workaround failed after update”).
3. Open **[GitHub Issues](https://github.com/bmurrtech/alchemux/issues/new/choose)** with: Alchemux version, OS, command run, and sanitized log output (no secrets).

Maintainers may add rows here when a limitation is understood and recurring; use the issue tracker for individual reports and discussion.
