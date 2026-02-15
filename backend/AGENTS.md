# Alchemux — Instructions for AI Agents

This document is for **AI agents** (e.g. OpenClaw, Cursor, Claude Code) that run the Alchemux CLI on behalf of a human. It covers install, capabilities, ephemeral mode, and how to handle cloud upload. This is **not** for contributing to the Alchemux codebase.

**Important:** Agents must use **CLI commands and option flags only**. Interactive wizards (`alchemux setup`, `alchemux config`) are for humans. Do not invoke wizards; use flags and non-interactive commands.

---

## Overview

Alchemux is a CLI for media transmutation: download and convert media from URLs (YouTube, Facebook, etc.) to audio/video formats (MP3, MP4, etc.). It wraps yt-dlp and FFmpeg. You may be asked to install it, run transmutations, or configure cloud upload (S3, GCP). This file tells you how to do that.

---

## Install

- **Persistent:** `uv tool install alchemux`
- **One-off:** `uvx alchemux ...`

**Prerequisites:** uv and system FFmpeg. See [docs/install.md](../docs/install.md) for platform setup.

**Cloud storage support:** Install is required for cloud upload (S3/GCP). Ephemeral mode (`--no-config`) does not support cloud; use config-based runs with credentials when cloud is needed.

**Prereq recovery (if missing):**  
- **uv:** `uv --version` fails → macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`; Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`. Restart shell or `source $HOME/.local/bin/env`.  
- **FFmpeg:** `ffmpeg -version` fails → macOS: `brew install ffmpeg`; Ubuntu/Debian: `sudo apt update && sudo apt install ffmpeg`; Fedora: `sudo dnf install ffmpeg`; Windows: `choco install ffmpeg`. Ensure `ffmpeg` and `ffprobe` on PATH.  
- **alchemux:** After uv installed →
   - **Stable (PyPI):** `uv tool install alchemux`
   - **Nightly/Experimental (latest source):**
     1. Clone: `git clone https://github.com/bmurrtech/alchemux.git`
     2. Install deps: `cd alchemux && uv pip install -e .`
     3. Run (from repo root): `uv run alchemux ...`
      (Use `uv run alchemux --help` to verify install. See [docs/install.md](../docs/install.md) for details.)

---

## Agent Usage Flow

1. **Verify install:** `alchemux -v` (or `alchemux --version`). If fail → check `uv --version`; if uv missing use Prereq recovery above, else run `uv tool install alchemux`. If transmutation fails with "ffmpeg not found" → install FFmpeg per Prereq recovery.
2. **Run transmutation:** Pass user-provided URL; set `--download-dir` per Output Path guidance (default `./media`).
   - **Default (audio only):** Run without any video flag. Example: `alchemux --no-config --download-dir ./media "URL"`. Output is audio only (no video). No flag needed for audio-only — this is the default.
   - **When user asks for video:** Add the **`--video`** flag for that run. Example: `alchemux --no-config --download-dir ./media --video "URL"`.
   - Combine with other flags as needed (e.g. `--flac`, `--local`, `--s3`, `--gcp`).
3. **Logs:** Read terminal output; stay abreast. Do not retry until command completes—CLI has builtin retry.
4. **Errors:** If console shows error → reattempt original CLI command. If 3 retries fail → brief error description + tips (check network, FFmpeg on PATH, try again).
5. **Success:** Provide user the path to the ready file (e.g. `./media/title.flac` by default, or `./media/title.mp4` if video was requested). Include full/absolute path if helpful.
6. **Memory:** Commit the output path to workspace memory for future lookup (see Memory). When user asks for that media again, recall from memory.

---

## CLI Capabilities (Agents: Flags and Non-Interactive Commands Only)

For full reference, read:

- **[docs/commands.md](../docs/commands.md)** — All commands, flags, URL quoting, ephemeral mode
- **[docs/legend.md](../docs/legend.md)** — Arcane vs technical terms (scribe, scry, distill, mux, seal)
- **[docs/install.md](../docs/install.md)** — FFmpeg, uv, Tier 1 vs Tier 2

### Quick Reference (Agent-Safe)

