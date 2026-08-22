# Changelog

All notable changes to Alchemux are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- YouTube HTTP 403 on distill: default `player_client=android,web` (override via `YTDL_PLAYER_CLIENT` / `[ytdl] player_client`; use `default` for yt-dlp stock)
- `alchemux update` falls back to `pip install -U yt-dlp` when yt-dlp’s self-updater refuses pip/wheel installs
- 403 fracture copy no longer claims residential CDN block; points to `alchemux update` / `YTDL_PLAYER_CLIENT`

### Changed

- Minimum `yt-dlp` dependency floor raised to `>=2026.8.19`

## [0.1.4] — 2026-08-07

Patch: cloud object URL provenance after S3/GCP evaporate, scry picker fix, release notes from CHANGELOG, and clearer upgrade guidance.

### Added

- Cloud Object URL in the companion info file (immediately after Source URL) when S3/GCP evaporate succeeds — omitted when local-only or upload fails; never invents URLs
- Evaporate stage prints the object URL on success (in addition to the seal line); upload failure remains a soft fracture
- `alchemux scry` reads Cloud Object URL from the companion file (JSON `cloud_object_url`); Metadata Health shows the row only when present
- GitHub Release body includes the matching `CHANGELOG.md` section plus install and upgrade commands
- README tip: if `uv tool upgrade` fails, uninstall then reinstall

### Fixed

- `scry` / `inspect` interactive picker: InquirerPy `(value, name)` choices now return the path string (not a tuple); cancel no longer scry’s the default file

## [0.1.3] — 2026-08-05

Media embed enrichment release: thumbnail/chapter embeds, per-title folders, **embed-first Layer-2 metadata** (Artist/comment/date/SOURCE_URL), default-on **companion info file**, optional yt-dlp machine sidecars, safer browser-cookie opt-in (video-gated setup + auto-detect), actionable rate-limit recovery, setup-time EULA acceptance, and **`scry`** media inspection.

### Added

- yt-dlp thumbnail write and embed defaults for supported audio and video outputs
- Chapter embedding for opted-in MP4 and MKV video transmutations
- Per-title output folders (`<title>/<title>.<ext>`) for audio and video, with flat per-entry playlist layout
- Layer-2 mutagen enrichment: channel/uploader as Artist, compact sanitized description→comment, upload date, SOURCE_URL from the input distill URL
- Companion information file (`download.info_file`, default true; `info_file_format` `md`|`txt`) written as `<stem>.info.md` / `.info.txt` beside the seal (includes source URL)
- Setup prompt (default Yes) and config wizard **Download Settings** for companion info file + yt-dlp sidecars
- `download.ytdlp_sidecars` (default false) to optionally write yt-dlp `.info.json` + `.description`
- Shared HTTP 429 / 402 recovery guidance for CLI fractures and future TUI reuse
- Browser-cookie opt-in in setup (when video is enabled) and the config wizard, with pathlib auto-detect/auto-pick of a browser name stored in `config.toml`
- Explicit at-your-own-risk browser-cookie comments in both configuration templates
- Setup-first EULA acceptance (`Y/n`) with the GitHub terms link; persists `eula.*` to `config.toml`
- `alchemux scry` — ffprobe-backed media inspection with Rich report, Metadata Health, optional interactive picker, `--json` / `--raw` / `--verbose` (technical alias `inspect` remains callable but hidden from `--help`)

### Changed

- `ytdl.cookies_from_browser` is treated as a non-secret preference so the browser selector persists in `config.toml`; cookie contents remain inaccessible to Alchemux
- Setup skips the cookie prompt when video is disabled and **preserves** any existing cookie preference
- Rate-limit recovery copy points to `alchemux config` first (setup only after enabling video)
- Always-on yt-dlp Artist–Title parse-metadata is disabled (Artist comes from Layer-2)

### Fixed

- `alchemux config show|doctor|mv` dispatch so the root `[URL]` argument no longer steals `config`
- `config … --help` (e.g. `config mv --help`) reaches the config subcommand instead of root help

## [0.1.2] — 2026-08-03

UX polish release: quieter failures by default, guided FFmpeg checks in setup, OS-native download defaults, clearer install docs, and configurable log levels.

### Added

- `[logging]` config with canonical `level` values and aliases:
  - `quiet` (`q`, `silent`, `error`)
  - `warning` (`warn`, `default`) — recommended default
  - `info` (`i`, `normal`)
  - `verbose` (`v`)
  - `debug` (`d`, `trace`)
- Boolean aliases `logging.debug` / `logging.verbose` (override `level` when true)
- Setup system checks for ffmpeg/ffprobe with ENTER / O / Q recheck loop (detect only; never auto-install)
- OS-tailored FFmpeg install hints and optional browser open to GitHub `docs/install.md`
- Doctor checks for ffmpeg/ffprobe on PATH
- Default user content path `~/Downloads/Alchemux` (via `get_default_output_dir`) during setup
- WSL rejection of Windows-style paths (`C:\...`) with `/mnt/c/...` guidance
- Runtime fail-fast when ffmpeg/ffprobe missing, with short fracture + install hint
- `backend/app/utils/deps.py` dependency helpers
- Root `CONTEXT.md` domain vocabulary for tests and interfaces
- UX polish unit tests (`test_ux_polish.py`) as behavior specs (WSL paths, FFmpeg hints, technical terms, log-level aliases, quiet errors)
- TDD standards section in `backend/app/tests/AGENTS.md` (seams, naming, anti-patterns)

### Changed

- Handled failures log a short message by default; full tracebacks only with `--debug` / `logging.level = "debug"`
- Rich traceback handler gated to debug mode
- Setup output-directory UX: use default Downloads/Alchemux or choose custom
- README / install docs: persistent install first; optional “try without installing?” uses `uvx alchemux` only
- `amx` kept as CLI alias; confusing `uvx … amx` examples removed from quickstart
- `arcane_terms = false` maps remaining spinner text (e.g. `distilling...` → `downloading...`); sigils unchanged
- `alchemux debug` / `alchemux verbose` / config wizard sync `logging.level` and bool aliases
- Fracture causes strip ANSI noise and surface clearer ffmpeg / HTTP messages

### Fixed

- Traceback walls on download failures (e.g. HTTP 403) when not in debug mode
- Missing technical wording when `arcane_terms = false` (spinner still said “distilling…”)
- Cryptic missing-`paths.output_dir` behavior when WSL users paste Windows paths

## [0.1.1] — 2026-06-06

### Fixed

- Normalize root CLI flag order for common invocations
- Clarify `amx` / `uvx` usage (avoid unrelated PyPI `amx` package confusion)
- CI help tests under narrow terminal width
- Declare pytest in the `dev` dependency group for CI and release workflows
- GitHub release / PyPI Trusted Publishing environment tag rule

## [0.1.0] — 2026-06-06

### Added

- First PyPI publish of Alchemux (`uv tool install` / `uvx`)
- Interactive setup and config wizards, batch mode, clipboard URL input
- Optional S3 / GCP upload, config doctor, video download support
- Agent-oriented docs (`backend/AGENTS.md`) and contributor guide

[Unreleased]: https://github.com/bmurrtech/alchemux/compare/v0.1.4...HEAD
[0.1.4]: https://github.com/bmurrtech/alchemux/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/bmurrtech/alchemux/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/bmurrtech/alchemux/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/bmurrtech/alchemux/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/bmurrtech/alchemux/releases/tag/v0.1.0
