# Contributor guide

This guide is for anyone contributing to Alchemux: running the test suite, using pre-commit hooks (prek), and where to find references.

---

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

**Quick run (from repo root, with venv activated):**

```bash
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
uv pip install -r backend/requirements.txt pytest
pytest backend/app/tests -q
```

**Recommended development flow:**

1. Make your changes.
2. Run `**prek run --all-files**` and fix any hook failures.
3. Run `**pytest backend/app/tests**` and fix any test failures.
4. Commit and push (the Git hook will run prek on commit if you ran `prek install --install-hooks`).

---

## 4. References


| Resource                                                          | Description                                                  |
| ----------------------------------------------------------------- | ------------------------------------------------------------ |
| [docs/commands.md](commands.md)                                   | CLI command reference                                        |
| [docs/install.md](install.md)                                     | User install (uv, ffmpeg, from source)                       |
| [docs/legend.md](legend.md)                                       | Arcane terminology                                           |
| [backend/app/tests/README.md](backend/app/tests/README.md)        | Test suite details and safe local run                        |
| [prek — GitHub](https://github.com/j178/prek)                     | prek project                                                 |
| [prek CLI](https://prek.j178.dev/cli/)                            | prek command reference                                       |
| [ADR 0005](../pm/ADRs/0005-ADR-prek-pre-commit-replacement-ci.md) | Decision to use prek for dev/CI (and AI guardrail rationale) |


---

## 5. CI and GitHub Actions

- **Prek:** On every push and pull request, the [Prek checks](.github/workflows/prek.yml) workflow runs `prek run --all-files` via [j178/prek-action](https://github.com/j178/prek-action).
