# Backend tests — agent & contributor guide

Publicly committable tests for Alchemux’s backend/CLI. Domain vocabulary lives in the repo-root [`CONTEXT.md`](../../../CONTEXT.md). TDD rules live in [`.cursor/skills/tdd/`](../../../.cursor/skills/tdd/).

- **Audience**: contributors, functional testers, and agents running checks on Linux/macOS/Windows.
- **Security**: tests must not print secrets/PII and must not require real credentials.
- **No `/pm/` dependency for runners**: intent is understandable from this file + `/docs`. ADRs under `pm/ADRs/` are for agents designing or refactoring tests.

---

## TDD standards (required)

### What a good test is

- Verifies **behavior through public seams**, not implementation details.
- Reads like a **behavior spec** in domain language (“WSL rejects Windows-style output paths”), not a method roll-call (`test_validate_output_path_…`).
- Survives internal refactors: if behavior is unchanged, the test stays green.
- Expected values come from an **independent source of truth** (known literal, legend table, ADR, install URL) — never recomputed the same way as the code under test.

### Seams

A **seam** is the public boundary you observe. Before adding tests, list the seams and keep them in the module docstring (see `test_ux_polish.py`).

| Seam area | Public interface | Notes |
|-----------|------------------|--------|
| Config discovery | `ConfigManager`, pointer helpers | Temp dirs only; secret masking |
| Config CLI | Typer app via `CliRunner` | `config show` / `config doctor` |
| Output dir validation | `validate_output_path`, `looks_like_windows_abs_path` | WSL rejection; default `~/Downloads/Alchemux` |
| FFmpeg check | `app.utils.deps` detect-only helpers | Never auto-install |
| Arcane vs technical | `ArcaneConsole.translate_message` | Sigils unchanged |
| Quiet errors / log level | `normalize_log_level`, `resolve_config_log_level`, `log_error` | Traceback only in debug |
| Ephemeral mode | `EphemeralConfig` | No config write |
| Video opt-in | distill / downloader gating | ADR 0007 |
| Batch / URL input | batch parsers + mocked InquirerPy/pyperclip/yt-dlp | System boundaries only |

**Mock only at system boundaries** (TTY prompts, clipboard, yt-dlp network, package-manager presence). Do not mock internal collaborators you own.

### Anti-patterns (reject in review)

- Implementation-coupled: private methods, call-count on internal helpers, DB/side-channel asserts.
- Tautological: expected value built by re-running the production algorithm.
- HOW-named tests: `test_<fn>_returns_true` instead of a capability statement.
- Horizontal bulk: all tests first, then all code — prefer vertical slices for new work.

### Naming

Prefer domain language from `CONTEXT.md`:

| Prefer | Avoid |
|--------|--------|
| `test_wsl_rejects_windows_style_output_path_with_mnt_guidance` | `test_validate_output_path_wsl` |
| `test_technical_terms_map_distill_spinner_to_download` | `test_arcane_terms_false_maps` |
| `test_quiet_errors_omit_traceback_outside_debug` | `test_log_error_skips_exc_info` |

---

## What these tests cover

- **Config management**: discovery, pointer files, secret masking, doctor/repair/backup.
- **CLI smoke**: `--help` / `--version` without config (ADR 0004); `config show` / `config doctor`.
- **UX polish (0.1.2)**: WSL path rejection, FFmpeg install hints, arcane word maps, log-level aliases, quiet errors.
- **Regression guardrails**: URL quoting guidance, multi-format output path extension, `product.arcane_terms` precedence, video disabled by default, ephemeral mode, argv normalization, batch URL flows.

---

## Reference configuration

- **Secrets template**: `env.example` (placeholders only).
- **Non-secret config**: `config.toml.example`.

**Docs:**

- Commands: `docs/commands.md`
- Install: `docs/install.md`
- Contributors: `docs/contributors.md`
- Legend: `docs/legend.md`
- Domain language: `CONTEXT.md`

---

## prek and the test suite

CI runs `prek run --all-files`, then this suite and uv smoke tests on Ubuntu, Windows, and macOS (`.github/workflows/ci.yml`).

```bash
prek run --all-files
uv run --group dev python -m pytest backend/app/tests -q
```

Hooks: trailing whitespace / EOF / TOML-YAML-JSON / private-key / large-file checks, plus Ruff lint+format via root `pyproject.toml`. See `docs/contributors.md`.

---

## Safe local run — isolate config

```bash
export ALCHEMUX_CONFIG_DIR="$(mktemp -d)"
cp env.example "$ALCHEMUX_CONFIG_DIR/.env"
cp config.toml.example "$ALCHEMUX_CONFIG_DIR/config.toml"
chmod 600 "$ALCHEMUX_CONFIG_DIR/.env" || true

uv run alchemux --help
uv run alchemux --version
uv run alchemux config show
uv run alchemux config doctor
```

- No network required for config tests.
- Quote URLs if you exercise download commands.
- Do not set cloud credentials unless explicitly testing cloud flows.

Useful flags: `--plain` (no colors), `--debug` (tracebacks — never with real secrets).

Verbose sanitized test hints:

```bash
ALCHEMUX_TEST_VERBOSE=1 uv run --group dev python -m pytest backend/app/tests -q -s
```

Even in verbose mode, never print values for keys containing `KEY`, `SECRET`, `TOKEN`, `PASSWORD`, etc.

---

## Inventory

| File | Seam / purpose |
|------|----------------|
| `test_config_manager.py` | Config discovery, pointer files, secret masking |
| `test_cli_config_smoke.py` | `config show` / `config doctor` via CliRunner; help/version without config |
| `test_config_doctor_repair.py` | Guided repair, single-latest backup, arcane_terms precedence |
| `test_downloader_path_resolution.py` | Multi-format output path prefers expected extension |
| `test_update_command.py` | Update throttling / version detection (no network) |
| `test_cli_interactive_input.py` | Interactive URL acquire (mocked prompts) |
| `test_cli_clipboard_input.py` | `-p` / `--clipboard` (mocked pyperclip) |
| `test_cli_argv_normalize.py` | Root flag order normalization |
| `test_batch_*.py` | Batch URL parse/discover/expand/command (mocked yt-dlp / inquirer) |
| `test_ephemeral_config.py` | Ephemeral mode defaults (ADR 0004) |
| `test_video_enabled_gating.py` | Video disabled by default; `--video` opt-in (ADR 0007) |
| `test_ux_polish.py` | WSL paths, FFmpeg hints, technical terms, log levels, quiet errors |

### PRD7 expectations (config)

- **FR-1**: `config` presents category selection; only selected categories change.
- **FR-3**: `config doctor` reports health without printing credentials.
- **FR-4**: Guided repair writes a single latest backup under `<config_dir>/.backups/latest/`; restore on failure.

### Batch (PRD 009)

```bash
uv run --group dev python -m pytest \
  backend/app/tests/test_batch_parsing.py \
  backend/app/tests/test_batch_file_discovery.py \
  backend/app/tests/test_batch_playlist_expansion.py \
  backend/app/tests/test_batch_command.py -q
```

Mocks: ConfigManager path, inquirer, yt-dlp `extract_info`. No secrets in logs.

### UX polish slice

```bash
uv run --group dev python -m pytest backend/app/tests/test_ux_polish.py -q
```

---

## Reporting failures

Include: exact command, exit code, stdout/stderr (redact secrets), temp `ALCHEMUX_CONFIG_DIR`, `python --version`, and whether you used `uv run`.
