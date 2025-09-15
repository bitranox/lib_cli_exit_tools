# Changelog

## [1.0.3] - 2025-09-16

- added make menu

## [1.0.2] - 2025-09-15

- minor internals

## [1.0.1] - 2025-09-15

- minor internals 

## [1.0.0] - 2025-09-15

- public release

## [Unreleased]

### Added
- CI job to execute Jupyter notebook on Python 3.10 (installs ipykernel, normalizes notebook IDs) and a tag‑time packaging‑consistency check.
- Packaging auto‑sync: `make test`, `make push`, and the bump script now align Conda/Brew/Nix files to `pyproject.toml` version, `requires-python`, and runtime deps. Homebrew resources are updated (URL + sha256) using PyPI metadata. A sync‑only mode is available via `python scripts/bump_version.py --sync-packaging`.
- Tests covering SystemExit variants, tolerant output printing, English CLI messages, and Windows mapping via monkeypatched `os.name`.

### Changed
- Robust SystemExit handling in `get_system_exit_code` (handles `None`, strings, and non‑int codes safely). Behavior remains backwards‑compatible for common cases.
- OS mapping now uses `os.name == 'posix'` instead of `sys.builtin_module_names`.
- `_print_output` now accepts `bytes` or `str` for `stdout`/`stderr` and avoids assertions; decodes bytes with UTF‑8 and `errors='replace'`.
- CLI signal messages switched to English: “Aborted (SIGINT).”, “Terminated (SIGTERM/SIGBREAK).”, “Terminated (SIGBREAK).”.
- Metadata lookup in `__init__conf__` resolved once and reused.
- Coverage gate relaxed to 80% and removed `# pragma: no cover` comments.
- Quickstart notebook defaults to install from GitHub; added cell IDs; last cell prints exit code example instead of exiting.

### Fixed
- Pyright 3.10 compatibility in `__init__conf__` by typing to a minimal metadata protocol; resolved unknown `.get` errors.
- Ruff F401 false positive on notebook by adding a per‑file ignore in `pyproject.toml`.

### Docs
- README: documented packaging sync behavior and notebook usage.
- CONTRIBUTING: clarified versioning (bump only `pyproject.toml` + `CHANGELOG.md`), and documented packaging sync workflow.

## [0.1.1] - 2025-09-15

- _Describe changes here._

## [0.1.0] - 2025-09-14

- Unify package name to `lib_cli_exit_tools` (project name, module path, console scripts).
- Fix public API imports in `__init__.py`.
- Add `from __future__ import annotations` and module docstring.
- Add tests for exit code mapping and CLI behavior.
- Expand README and add Makefile; add dev extras (pytest/ruff/pyright).

## [0.0.1] - 2025-09-13

- Initial public release.

---

All notable changes to this project will be documented in this file.
The format is based on Keep a Changelog, and this project adheres to
Semantic Versioning (where applicable for add-on releases).
