# Feature Documentation: lib_cli_exit_tools Module Reference

## Status
Complete

## Links & References
**Feature Requirements:** Not formally captured; inferred from package behavior and README installation notes.  
**Task/Ticket:** Internal maintenance directive to align documentation with architecture prompts.  
**Pull Requests:** Pending (documentation refresh).  
**Related Files:**

* `src/lib_cli_exit_tools/lib_cli_exit_tools.py`
* `src/lib_cli_exit_tools/core/configuration.py`
* `src/lib_cli_exit_tools/core/exit_codes.py`
* `src/lib_cli_exit_tools/application/runner.py`
* `src/lib_cli_exit_tools/adapters/signals.py`
* `src/lib_cli_exit_tools/cli.py`
* `src/lib_cli_exit_tools/__init__conf__.py`
* `src/lib_cli_exit_tools/__init__.py`
* `src/lib_cli_exit_tools/__main__.py`
* `pyproject.toml` (`[project]` metadata, console scripts)
* `tests/test_exit_tools.py`
* `tests/test_cli.py`
* `tests/test_cli_extra.py`
* `tests/test_extend_cli.py`
* `tests/test_lib_extra.py`

---

## Problem Statement
Automations and downstream CLIs rely on `lib_cli_exit_tools` for deterministic exit codes and signal handling, yet historic documentation mixed implementation detail with intent and omitted several helper functions. Maintainers lacked a single authoritative source that ties runtime configuration, CLI adapters, and packaging metadata back to the system design principles defined for the project.

## Solution Overview

* Establish a canonical module reference that describes why each component exists, what contract it exposes, and how it interacts with CLI surfaces.
* Align inline docstrings and system documentation so that CLI behavior, exit code mappings, and packaging metadata remain consistent.
* Highlight configuration knobs (`config.traceback`, `config.exit_code_style`, `config.broken_pipe_exit_code`) and their impact on shell consumers.
* Document platform-aware signal wiring and restoration expectations to prevent leaked handlers in embedding contexts.

---

## Architecture Integration

**App Layer Fit:** CLI adapter layer wrapping domain logic for exit orchestration; integrates with other Click-based applications that need consistent exit semantics.  
**Data Flow:**
1. Console script (or `python -m lib_cli_exit_tools`) resolves to `lib_cli_exit_tools.cli.main`.  
2. The Click group stores global flags and mutates `lib_cli_exit_tools.config`.  
3. `run_cli` optionally installs signal handlers, executes the requested Click command, and funnels exceptions into `handle_cli_exception`.  
4. `handle_cli_exception` maps signals and errors to exit codes using `default_signal_specs` and `get_system_exit_code`.  
5. `print_exception_message` and `_print_output` (within `application.runner`) render diagnostics when tracebacks are suppressed.  
6. Packaging metadata from `__init__conf__` feeds CLI help/version output so docs and runtime stay synchronized.

**System Dependencies:** Standard library (`signal`, `subprocess`, `sys`, `importlib.metadata`) plus `click` and `rich-click` for CLI/TUI behavior.

---

## Core Components

### Module: lib_cli_exit_tools/lib_cli_exit_tools.py
* **Purpose:** Provide a façade that re-exports configuration, signal helpers, and orchestration utilities so existing imports stay valid after the refactor.
* **Location:** `src/lib_cli_exit_tools/lib_cli_exit_tools.py`
* **Notes:** Aggregates symbols from the layered modules to minimise breaking changes and exposes `i_should_fail()` as a deterministic failure helper for exercising error-handling paths.

### Module: lib_cli_exit_tools/core/configuration.py
* **Purpose:** Own the mutable runtime configuration shared across CLI executions.
* **Location:** `src/lib_cli_exit_tools/core/configuration.py`

#### Dataclass: `_Config`
* **Role:** Captures traceback, exit-code style, broken-pipe handling, and Rich colouring toggles.
* **Notes:** Mutations apply process-wide; tests must restore defaults to avoid leakage.

#### Constant: `config`
* **Role:** Singleton instance consumed by adapters and orchestration code.
* **Interactions:** Mutated by the CLI (`--traceback`) and inspected by error handlers and exit-code mappers.

### Module: lib_cli_exit_tools/core/exit_codes.py
* **Purpose:** Convert exceptions into deterministic OS exit statuses.
* **Location:** `src/lib_cli_exit_tools/core/exit_codes.py`

