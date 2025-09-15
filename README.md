# lib_cli_exit_tools

<!-- Badges -->
[![CI](https://github.com/bitranox/lib_cli_exit_tools/actions/workflows/ci.yml/badge.svg)](https://github.com/bitranox/lib_cli_exit_tools/actions/workflows/ci.yml)
[![CodeQL](https://github.com/bitranox/lib_cli_exit_tools/actions/workflows/codeql.yml/badge.svg)](https://github.com/bitranox/lib_cli_exit_tools/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Jupyter](https://img.shields.io/badge/Jupyter-Launch-orange?logo=jupyter)](https://mybinder.org/v2/gh/bitranox/lib_cli_exit_tools/HEAD?labpath=notebooks%2FQuickstart.ipynb)
[![PyPI](https://img.shields.io/pypi/v/lib_cli_exit_tools.svg)](https://pypi.org/project/lib_cli_exit_tools/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/lib_cli_exit_tools.svg)](https://pypi.org/project/lib_cli_exit_tools/)
[![Code Style: Ruff](https://img.shields.io/badge/Code%20Style-Ruff-46A3FF?logo=ruff&labelColor=000)](https://docs.astral.sh/ruff/)
[![codecov](https://codecov.io/gh/bitranox/lib_cli_exit_tools/graph/badge.svg?token=z1D8JSjWEH)](https://codecov.io/gh/bitranox/lib_cli_exit_tools)
[![Maintainability](https://qlty.sh/gh/bitranox/projects/lib_cli_exit_tools/maintainability.svg)](https://qlty.sh/gh/bitranox/projects/lib_cli_exit_tools)
[![Known Vulnerabilities](https://snyk.io/test/github/bitranox/lib_cli_exit_tools/badge.svg)](https://snyk.io/test/github/bitranox/lib_cli_exit_tools)

Small helpers for robust CLI exit handling:
- Portable signal handling (SIGINT, SIGTERM/SIGBREAK)
- Consistent exception → exit code mapping
- Concise error printing with optional traceback and subprocess stdout/stderr capture

## Install

Pick one of the options below. All methods register the `lib_cli_exit_tools` and `cli-exit-tools` commands on your PATH.

### 1) Standard virtualenv (pip)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e .[dev]       # dev install
# or for runtime only:
pip install .
```

### 2) Per-user (no venv)

```bash
pip install --user .
```

Note: respects PEP 668; avoid on system Python if “externally managed”. Ensure `~/.local/bin` (POSIX) is on PATH.

### 3) pipx (isolated, recommended for end users)

```bash
pipx install .
pipx upgrade lib_cli_exit_tools
# From Git tag/commit:
pipx install "git+https://github.com/bitranox/lib_cli_exit_tools@v0.1.0"
```

### 4) uv (fast installer/runner)

```bash
uv pip install -e .[dev]
uv tool install .
uvx lib_cli_exit_tools --help
```

### 5) From artifacts

```bash
python -m build
pip install dist/lib_cli_exit_tools-*.whl
pip install dist/lib_cli_exit_tools-*.tar.gz   # sdist
```

### 6) Poetry / PDM (project-managed envs)

```bash
# Poetry
poetry add lib_cli_exit_tools     # as dependency
poetry install                    # for local dev

# PDM
pdm add lib_cli_exit_tools
pdm install
```

### 7) From Git via pip (CI-friendly)

```bash
pip install "git+https://github.com/bitranox/lib_cli_exit_tools@v0.1.0#egg=lib_cli_exit_tools"
```

### 8) Conda/mamba (optional)

```bash
mamba create -n cli-exit python=3.12 pip
mamba activate cli-exit
pip install .
```

### 9) System package managers (optional distribution)

- Homebrew formula (macOS): `brew install lib_cli_exit_tools` (if published)
- Nix: flake/package for reproducible installs
- Deb/RPM via `fpm` for OS-native packages

### Make Targets

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
| `build`           | Build wheel/sdist and attempt conda, brew, and nix builds (auto-installs tools if missing) |
| `menu`            | Interactive TUI to run targets and edit parameters (requires dev dep: textual)             |

#### Target Parameters (env vars)

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
  - No parameters via `make` (always shows `--help`). For custom args: `python scripts/run_cli.py -- <args>`.

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
  - No parameters via `make`. Advanced: use the script directly, e.g. `python scripts/build.py --no-conda --no-nix`.

- `release`
  - `REMOTE=<name>` (default: `origin`) — git remote to push to
  - Advanced (via script): `python scripts/release.py --retries 5 --retry-wait 3.0`

### Interactive Menu (Textual)

`make menu` launches a colorful terminal UI (powered by `textual`) to browse targets, edit parameters, and run them with live output.

Install dev extras if you haven’t:

```bash
pip install -e .[dev]
```

Run the menu:

```bash
make menu
```

#### Target Details

- `test`: single entry point for local CI — runs ruff lint + format check, pyright, pytest (including doctests) with coverage (enabled by default), and uploads coverage to Codecov if configured (reads `.env`).
- Auto‑bootstrap: `make test` will try to install dev tools (`pip install -e .[dev]`) if `ruff`/`pyright`/`pytest` are missing. Set `SKIP_BOOTSTRAP=1` to skip this behavior.
- `build`: convenient builder — creates Python wheel/sdist, then attempts Conda, Homebrew, and Nix builds. It auto‑installs missing tools (Miniforge, Homebrew, Nix) when needed.
- `install`/`dev`/`user-install`: common install flows for editable or per‑user installs.
- `version-current`: prints current version from `pyproject.toml`.
- `bump`: updates `pyproject.toml` version and inserts a new section in `CHANGELOG.md`. Use `VERSION=X.Y.Z make bump` or `make bump-minor`/`bump-major`/`bump-patch`.
- `pipx-*` and `uv-*`: isolated CLI installations for end users and fast developer tooling.
- `which-cmd`/`verify-install`: quick diagnostics to ensure the command is on PATH.

## Usage

Console script:

```bash
# After install (pip/pipx/uv tool)
lib_cli_exit_tools --help
cli-exit-tools --help  # alias
lib_cli_exit_tools info
```

Library:

```python
import lib_cli_exit_tools

lib_cli_exit_tools.config.traceback = False  # show short messages
try:
    raise FileNotFoundError("missing.txt")
except Exception as e:
    code = lib_cli_exit_tools.get_system_exit_code(e)   # 2 on POSIX
    lib_cli_exit_tools.print_exception_message()        # prints: FileNotFoundError: missing.txt
    raise SystemExit(code)
```

Command names registered on install
- lib_cli_exit_tools (default)
- cli-exit-tools (alias)
- python -m lib_cli_exit_tools (module entry)

If you installed with --user or in a venv, make sure the corresponding bin directory is on PATH:
- Linux/macOS venv: .venv/bin
- Linux/macOS user: ~/.local/bin
- Windows venv: .venv\Scripts
- Windows user: %APPDATA%\Python\PythonXY\Scripts

## Exit Codes

- SIGINT → 130, SIGTERM → 143 (POSIX), SIGBREAK → 149 (Windows)
- SystemExit(n) → n
- Common exceptions map to POSIX/Windows codes (FileNotFoundError, PermissionError, ValueError, etc.)

### Broken pipe behavior
- Default: exit 141 quietly (128+SIGPIPE), no noisy error output.
- Configure: `config.broken_pipe_exit_code = 0` to treat as benign truncation, or `32` (EPIPE).

### Sysexits mode (optional)
- Set `config.exit_code_style = "sysexits"` to map ValueError/TypeError → EX_USAGE(64),
  FileNotFoundError → EX_NOINPUT(66), PermissionError → EX_NOPERM(77), generic OSError → EX_IOERR(74).

## Development

```bash
make test                 # ruff + pyright + pytest + coverage (default ON)
SKIP_BOOTSTRAP=1 make test  # skip auto-install of dev deps
COVERAGE=off make test       # disable coverage locally
COVERAGE=on make test        # force coverage and generate coverage.xml/codecov.xml
```

### Packaging sync (Conda/Brew/Nix)

- `make test` and `make push` automatically align the packaging skeletons in `packaging/` with the current `pyproject.toml`:
  - Conda: updates `{% set version = "X.Y.Z" %}` and both `python >=X.Y` constraints to match `requires-python`.
  - Homebrew: updates the source URL tag to `vX.Y.Z` and sets `depends_on "python@X.Y"` to match `requires-python`.
  - Nix: updates the package `version`, example `rev = "vX.Y.Z"`, and switches `pkgs.pythonXYZPackages` / `pkgs.pythonXYZ` to match the minimum Python version from `requires-python`.

- To run just the sync without bumping versions: `python scripts/bump_version.py --sync-packaging`.

- On release tags (`v*.*.*`), CI validates that packaging files are consistent with `pyproject.toml` and will fail if they drift.

## Versioning & Metadata

- Single source of truth for package metadata is `pyproject.toml` (`[project]`).
- The library reads its own installed metadata at runtime via `importlib.metadata` (see `src/lib_cli_exit_tools/__init__conf__.py`).
- Do not duplicate the version in code; bump only `pyproject.toml` and update `CHANGELOG.md`.
- Console script name is discovered from entry points; defaults to `lib_cli_exit_tools`.

## Packaging Skeletons

Starter files for package managers live under `packaging/`:

- Conda: `packaging/conda/recipe/meta.yaml` (update version + sha256)
- Homebrew: `packaging/brew/Formula/lib-cli-exit-tools.rb` (fill sha256 and vendored resources)
- Nix: `packaging/nix/flake.nix` (use working tree or pin to GitHub rev with sha256)

These are templates; fill placeholders (e.g., sha256) before publishing. Version and Python constraints are auto-synced from `pyproject.toml` by `make test`/`make push` and during version bumps.

## CI & Publishing

GitHub Actions workflows are included:

- `.github/workflows/ci.yml` — lint/type/test, build wheel/sdist, verify pipx and uv installs, Nix and Conda builds (CI-only; no local install required).
- `.github/workflows/release.yml` — on tags `v*.*.*`, builds artifacts and publishes to PyPI when `PYPI_API_TOKEN` secret is set.

To publish a release:
1. Bump `pyproject.toml` version and update `CHANGELOG.md`.
2. Tag the commit (`git tag v0.1.1 && git push --tags`).
3. Ensure `PYPI_API_TOKEN` secret is configured in the repo.
4. Release workflow uploads wheel/sdist to PyPI.

Conda/Homebrew/Nix: use files in `packaging/` to submit to their ecosystems. CI also attempts builds to validate recipes, but does not publish automatically.

### Local Codecov uploads

- `make test` (with coverage enabled) generates `coverage.xml` and `codecov.xml`, then attempts to upload via the Codecov CLI or the bash uploader.
- For private repos, set `CODECOV_TOKEN` (see `.env.example`) or export it in your shell.
- For public repos, a token is typically not required.

## License

MIT
