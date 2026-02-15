## Backend tests (public-safe) — Linux runner guide

This directory contains **publicly committable** tests for Alchemux’s backend/CLI.

- **Audience**: functional testers + pentesters running on Linux.
- **Security posture**: tests **must not** print secrets/PII and must not require real credentials.
- **No `/pm/` dependency**: testers should be able to understand intent from this README + `/docs`.

---

## What these tests are for (high level)

These tests validate **configuration management behavior** (PRD7) and guard against regressions from prior work (PRD6 debugging notes):

- **Config discovery and safety**: config location rules, pointer file behavior, secret masking.
- **Config CLI behaviors**: `config show`, `config doctor` diagnostics output, and (PRD7) guided repair/backup behavior.
- **Regression guardrails**:
  - **URL quoting guidance** (shell globbing / special chars): docs + help paths must encourage quoting URLs.
  - **Multi-format output path correctness**: when multiple formats are produced, the resolved output path must match the requested extension.
  - **Config key resolution**: `product.arcane_terms` in `config.toml` must take precedence over env fallback.

---

## Reference configuration (templates)

These are **repo-tracked templates** you can use as reference while testing:

- **Secrets template**: `env.example`
  - Only contains placeholders for secrets (OAuth/GCP/S3).
  - Do **not** put real credentials into a repo checkout used for testing.
- **Non-secret config template**: `config.toml.example`
  - Contains UX + default behavior settings (paths, formats, storage destination, arcane terminology).

**Docs to read (repo-tracked):**

- **Commands**: `docs/commands.md`
- **Install**: `docs/install.md`
- **Contributors (prek, test suite, refs)**: `docs/contributors.md`
- **Legend/terminology**: `docs/legend.md`

---

## prek (pre-commit) and the test suite

