# Feature Documentation: lib_cli_exit_tools Runtime & CLI

## Status

Complete

## Links & References

**Feature Requirements:** Internal runtime/CLI standardisation (captured in architecture prompts)  
**Task/Ticket:** Library maintenance directive (no external ticket)  
**Pull Requests:** Refactor and documentation alignment delivered as part of v1.5.0 and subsequent documentation update  
**Related Files:**

* `src/lib_cli_exit_tools/lib_cli_exit_tools.py`
* `src/lib_cli_exit_tools/__init__.py`
* `src/lib_cli_exit_tools/__init__conf__.py`
* `src/lib_cli_exit_tools/core/configuration.py`
* `src/lib_cli_exit_tools/core/exit_codes.py`
* `src/lib_cli_exit_tools/adapters/signals.py`
* `src/lib_cli_exit_tools/application/runner.py`
* `src/lib_cli_exit_tools/cli.py`
* `src/lib_cli_exit_tools/__main__.py`
* `tests/core/test_exit_code_poetry.py`
* `tests/application/test_runner_poetry.py`
* `tests/application/test_signal_poetry_posix.py`
* `tests/application/test_signal_poetry_windows.py`
* `tests/adapters/test_signals_poetry.py`
* `tests/cli/test_cli_poetry.py`

---

## Problem Statement

Downstream CLIs and automation pipelines need deterministic exit codes, signal handling, and provenance information. Early iterations mixed implementation detail with intent, lacked platform-aware documentation, and provided limited guidance on configuration toggles. Contributors also needed an authoritative map tying runtime modules to system-level architecture guidance.

## Solution Overview

* Split runtime responsibilities into well-documented modules (`core`, `application`, `adapters`, `cli`) that mirror clean-architecture prompts.
* Provide a lightweight metadata façade (`__init__conf__.py`) so CLI commands expose provenance without heavy packaging dependencies.
* Funnel all exit handling through `application.runner` and `core.exit_codes`, documenting each resolver path and configuration hook.
* Publish poetry-style, environment-aware tests that read like specifications and explicitly cover POSIX and Windows signal behaviours.
* Align system documentation with inline docstrings and testing strategy to create a single source of truth for maintainers.

---

## Architecture Integration

**App Layer Fit:** CLI adapter and supporting runtime layers within a clean architecture (core policy → application orchestration → adapters → CLI façade).

**Data Flow:**

1. Users invoke console scripts (`lib_cli_exit_tools`, `cli-exit-tools`) or `python -m lib_cli_exit_tools`.
2. `cli.main` configures Rich styling, toggles `config.traceback`, and delegates to `lib_cli_exit_tools.run_cli`.
3. `application.runner.run_cli` optionally installs signal handlers, executes the Click command, and routes exceptions through `handle_cli_exception`.
4. `handle_cli_exception` prints diagnostics (`print_exception_message`), honours configuration overrides, and calls `core.exit_codes.get_system_exit_code`.
5. `core.exit_codes` resolves exit codes via ordered strategies (subprocess return codes, signals, errno/winerror, sysexits, platform tables).
6. `__init__conf__.py` supplies metadata for `info` commands and documentation output.

**System Dependencies:** Standard library (`signal`, `sys`, `subprocess`, `importlib.metadata`, `contextlib`, `dataclasses`), `click`, `rich`, `rich-click`.

---

## Core Components

### Module: lib_cli_exit_tools/lib_cli_exit_tools.py

* **Purpose:** Facade re-exporting public APIs after refactoring into layered modules; preserves historic import paths.
* **Input:** Downstream imports (`from lib_cli_exit_tools import run_cli` etc.).
* **Output:** Stable symbols (`config`, `run_cli`, `handle_cli_exception`, `SignalSpec`, etc.) and the deterministic failure helper `i_should_fail()`.
* **Location:** `src/lib_cli_exit_tools/lib_cli_exit_tools.py`

### Module: lib_cli_exit_tools/__init__.py

* **Purpose:** Re-export facade symbols while validating alignment with `PUBLIC_API`.
* **Input:** Imports from `lib_cli_exit_tools.lib_cli_exit_tools`.
* **Output:** Public module namespace for library consumers; raises `ImportError` if the facade and exports drift.
* **Location:** `src/lib_cli_exit_tools/__init__.py`

### Module: lib_cli_exit_tools/__init__conf__.py

* **Purpose:** Provide metadata helpers and `print_info()` for CLI provenance.
* **Input:** Distribution metadata via `importlib.metadata`; fallback defaults.
* **Output:** Constants (`name`, `title`, `version`, `homepage`, `author`, `shell_command`) and metadata helpers (`_meta`, `_version`, `_home_page`, `_author`, `_summary`).
* **Location:** `src/lib_cli_exit_tools/__init__conf__.py`

### Module: lib_cli_exit_tools/core/configuration.py

* **Purpose:** Centralise runtime toggles (`traceback`, `exit_code_style`, `broken_pipe_exit_code`, `traceback_force_color`).
* **Input:** CLI switches, application code, tests.
* **Output:** Mutable singleton `config`, context manager `config_overrides`, and `reset_config()` helper.
* **Location:** `src/lib_cli_exit_tools/core/configuration.py`

### Module: lib_cli_exit_tools/core/exit_codes.py

* **Purpose:** Map exceptions to deterministic exit codes across POSIX, Windows, and BSD sysexits semantics.
* **Input:** Exceptions from `handle_cli_exception`.
* **Output:** Integer exit codes via `get_system_exit_code` and helper resolvers (`_code_from_*`, `_sysexits_mapping`, `_safe_int`).
* **Location:** `src/lib_cli_exit_tools/core/exit_codes.py`

### Module: lib_cli_exit_tools/adapters/signals.py

