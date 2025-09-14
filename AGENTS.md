# Repository Guidelines

## On session start

- Connect to the `systemprompts` MCP filesystem.
- Read following files and keep their guidance in working memory:
  - core_programming_solid.md
  - bash_clean_architecture.md
  - bash_clean_code.md
  - bash_small_functions.md
  - python_solid_architecture_enforcer.md
  - python_clean_architecture.md
  - python_clean_code.md
  - python_small_functions_style.md
  - python_libraries_to_use.md
  - python_structure_template.md

always apply those Rules :

- core_programming_solid.md

when writing or refracturing Bash scripts, apply those Rules :

- core_programming_solid.md
- bash_clean_architecture.md
- bash_clean_code.md
- bash_small_functions.md

when writing or refracturing Python scripts, apply those Rules :
- core_programming_solid.md
- python_solid_architecture_enforcer.md
- python_clean_architecture.md
- python_clean_code.md
- python_small_functions_style.md
- python_libraries_to_use.md
- python_lib_structure_template.md

## Project Structure & Module Organization

## Build, Test, and Development Commands

- `make help` — list all targets with one‑line docs.
- `make test` — run ruff (lint + format check), pyright, pytest with coverage, and upload to Codecov (if configured via `.env`).
- Auto‑bootstrap: `make test` installs dev tools (`pip install -e .[dev]`) if linters/test deps are missing. Use `SKIP_BOOTSTRAP=1 make test` to disable.
- `make build-all` — build Python wheel/sdist and attempt Conda/Homebrew/Nix builds (skips automatically if tools are missing).
- `make clean` — remove caches, coverage, and build artifacts (includes `dist/` and `build/`).

### Common Make Targets (Alphabetical)

| Target            | One‑line description |
| ----------------- | -------------------- |
| `brew-audit`      | Audit Homebrew formula (may fail until sha256 is set). |
| `brew-uninstall`  | Uninstall local Homebrew package. |
| `build-all`       | Build wheel/sdist and attempt Conda/Brew/Nix builds. |
| `cli`             | Run console script help. |
| `clean`           | Remove caches, coverage, and build artifacts (includes `dist/` and `build/`). |
| `dev`             | Editable install with dev extras. |
| `help`            | Show this table. |
| `install`         | Editable install. |
| `menu`            | Alias for `help`. |
| `nix-run`         | Run CLI from Nix build result. |
| `pip-git-install` | Install from Git ref/tag. |
| `pipx-install`    | pipx install. |
| `pipx-uninstall`  | pipx uninstall. |
| `pipx-upgrade`    | pipx upgrade. |
| `run`             | Run module entry (`python -m ... --help`). |
| `sdist-install`   | Install from built sdist. |
| `test`            | Lint, type‑check, tests with coverage, upload to Codecov. |
| `uv-dev`          | Dev install via `uv`. |
| `uv-tool-install` | Install as `uv` tool. |
| `uv-tool-run`     | One‑off run via `uvx`. |
| `uv-tool-upgrade` | Upgrade `uv` tool. |
| `user-install`    | Per‑user install. |
| `venv`            | Create `.venv`. |
| `verify-install`  | Verify CLI is on PATH. |
| `which-cmd`       | Show which CLI shim resolves. |
| `wheel-install`   | Install from built wheel. |

## Coding Style & Naming Conventions

## Testing Guidelines

## Commit & Pull Request Guidelines

## Architecture Overview

## Security & Configuration Tips

## Translations (Docs)

## Translations (App UI Strings)

## Changes in WEB Documentation

- when asked to update documentation - only do that in the english docs under /website/docs because other languages will be translated automatically,
  unless stated otherwise by the user. In doubt - ask the user

## Changes in APP Strings

- when i18 strings are changed, only to that in sources/\_locales/en because other languages will be translated automatically,
  unless stated otherwise by the user. In doubt - ask the user

## commit/push/GitHub policy

- run "make test" before any push to avoid lint/test breakage.
- after push, monitor errors in the github actions and try to correct the errors