The repo uses **[prek](https://github.com/j178/prek)** for pre-commit hooks (format, lint, repo hygiene). CI runs `prek run --all-files` on push/PR, then runs this test suite and uv integration smoke tests on **Ubuntu, Windows, and macOS** (see `.github/workflows/ci.yml`). Recommended flow before committing:

1. **Run hooks:** `prek run --all-files` (from repo root). Fix any failures.
2. **Run tests:** `uv run python -m pytest backend/app/tests -q` (no venv activation). Alternatively, with venv activated and deps installed: `pytest backend/app/tests -q`.

**Pre-commit checks included:**

- **Built-in hooks:** trailing whitespace, end-of-file fixer, mixed line endings, check-toml, check-yaml, check-json, merge conflict detection, private-key detection, large-file check, case/symlink checks.
- **Ruff:** Python linting (with `--fix`) and formatting. Ruff is configured via the repo-root **`pyproject.toml`** (`[tool.ruff]`, `[tool.ruff.format]`, `[tool.ruff.lint]`). Source paths and rules are defined there; run `ruff check .` or `ruff format .` from the repo root to reproduce hook behavior locally if needed.

See [docs/contributors.md](../../docs/contributors.md) for prek install ([installation](https://github.com/j178/prek?tab=readme-ov-file#installation)), `prek install --install-hooks`, and the full CLI reference ([prek.j178.dev/cli](https://prek.j178.dev/cli/)).

---

## Safe local run — isolate config to a temp directory

Alchemux reads config from a directory via `ALCHEMUX_CONFIG_DIR`. For testing, point it at a temp dir so you do not touch real user config paths.

**Preferred (from repo root; no venv activation):**

```bash
export ALCHEMUX_CONFIG_DIR="$(mktemp -d)"
echo "Using ALCHEMUX_CONFIG_DIR=$ALCHEMUX_CONFIG_DIR"
cp env.example "$ALCHEMUX_CONFIG_DIR/.env"
cp config.toml.example "$ALCHEMUX_CONFIG_DIR/config.toml"
chmod 600 "$ALCHEMUX_CONFIG_DIR/.env" || true

uv run alchemux --help
uv run alchemux --version
uv run alchemux config show
uv run alchemux config doctor
```

**Alternatively**, use a venv and install the project in editable mode (less preferred):

```bash
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
uv pip install -e .
uv pip install pytest

export ALCHEMUX_CONFIG_DIR="$(mktemp -d)"
# ... seed config from env.example and config.toml.example as above ...

python backend/app/main.py --help
python backend/app/main.py config show
# or, with editable install, use: alchemux / amx
```

If Alchemux is installed as a tool (`uv tool install alchemux`), you can use `alchemux` or `amx` from any directory (no `uv run`).

### CLI options (tester quick inventory)

For the authoritative list, read `docs/commands.md`. The most relevant PRD7 config commands are:

- `python backend/app/main.py config` — interactive configuration wizard (persistent preferences).
- `python backend/app/main.py config show` — print current config paths and key settings.
- `python backend/app/main.py config doctor` — run config diagnostics (and in PRD7, offer guided repair).
- `python backend/app/main.py config mv` — copy/move config files and update the pointer.

Common one-run flags you may use during CLI smoke checks:

- `--plain` — disable colors/animations (useful for log capture).
- `--debug` — verbose tracebacks/logging (do **not** use with real secrets in environment).

**Notes for testers**

- **No network required** for config tests.
- If you run URL download commands, use **test URLs you own/are authorized** to access and always **quote URLs** (see `docs/commands.md`).
- Do not set cloud credentials unless explicitly testing cloud flows; PRD7 config tests should stay local-only.

---

## Running the unit tests

From repo root. Recommended: run prek first (see "prek (pre-commit) and the test suite" above). No venv activation required:

```bash
prek run --all-files    # optional but recommended before pushing
uv run python -m pytest backend/app/tests -q
```

With venv activated you can use `pytest backend/app/tests -q` instead.

If you want tests to print additional **sanitized** debug hints, run:

```bash
ALCHEMUX_TEST_VERBOSE=1 uv run python -m pytest backend/app/tests -q -s
```

**Important security note**: even in verbose mode, tests must never print values for keys that look like secrets (anything containing `KEY`, `SECRET`, `TOKEN`, `PASSWORD`, etc.). If you observe such output, treat it as a security bug and report it.

---

## Interactive mode and clipboard (PRD6 expansion)

Tests for interactive URL prompt and `-p`/`--clipboard` use **mocks** only:

- **InquirerPy**: prompt calls (text, confirm, checkbox) are mocked so tests do not hang; no real terminal UI.
- **pyperclip**: `pyperclip.paste()` is mocked; tests never read or assert on real clipboard content.
- **Non-interactive behavior**: run with CliRunner (no TTY) to assert exit codes and messages (e.g. "No URL provided", "Clipboard unsupported. Retry with …").

To run only the PRD6 input tests:

```bash
uv run python -m pytest backend/app/tests/test_cli_interactive_input.py backend/app/tests/test_cli_clipboard_input.py -q -v
```

---

## Inventory: tests in this directory

## PRD7 functional expectations (what to validate)

This section summarizes PRD7 behavior in tester terms (no `/pm` required).

- **FR-1 (Config category selection)**:
  - Running `python backend/app/main.py config` should present a **category selection** UI and require at least one category before proceeding.
  - Only the selected categories should be modified; unrelated settings should remain unchanged.
- **FR-3 (Diagnostics)**:
  - Running `python backend/app/main.py config doctor` should print a **clear report** of config health: files present, TOML validity, paths, pointer validity, and (if selected) cloud-credential presence (without printing credentials).
- **FR-4 (Guided repair + backup)**:
  - If `config doctor` finds issues, it should offer **guided repair** actions.
  - Repairs must create/overwrite a **single latest backup** under `<config_dir>/.backups/latest/` before modifying files.
  - If a repair fails, it should attempt restore and report failure cleanly.

### `test_config_manager.py`

**Purpose**
- Validates config location and pointer-file priority rules.
- Ensures secrets are masked in logs (no accidental leaks).

**What to expect**
- Tests create temporary directories and never require real credentials.
- The “no secrets in logs” test uses a synthetic secret string and asserts it is not printed.

### Additional tests added by PRD7 (config management)

This directory includes minimal smoke/unit coverage for:

- **`config doctor` / `config show` smoke** (report structure and stable messaging): `test_cli_config_smoke.py`
- **Downloader output-path selection** for multi-format flows (extension correctness): `test_downloader_path_resolution.py`
- **Guided repair + backup** behavior (single-latest backup policy; restore-on-failure): `test_config_doctor_repair.py`

**Test file inventory:**

| File | Purpose | Key Tests |
|------|---------|-----------|
| `test_config_manager.py` | Config discovery, pointer files, secret masking | Config location priority, pointer read/write, no secrets in logs |
| `test_cli_config_smoke.py` | CLI smoke tests (user-action simulation) | `config show`, `config doctor` invocation via Typer CliRunner |
| `test_config_doctor_repair.py` | Doctor/repair/backup unit tests | Backup creation/overwrite, restore, doctor diagnostics, arcane_terms precedence |
| `test_downloader_path_resolution.py` | Multi-format path regression test | Expected extension wins when multiple formats exist |
| `test_update_command.py` | Update command logic (throttling, version checks) | Update check throttling, timestamp file creation, version detection |
| `test_cli_interactive_input.py` | PRD6 interactive URL input (no-args flow) | URL validation, prereq gating, acquire_url with mocks |
| `test_cli_clipboard_input.py` | PRD6 clipboard URL input (`-p`/`--clipboard`) | Clipboard empty/invalid/unavailable, help shows `-p` |
| `test_batch_parsing.py` | PRD009 batch URL extraction (TXT/CSV) | filter_url_candidates, extract_urls_from_text, extract_urls_from_csv; comments, blanks, invalid tokens |
| `test_batch_file_discovery.py` | PRD009 batch file discovery | Config-dir scan (.txt/.csv only), _format_file_size, _collect_urls_from_files with mocked ConfigManager/inquirer |
| `test_batch_playlist_expansion.py` | PRD009 batch playlist expansion | _expand_playlist_urls with mocked yt_dlp (entries → URLs); empty/failure cases |
| `test_batch_command.py` | PRD009 batch command | batch in --help; TTY/prereq gating (patch.object on batch module); flow reaches inquirer.select |

**What each test validates:**

- **test_config_manager.py**: Core config location resolution, pointer file behavior, secret masking in logs
- **test_cli_config_smoke.py**: End-to-end CLI invocation (simulates `alchemux config show` and `alchemux config doctor` commands)
- **test_config_doctor_repair.py**: Backup/restore functionality, single-latest overwrite policy, restore-on-failure, config key precedence (product.arcane_terms)
- **test_downloader_path_resolution.py**: Regression guard for multi-format downloads (ensures correct file path returned per format)
- **test_update_command.py**: Update command throttling logic, timestamp file management, version detection (no network operations in tests)
- **test_cli_interactive_input.py**: PRD6 interactive URL acquisition (validate_url_like, domain_preview, prereq gating, acquire_url with mocks; no real InquirerPy/pyperclip)
- **test_cli_clipboard_input.py**: PRD6 clipboard flow (_read_clipboard empty/invalid/unavailable, CLI --help shows -p/--clipboard, no-URL non-interactive exit message)
- **test_batch_parsing.py**: Batch URL parsing (TXT newline/comma, comment lines; CSV cells; filter_url_candidates)
- **test_batch_file_discovery.py**: Batch file discovery in config dir; one .txt file selected (mocked) yields extracted URLs
- **test_batch_playlist_expansion.py**: Playlist expansion via mocked yt_dlp (webpage_url/url extraction; empty/failure returns [])
- **test_batch_command.py**: Batch command in --help; batch.batch() exits with code 1 when is_tty False or _check_prerequisites False; flow calls inquirer.select when prereqs OK

---

## Batch mode tests (PRD 009)

- **How to run:** `uv run python -m pytest backend/app/tests/test_batch_parsing.py backend/app/tests/test_batch_file_discovery.py backend/app/tests/test_batch_playlist_expansion.py backend/app/tests/test_batch_command.py -q` (or `uv run python -m pytest backend/app/tests -q` for full suite).
- **Expected outcome:** All batch tests pass without network; InquirerPy and yt_dlp are mocked so no real prompts or downloads.
- **What is mocked:** ConfigManager (config dir path), inquirer (select/checkbox/execute), yt_dlp (YoutubeDL.extract_info for playlist expansion). No secrets in logs.

All tests are public-safe: use temp directories only, never print secrets/PII.

---

## What to report back to devs (useful artifacts)

When reporting failures, include:

- **Exact command** you ran (copy/paste).
- **Exit code** and **stdout/stderr** (redact anything that looks like a secret).
- The **temp config dir path** you used (safe to share).
- `python --version`, and whether you ran inside a virtualenv.
