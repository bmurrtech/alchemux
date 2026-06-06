# Contributor guide

## How to contribute

**Read [known-issues.md](known-issues.md) first** — check whether your symptom is already documented and try the listed workaround.

Feedback, bug reports, and feature ideas are welcome via **[GitHub Issues](https://github.com/bmurrtech/alchemux/issues/new/choose)**.

---

The sections below document local development tooling (prek, tests, CI) for project maintenance.


## 1. Install prek (pre-commit replacement)

The repo uses **[prek](https://github.com/j178/prek)** for pre-commit-style hooks (lint, format, repo hygiene). Install prek once so you can run the same checks locally that CI runs.

**Install (choose one):**

- **GitHub README:** [prek installation (GitHub)](https://github.com/j178/prek?tab=readme-ov-file#installation)
- **Docs:** [prek.j178.dev/installation](https://prek.j178.dev/installation/)

**Examples:**

```bash
# Using uv (recommended)
uv tool install prek

# Using uvx (run without installing)
uvx prek --version

# Standalone installer (macOS/Linux)
curl --proto '=https' --tlsv1.2 -LsSf https://github.com/j178/prek/releases/download/v0.3.2/prek-installer.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://github.com/j178/prek/releases/download/v0.3.2/prek-installer.ps1 | iex"
```

**Full CLI reference:** [prek.j178.dev/cli](https://prek.j178.dev/cli/)

---

## 2. Pre-commit best practice (local checks before push)

**One-time setup:** Install the Git hook and prepare hook environments so prek runs automatically on `git commit`:

```bash
prek install --install-hooks
```

**Recommended before every push:** Run all hooks on the repo (same as CI):

```bash
prek run --all-files
```

**Other useful commands:**


| Command                        | Purpose                                                          |
| ------------------------------ | ---------------------------------------------------------------- |
| `prek run --all-files`         | Run all hooks on the whole repo (what CI runs)                   |
| `prek install --install-hooks` | Install Git hook + prepare hook environments                     |
| `prek list`                    | List configured hooks and their IDs                              |
| `prek run --last-commit`       | Run hooks only on files changed in the last commit               |
| `prek run -vvv`                | Verbose tracing (debugging)                                      |
| `prek run --refresh`           | Force fresh project discovery (e.g. after editing `.prekignore`) |


**Config:**

- **prek.toml** at the repo root defines hooks (built-in hygiene + [Ruff](https://docs.astral.sh/ruff/) for Python lint and format). Ruff runs as `ruff --fix` and `ruff-format` via the `astral-sh/ruff-pre-commit` repo.
- **pyproject.toml** at the repo root configures Ruff: `[tool.ruff]` (e.g. `target-version`, `line-length`, `src` for the backend), `[tool.ruff.format]`, and `[tool.ruff.lint]` (exclude patterns). This ensures consistent formatting and lint rules locally and in CI.

Prek also writes a log file to `~/.cache/prek/prek.log` by default.

---

## 3. Test suite

Tests live in `**backend/app/tests/**`. Full instructions: [backend/app/tests/README.md](backend/app/tests/README.md).

**Quick run (from repo root; no venv activation required):**

```bash
uv run python -m pytest backend/app/tests -q
```

**Alternatively**, with venv activated:

```bash
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
uv pip install -e .
uv pip install pytest
pytest backend/app/tests -q
```

**Recommended local check flow (maintainers):**

1. Make your changes.
2. Run `**prek run --all-files**` and fix any hook failures.
3. Run `**uv run python -m pytest backend/app/tests**` (or `pytest backend/app/tests` with venv activated) and fix any test failures.

---

## 4. References


| Resource                                                          | Description                                                  |
| ----------------------------------------------------------------- | ------------------------------------------------------------ |
| [known-issues.md](known-issues.md)                                | Documented limitations — read before opening an issue        |
| [docs/commands.md](commands.md)                                   | CLI command reference                                        |
| [docs/install.md](install.md)                                     | User install (uv, ffmpeg, from source)                       |
| [docs/legend.md](legend.md)                                       | Arcane terminology                                           |
| [backend/app/tests/README.md](backend/app/tests/README.md)        | Test suite details and safe local run                        |
| [prek — GitHub](https://github.com/j178/prek)                     | prek project                                                 |
| [prek CLI](https://prek.j178.dev/cli/)                            | prek command reference                                       |


---

## 5. CI and GitHub Actions

- **Prek:** On every push, the [Prek checks](.github/workflows/prek.yml) workflow runs `prek run --all-files` via [j178/prek-action](https://github.com/j178/prek-action).
- **Release (PyPI):** Pushing a version tag `v*` triggers the [release](.github/workflows/release.yml) workflow (build, smoke, PyPI publish, GitHub Release). Maintainer checklist, SemVer table, and Trusted Publishing setup: **[release.md](release.md)**.
