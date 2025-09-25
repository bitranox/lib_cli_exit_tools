# Feature Documentation: lib_cli_exit_tools Module Reference

## Status
Complete

## Links & References
**Feature Requirements:** Not formally documented; inferred from existing library behavior and README.  
**Task/Ticket:** Internal maintenance request (no external ticket).  
**Related Files:**
- `src/lib_cli_exit_tools/lib_cli_exit_tools.py`
- `src/lib_cli_exit_tools/cli.py`
- `src/lib_cli_exit_tools/__init__conf__.py`
- `src/lib_cli_exit_tools/__init__.py`
- `src/lib_cli_exit_tools/__main__.py`
- `pyproject.toml` (`[project]` metadata and entry points)
- `tests/test_exit_tools.py`, `tests/test_cli.py`, `tests/test_cli_extra.py`, `tests/test_extend_cli.py`, `tests/test_lib_extra.py`

## Solution Overview
This document catalogs every module, class, and function inside `src/lib_cli_exit_tools`, explaining responsibilities, inputs, outputs, and file locations. The goal is to provide maintainers with an at-a-glance reference that clarifies how configuration, signal handling, and Click orchestration interact without changing the existing runtime behavior.

## Architecture Integration
**Where this fits in the overall app:**
The package is the core runtime library for handling CLI exits within the broader project. The `lib_cli_exit_tools` module exposes signal-aware exit code helpers, while `cli.py` wires those helpers into a Click-based command group. `__init__conf__.py` retrieves distribution metadata so that the CLI and documentation stay in sync with `pyproject.toml`. `__init__.py` re-exports the public API, and `__main__.py` enables `python -m lib_cli_exit_tools` execution.

**Data flow:**
1. Users invoke the CLI (`cli.py` or console script).  
2. The CLI stores global options in Click context and updates `lib_cli_exit_tools.config`.  
3. Commands execute; on exit or exception, `run_cli` and `handle_cli_exception` translate outcomes into exit codes, optionally using registered signal handlers.  
4. `get_system_exit_code` derives platform-aware codes; `print_exception_message` formats traceback output when enabled.  
5. Metadata for help/version commands flows from `__init__conf__.py`, which reads `importlib.metadata` at import time.

## Core Components

