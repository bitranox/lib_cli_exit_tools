from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Utilities are available for non-TUI flows; TUI uses asyncio subprocess directly


Semver = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


@dataclass
class Param:
    name: str
    desc: str
    default: Optional[str] = None
    choices: Optional[List[str]] = None
    validate: Optional[Callable[[str], bool]] = None


@dataclass
class Target:
    name: str
    desc: str
    params: List[Param]


def _env_default(name: str, fallback: Optional[str] = None) -> Optional[str]:
    val = os.environ.get(name)
    return val if val is not None else fallback


def _targets() -> List[Target]:
    return [
        Target("install", "Editable install", []),
        Target("dev", "Editable install with dev extras", []),
        Target(
            "test",
            "Lint, type-check, tests with coverage, Codecov upload",
            [
                Param("COVERAGE", "Coverage mode", default=_env_default("COVERAGE", "on"), choices=["on", "auto", "off"]),
                Param("SKIP_BOOTSTRAP", "Skip dev dependency bootstrap (1=yes, 0=no)", default=_env_default("SKIP_BOOTSTRAP", "0"), choices=["0", "1"]),
            ],
        ),
        Target("run", "Run CLI (shows --help)", []),
        Target("version-current", "Print version from pyproject.toml", []),
        Target(
            "bump",
            "Bump version (pyproject + CHANGELOG)",
            [
                Param(
                    "VERSION",
                    "Explicit version X.Y.Z (leave empty to use PART)",
                    default=_env_default("VERSION"),
                    validate=lambda s: bool(Semver.match(s)) if s else True,
                ),
                Param("PART", "Semver part to bump if VERSION empty", default=_env_default("PART", "patch"), choices=["major", "minor", "patch"]),
            ],
        ),
        Target("bump-patch", "Bump patch version", []),
        Target("bump-minor", "Bump minor version", []),
        Target("bump-major", "Bump major version", []),
        Target("clean", "Remove caches/build artifacts/coverage", []),
        Target(
            "push",
            "Run tests, sync packaging, commit, push",
            [
                Param("REMOTE", "Git remote", default=_env_default("REMOTE", "origin")),
            ],
        ),
        Target("build", "Build wheel/sdist; attempt conda/brew/nix if available", []),
        Target(
            "release",
            "Tag vX.Y.Z from pyproject; create GitHub release; sync packaging",
            [
                Param("REMOTE", "Git remote", default=_env_default("REMOTE", "origin")),
            ],
        ),
    ]


def _cli_menu() -> None:
    """Fallback simple CLI menu (no Textual)."""
    import click

    targets = _targets()
    click.echo("Select a target:\n")
    for i, t in enumerate(targets, start=1):
        click.echo(f"[{i}] {t.name:<16} — {t.desc}")
    click.echo("")
    sel = click.prompt("Enter number", type=click.IntRange(1, len(targets)))
    target = targets[sel - 1]
    env_updates: Dict[str, str] = {}
    if target.params:
        click.echo("\nParameters (press Enter to keep defaults):")
        for p in target.params:
            default = p.default or ""
            suffix = f" [{'/'.join(p.choices)}]" if p.choices else ""
            while True:
                ans = click.prompt(f"{p.name}{suffix}", default=default, show_default=True)
                if p.choices and ans not in p.choices:
                    click.echo(f"Invalid value. Choose one of: {', '.join(p.choices)}")
                    continue
                if p.validate and not p.validate(ans):
                    click.echo("Invalid value.")
                    continue
                env_updates[p.name] = ans
                break
        # Special rule for bump
        if target.name == "bump":
            ver = (env_updates.get("VERSION") or "").strip()
            if ver and not Semver.match(ver):
                raise SystemExit("VERSION must be X.Y.Z")
            if not ver and not env_updates.get("PART"):
                env_updates["PART"] = "patch"

    # Preview and run
    preview_env = " ".join(f"{k}={v}" for k, v in env_updates.items() if v)
    if preview_env:
        click.echo(f"\nAbout to run: {preview_env} make {target.name}")
    else:
        click.echo(f"\nAbout to run: make {target.name}")
    if not click.confirm("Proceed?", default=True):
        raise SystemExit(0)
    env = os.environ | env_updates
    from scripts._utils import run as _run

    res = _run(["make", target.name], env=env, check=False)
    raise SystemExit(res.code)