* **Purpose:** Define signal-to-exception translations and reversible installer utilities.
* **Input:** Host platform signal availability (`SIGINT`, `SIGTERM`, `SIGBREAK`).
* **Output:** Exception hierarchy (`CliSignalError` et al.), dataclass `SignalSpec`, `default_signal_specs`, and `install_signal_handlers`.
* **Location:** `src/lib_cli_exit_tools/adapters/signals.py`

### Module: lib_cli_exit_tools/application/runner.py

* **Purpose:** Execute Click commands with shared signal handling, diagnostics, and exit-code translation.
* **Input:** Click command objects, optional overrides for signal specs/handlers, configuration state.
* **Output:** Integer exit codes, console output, restoration callbacks; utilities (`flush_streams`, `print_exception_message`, `handle_cli_exception`, `run_cli`).
* **Location:** `src/lib_cli_exit_tools/application/runner.py`

### Module: lib_cli_exit_tools/cli.py

* **Purpose:** Expose Click CLI group (`cli`) and subcommands (`info`, `fail`), manage Rich styling downgrades, and bridge into the application layer.
* **Input:** Command-line arguments, terminal capabilities.
* **Output:** Exit statuses (via `main`), Rich-styled output, configuration mutations (`config.traceback`).
* **Location:** `src/lib_cli_exit_tools/cli.py`

### Module: lib_cli_exit_tools/__main__.py

* **Purpose:** Support `python -m lib_cli_exit_tools` execution by delegating to `cli.main()`.
* **Input:** Module execution.
* **Output:** Propagated exit code.
* **Location:** `src/lib_cli_exit_tools/__main__.py`

---

## Implementation Details

**Dependencies:**

* External: `click`, `rich`, `rich-click`.
* Internal: Core modules described above; no third-party network services.

**Key Configuration:**

* Runtime toggles stored in `core.configuration._Config` (`traceback`, `exit_code_style`, `broken_pipe_exit_code`, `traceback_force_color`).
* CLI-level flag `--traceback/--no-traceback` and environment detection for Rich styling.

**Database Changes:** None.

**Error Handling Strategy:**

* Signals converted to structured exceptions (`SigIntInterrupt`, `SigTermInterrupt`, `SigBreakInterrupt`).
* `handle_cli_exception` emits Rich tracebacks or summaries depending on configuration.
* `get_system_exit_code` resolves standard exit statuses and falls back to platform tables or sysexits semantics.

---

## Testing Approach

**Manual Testing Steps:**

1. Install locally (`pip install -e .[dev]`).
2. Run `lib_cli_exit_tools info` to inspect metadata; expect formatted output matching `__init__conf__.py` values.
3. Run `lib_cli_exit_tools fail` and `lib_cli_exit_tools --traceback fail`; confirm exit codes (`1` or sysexits equivalent) and Rich traceback when requested.
4. On POSIX: pipe a command (`lib_cli_exit_tools info | head -n1`) and send `SIGINT` to verify exit code `130`.
5. On Windows: run `python -m lib_cli_exit_tools info` then send `CTRL+BREAK` to verify exit code `149`.

**Automated Tests:**

* `python3 -m scripts test --coverage on` executes Ruff, import-linter, Pyright, Bandit, pip-audit, and pytest with coverage upload.
* Unit/property tests: `tests/core/test_exit_code_poetry.py`, `tests/application/test_runner_poetry.py`, `tests/adapters/test_signals_poetry.py`.
* Integration tests: `tests/application/test_signal_poetry_posix.py` (POSIX SIGINT), `tests/application/test_signal_poetry_windows.py` (Windows SIGBREAK), CLI smoke tests in `tests/cli/test_cli_poetry.py`.
* Environment markers ensure OS-specific tests are skipped only when unsupported; CI matrix (Ubuntu/macOS/Windows) exercises each path.

**Edge Cases:**

* Invalid `SystemExit` payloads default to exit code `1` (tested).
* Sysexits mapping covers non-numeric payloads, external process failures, missing metadata.
* Broken pipe exit codes obey configuration overrides.

**Test Data:**

* Poetry-style tests embed inline data; property-based tests rely on Hypothesis strategies (integers across wide ranges).

---

## Known Issues & Future Improvements

**Current Limitations:**

* Windows SIGBREAK integration requires a real console capable of delivering the signal; test skips on hosts without `SIGBREAK` support.
* Rich styling downgrades rely on encoding detection; non-UTF encodings that still support Unicode may bypass styling.

**Future Enhancements:**

* Consider publishing API docs (mkdocs/Sphinx) derived from the new docstrings.
* Explore adding macOS-specific signal integration tests when additional signals become relevant.

---

## Risks & Considerations

**Technical Risks:**

* Changes to Click or Rich APIs could affect styling or version detection; monitor upstream releases.
* Windows-only paths are harder to validate locally; rely on CI and minimise platform-specific branching.

**User Impact:**

* Breaking changes are gated through semantic versioning; CLI behaviour remains stable.
* Rich styling downgrades ensure compatibility with non-UTF terminals, reducing surprise for script consumers.

---

## Documentation & Resources

**Internal References:**

* Clean architecture prompts under `/media/srv-main-softdev/projects/softwarestack/systemprompts`.
* README, INSTALL, CONTRIBUTING, DEVELOPMENT guides (updated alongside this documentation).

**External References:**

* Click documentation – <https://click.palletsprojects.com/>
* Rich documentation – <https://rich.readthedocs.io/>
* BSD sysexits reference – <https://man.freebsd.org/cgi/man.cgi?sysexits(3)>

---

**Created:** 2025-10-08 by Codex (automated)  
**Last Updated:** 2025-10-08 by Codex (automated)  
**Review Cycle:** Revisit every 90 days or after major CLI/runtime changes
