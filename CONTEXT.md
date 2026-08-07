# Alchemux

Domain language for Alchemux: a CLI that transmute media URLs into local (or cloud) artifacts. Use these terms in tests, seams, docs, and interfaces. Prefer this vocabulary over synonyms. When touching an area, also respect the ADRs under `pm/ADRs/`.

## Product

**Transmutation**:
A single run that turns a media URL into one or more output files (audio by default; video when opted in).
_Avoid_: Job, task, conversion job, pipeline run

**Distill**:
The download-and-convert stage of a transmutation (arcane). Technical equivalent is **download**.
_Avoid_: Fetch, scrape, pull, rip

**Seal**:
Successful completion and persistence of the result (arcane). Technical equivalent is **save**.
_Avoid_: Finish, done, complete (as the named stage)

**Fracture**:
A handled failure surfaced to the user as a short cause (not a traceback wall by default).
_Avoid_: Exception dump, crash log, stack trace (as the default UX)

**Arcane terms**:
Product-facing wording (`distill`, `attune`, `seal`, …) when `product.arcane_terms` is true.
_Avoid_: Fantasy mode, theme mode, flavor text

**Technical terms**:
Plain wording (`download`, `locate`, `save`, …) when `product.arcane_terms` is false. Sigils stay.
_Avoid_: Plain English mode, no-theme mode

**Scry (command)**:
Standalone inspection of a sealed media file (`alchemux scry`). Technical alias: **inspect**. Uses ffprobe + embedded tags + companion presence; parses companion **Cloud Object URL** when present; inspection only.
_Avoid_: Confusing with the pipeline stage **scry** (detect source during distill)

## CLI & modes

**Setup**:
The human-only interactive wizard that creates first-run config (`.env`, `config.toml`) and system checks.
_Avoid_: Init, bootstrap, onboarding command (as the command name)

**Config wizard**:
The human-only interactive command that changes persistent preferences.
_Avoid_: Settings UI, preferences CLI, `config set`

**Ephemeral mode**:
A no-config-read/write run (`--no-config` + `--download-dir`). Cloud upload is not available.
_Avoid_: Temp mode, dry config, guest mode

**One-run override**:
A CLI flag that changes behavior for the current invocation only (e.g. `--video`, `--flac`, `--local`).
_Avoid_: Temporary setting, session preference

**Action vs preference** (ADR 0002):
Actions do work now without persistence; preferences change defaults via setup/config wizards.
_Avoid_: Mixing “do once” and “remember forever” in one control

## Paths & dependencies

**Output dir**:
User content root for downloaded/converted files (`paths.output_dir`). Default is `~/Downloads/Alchemux`.
_Avoid_: Download folder (as the config key name), media root, vault

**Config dir**:
OS-standard per-user directory (platformdirs) holding `.env` and `config.toml`.
_Avoid_: Install dir, repo root, next to binary

**FFmpeg check**:
Detect-only verification that `ffmpeg` and `ffprobe` are on PATH. Never auto-installs or shells out to package managers.
_Avoid_: FFmpeg install step, dependency bootstrapper

**WSL path rejection**:
Under WSL, refuse Windows-style absolute paths (`C:\…`) and guide toward `/mnt/c/…` or a Linux path.
_Avoid_: Path rewrite, silent path conversion

## Media

**Audio-only (default)**:
Default transmutation path; video code paths do not run (ADR 0007).
_Avoid_: Audio mode as if it were a special opt-in

**Video opt-in**:
Video pipeline enabled via `media.video.enabled` or the `--video` one-run override.
_Avoid_: Video-on-by-default, always-merge

**Companion info file**:
Human-readable `<stem>.info.md` or `.info.txt` beside a seal (`download.info_file`; format via `info_file_format`). Default on; soft-fail on write. Written after evaporate so an optional **Cloud Object URL** can be included when S3/GCP upload succeeds.
_Avoid_: Provenance sidecar, metadata dump (as the user-facing name)

**yt-dlp machine sidecars**:
Optional `.info.json` + `.description` from yt-dlp (`download.ytdlp_sidecars`, default off). Independent of the companion info file.
_Avoid_: Calling these the companion info file; conflating with `info_file`

## Logging

**Log level**:
Canonical `[logging].level`: `quiet`, `warning` (recommended default), `info`, `verbose`, `debug`.
_Avoid_: Ad-hoc severity strings outside the alias map

**Quiet errors**:
Handled failures log a short message; include traceback only when debug is active.
_Avoid_: Always-on Rich traceback, `logger.exception` as the default handled-failure path

## Testing vocabulary

**Seam**:
A pre-agreed public boundary where tests observe behavior without reaching into internals.
_Avoid_: Private-method test, collaborator call-count assertion

**Behavior spec**:
A test name that states a capability in domain language (“WSL rejects Windows-style output paths”), not an implementation step.
_Avoid_: `test_<function>_works`, HOW-oriented names

## ADR touchpoints

| Area | ADR |
|------|-----|
| Action vs preference, URL quoting, wizard taxonomy | `pm/ADRs/0002-config-rubric.md` |
| uvx zero-config / ephemeral / help-always-works | `pm/ADRs/0004-ADR-uvx-zero-config-first-run.md` |
| prek + CI test gates | `pm/ADRs/0005-ADR-prek-pre-commit-replacement-ci.md` |
| Video disabled by default; `--video` opt-in | `pm/ADRs/0007-ADR-video-disabled-by-default-opt-in.md` |
| Companion info file; yt-dlp machine sidecars | `pm/ADRs/0008-ADR-companion-info-file.md` |

Human-readable arcane ↔ technical tables: `docs/legend.md`.