#### Function: `get_system_exit_code(exc: BaseException) -> int`
* **Role:** Mirrors platform-specific errno/winerror semantics or BSD sysexits based on `config.exit_code_style`.
* **Notes:** Handles `CalledProcessError`, `SystemExit`, and `BrokenPipeError` explicitly before falling back to errno tables.

### Module: lib_cli_exit_tools/adapters/signals.py
* **Purpose:** Translate operating-system signals into structured exceptions and reversible handlers.
* **Location:** `src/lib_cli_exit_tools/adapters/signals.py`

#### Exceptions: `CliSignalError`, `SigIntInterrupt`, `SigTermInterrupt`, `SigBreakInterrupt`
* **Role:** Represent distinct signal pathways so exit handling can map them to stable codes (130/143/149).

#### Dataclass: `SignalSpec`
* **Role:** Describe signal metadata (signum, exception, message, exit code) used by installers and handlers.

#### Function: `default_signal_specs(extra: Iterable[SignalSpec] | None = None) -> list[SignalSpec]`
* **Role:** Provide platform-aware defaults (always SIGINT; conditional SIGTERM/SIGBREAK) with optional extension points.

#### Function: `install_signal_handlers(specs: Sequence[SignalSpec] | None = None) -> Callable[[], None]`
* **Role:** Register handlers that raise the specified exceptions and return a restoration callback for clean-up.

### Module: lib_cli_exit_tools/application/runner.py
* **Purpose:** Orchestrate Click command execution with shared signal wiring, exception translation, and Rich-based diagnostics.
* **Location:** `src/lib_cli_exit_tools/application/runner.py`

#### Protocol: `_Echo`
* **Role:** Structural type enabling dependency injection for stderr writers in tests.

#### Utilities: `flush_streams`, `_build_console`, `_print_output`, `print_exception_message`
* **Role:** Manage stream flushing and Rich rendering when tracebacks are suppressed or forced.

#### Function: `handle_cli_exception(exc, *, signal_specs=None, echo=None) -> int`
* **Role:** Map exceptions to exit codes, emit signal messages, honour `config.traceback`, and delegate to `get_system_exit_code` when needed.
* **Notes:** Raises the original exception when traceback mode is enabled; otherwise trims output and prints captured subprocess streams.

#### Function: `run_cli(cli, argv=None, *, prog_name=None, signal_specs=None, install_signals=True, exception_handler=None, signal_installer=None) -> int`
* **Role:** Install signal handlers (unless disabled), execute the passed Click command, and funnel exceptions through an injectable handler before flushing streams.
* **Notes:** New `exception_handler` and `signal_installer` hooks support advanced embedding and unit testing scenarios.
### Module: lib_cli_exit_tools/cli.py
* **Purpose:** Provide the Click command group and subcommands that surface the exit tooling.  
* **Location:** `src/lib_cli_exit_tools/cli.py`

#### Constant: `CLICK_CONTEXT_SETTINGS`
* **Purpose:** Standardize help option flags (`-h`, `--help`).

#### Function: `_configure_rich_click_output() -> None`
* **Purpose:** Neutralize rich-click styling when stdout lacks UTF support (e.g., Windows CI pipes) to prevent `UnicodeEncodeError`.  
* **Side Effects:** Adjusts global rich-click configuration at import time based on stream capabilities.

#### Function: `cli(ctx, traceback) -> None`
* **Purpose:** Root Click group; records the `--traceback` option and mutates `lib_cli_exit_tools.config.traceback`.

#### Function: `cli_info() -> None`
* **Purpose:** Emit project metadata by delegating to `__init__conf__.print_info()`.

#### Function: `cli_fail() -> None`
* **Purpose:** Invoke `lib_cli_exit_tools.i_should_fail()` so operators can validate error-path handling from the packaged CLI without crafting bespoke failing commands.
* **Notes:** Surfaces the stable `RuntimeError('i should fail')` message, making it safe for scripted assertions and support playbooks.

#### Function: `main(argv=None) -> int`
* **Purpose:** Compose the CLI invocation by delegating to `lib_cli_exit_tools.run_cli`, returning exit codes instead of exiting directly.

### Module: lib_cli_exit_tools/__init__conf__.py
* **Purpose:** Expose metadata derived from the installed distribution for use in CLI help/version output.  
* **Location:** `src/lib_cli_exit_tools/__init__conf__.py`

#### Protocol: `_MetaMapping`
* **Purpose:** Unify metadata API across Python versions by guaranteeing the `.get` method.

