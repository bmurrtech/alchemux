# Release guide (PyPI)

Alchemux is published to [PyPI](https://pypi.org/project/alchemux/) as the **`alchemux`** package. The project name is reserved by the maintainer; end users install via **`uv tool install alchemux`** or **`uvx alchemux`** (see [README](../README.md)).

Publishing is **fully automated** from GitHub Actions using [PyPI Trusted Publishing (OIDC)](https://docs.pypi.org/trusted-publishers/) — no long-lived PyPI API tokens in the repository.

---

## One-time setup (maintainer)

### 1. PyPI project and Trusted Publisher

1. Create (or claim) the PyPI project **`alchemux`** under your PyPI account.
2. Add a **Trusted Publisher** on the project’s publishing settings. Values must match **exactly**:

| Field | Value |
|-------|-------|
| **Project name** | `alchemux` |
| **Owner** | `bmurrtech` |
| **Repository** | `alchemux` |
| **Workflow filename** | `release.yml` |
| **Environment name** | `pypi` |

The pending publisher is approved on the **first successful** GitHub Actions publish that matches owner, repo, workflow, and environment.

### 2. GitHub environment

In the repo: **Settings → Environments → `pypi`**

| Setting | Recommended value |
|---------|-------------------|
| **Name** | `pypi` (must match workflow `environment.name`) |
| **Deployment branches and tags** | **Selected tags only** → pattern `v*` |
| **Required reviewers** | Optional (solo maintainer: off) |
| **Environment secrets** | None (OIDC only) |

> **Tags, not branches.** The release workflow triggers on **tag push** (`v*`). In the environment UI, add the rule under **tags** — not under branches. If the pattern is applied to branches only, publish fails with: *Tag "v0.1.0" is not allowed to deploy to pypi due to environment protection rules.*

This aligns with the workflow trigger:

```yaml
on:
  push:
    tags:
      - "v*"
```

---

## How a release runs

Pushing a version tag triggers [`.github/workflows/release.yml`](../.github/workflows/release.yml):

| Job | Purpose |
|-----|---------|
| **quality** | `prek run --all-files` |
| **build** | `uv lock --check`, `uv build`, `uvx twine check dist/*`, upload artifact |
| **smoke-uvx** | `uvx --from wheel alchemux --version` and `--help` on three OSes |
| **pypi-publish** | Trusted Publishing to PyPI (`environment: pypi`) |
| **github-release** | Creates GitHub Release with generated notes |

Monitor runs: [Actions → release](https://github.com/bmurrtech/alchemux/actions/workflows/release.yml).

---

## Maintainer release checklist

1. **Merge** all release changes to `main`.
2. **Set version** in [`pyproject.toml`](../pyproject.toml) `project.version` (match tag without `v`).
3. **Run local gates** (recommended):

   ```bash
   prek run --all-files
   uv lock --check
   uv run python -m pytest backend/app/tests -q
   uv build
   uvx twine check dist/*
   ```

4. **Commit** the version bump on `main`.
5. **Tag and push:**

   ```bash
   git tag -a v0.1.0 -m "Release v0.1.0"
   git push origin v0.1.0
   ```

6. **Watch** until **pypi-publish** and **github-release** succeed.
7. **Verify:** `uvx alchemux --version`, `uv tool install alchemux`

See [Versioning](#versioning-semver) for SemVer rules.

---

## Versioning (SemVer)

Alchemux follows [Semantic Versioning 2.0.0](https://semver.org/): **`MAJOR.MINOR.PATCH`**, with optional pre-release labels (`alpha.1`, `beta.1`, `rc.1`).

| Segment | When to increment | Example tag | `pyproject.toml` |
|---------|-------------------|-------------|------------------|
| **MAJOR** | Breaking CLI/config behavior | `v2.0.0` | `2.0.0` |
| **MINOR** | New backward-compatible features | `v1.1.0` | `1.1.0` |
| **PATCH** | Bug fixes only | `v1.0.1` | `1.0.1` |
| **0.x preview** | First PyPI line | `v0.1.0` | `0.1.0` |

Git tags use a leading **`v`**; `pyproject.toml` omits it.

---

## Troubleshooting publish failures

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Tag not allowed to deploy to pypi | Environment rule on **branches** not **tags** | Settings → Environments → `pypi` → **Selected tags only** → `v*` |
| Trusted publisher rejected | Publisher pending or field mismatch | Confirm PyPI publisher fields and `environment: pypi` |
| Environment not found | GitHub env missing | Create **`pypi`** environment |
| Duplicate version on PyPI | Version already published | Bump version; new tag |
| GitHub Release skipped | PyPI job failed | Fix publish first; re-run or new tag |

---

## Related docs

- [README — Installation](../README.md#quick-start)
- [contributors.md — CI overview](contributors.md#5-ci-and-github-actions)
- [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
