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

- `make help` — list all targets with one‑line docs (reads lines annotated with `##`).
- `make menu` — open the interactive menu explicitly (same as running `make` with no args).
- `make clean` — remove local artifacts

- Tests
- `make test`

### Common Make Targets (Alphabetical)

| Target                     | One‑line description                                                                   |
| -------------------------- | -------------------------------------------------------------------------------------- |
| `clean`                    | Remove local build/preview artifacts (`tmp/`, `web-local-preview/`, `website/build/`). |
| `test`                     | Prettier (write), ESLint, then Vitest (coverage if configured) + docs URL guard.       |

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
