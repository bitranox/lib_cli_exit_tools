from __future__ import annotations
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence
from subprocess import CompletedProcess


@dataclass(slots=True)
class RunResult:
    code: int
    out: str
    err: str


def run(
    cmd: Sequence[str] | str, *, check: bool = True, capture: bool = True, cwd: str | None = None, env: Mapping[str, str] | None = None, dry_run: bool = False
) -> RunResult:
    if isinstance(cmd, str):
        display = cmd
        shell = True
        args: Sequence[str] | str = cmd
    else:
        display = " ".join(shlex.quote(p) for p in cmd)
        shell = False
        args = list(cmd)
    if dry_run:
        print(f"[dry-run] {display}")
        return RunResult(0, "", "")
    proc: CompletedProcess[str] = subprocess.run(
        args,
        shell=shell,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=capture,
    )
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return RunResult(int(proc.returncode or 0), proc.stdout or "", proc.stderr or "")


def cmd_exists(name: str) -> bool:
    return subprocess.call(["bash", "-lc", f"command -v {shlex.quote(name)} >/dev/null 2>&1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0


def read_version_from_pyproject(pyproject: Path = Path("pyproject.toml")) -> str:
    try:
        import tomllib  # pyright: ignore[reportMissingImports]

        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        version = str(data.get("project", {}).get("version", ""))
        if version:
            return version
    except Exception:
        pass
    m = re.search(r'(?m)^version\s*=\s*"([0-9]+(?:\.[0-9]+){2})"', pyproject.read_text(encoding="utf-8"))
    return m.group(1) if m else ""


def ensure_clean_git_tree() -> None:
    # unstaged or staged changes?
    dirty = subprocess.call(["bash", "-lc", "! git diff --quiet || ! git diff --cached --quiet"], stdout=subprocess.DEVNULL)
    if dirty == 0:
        print("[release] Working tree not clean. Commit or stash changes first.", file=sys.stderr)
        raise SystemExit(1)


def git_branch() -> str:
    return run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture=True).out.strip()


def git_delete_tag(name: str, *, remote: str | None = None) -> None:
    run(["git", "tag", "-d", name], check=False, capture=True)
    if remote:
        run(["git", "push", remote, f":refs/tags/{name}"], check=False)


def git_tag_exists(name: str) -> bool:
    return subprocess.call(["bash", "-lc", f"git rev-parse -q --verify {shlex.quote('refs/tags/' + name)} >/dev/null"], stdout=subprocess.DEVNULL) == 0


def git_create_annotated_tag(name: str, message: str) -> None:
    run(["git", "tag", "-a", name, "-m", message])


def git_push(remote: str, ref: str) -> None:
    run(["git", "push", remote, ref])


def gh_available() -> bool:
    return cmd_exists("gh")


def gh_release_exists(tag: str) -> bool:
    return subprocess.call(["bash", "-lc", f"gh release view {shlex.quote(tag)} >/dev/null 2>&1"], stdout=subprocess.DEVNULL) == 0


def gh_release_create(tag: str, title: str, body: str) -> None:
    run(["gh", "release", "create", tag, "-t", title, "-n", body], check=False)


def gh_release_edit(tag: str, title: str, body: str) -> None:
    run(["gh", "release", "edit", tag, "-t", title, "-n", body], check=False)


def sync_packaging() -> None:
    run([sys.executable, "tools/bump_version.py", "--sync-packaging"], check=False)


def bootstrap_dev() -> None:
    # Install dev deps if ruff/pyright/pytest are missing
    if not (cmd_exists("ruff") and cmd_exists("pyright")):
        print("[bootstrap] Installing dev dependencies via 'pip install -e .[dev]'")
        run([sys.executable, "-m", "pip", "install", "-e", ".[dev]"])
    # sqlite fallback (rare)
    try:
        from importlib import import_module

        import_module("sqlite3")
    except Exception:
        run([sys.executable, "-m", "pip", "install", "pysqlite3-binary"], check=False)
