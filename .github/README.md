# .github

This directory contains GitHub-specific automation configuration files for the universal-doc-parser repository. It is automatically recognized by GitHub and used to configure CI/CD pipelines, Actions workflows, branch protection rules, and repository metadata.

---

## Directory Structure

```
.github/
    workflows/
        ci.yml
        release.yml
```

---

## workflows/

The `workflows/` subdirectory contains YAML workflow definitions for GitHub Actions. Each file in this directory represents one or more automated pipeline jobs that run in response to specified repository events.

---

### ci.yml — Continuous Integration Workflow

**Trigger:** Every push to `main` and every pull request targeting `main`.

**Matrix:** The CI runs a full cross-platform matrix covering the following combinations:
- Operating systems: `ubuntu-latest`, `macos-latest`, `windows-latest`
- Python versions: `3.11`, `3.12`

This produces 6 parallel matrix jobs per push.

**Pipeline Steps:**

1. `actions/checkout@v4` — Checks out the repository including all test fixture files.
2. `actions/setup-python@v5` — Installs the specified Python version from the matrix.
3. `astral-sh/setup-uv@v5` — Installs the `uv` package manager.
4. System dependency installation (Linux runners only):
   - `libmagic1` — Required by `python-magic` for MIME-type detection.
   - `libgl1` — Required by `opencv-python` for image preprocessing.
5. System dependency installation (macOS runners only):
   - `libmagic` via Homebrew — Same requirement as Linux.
6. `uv sync --all-extras` — Resolves and installs all package dependencies from `uv.lock`.
7. `uv run pytest -v` — Executes the full test suite.

**Purpose:** The CI workflow provides confidence that every commit in the repository does not introduce regressions across the supported operating system and Python version combinations.

---

### release.yml — PyPI Publishing Workflow

**Trigger:** Every push of a version tag matching the pattern `v*` (e.g., `v1.0.0`, `v1.0.1`, `v2.0.0`).

**Authentication:** This workflow uses PyPI Trusted Publishing (OpenID Connect / OIDC) for authentication. No stored API tokens or passwords are required. The workflow is pre-registered as a trusted publisher on PyPI under the project `universal-doc-parser`, linked specifically to the `Edge-Explorer/Parse-Anything-` repository and the `release.yml` workflow file.

**Permissions required by the workflow job:**
- `id-token: write` — Required for OIDC token generation.
- `contents: write` — Required to create GitHub Releases.

**Pipeline Steps:**

1. `actions/checkout@v4` — Checks out the exact tagged commit.
2. `astral-sh/setup-uv@v3` — Installs `uv`.
3. `uv python install 3.11` — Installs Python 3.11 for the build.
4. `uv build` — Builds the source distribution (`.tar.gz`) and wheel (`.whl`) into the `dist/` directory.
5. `pypa/gh-action-pypi-publish@release/v1` — Authenticates with PyPI via OIDC and publishes the `dist/` artifacts. Duplicate uploads are silently skipped.

**How to trigger a release:**

```bash
# 1. Bump version in pyproject.toml
# 2. Commit the version bump
git add pyproject.toml
git commit -m "release: bump version to v1.x.x"
git push origin main

# 3. Create and push the version tag
git tag v1.x.x
git push origin v1.x.x
```

This will automatically build and publish the new version to https://pypi.org/project/universal-doc-parser within approximately 90 seconds.

---

## Adding New Workflows

When adding a new GitHub Actions workflow:

1. Place the `.yml` file in `.github/workflows/`.
2. Use `on:` triggers as narrowly as possible to avoid unnecessary compute consumption.
3. Add an entry to the table in this README documenting the workflow's trigger, purpose, and required permissions.
4. Validate the workflow syntax using the GitHub Actions extension in VS Code or the `actionlint` tool before pushing.