### Module: lib_cli_exit_tools/lib_cli_exit_tools.py
**Purpose:** Provide configurable signal handling, exit-code derivation, and Click wiring helpers.  
**Input:** Called by CLI code and downstream projects that import the library.  
**Output:** Exposes configuration, exceptions, helper functions, and side effects (signal registration, stream flushing).  
**Location:** `src/lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Dataclass: _Config
**Purpose:** Stores runtime toggles (`traceback`, `exit_code_style`, `broken_pipe_exit_code`).  
**Input:** Field values set at instantiation or mutated by callers (e.g., CLI).  
**Output:** Shared configuration instance consumed by helper functions.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Object: config
**Purpose:** Module-level `_Config` instance used to control traceback emission and exit-code style globally.  
**Input:** Attributes mutated by CLI option handlers or tests.  
**Output:** Read by functions such as `handle_cli_exception`, `get_system_exit_code`, and `print_exception_message`.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Class: CliSignalError
**Purpose:** Base exception for signal-triggered interruptions translated into Python errors.  
**Input:** Raised by signal handlers created via `_make_raise_handler`.  
**Output:** Provides a common ancestor for signal-specific exceptions so callers can catch them collectively.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Class: SigIntInterrupt
**Purpose:** Indicates the process received `SIGINT` (Ctrl+C).  
**Input:** Raised when the installed signal handler observes `SIGINT`.  
**Output:** Caught by `handle_cli_exception`, which maps it to exit code `130`.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Class: SigTermInterrupt
**Purpose:** Indicates the process received `SIGTERM`.  
**Input:** Raised by signal handlers for termination signals.  
**Output:** Leads to exit code `143` (or platform equivalent) via `handle_cli_exception`.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Class: SigBreakInterrupt
**Purpose:** Windows-specific exception for `SIGBREAK` (Ctrl+Break).  
**Input:** Triggered when the optional `SIGBREAK` handler fires.  
**Output:** Handled like `SIGTERM`, returning exit code `149`.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Dataclass: SignalSpec
**Purpose:** Describes how to translate an OS signal into an exception, user-facing message, and exit code.  
**Input:** Constructed with `signum`, `exception`, `message`, `exit_code`.  
**Output:** Consumed by `install_signal_handlers` and `handle_cli_exception`.  
**Implementation notes:** Instances are immutable; `default_signal_specs()` returns a fresh list each call so consumers can mutate copies safely.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Protocol: _Echo
**Purpose:** Structural type for echo-like callables compatible with `click.echo`.  
**Input:** Call signature `(message: str, *, err: bool)`.  
**Output:** Allows dependency injection of custom echo functions for testing or adapters.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Function: _default_echo
**Purpose:** Bridge to `click.echo` respecting stderr routing.  
**Input:** `message: str`, `err: bool = True`.  
**Output:** Writes text to stdout/stderr via Click.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Function: default_signal_specs
**Purpose:** Produce platform-aware default `SignalSpec` instances.  
**Input:** None; inspects available `signal` attributes (`SIGINT`, `SIGTERM`, `SIGBREAK`).  
**Output:** `List[SignalSpec]` appropriate for the runtime platform.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Function: _make_raise_handler
**Purpose:** Wrap a `BaseException` subclass in a signal handler that raises it when invoked.  
**Input:** `exc_type: type[BaseException]`.  
**Output:** `_Handler` callable compatible with `signal.signal`.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Function: install_signal_handlers
**Purpose:** Register handlers for the provided signal specs and return a restoration callback.  
**Input:** `specs: Sequence[SignalSpec] | None`. Defaults to `default_signal_specs()`.  
**Output:** `Callable[[], None]` that restores prior handlers; skips unsupported signals gracefully.  
**Implementation notes:** Handlers are process-wide; callers must invoke the restore callback in a `finally` block to avoid leaking altered signal state.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Function: handle_cli_exception
**Purpose:** Convert exceptions thrown by Click commands into deterministic exit codes and user feedback.  
**Input:** `exc: BaseException`, optional `signal_specs`, optional `echo` callable.  
**Output:** Integer exit code; may emit messages or re-raise based on `config.traceback`.  
**Implementation notes:** Falls back to `print_exception_message()` and `get_system_exit_code()` when no special-case matches. When `config.traceback` is `True` the original exception propagates.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Function: run_cli
**Purpose:** Execute a Click `BaseCommand` with consistent error handling and signal wiring.  
**Input:** `cli`, optional `argv`, optional `prog_name`, optional `signal_specs`, `install_signals` flag.  
**Output:** Integer exit code (0 on success, otherwise derived via `handle_cli_exception`).  
**Implementation notes:** Installs signal handlers unless `install_signals=False`, ensures restoration in a `finally` block, and flushes streams before returning.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Function: get_system_exit_code
**Purpose:** Map arbitrary exceptions to platform-appropriate integer exit codes.  
**Input:** `exc: BaseException`.  
**Output:** Exit code using POSIX errno, Windows error codes, or sysexits mapping based on `config.exit_code_style`.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Function: _sysexits_mapping
**Purpose:** Provide BSD `sysexits`-style numeric codes when that mode is enabled.  
**Input:** `exc: BaseException`.  
**Output:** Integer exit code consistent with sysexits semantics.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Function: print_exception_message
**Purpose:** Display the current exception message (and optional rich-formatted traceback) with output truncation safeguards.  
**Input:** `trace_back`, `length_limit`, optional `stream`.  
**Output:** Writes formatted error details to the target stream using a `rich` console and flushes stdout/stderr.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Function: _print_output
**Purpose:** Helper that prints captured subprocess output (stdout/stderr) stored on exception objects.  
**Input:** `exc_info: Any`, `attr: str`, optional `stream`.  
**Output:** Writes decoded output with uppercase prefix (e.g., `STDOUT`).  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

#### Function: flush_streams
**Purpose:** Best-effort flush of `sys.stdout` and `sys.stderr` to avoid buffering artifacts.  
**Input:** None.  
**Output:** Flush side effects only; exceptions suppressed.  
**Location:** `lib_cli_exit_tools/lib_cli_exit_tools.py`

### Module: lib_cli_exit_tools/cli.py
**Purpose:** Define the public Click command group and integrate library-level helpers.  
**Input:** Command-line arguments routed through Click.  
**Output:** CLI commands (`lib_cli_exit_tools` console script) with shared options and metadata printing.  
**Location:** `src/lib_cli_exit_tools/cli.py`

#### Constant: CLICK_CONTEXT_SETTINGS
**Purpose:** Provide consistent `help_option_names` (`-h`, `--help`) for commands.  
**Input:** Used by Click decorators.  
**Output:** Dict passed to Click context settings.  
**Location:** `lib_cli_exit_tools/cli.py`

#### Function: _configure_rich_click_output
**Purpose:** Neutralise rich-click styling when stdout is a pipe or uses non-UTF encodings so help text stays ASCII-safe on Windows CI.  
**Input:** None; inspects the active stdout stream via `click.get_text_stream`.  
**Output:** Adjusts rich-click globals (forced terminal flag, colour system, panel boxes) to avoid emitting characters that legacy encodings cannot represent.  
**Location:** `lib_cli_exit_tools/cli.py`


#### Function: cli
**Purpose:** Root Click group that stores global options (currently `--traceback`) and updates library configuration.  
**Input:** Click `Context`, boolean `traceback` option.  
**Output:** Populates `ctx.obj` and mutates `lib_cli_exit_tools.config.traceback`.  
**Location:** `lib_cli_exit_tools/cli.py`

#### Function: cli_info
**Purpose:** `info` subcommand that prints distribution metadata.  
**Input:** None.  
**Output:** Calls `__init__conf__.print_info()`; emits text to stdout.  
**Location:** `lib_cli_exit_tools/cli.py`

#### Function: main
**Purpose:** CLI entry point returning an exit code by delegating to `lib_cli_exit_tools.run_cli`.  
**Input:** Optional `argv` sequence supplied by callers/tests.  
**Output:** Integer exit code.  
**Location:** `lib_cli_exit_tools/cli.py`

### Module: lib_cli_exit_tools/__init__conf__.py
**Purpose:** Resolve package metadata from the installed distribution, exposing safe defaults when metadata is unavailable.  
**Input:** Queries `importlib.metadata` for the `lib_cli_exit_tools` distribution.  
**Output:** Module-level constants (`name`, `title`, `version`, `homepage`, `author`, `author_email`, `shell_command`) and helper functions.  
**Location:** `src/lib_cli_exit_tools/__init__conf__.py`

#### Protocol: _MetaMapping
**Purpose:** Abstract interface bridging differences between `Message` and `PackageMetadata` mappings across Python versions.  
**Input:** Provides `.get` access to metadata keys.  
**Output:** Enables static type checking without version-specific conditionals.  
**Location:** `lib_cli_exit_tools/__init__conf__.py`

#### Function: _get_str
**Purpose:** Safely read metadata values as strings with a default fallback.  
**Input:** `_MetaMapping` implementation, metadata key, default string.  
**Output:** String value (default when missing or not a string).  
**Location:** `lib_cli_exit_tools/__init__conf__.py`

#### Function: _meta
**Purpose:** Retrieve metadata for the distribution using `importlib.metadata.metadata`.  
**Input:** None.  
**Output:** Metadata object or `None` when the package is not installed.  
**Location:** `lib_cli_exit_tools/__init__conf__.py`

#### Function: _version
**Purpose:** Determine the installed version of the distribution.  
**Input:** None.  
**Output:** Version string; defaults to `"0.0.0.dev0"` if unresolved.  
**Location:** `lib_cli_exit_tools/__init__conf__.py`

#### Function: _home_page
**Purpose:** Resolve the project homepage URL from metadata or fall back to GitHub.  
**Input:** Metadata object (or `None`).  
**Output:** URL string.  
**Location:** `lib_cli_exit_tools/__init__conf__.py`

#### Function: _author
**Purpose:** Extract author name and email from metadata.  
**Input:** Metadata object (or `None`).  
**Output:** Tuple `(author_name, author_email)` with defaults when missing.  
**Location:** `lib_cli_exit_tools/__init__conf__.py`

#### Function: _summary
**Purpose:** Build a human-friendly project summary string.  
**Input:** Metadata object (or `None`).  
**Output:** Summary text with fallback to a default description.  
**Location:** `lib_cli_exit_tools/__init__conf__.py`

#### Function: _shell_command
**Purpose:** Discover the console-script name mapped to `lib_cli_exit_tools.cli:main`.  
**Input:** None (inspects `importlib.metadata.entry_points`).  
**Output:** Console script name or falls back to the distribution name.  
**Location:** `lib_cli_exit_tools/__init__conf__.py`

#### Function: print_info
**Purpose:** Render resolved metadata as an aligned block for CLI output.  
**Input:** None.  
**Output:** Prints lines describing package metadata.  
**Location:** `lib_cli_exit_tools/__init__conf__.py`

#### Constants: name, title, version, homepage, author, author_email, shell_command
**Purpose:** Public metadata derived at import time for reuse across CLI and documentation.  
**Input:** Populated by helper functions above.  
**Output:** Strings available to consumers.  
**Location:** `lib_cli_exit_tools/__init__conf__.py`

### Module: lib_cli_exit_tools/__init__.py
**Purpose:** Define the public API surface by re-exporting selected helpers and classes.  
**Input:** Imports components from `lib_cli_exit_tools.py`.  
**Output:** Populates `__all__` and simplifies user imports (`from lib_cli_exit_tools import run_cli`).  
**Location:** `src/lib_cli_exit_tools/__init__.py`

### Module: lib_cli_exit_tools/__main__.py
**Purpose:** Support `python -m lib_cli_exit_tools` invocation.  
**Input:** Delegates to `cli.main()` when the module is executed as a script.  
**Output:** Raises `SystemExit` with the CLI exit code.  
**Location:** `src/lib_cli_exit_tools/__main__.py`

**Entry point wiring notes:**
- `pyproject.toml`’s `[project.scripts]` section wires the `lib_cli_exit_tools`, `cli-exit-tools`, and `lib-cli-exit-tools` commands to `lib_cli_exit_tools.cli:main`. Pip-generated console scripts simply import that module and invoke `main()`, so they share all behavior with the in-repo callable.
- `python -m lib_cli_exit_tools` resolves through `src/lib_cli_exit_tools/__main__.py`, which imports `cli.main` and raises `SystemExit(main())`, keeping the module execution path aligned with the console-script wrappers.

## Implementation Details
**Dependencies:**
- Runtime: `click`, standard library modules (`os`, `signal`, `subprocess`, `traceback`, `importlib.metadata`).
- Typing: `typing`, `dataclasses` for structured data.
- Optional platform-specific signals (`SIGBREAK`) handled defensively.

**Key Configuration:**
- `config.traceback`: Enables traceback printing when `True`.
- `config.exit_code_style`: Controls whether exit codes follow `errno` (default) or `sysexits` semantics.
  - `errno` (default): maps to POSIX/Windows signal-style codes. For example, `FileNotFoundError` becomes `2`, `PermissionError` → `13`, `BrokenPipeError` → `141`, and signals become `128 + signal_number` (so `SIGINT` → `130`, `SIGTERM` → `143`).
  - `sysexits`: uses the BSD `sysexits` specification (see `sysexits.h`). In this mode `FileNotFoundError` turns into `EX_NOINPUT (66)`, `PermissionError` → `EX_NOPERM (77)`, `ValueError`/`TypeError` → `EX_USAGE (64)`, etc., giving semantically grouped codes for scripting across BSD-like environments.
  Switch between them to align exit codes with the conventions your consumers expect.
- `config.broken_pipe_exit_code`: Overrides exit code when `BrokenPipeError` occurs (default `141`).

**Database Changes:**
None.

## Testing Approach
**How to test this feature:**
- Run `make test` to exercise pytest suites covering CLI behavior, exit code mapping, and metadata helpers.
- Manual spot checks: invoke `python -m lib_cli_exit_tools info`, simulate `SIGINT` by pressing `Ctrl+C`, and observe exit codes.
- Edge cases: simulate broken pipe scenarios (e.g., piping to `head -n0` on POSIX) to confirm exit code 141.

**Test data needed:**
- Environment with Click installed.
- Optionally mock `importlib.metadata` to simulate installed vs. missing package metadata during unit tests.

## Known Issues & Future Improvements
**Current limitations:**
- Windows-specific signals (`SIGBREAK`) are best-effort; more coverage on Windows CI would increase confidence.
- `_sysexits_mapping` covers common exceptions but could be extended for additional error types if needed.

**Edge cases to handle:**
- Long traceback output truncates at 500 characters; consider configurability if verbose debugging is required.
- `config` is module-level state; concurrent CLI invocations within the same interpreter share configuration.

**Planned improvements:**
- Document recommended patterns for integrating these utilities into third-party Click CLIs.
- Consider exporting higher-level helper(s) for configuring `config.exit_code_style` via CLI flags.

## Risks & Considerations
**Technical risks:**
- Misconfigured signal handlers can interfere with host applications if `install_signal_handlers` is used in embedded contexts; always call the restore callback.  
- Changing `config` globally may have unintended effects when multiple CLIs share the process.  
- Reliance on `importlib.metadata.entry_points` may incur performance costs in environments with many installed packages.

**User impact:**
- Stable exit codes benefit scripts and automation; altering defaults should follow semantic versioning guidelines.  
- Traceback suppression is the default—developers needing full tracebacks must opt in with `--traceback`.

## Documentation & Resources
**Related documentation:**
- `README.md` (project overview and installation).  
- Existing docstrings within modules (`lib_cli_exit_tools.py`, `__init__conf__.py`).  
- Tests (`tests/test_exit_tools.py`) as executable specifications for error handling.

**External references:**
- [Click Documentation](https://click.palletsprojects.com/) for command definitions.  
- [Python `signal` module documentation](https://docs.python.org/3/library/signal.html).  
- [BSD `sysexits` constants reference](https://man.freebsd.org/cgi/man.cgi?sysexits).

---
**Created:** 2025-09-17 by Codex Assistant  
**Last Updated:** 2025-09-17 by Codex Assistant  
**Review Date:** 2025-12-17