def _textual_menu() -> None:
    """Textual TUI menu with live logs. If textual is unavailable, fall back to CLI."""
    try:
        from textual.app import App  # type: ignore[reportMissingImports]
        from textual.widgets import Header, Footer, ListView, ListItem, Label, Input, Button, Static, Select, TextLog  # type: ignore[reportMissingImports]
        from textual.containers import Horizontal, Vertical, Container  # type: ignore[reportMissingImports]
        from textual.screen import Screen  # type: ignore[reportMissingImports]
        from textual.reactive import reactive  # type: ignore[reportMissingImports]
    except Exception:
        print("[menu] textual not available; falling back to simple menu. Install with: pip install -e .[dev]", file=sys.stderr)
        return _cli_menu()

    # Define TUI classes inside to avoid top-level import issues
    class ParamEditor(Vertical):  # type: ignore[name-defined]
        def __init__(self, target: Target) -> None:
            super().__init__()
            self.target = target
            self.inputs: Dict[str, Input | Select[str]] = {}

        def compose(self):  # type: ignore[override]
            yield Label(f"Parameters for: {self.target.name}")
            for p in self.target.params:
                yield Label(p.desc)
                if p.choices:
                    sel = Select(((c, c) for c in p.choices), value=p.default or (p.choices[0] if p.choices else ""))
                    self.inputs[p.name] = sel
                    yield sel
                else:
                    inp = Input(value=p.default or "", placeholder=p.desc)
                    self.inputs[p.name] = inp
                    yield inp
            yield Button("Run", id="run")

        def values(self) -> Dict[str, str]:
            vals: Dict[str, str] = {}
            for name, widget in self.inputs.items():
                if isinstance(widget, Input):
                    vals[name] = widget.value
                else:
                    vals[name] = widget.value or ""
            if self.target.name == "bump":
                ver = vals.get("VERSION", "").strip()
                if ver and not Semver.match(ver):
                    raise ValueError("VERSION must be X.Y.Z")
                if not ver:
                    vals["PART"] = vals.get("PART") or "patch"
            return vals

    class RunScreen(Screen[None]):  # type: ignore[name-defined]
        def __init__(self, target: Target, env: Dict[str, str]) -> None:
            super().__init__()
            self.target = target
            self.env = env
            self.log = TextLog(highlight=True)

        def compose(self):  # type: ignore[override]
            yield Header()
            yield self.log
            yield Footer()

        async def on_mount(self) -> None:  # type: ignore[override]
            import asyncio

            preview_env = " ".join(f"{k}={v}" for k, v in self.env.items() if v)
            cmd = ["make", self.target.name]
            cmd_txt = f"{preview_env} {' '.join(cmd)}" if preview_env else " ".join(cmd)
            self.log.write(f"[b bold green]Running:[/] {cmd_txt}\n")

            env = os.environ | self.env
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )
            except Exception as e:  # failed to spawn
                self.log.write(f"[red]Failed to start process:[/] {e}")
                return

            async def pump(stream, label: str, style: str) -> None:
                assert stream is not None
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    txt = line.decode("utf-8", "replace").rstrip("\n")
                    if txt:
                        self.log.write(f"[{style}]{label}[/] {txt}")

            await asyncio.gather(
                pump(proc.stdout, "stdout", "white"),
                pump(proc.stderr, "stderr", "bright_black"),
            )
            code = await proc.wait()
            self.log.write(f"\n[b]Exit code:[/] {code}")

    class MenuApp(App):  # type: ignore[name-defined]
        CSS = """
        Screen { layout: horizontal; }
        #left { width: 36%; border: solid green; }
        #right { width: 64%; border: solid blue; }
        ListView { height: 1fr; }
        TextLog { height: 1fr; }
        """

        selected = reactive(None)  # type: ignore[reportUnknownVariableType]

        def __init__(self) -> None:
            super().__init__()
            self.targets = _targets()
            self.param_editor: Optional[ParamEditor] = None

        def compose(self):  # type: ignore[override]
            yield Header(show_clock=True)
            with Horizontal():
                with Container(id="left"):
                    lv = ListView(id="targets")
                    for t in self.targets:
                        lv.append(ListItem(Label(f"{t.name} — {t.desc}")))
                    yield lv
                with Container(id="right"):
                    yield Static("Select a target on the left.")
            yield Footer()

        def on_list_view_selected(self, message) -> None:  # type: ignore[override]
            if message.list_view.id != "targets":
                return
            idx = message.index
            try:
                self.selected = self.targets[idx]
            except Exception:
                self.selected = None
            right = self.query_one("#right", Container)
            right.remove_children()
            if self.selected is None:
                right.mount(Static("Select a target on the left."))
                return
            self.param_editor = ParamEditor(self.selected)
            right.mount(self.param_editor)

        def on_button_pressed(self, event) -> None:  # type: ignore[override]
            if event.button.id == "run" and self.selected and self.param_editor:
                try:
                    env = self.param_editor.values()
                except Exception:
                    self.bell()
                    return
                self.push_screen(RunScreen(self.selected, env))

    MenuApp().run()


def main() -> None:  # pragma: no cover
    mode = os.environ.get("MENU_MODE", "").lower()
    # Respect explicit CLI mode or non-interactive terminals
    if mode == "cli" or not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("[menu] Non-interactive terminal or MENU_MODE=cli; using simple menu.")
        return _cli_menu()
    # TERM sanity check
    term = os.environ.get("TERM", "")
    if term in ("", "dumb") and mode != "tui":
        print("[menu] TERM is not a full terminal; using simple menu.")
        return _cli_menu()
    try:
        if mode == "tui":
            _textual_menu()
        else:
            _textual_menu()
    except SystemExit:
        raise
    except Exception:
        # In case of any runtime UI failure, fallback to simple menu
        _cli_menu()
