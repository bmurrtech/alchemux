# Changelog

All notable changes to Alchemux are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[Unreleased]: https://github.com/bmurrtech/alchemux/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/bmurrtech/alchemux/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/bmurrtech/alchemux/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/bmurrtech/alchemux/releases/tag/v0.1.0