#### Helper Functions: `_get_str`, `_meta`, `_version`, `_home_page`, `_author`, `_summary`, `_shell_command`
* **Purpose:** Normalize metadata values (strings, URLs, author details) and discover console-script bindings.  
* **Behavior:** Fall back to safe defaults when metadata is missing.

#### Constants: `name`, `title`, `version`, `homepage`, `author`, `author_email`, `shell_command`
* **Purpose:** Public metadata consumed by CLI commands and documentation. Values resolve once per import using helper functions.

#### Function: `print_info() -> None`
* **Purpose:** Render an aligned metadata block for CLI consumers.

### Module: lib_cli_exit_tools/__init__.py
* **Purpose:** Define the canonical public API surface by re-exporting helpers from `lib_cli_exit_tools.py`.  
* **Notes:** Maintains `__all__` in sync with documentation for semantic versioning guarantees.

### Module: lib_cli_exit_tools/__main__.py
* **Purpose:** Allow `python -m lib_cli_exit_tools` to behave identically to the installed console script by delegating to `cli.main()`.

---

## Implementation Details

**Dependencies:** Runtime requires `click` and `rich-click`. Rich traceback rendering uses `rich`. No optional extras beyond test dependencies.  
**Key Configuration:**

* `config.traceback` — toggled by CLI `--traceback`; affects whether exceptions re-raise or produce formatted output.  
* `config.exit_code_style` — defaults to `"errno"`; when set to `"sysexits"` exit codes map to BSD sysexits constants.  
* `config.broken_pipe_exit_code` — defaults to `141` to align with POSIX pipeline conventions.

**Signal Handling:**

* `install_signal_handlers` returns a restoration callback; callers must execute it (preferably in `finally`) to restore original handlers.  
* SIGTERM and SIGBREAK specs are conditionally added based on platform capabilities.

**Extensibility:**

* `run_cli` exposes `exception_handler` and `signal_installer` hooks so embedders and unit tests can replace the default wiring without patching globals.

---

## Testing Approach

**Manual Testing Steps:**
1. Run `python -m lib_cli_exit_tools info` to confirm metadata output.  
2. Invoke a sample Click command through `run_cli` and trigger `Ctrl+C` to verify SIGINT exit code 130.  
3. Pipe CLI output to `head -n0` (POSIX) or a closed pipe to simulate `BrokenPipeError` and observe `config.broken_pipe_exit_code`.

**Automated Tests:**

* `make test` runs Ruff, Pyright, and pytest suites (`tests/test_exit_tools.py`, `tests/test_cli.py`, etc.) with coverage enabled.  
* Signal handler behavior is simulated using pytest fixtures to avoid actual OS signal delivery.  
* Metadata helpers use monkeypatched `importlib.metadata` to exercise fallback paths.

**Edge Cases:** Missing metadata, unsupported signals, subprocess errors with captured output, non-UTF stdout encodings.

**Test Data:** No fixtures beyond temporary directories; pytest handles isolation.

---

## Known Issues & Future Improvements

* Windows-specific signals (`SIGBREAK`) best-effort only; additional CI coverage would increase confidence.  
* `_sysexits_mapping` covers common built-in exceptions; extend if consumers require additional mappings.  
* Global `config` state is process-wide—embedding in long-running hosts should reset configuration between invocations.

---

## Risks & Considerations

**Technical Risks:**

* Forgetting to call the restoration callback from `install_signal_handlers` can leak handlers into host applications.  
* Changing default exit codes is a breaking change for automation scripts; follow Semantic Versioning and document in the changelog.

**User Impact:**

* Default behavior suppresses tracebacks; support teams should instruct users to pass `--traceback` when debugging complex failures.  
* Platform-specific exit codes (Windows vs POSIX) remain intentional; cross-platform scripts should handle both values.

---

## Documentation & Resources

**Internal References:**

* README for installation and quickstart guidance.  
* Inline module docstrings reflecting the same intent and behavior.  
* `AGENTS.md` for documentation workflow requirements.

**External References:**

* [Click Documentation](https://click.palletsprojects.com)  
* [Python `signal` module](https://docs.python.org/3/library/signal.html)  
* [BSD sysexits reference](https://man.freebsd.org/cgi/man.cgi?sysexits)

---

**Created:** 2025-09-25 by Codex Assistant  
**Last Updated:** 2025-09-25 by Codex Assistant  
**Review Cycle:** Revisit quarterly or after each feature addition impacting CLI exits.
