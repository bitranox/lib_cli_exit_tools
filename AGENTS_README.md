# AGENTS README — Using `lib_cli_exit_tools`

This guide targets coding agents (Codex, Claude-CLI, etc.) that need to consume the
`lib_cli_exit_tools` library while building or refactoring Python CLIs. It focuses
on runtime usage rather than project maintenance.

## 1. Install

```bash
pip install lib_cli_exit_tools
```

If you are operating inside a virtual environment, ensure the environment is
active before installing so the console scripts (`lib_cli_exit_tools`,
`cli-exit-tools`, `lib-cli-exit-tools`) land on PATH.

## 2. Minimal Usage

Wrap an existing Click command with the bundled orchestration so signals and
exit codes work consistently:

```python
from __future__ import annotations

import click
from lib_cli_exit_tools import run_cli


@click.command()
def hello() -> None:
    click.echo("Hello world")


if __name__ == "__main__":
    raise SystemExit(run_cli(hello))
```

`run_cli` intercepts `SIGINT`, `SIGTERM`/`SIGBREAK`, and standard exceptions,
translating them into predictable exit codes for shells and calling scripts.

## 3. Temporary Overrides with `cli_session`

Enable traceback output or other configuration for a single invocation:

```python
from collections.abc import Sequence
from lib_cli_exit_tools import cli_session


def run_command(argv: Sequence[str] | None = None, *, verbose: bool = False) -> int:
    overrides = {"traceback": verbose}
    with cli_session(overrides=overrides) as execute:
        return execute(hello, argv=argv)
```

Outside the `with` block, global configuration reverts to its previous state,
so you can safely toggle verbose diagnostics based on flags or environment.

## 4. Global Configuration Surface

The module-level `config` object exposes runtime switches. Mutate them once
at process startup if you need persistent behaviour changes:

```python
from lib_cli_exit_tools import config

config.traceback = True              # always render full tracebacks
config.exit_code_style = "sysexits"  # use BSD sysexits mapping
config.broken_pipe_exit_code = 0     # treat BrokenPipeError as success
```

For scoped overrides (tests, nested CLIs), prefer `config_overrides`:

```python
from lib_cli_exit_tools import config_overrides

with config_overrides(traceback=True, traceback_force_color=True):
    run_something()
# state restored automatically
```

## 5. Direct Exit-Code Translation

If you catch exceptions manually, reuse the resolver:

```python
from lib_cli_exit_tools import get_system_exit_code, print_exception_message

try:
    risky_operation()
except Exception as exc:
    print_exception_message()
    raise SystemExit(get_system_exit_code(exc))
```

## 6. Custom Signal Handling

You can supply your own `SignalSpec` list and installer when calling `run_cli`:

```python
import signal
from contextlib import ExitStack

from lib_cli_exit_tools import SignalSpec, default_signal_specs, run_cli

CUSTOM_SIG = getattr(signal, "SIGUSR1", None)


def custom_specs() -> list[SignalSpec]:
    specs = default_signal_specs()
    if CUSTOM_SIG is not None:
        specs.append(
            SignalSpec(
                signum=CUSTOM_SIG,
                exception=RuntimeError,
                message="USR1 received",
                exit_code=75,
            )
        )
    return specs


def install_specs(specs: list[SignalSpec] | None) -> callable[[], None]:
    stack = ExitStack()
    for spec in specs or []:
        def _handler(signum: int, frame: object | None, *, spec: SignalSpec = spec) -> None:
            raise spec.exception(spec.message)

        try:
            previous = signal.getsignal(spec.signum)
            signal.signal(spec.signum, _handler)
        except OSError:
            continue
        stack.callback(signal.signal, spec.signum, previous)
    return stack.close


exit_code = run_cli(
    hello,
    signal_specs=custom_specs(),
    signal_installer=install_specs,
)
```

The installer must return a zero-argument callable that restores prior handlers.
`run_cli` invokes it automatically during teardown.

## 7. Testing Your Integration

When you wire the library into your project, add behaviour tests that mirror the
bundled suite:

```bash
PYTHONPATH=src python -m pytest tests/test_my_cli.py
```

Focus on asserting exit codes and stderr text under failures or signals.

## 8. Troubleshooting

| Symptom | Fix |
| --- | --- |
| Tracebacks not showing despite `--traceback` | Ensure you call `cli_session` or set `config.traceback = True` before running the command. |
| SIGINT doesn’t produce exit code 130 | Verify the command is executed via `run_cli` and no other signal handlers override the one supplied by the library. |
| Windows CTRL+BREAK ignored | Include `SignalSpec` for `SIGBREAK` or rely on `default_signal_specs()` which already accounts for it when available. |
| “Unknown configuration fields” error | Check the keyword names passed into `config_overrides`; they must match the dataclass fields (`traceback`, `exit_code_style`, `broken_pipe_exit_code`, `traceback_force_color`). |

## 9. Need a Quick Reference?

- **run_cli**: Orchestrates Click commands with signal-aware exit handling.
- **cli_session**: Context manager wrapping `run_cli` that applies temporary config overrides and returns a callable bound to the standard exception handler.
- **config/reset_config**: Global defaults; call `reset_config()` in tests to avoid leakage.
- **get_system_exit_code**: Standalone mapping from `BaseException` to numeric exit codes.
- **SignalSpec + default_signal_specs**: Build or extend the signal handling roster for `run_cli`.

Use these primitives to retrofit deterministic exit behaviour into any Click-based CLI your agent constructs.
