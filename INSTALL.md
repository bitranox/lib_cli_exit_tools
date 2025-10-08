# Installation Guide

This document collects every supported installation path for `lib_cli_exit_tools`, plus notes on platform quirks and troubleshooting. If you only need the standard release from PyPI, see the short "Install" section in `README.md` or run:

```bash
pip install lib_cli_exit_tools
```

The sections below cover more specialised workflows, from editable installs to package-manager builds.

## Table of Contents
- [Supported Python Versions](#supported-python-versions)
- [Installation Flows](#installation-flows)
  - [PyPI (latest release)](#pypi-latest-release)
  - [Editable install in a virtual environment](#editable-install-in-a-virtual-environment)
  - [Per-user installs (`pip --user`)](#per-user-installs-pip---user)
  - [pipx](#pipx)
  - [uv](#uv)
  - [Installing from local artifacts](#installing-from-local-artifacts)
  - [Poetry / PDM](#poetry--pdm)
  - [Install directly from Git](#install-directly-from-git)
  - [Conda / Mamba environments](#conda--mamba-environments)
  - [System package managers](#system-package-managers)
- [Path configuration](#path-configuration)
- [Troubleshooting](#troubleshooting)
  - [PEP 668 “externally managed environment” errors](#pep-668-externally-managed-environment-errors)
  - [Missing command on PATH](#missing-command-on-path)
  - [Colour output not appearing](#colour-output-not-appearing)

## Supported Python Versions

`lib_cli_exit_tools` targets Python 3.13 and newer. Wheels are published for CPython on Linux, macOS, and Windows. For alternative interpreters (PyPy) install from source using `pip install lib_cli_exit_tools`.

## Installation Flows

### PyPI (latest release)

The quickest path for production use:

```bash
pip install lib_cli_exit_tools
# Pin to a specific release when reproducibility matters
pip install "lib_cli_exit_tools==X.Y.Z"
# Upgrade later
pip install --upgrade lib_cli_exit_tools
```

This command registers the `lib_cli_exit_tools`, `cli-exit-tools`, and `lib-cli-exit-tools` entry points on your PATH.

### Editable install in a virtual environment

Use this flow when developing the library locally:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[dev]
# Alternatively, install runtime dependencies only
pip install .
```

### Per-user installs (`pip --user`)

Install to the user site-packages directory without creating a virtual environment:

```bash
pip install --user lib_cli_exit_tools
```

Ensure `~/.local/bin` (POSIX) or `%APPDATA%\Python\PythonXY\Scripts` (Windows) is on your PATH. This approach respects [PEP 668](https://peps.python.org/pep-0668/)—avoid running it in system-managed Python installs that disallow modifications.

### pipx

`pipx` isolates CLI tools in dedicated environments, making upgrades easy:

```bash
pipx install lib_cli_exit_tools
pipx upgrade lib_cli_exit_tools
# Install directly from a tagged release or commit
pipx install "git+https://github.com/bitranox/lib_cli_exit_tools@vX.Y.Z"
```

### uv

[uv](https://github.com/astral-sh/uv) provides fast installs and execution:

```bash
uv pip install -e .[dev]
uv tool install lib_cli_exit_tools
uvx lib_cli_exit_tools --help
```

### Installing from local artifacts

Build a wheel or sdist locally and install it in offline environments:

```bash
python -m build
pip install dist/lib_cli_exit_tools-*.whl
pip install dist/lib_cli_exit_tools-*.tar.gz
```

### Poetry / PDM

Add the library to a project managed by Poetry or PDM:

```bash
# Poetry
poetry add lib_cli_exit_tools
poetry install

# PDM
pdm add lib_cli_exit_tools
pdm install
```

### Install directly from Git

CI systems or early adopters can install from a specific revision:

```bash
pip install "git+https://github.com/bitranox/lib_cli_exit_tools@vX.Y.Z#egg=lib_cli_exit_tools"
```

### Conda / Mamba environments

Create a dedicated Conda environment and install via `pip` inside it:

```bash
mamba create -n cli-exit python=3.13 pip
mamba activate cli-exit
pip install lib_cli_exit_tools
```

### System package managers

Packages may be published for platform-native installers:

- **Homebrew (macOS):** `brew install lib_cli_exit_tools`
- **Nix:** `nix run github:bitranox/lib_cli_exit_tools` or `nix develop` with the provided flake
- **Deb/RPM:** build with `fpm` using the project’s `packaging/` scripts

Check the repository’s release notes for the current distribution status.

## Path configuration

After installation the following commands should resolve:

- `lib_cli_exit_tools`
- `cli-exit-tools`
- `python -m lib_cli_exit_tools`

If you installed inside a virtual environment, activate it before running the commands. For user installs, ensure the relevant `bin`/`Scripts` directory is included in your PATH:

- Linux/macOS venv: `<venv>/bin`
- Linux/macOS user site: `~/.local/bin`
- Windows venv: `<venv>\Scripts`
- Windows user site: `%APPDATA%\Python\PythonXY\Scripts`

## Troubleshooting

### PEP 668 “externally managed environment” errors

Some OS distributions (Ubuntu, Fedora, Debian) mark the system Python as externally managed. Running `pip install` directly into that interpreter raises an error similar to:

```
error: externally-managed-environment
```

**Fix:**
- Create a virtual environment (`python -m venv .venv`) and install inside it, or
- Use `pipx`, `conda`, `uv`, or another isolated environment manager.

### Missing command on PATH

If `lib_cli_exit_tools --help` returns “command not found”, confirm that the installation location is on PATH. The most common fix is adding `~/.local/bin` (POSIX) or `%APPDATA%\Python\PythonXY\Scripts` (Windows) to your PATH environment variable, then re-opening the shell.

### Colour output not appearing

Set `lib_cli_exit_tools.config.traceback_force_color = True` in your application to force Rich to emit coloured tracebacks even when stderr is not detected as a TTY. Alternatively, export `RICH_FORCE_TERMINAL=1` before running the CLI.

---

For additional environment automation (Conda, Nix, Homebrew formulas), consult the scripts under `packaging/` and the Makefile targets described in `README.md`.