| Command / Flag | Purpose |
|----------------|---------|
| `alchemux "URL"` | Transmute URL — **audio only** (default) |
| `alchemux --no-config --download-dir ./media "URL"` | Ephemeral, audio only; output in `./media` |
| `alchemux --no-config --download-dir ./media --video "URL"` | Same as above but **include video** for this run (use when user requests video) |
| `alchemux --flac "URL"` | FLAC conversion (one-time override) |
| `alchemux --s3 "URL"` | Upload to S3 (one-time override) |
| `alchemux --gcp "URL"` | Upload to GCP (one-time override) |
| `alchemux --local "URL"` | Local storage only (one-time override) |
| `alchemux --plain ...` | No colors (useful for capture) |
| `alchemux --help` / `alchemux --version` | Always work (no config) |
| `alchemux batch ...` | Multiple URLs (non-interactive when prereqs met) |

**Do not use:** `alchemux setup`, `alchemux config` — these are interactive wizards for humans. Use flags for one-time overrides.

**Default = audio only.** To include video in a run (when the user asks for it), use the **`--video`** flag.

**Ephemeral mode:** `--no-config` + `--download-dir` = no config files read or written. **Cloud upload is not available in ephemeral mode.**

---

## Ephemeral Mode (No Config, No Writes)

When the user does **not** need cloud upload, use ephemeral mode:

```bash
uvx alchemux --no-config --download-dir ./media "https://..."
```

or (if installed):

```bash
alchemux --no-config --download-dir ./media "https://..."
```

- No .env or config.toml read or written
- Output goes to `<path>`
- Safe for "try it now" and when the agent should not touch the user's config

---

## Output Path (--download-dir)

**Default:** `./media` — places converted files in a `media` subdir of the agent workspace/cwd. User and agent can find outputs there.

**Path logic (plain English):**  
If user specifies a path → use it.  
Else if your workspace/cwd is known (e.g. OpenClaw `~/.openclaw/workspace` or `workspace-<profile>`) → use `./media` (relative to that).  
Else if sandboxed (e.g. `~/.openclaw/sandboxes/...`) → still use `./media`; tools resolve relative to workspace.  
Else → use `./media` or `~/Downloads/Alchemux`; prefer workspace-relative so outputs stay in one place.  

**Skill scope:** Media conversion. Keep output under workspace or user-visible dir so the user can access converted files.

---

## Cloud Upload and Secrets

**Rule:** Never ask the user to paste API keys, tokens, or credentials in chat. Never log or echo secrets.

**Secure secret handoff for agents:** TBD / Roadmap. Until a supported flow exists:

- Direct the user to run `alchemux setup` or `alchemux config` interactively (human-only) to configure cloud credentials.
- **⚠️ HIGH RISK WARNING:** Any secrets configured this way are stored locally in the `.env` file. Assume keys may be publicly exposed if the LLM or host system is ever compromised (e.g. prompt injection, jailbreak, exposed ports, malware). Use cloud credentials only when the human accepts this risk.
- **For AI agent use:** Only recommend ephemeral mode (`--no-config --download-dir <path>`) for local-only transmutation. Do not recommend cloud upload when an AI agent controls the CLI.

**Secrets manager / vault integration:** TBD / Roadmap. Future integration may use Vaultwarden or similar as the vault backend with a capability daemon; the LLM would request outcomes (e.g. upload) without ever receiving secret material.

---

## Security Rules for Agents

1. **Never** ask for or accept secrets in chat.
2. **Never** log, echo, or store secrets in prompts or logs.
3. Use **CLI flags and non-interactive commands only**; do not invoke setup/config wizards.
4. Prefer **ephemeral mode** when cloud is not needed: `--no-config --download-dir <path>`.
5. When cloud is needed: direct the user to configure credentials via human-run setup (with the high-risk warning above). For AI agent use, recommend ephemeral mode only—do not recommend cloud upload.

---

## Memory

Memory lives as plain Markdown in the agent workspace. The model remembers only what is written to disk.

**Files (workspace layout):**
- `memory/YYYY-MM-DD.md` — Daily log (append). Read today + yesterday at session start.
- `MEMORY.md` — Curated long-term. Durable facts, preferences, paths to converted media.

**When to write:** Decisions, preferences, output paths → `MEMORY.md`. Day-to-day notes → `memory/YYYY-MM-DD.md`. If user says "remember this" → write it. Do not keep in RAM.

**Template — save media path after successful transmutation:**
```markdown
## Media (YYYY-MM-DD)
- <source_url> → ./media/<output_filename>
```
Append to `MEMORY.md` or `memory/YYYY-MM-DD.md`. Use when user asks for that media again or you need to look up the path.

---

## References

- [docs/commands.md](../docs/commands.md) — CLI reference
- [docs/legend.md](../docs/legend.md) — Arcane terminology
- [docs/install.md](../docs/install.md) — Install and prerequisites
