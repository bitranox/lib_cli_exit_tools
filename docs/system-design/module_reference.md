# Feature Documentation: lib_cli_exit_tools Module Reference

## Status
Complete

## Links & References
**Feature Requirements:** Not formally captured; inferred from package behavior and README installation notes.  
**Task/Ticket:** Internal maintenance directive to align documentation with architecture prompts.  
**Pull Requests:** Pending (documentation refresh).  
**Related Files:**

* `src/lib_cli_exit_tools/lib_cli_exit_tools.py`
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
4. `handle_cli_exception` maps signals and errors to exit codes using `default_signal_specs`, `_sysexits_mapping`, and `get_system_exit_code`.  
5. `print_exception_message` and `_print_output` render diagnostics when tracebacks are suppressed.  
6. Packaging metadata from `__init__conf__` feeds CLI help/version output so docs and runtime stay synchronized.

**System Dependencies:** Standard library (`signal`, `subprocess`, `sys`, `importlib.metadata`) plus `click` and `rich-click` for CLI/TUI behavior.

---

## Core Components

### Module: lib_cli_exit_tools/lib_cli_exit_tools.py
* **Purpose:** Centralize configuration, signal registration, and exception-to-exit-code translation so all CLIs share identical behavior.  
* **Location:** `src/lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Dataclass: `_Config`
* **Purpose:** Mutable singleton holding traceback, exit-code style, and broken-pipe overrides.  
* **Fields:**
  * `traceback` (bool) — emit full tracebacks when `True`.
  * `exit_code_style` (`"errno" | "sysexits"`) — choose mapping strategy.
  * `broken_pipe_exit_code` (int) — exit status for `BrokenPipeError`.  
  * `traceback_force_color` (bool) — opt-in flag to force ANSI-coloured Rich tracebacks on non-TTY streams.  
* **Notes:** Mutations apply process-wide; callers should restore defaults in tests.

#### Constant: `config`
* **Purpose:** Shared `_Config` instance consulted by all helpers.  
* **Interactions:** Mutated by CLI options and tests; read by `handle_cli_exception`, `get_system_exit_code`, and `print_exception_message`.

#### Exception Hierarchy: `CliSignalError`, `SigIntInterrupt`, `SigTermInterrupt`, `SigBreakInterrupt`
* **Purpose:** Represent signal-triggered interruptions so exit handlers can differentiate them from generic errors.  
* **Notes:** Raised by generated signal handlers; mapped to exit codes 130 (SIGINT), 143 (SIGTERM), 149 (SIGBREAK).

#### Dataclass: `SignalSpec`
* **Purpose:** Describe how to translate a signal into an exception, stderr message, and exit code.  
* **Key Fields:** `signum`, `exception`, `message`, `exit_code`.  
* **Usage:** Consumed by `install_signal_handlers`, `handle_cli_exception`.

#### Protocol: `_Echo`
* **Purpose:** Structural type for echo-like callables (defaulting to `click.echo`).  
* **Usage:** Enables dependency injection/testing of output behavior.

#### Function: `_default_echo(message: str, *, err: bool = True) -> None`
* **Purpose:** Bridge to `click.echo` when no custom echo is provided.  
* **Side Effects:** Writes text to stdout/stderr via Click.

#### Function: `default_signal_specs() -> list[SignalSpec]`
* **Purpose:** Produce platform-aware default signal specs.  
* **Behavior:** Always includes SIGINT; adds SIGTERM/SIGBREAK when available.

#### Function: `_make_raise_handler(exc_type) -> Callable`
* **Purpose:** Wrap an exception type into a signal-compatible `(signum, frame)` handler that raises the type immediately.  
* **Usage:** Internal helper for `install_signal_handlers`.

#### Function: `install_signal_handlers(specs | None) -> Callable[[], None]`
* **Purpose:** Register handlers for provided signal specs and return a restoration callback.  
* **Considerations:** Handlers are process-wide; callers must invoke the returned function to restore prior state.

#### Function: `handle_cli_exception(exc, *, signal_specs=None, echo=None) -> int`
* **Purpose:** Convert exceptions into deterministic exit codes, honoring configured signal mappings and traceback settings.  
* **Behavior:** Detects signal exceptions, `BrokenPipeError`, `click.ClickException`, and `SystemExit`; otherwise defers to `print_exception_message` and `get_system_exit_code`.

#### Function: `run_cli(cli, argv=None, *, prog_name=None, signal_specs=None, install_signals=True) -> int`
* **Purpose:** Execute a Click command under shared signal/error handling, flushing streams before returning.  
* **Behavior:** Optionally installs handlers, invokes `cli.main(...)`, funnels exceptions to `handle_cli_exception`, and restores handlers.

#### Function: `get_system_exit_code(exc) -> int`
* **Purpose:** Map exceptions to platform-appropriate exit codes using errno, Windows `winerror`, or sysexits semantics.  
* **Behavior:** Supports subprocess return codes, `SystemExit`, `KeyboardInterrupt`, `BrokenPipeError`, and default fallbacks.

#### Function: `_sysexits_mapping(exc) -> int`
* **Purpose:** Provide BSD `sysexits` codes when `config.exit_code_style == "sysexits"`.

#### Function: `_build_console(stream=None) -> rich.console.Console`
* **Purpose:** Construct a Rich console aligned with current rich-click styling for consistent error/help rendering.  
* **Usage:** Employed by `print_exception_message`.

#### Function: `print_exception_message(trace_back=config.traceback, length_limit=500, stream=None) -> None`
* **Purpose:** Emit the active exception message (and optional Rich traceback) with truncation safeguards.  
* **Behavior:** Flushes streams, surfaces captured subprocess output, renders highlighted tracebacks when enabled.

#### Function: `_print_output(exc_info, attr, stream=None) -> None`
* **Purpose:** Print `stdout`/`stderr` captured on exceptions such as `subprocess.CalledProcessError`.

#### Function: `flush_streams() -> None`
* **Purpose:** Best-effort flush of `sys.stdout` / `sys.stderr` to avoid buffered output loss during termination.

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
