# Development Guide

This guide aggregates everything maintainers need for building, testing, and releasing `lib_cli_exit_tools`.

## Make Targets

| Target            | Description                                                                                |
|-------------------|--------------------------------------------------------------------------------------------|
| `help`            | Show help                                                                                  |
| `install`         | Install package editable                                                                   |
| `dev`             | Install package with dev extras                                                            |
| `test`            | Lint, type-check, run tests with coverage, upload to Codecov                               |
| `run`             | Run module CLI (requires dev install or src on PYTHONPATH)                                 |
| `version-current` | Print current version from pyproject.toml                                                  |
| `bump`            | Bump version (updates pyproject.toml and CHANGELOG.md)                                     |
| `bump-patch`      | Bump patch version (X.Y.Z -> X.Y.(Z+1))                                                    |
| `bump-minor`      | Bump minor version (X.Y.Z -> X.(Y+1).0)                                                    |
| `bump-major`      | Bump major version ((X+1).0.0)                                                             |
| `clean`           | Remove caches, build artifacts, and coverage                                               |
| `push`            | Commit all changes once and push to GitHub (no CI monitoring)                              |
| `build`           | Build wheel/sdist artifacts for PyPI distribution                                         |
| `menu`            | Interactive TUI to run targets and edit parameters (requires dev dep: textual)             |

### Target Parameters (env vars)

- Global
  - `PY` (default: `python3`) — Python interpreter used to run scripts
  - `PIP` (default: `pip`) — pip executable used by bootstrap/install
- `install`
  - No specific parameters (respects `PY`, `PIP`).
- `dev`
  - No specific parameters (respects `PY`, `PIP`).
- `test`
  - `COVERAGE=on|auto|off` (default: `on`) — controls pytest coverage run and Codecov upload
  - `SKIP_BOOTSTRAP=1` — skip auto-install of dev tools if missing
  - `TEST_VERBOSE=1` — echo each command executed by the test harness
  - Also respects `CODECOV_TOKEN` when needed for uploads
- `run`
  - No parameters via `make` (always shows `--help`). For custom args: `python -m scripts.run_cli -- <args>`.
- `version-current`
  - No parameters
- `bump`
  - `VERSION=X.Y.Z` — explicit target version
  - `PART=major|minor|patch` — semantic part to bump (default if `VERSION` not set: `patch`)
  - Examples:
    - `make bump VERSION=1.0.2`
    - `make bump PART=minor`
- `bump-patch` / `bump-minor` / `bump-major`
  - No parameters; shorthand for `make bump PART=...`
- `clean`
  - No parameters
- `push`
  - `REMOTE=<name>` (default: `origin`) — git remote to push to
- `build`
  - No parameters via `make`. Advanced: call `python -m scripts.build` directly for custom flows.
- `release`
  - `REMOTE=<name>` (default: `origin`) — git remote to push to
  - Advanced (via script): `python -m scripts.release --retries 5 --retry-wait 3.0`

## Interactive Menu (Textual)

`make menu` launches a colorful terminal UI (powered by `textual`) to browse targets, edit parameters, and run them with live output.

Install dev extras if you haven’t (first mirror the CI guard against pip 25.2):

```bash
python -m pip install --upgrade "pip!=25.2"
pip install -e .[dev]
```

Run the menu:

```bash
make menu
```

### Target Details

- `test`: single entry point for local CI — runs ruff lint + format check, pyright, pytest (including doctests) with coverage (enabled by default), and uploads coverage to Codecov if configured (reads `.env`).
- Auto‑bootstrap: `make test` will try to install dev tools (`pip install -e .[dev]`) if `ruff`/`pyright`/`pytest` are missing. Set `SKIP_BOOTSTRAP=1` to skip this behavior.
- `build`: creates Python wheel/sdist artifacts that match what CI uploads to PyPI.
- `install`/`dev`/`user-install`: common install flows for editable or per‑user installs.
- `version-current`: prints current version from `pyproject.toml`.
- `bump`: updates `pyproject.toml` version and inserts a new section in `CHANGELOG.md`. Use `VERSION=X.Y.Z make bump` or `make bump-minor`/`bump-major`/`bump-patch`.
- `pipx-*` and `uv-*`: isolated CLI installations for end users and fast developer tooling.
- `which-cmd`/`verify-install`: quick diagnostics to ensure the command is on PATH.

## Testing & Coverage

```bash
make test                 # ruff + pyright + pytest + coverage (default ON)
SKIP_BOOTSTRAP=1 make test  # skip auto-install of dev deps
COVERAGE=off make test       # disable coverage locally
COVERAGE=on make test        # force coverage and generate coverage.xml/codecov.xml
make coverage               # python -m coverage run -m pytest -vv (no coverage CLI needed)
```

The same helper can be run directly without Make:

```bash
python -m scripts coverage
```

The coverage helper sets `COVERAGE_NO_SQL=1` before launching pytest so the
legacy file-backed coverage data store is used instead of SQLite. This sidesteps
the "database is locked" failures that occur when multiple runs touch the same
workspace.

The pytest suite uses OS markers (`skipif` guards) to exercise POSIX-, Windows-,
and platform-agnostic behaviours. Run `make test` on every platform you ship to
keep the signal-handling guarantees honest.

### Local Codecov uploads

- `make test` (with coverage enabled) generates `coverage.xml` and `codecov.xml`, then attempts to upload via the Codecov CLI or the bash uploader.
- For private repos, set `CODECOV_TOKEN` (see `.env.example`) or export it in your shell.
- For public repos, a token is typically not required.

## Versioning & Metadata

- `pyproject.toml` (`[project]`) remains the single source of truth for name, version, homepage, and authors.
- `scripts._utils.sync_metadata_module()` rewrites `src/lib_cli_exit_tools/__init__conf__.py` so runtime code consumes generated constants instead of `importlib.metadata`.
- After editing project metadata (name, version, description, URLs, authors), run `make test` or `python -m scripts.test` to regenerate the module before committing.
- Console script name is still discovered from entry points; automation falls back to `lib_cli_exit_tools` when no explicit alias exists.

## CI & Publishing

GitHub Actions workflows are included:

- `.github/workflows/ci.yml` — lint/type/test, build wheel/sdist, and verify pipx/uv installs.
- `.github/workflows/release.yml` — on tags `v*.*.*`, builds artifacts and publishes to PyPI when `PYPI_API_TOKEN` secret is set.

To publish a release:
1. Bump `pyproject.toml` version and update `CHANGELOG.md`.
2. Tag the commit (`git tag v1.1.0 && git push --tags`).
3. Ensure `PYPI_API_TOKEN` secret is configured in the repo.
4. Release workflow uploads wheel/sdist to PyPI.

Third-party packaging targets (Conda, Homebrew, Nix) were removed; distribution now flows solely through PyPI.
