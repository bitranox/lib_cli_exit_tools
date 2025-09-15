from __future__ import annotations

import argparse
import datetime as _dt
import re
from pathlib import Path
from typing import Any, Dict, Tuple, Optional, cast
import json
import urllib.request
import hashlib

# Optional TOML parser for Python < 3.11 support during type checking
try:  # pragma: no cover - import resolution
    import tomllib as _tomllib  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - best-effort fallback
    try:
        import tomli as _tomllib  # type: ignore
    except Exception:  # noqa: PLC1901
        _tomllib = None  # type: ignore[assignment]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bump version in pyproject.toml and CHANGELOG.md")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--version", dest="version", help="Explicit new version X.Y.Z")
    g.add_argument("--part", choices=["major", "minor", "patch"], default="patch", help="Semver part to bump")
    p.add_argument(
        "--sync-packaging",
        action="store_true",
        help="Align conda/brew/nix files to current pyproject version and requires-python without changing pyproject or CHANGELOG",
    )
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


def _read_requires_python(pyproject: Path) -> str | None:
    try:
        text = pyproject.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    m = re.search(r"^requires-python\s*=\s*\"([^\"]+)\"", text, re.M)
    return m.group(1) if m else None


def _min_py_from_requires(spec: str) -> str | None:
    """Extract the minimum X.Y from a requires-python spec like ">=3.10"."""
    m = re.search(r">=\s*(3\.[0-9]+)", spec)
    return m.group(1) if m else None


_COMPARATORS: tuple[str, ...] = ("==", "===", ">=", "<=", "~=", ">", "<", "!=")


def _split_dep_spec(raw: str) -> tuple[str, str]:
    name, spec = raw, ""
    for cmp_ in _COMPARATORS:
        if cmp_ in raw:
            left, right = raw.split(cmp_, 1)
            name = left.strip()
            spec = cmp_ + right.strip()
            break
    return name.lower(), spec


def _deps_from_toml_text(text: str) -> Dict[str, str]:
    """Parse dependencies from TOML text using tomllib/tomli if available.

    Returns an empty dict if toml parsing is unavailable or fails.
    """
    if _tomllib is None:
        return {}
    try:
        data = cast(dict[str, Any], cast(Any, _tomllib).loads(text))
        raw_deps = cast(list[Any], data.get("project", {}).get("dependencies", []))
    except Exception:
        return {}

    out: Dict[str, str] = {}
    for d in raw_deps:
        if isinstance(d, str) and d:
            name, spec = _split_dep_spec(d)
            out[name] = spec
    return out


def _deps_from_regex_text(text: str) -> Dict[str, str]:
    """Best-effort dependency parse via regex.

    Looks for a top-level 'dependencies = ["..."]' array inside the [project] table.
    This is intentionally minimal and serves as a fallback when TOML parsing is
    not available.
    """
    out: Dict[str, str] = {}
    m = re.search(r"(?ms)^dependencies\s*=\s*\[(.*?)\]", text)
    if not m:
        return out
    body = m.group(1)
    for d in re.findall(r"\"([^\"]+)\"", body):
        if not d:
            continue
        name, spec = _split_dep_spec(d)
        out[name] = spec
    return out


def _read_pyproject_deps(pyproject: Path) -> Dict[str, str]:
    """Read [project].dependencies into a normalized mapping.

    Strategy: try TOML parsing first for correctness, otherwise fall back to a
    simple regex-based extraction. Output keys are normalized to lowercase and
    values are the raw version spec (possibly empty).
    """
    text = pyproject.read_text(encoding="utf-8")
    deps = _deps_from_toml_text(text)
    if deps:
        return deps
    return _deps_from_regex_text(text)


def _pinned_version(spec: str) -> str | None:
    """Return exact version string if spec pins the dependency (== or ===)."""
    m = re.match(r"===?\s*([0-9][^,; ]*)", spec)
    return m.group(1) if m else None


