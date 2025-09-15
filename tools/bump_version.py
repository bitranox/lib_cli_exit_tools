from __future__ import annotations

import argparse
import datetime as _dt
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bump version in pyproject.toml and CHANGELOG.md")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--version", dest="version", help="Explicit new version X.Y.Z")
    g.add_argument("--part", choices=["major", "minor", "patch"], default="patch", help="Semver part to bump")
    p.add_argument("--pyproject", default="pyproject.toml")
    p.add_argument("--changelog", default="CHANGELOG.md")
    return p.parse_args()


def bump_semver(old: str, part: str) -> str:
    a = old.split(".")
    while len(a) < 3:
        a.append("0")
    major, minor, patch = map(int, a[:3])
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    return f"{major}.{minor}.{patch}"


def main() -> int:
    ns = parse_args()
    py = Path(ns.pyproject)
    cl = Path(ns.changelog)
    text = py.read_text(encoding="utf-8")
    m = re.search(r"^version\s*=\s*\"([^\"]+)\"", text, re.M)
    if not m:
        raise SystemExit("version not found in pyproject.toml")
    old = m.group(1)
    target = ns.version or bump_semver(old, ns.part)
    text2 = re.sub(r"^version\s*=\s*\"[^\"]+\"", f'"version = "{target}"', text, count=1, flags=re.M)
    # Fix accidental leading quote in the replacement string above
    text2 = text2.replace('"version = ', "version = ", 1)
    py.write_text(text2, encoding="utf-8")
    print(f"[bump] pyproject.toml: {old} -> {target}")

    today = _dt.date.today().isoformat()
    entry = f"## [{target}] - {today}\n\n- _Describe changes here._\n\n"
    if cl.exists():
        lines = cl.read_text(encoding="utf-8").splitlines(True)
        idx = next((i for i, line in enumerate(lines) if line.startswith("## ")), len(lines))
        lines[idx:idx] = [entry]
        cl.write_text("".join(lines), encoding="utf-8")
    else:
        cl.write_text("# Changelog\n\n" + entry, encoding="utf-8")
    print(f"[bump] CHANGELOG.md: inserted section for {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
