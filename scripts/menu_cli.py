from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import click


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


def main() -> None:
    targets = _targets()
    click.echo("Select a target:\n")
    for i, t in enumerate(targets, start=1):
        click.echo(f"[{i}] {t.name:<16} — {t.desc}")
    click.echo("")
    sel: int = click.prompt("Enter number", type=click.IntRange(1, len(targets)))
    target: Target = targets[sel - 1]

    env_updates: Dict[str, str] = {}
    if target.params:
        click.echo("\nParameters (press Enter to keep defaults):")
        for p in target.params:
            default: str = p.default or ""
            suffix = f" [{'/'.join(p.choices)}]" if p.choices else ""
            while True:
                ans: str = click.prompt(
                    f"{p.name}{suffix}",
                    default=default,
                    show_default=True,
                )
                if p.choices and ans not in p.choices:
                    click.echo(f"Invalid value. Choose one of: {', '.join(p.choices)}")
                    continue
                if p.validate and not p.validate(ans):
                    click.echo("Invalid value.")
                    continue
                env_updates[p.name] = ans
                break
        if target.name == "bump":
            ver = (env_updates.get("VERSION") or "").strip()
            if ver and not Semver.match(ver):
                raise SystemExit("VERSION must be X.Y.Z")
            if not ver and not env_updates.get("PART"):
                env_updates["PART"] = "patch"

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


if __name__ == "__main__":
    main()