def _pypi_sdist_info(name: str, version: str) -> Tuple[str | None, str | None]:
    """Return (sdist_url, sha256) for a PyPI project version.

    Handles both the version-specific endpoint (preferred) and falls back to
    scanning the global releases map if necessary.
    """
    try:
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        with urllib.request.urlopen(url, timeout=10) as resp:  # nosec - metadata only
            data = json.loads(resp.read().decode("utf-8"))
        # Version-specific payload exposes artifacts under the top-level 'urls'
        for file in data.get("urls", []):
            if file.get("packagetype") == "sdist":
                return file.get("url"), file.get("digests", {}).get("sha256")
        # Some mirrors or legacy endpoints may include a 'releases' map
        for file in data.get("releases", {}).get(version, []):
            if file.get("packagetype") == "sdist":
                return file.get("url"), file.get("digests", {}).get("sha256")
    except Exception:
        return None, None
    return None, None


def _update_conda_recipe(version: str, path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return
    # Replace Jinja version pin: {% set version = "X.Y.Z" %}
    pattern = r"(\{\%\s*set\s+version\s*=\s*\")([^\"]+)(\"\s*\%\})"

    def repl(m: re.Match[str]) -> str:
        return f"{m.group(1)}{version}{m.group(3)}"

    text2 = re.sub(pattern, repl, text)
    changed = text2 != text
    text = text2
    # Sync Python constraint with pyproject requires-python (>=X.Y)
    req = _read_requires_python(Path("pyproject.toml"))
    min_py = _min_py_from_requires(req or "") if req else None
    if min_py:
        pat = r"(python\s*>=\s*)3\.[0-9]+"

        def _repl_py(m: re.Match[str]) -> str:
            return f"{m.group(1)}{min_py}"

        text3 = re.sub(pat, _repl_py, text)
        if text3 != text:
            text = text3
            changed = True
    # Rebuild the run: requirements list from pyproject deps
    deps = _read_pyproject_deps(Path("pyproject.toml"))
    lines = text.splitlines(True)
    # Find 'run:' line indent
    run_idx = next((i for i, ln in enumerate(lines) if re.match(r"^\s+run:\s*$", ln)), -1)
    if run_idx != -1:
        # Determine indentation for list items (two extra spaces under 'run:')
        m_indent = re.match(r"^(\s*)", lines[run_idx])
        indent = m_indent.group(1) if m_indent else "  "
        item_prefix = indent + "  - "
        # Remove existing run list lines following run_idx
        j = run_idx + 1
        while j < len(lines) and re.match(rf"^{re.escape(indent)}\s*-\s*", lines[j]):
            j += 1
        # Build new run list
        new_items: list[str] = []
        if min_py:
            new_items.append(f"{item_prefix}python >={min_py}\n")
        else:
            new_items.append(f"{item_prefix}python\n")
        for name, spec in sorted(deps.items()):
            if name.lower() == "python":
                continue
            entry = name
            if spec:
                entry += f" {spec}"
            new_items.append(f"{item_prefix}{entry}\n")
        lines[run_idx + 1 : j] = new_items[:]
        new_text = "".join(lines)
        if new_text != text:
            text = new_text
            changed = True
    # Attempt to set sha256 for remote source tarball (used when COND A_USE_LOCAL != 1)
    try:
        tar_url = f"https://github.com/bitranox/lib_cli_exit_tools/archive/refs/tags/v{version}.tar.gz"
        with urllib.request.urlopen(tar_url, timeout=10) as resp:
            data = resp.read()
        sha = hashlib.sha256(data).hexdigest()
        text_sha = re.sub(r'(sha256:\s*")([^"]*)(")', rf"\1{sha}\3", text)
        if text_sha != text:
            text = text_sha
            changed = True
            print(f"[bump] conda recipe: sha256 updated for v{version}")
    except Exception:
        # Network may be unavailable; leave sha256 as-is
        pass

    if changed:
        path.write_text(text, encoding="utf-8")
        print(f"[bump] conda recipe: version/python/deps synced ({version})")


def _brew_set_source_tag(text: str, version: str) -> tuple[str, bool]:
    """Set source URL tag and sha256 for the main formula tarball (not resources)."""
    changed = False
    new_text = re.sub(r"(refs/tags/)v[0-9]+\.[0-9]+\.[0-9]+(\.tar\.gz)", rf"\1v{version}\2", text)
    if new_text != text:
        changed = True
        text = new_text
    # Try to fetch tarball and compute sha256; replace first sha256 occurrence (main formula)
    try:
        tar_url = f"https://github.com/bitranox/lib_cli_exit_tools/archive/refs/tags/v{version}.tar.gz"
        with urllib.request.urlopen(tar_url, timeout=10) as resp:
            data = resp.read()
        sha = hashlib.sha256(data).hexdigest()
        pattern = r'(^\s*sha256\s+")([^"]+)(")'
        updated = re.sub(pattern, rf"\1{sha}\3", text, count=1, flags=re.M)
        if updated != text:
            text = updated
            changed = True
    except Exception:
        pass
    return text, changed


def _brew_set_python_dep(text: str, min_py: str | None) -> tuple[str, bool]:
    if not min_py:
        return text, False
    new_text = re.sub(r"depends_on\s+\"python(@[0-9]+\.[0-9]+)?\"", f'depends_on "python@{min_py}"', text)
    return new_text, new_text != text


def _brew_latest_version(name: str) -> str | None:
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json", timeout=10) as resp:
            info = json.loads(resp.read().decode("utf-8"))
        return cast(Optional[str], info.get("info", {}).get("version"))
    except Exception:
        return None


def _brew_update_or_insert_resource(text: str, name: str, sdist_url: str | None, sha256: str | None) -> str:
    res_block_re = re.compile(rf"(resource\s+\"{re.escape(name)}\"\s+do[\s\S]*?end)", re.S)
    mblk = res_block_re.search(text)
    if mblk:
        block = mblk.group(1)
        updated = block
        if sdist_url:
            updated = re.sub(r'(url\s+")([^"]+)(")', rf"\g<1>{sdist_url}\3", updated)
        if sha256:
            updated = re.sub(r'(sha256\s+")([^"]+)(")', rf"\g<1>{sha256}\3", updated)
        return text.replace(block, updated) if updated != block else text
    # insert before def install
    if sdist_url and sha256:
        insert_re = re.compile(r"^\s*def\s+install\b", re.M)
        m = insert_re.search(text)
        if m:
            block = f'\n  resource "{name}" do\n    url "{sdist_url}"\n    sha256 "{sha256}"\n  end\n'
            return text[: m.start()] + block + text[m.start() :]
    return text


def _update_brew_formula(version: str, path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return

    text, changed_tag = _brew_set_source_tag(text, version)
    # Sync python@X.Y from requires-python
    req = _read_requires_python(Path("pyproject.toml"))
    min_py = _min_py_from_requires(req or "") if req else None
    text, changed_py = _brew_set_python_dep(text, min_py)
    if changed_tag or changed_py:
        path.write_text(text, encoding="utf-8")
        print(f"[bump] brew formula: url/python -> v{version}{' / @' + (min_py or '') if min_py else ''}")

    # Sync resources for all runtime deps
    deps = _read_pyproject_deps(Path("pyproject.toml"))
    new_all = text
    for name, spec in deps.items():
        if name.lower() == "python":
            continue
        ver = _pinned_version(spec) or _brew_latest_version(name)
        if not ver:
            continue
        sdist_url, sha256 = _pypi_sdist_info(name, ver)
        new_all = _brew_update_or_insert_resource(new_all, name, sdist_url, sha256)
    if new_all != text:
        path.write_text(new_all, encoding="utf-8")
        print("[bump] brew formula: resources synced from pyproject dependencies")


def _update_nix_flake(version: str, path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return

    # Replace version = "X.Y.Z";
    # Update package block version only for pname = "lib_cli_exit_tools"
    def repl_pkg_block(m: re.Match[str]) -> str:
        return f"{m.group(1)}{version}{m.group(3)}"

    t1 = re.sub(
        r"(pname\s*=\s*\"lib_cli_exit_tools\";\s*[^}]*?\bversion\s*=\s*\")(\d+\.\d+\.\d+)(\";)",
        repl_pkg_block,
        text,
        flags=re.S,
    )
    # Replace example rev = "vX.Y.Z"
    t2 = re.sub(r"(rev\s*=\s*\")v[0-9]+\.[0-9]+\.[0-9]+(\")", rf"\1v{version}\2", t1)
    changed = t2 != text
    text = t2
    # Sync python package set (python312Packages -> python310Packages for >=3.10) and interpreter in devShell
    req = _read_requires_python(Path("pyproject.toml"))
    min_py = _min_py_from_requires(req or "") if req else None
    if min_py:
        digits = min_py.replace(".", "")  # e.g., 3.10 -> 310

        # pypkgs line
        def repl_pypkgs(m: re.Match[str]) -> str:
            return f"{m.group(1)}{digits}{m.group(3)}"

        text3 = re.sub(r"(pypkgs\s*=\s*pkgs\.python)([0-9]{3})(Packages)", repl_pypkgs, text)

        # devShell interpreter entries
        def repl_dev_python(m: re.Match[str]) -> str:
            return f"{m.group(1)}{digits}"

        text3b = re.sub(r"(pkgs\.python)([0-9]{3})\b", repl_dev_python, text3)
        if text3b != text:
            text = text3b
            changed = True
    if changed:
        # Also sync propagatedBuildInputs in the library package block (not the hatchling vendor)
        deps = _read_pyproject_deps(Path("pyproject.toml"))
        pkgs_list = " ".join(sorted({f"pypkgs.{k.replace('-', '_')}" for k in deps.keys() if k.lower() != "python"}))

        def _update_pkg_block(m: re.Match[str]) -> str:
            block = m.group(0)
            return re.sub(r"propagatedBuildInputs\s*=\s*\[[^\]]*\];", f"propagatedBuildInputs = [ {pkgs_list} ];", block, flags=re.S)

        text = re.sub(r"packages\.default\s*=\s*pypkgs\.buildPythonPackage\s*\{[\s\S]*?\}\s*;", _update_pkg_block, text)
        path.write_text(text, encoding="utf-8")
        print(f"[bump] nix flake: version/rev/python/deps -> {version}{' / ' + (min_py or '') if min_py else ''}")


def main() -> int:
    ns = parse_args()
    py = Path(ns.pyproject)

    # Sync-only mode: read current pyproject values and align packaging; no edits to pyproject/CHANGELOG
    if ns.sync_packaging:
        text = py.read_text(encoding="utf-8")
        m = re.search(r"^version\s*=\s*\"([^\"]+)\"", text, re.M)
        if not m:
            raise SystemExit("version not found in pyproject.toml")
        target = m.group(1)
        _update_conda_recipe(target, Path("packaging/conda/recipe/meta.yaml"))
        _update_brew_formula(target, Path("packaging/brew/Formula/lib-cli-exit-tools.rb"))
        _update_nix_flake(target, Path("packaging/nix/flake.nix"))
        return 0

    # Normal bump flow
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

    # Also bump packaging skeletons if present
    _update_conda_recipe(target, Path("packaging/conda/recipe/meta.yaml"))
    _update_brew_formula(target, Path("packaging/brew/Formula/lib-cli-exit-tools.rb"))
    _update_nix_flake(target, Path("packaging/nix/flake.nix"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
