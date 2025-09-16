from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from types import ModuleType

import click

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts._utils import (  # noqa: E402
    RunResult,
    bootstrap_dev,
    cmd_exists,
    get_project_metadata,
    run,
    sync_packaging,
)

PROJECT = get_project_metadata()
COVERAGE_TARGET = PROJECT.coverage_source
_TOML_MODULE: ModuleType | None = None


@click.command(help="Run lints, type-check, tests with coverage, and Codecov upload if configured")
@click.option("--coverage", type=click.Choice(["on", "auto", "off"]), default="on")
@click.option("--verbose", "-v", is_flag=True, help="Print executed commands before running them")
def main(coverage: str, verbose: bool) -> None:
    env_verbose = os.getenv("TEST_VERBOSE", "").lower()
    if not verbose and env_verbose in {"1", "true", "yes", "on"}:
        verbose = True

    def _run(
        cmd: list[str] | str,
        *,
        env: dict[str, str] | None = None,
        check: bool = True,
        capture: bool = True,
    ) -> RunResult:
        display = cmd if isinstance(cmd, str) else " ".join(cmd)
        if verbose:
            click.echo(f"  $ {display}")
            if env:
                overrides = {k: v for k, v in env.items() if os.environ.get(k) != v}
                if overrides:
                    env_view = " ".join(f"{k}={v}" for k, v in overrides.items())
                    click.echo(f"    env {env_view}")
        return run(cmd, env=env, check=check, capture=capture)  # type: ignore[arg-type]

    bootstrap_dev()

    click.echo("[0/4] Sync packaging (conda/brew/nix) with pyproject")
    sync_packaging()

    click.echo("[1/4] Ruff lint")
    _run(["ruff", "check", "."], check=False)  # type: ignore[list-item]

    click.echo("[2/4] Ruff format (apply)")
    _run(["ruff", "format", "."], check=False)  # type: ignore[list-item]

    click.echo("[3/4] Pyright type-check")
    _run(["pyright"], check=False)  # type: ignore[list-item]

    click.echo("[4/4] Pytest with coverage")
    for f in (".coverage", "coverage.xml"):
        try:
            Path(f).unlink()
        except FileNotFoundError:
            pass

    if coverage == "on" or (coverage == "auto" and (os.getenv("CI") or os.getenv("CODECOV_TOKEN"))):
        click.echo("[coverage] enabled")
        fail_under = _read_fail_under(Path("pyproject.toml"))
        with tempfile.TemporaryDirectory() as tmp:
            cov_file = Path(tmp) / ".coverage"
            click.echo(f"[coverage] file={cov_file}")
            env = os.environ | {"COVERAGE_FILE": str(cov_file)}
            _run(
                [
                    "python",
                    "-m",
                    "pytest",
                    f"--cov={COVERAGE_TARGET}",
                    "--cov-report=xml:coverage.xml",
                    "--cov-report=term-missing",
                    f"--cov-fail-under={fail_under}",
                    "-vv",
                ],
                env=env,
                capture=False,
            )
    else:
        click.echo("[coverage] disabled (set --coverage=on to force)")
        _run(["python", "-m", "pytest", "-vv"], capture=False)  # type: ignore[list-item]

    if Path("coverage.xml").exists():
        click.echo("Uploading coverage to Codecov")
        upload_result: RunResult | None = None
        if cmd_exists("codecov"):
            version = run(["python", "-c", "import platform; print(platform.python_version())"]).out.strip()
            upload_result = _run(
                [
                    "codecov",
                    "-f",
                    "coverage.xml",
                    "-F",
                    "local",
                    "-n",
                    f"local-$(uname)-{version}",
                ],
                check=False,
            )
        else:
            upload_result = _run(
                [
                    "bash",
                    "-lc",
                    "curl -s https://codecov.io/bash -o codecov.sh && bash codecov.sh -f coverage.xml -F local -n local-$(uname)-$(python -c 'import platform; print(platform.python_version())') ${CODECOV_TOKEN:+-t $CODECOV_TOKEN} || true && rm -f codecov.sh",
                ],
                check=False,
            )

        if upload_result is not None and not os.getenv("CI"):
            if upload_result.code == 0:
                click.echo("[codecov] upload succeeded")
            else:
                click.echo(f"[codecov] upload failed (exit {upload_result.code})")
                if upload_result.err:
                    click.echo(upload_result.err, err=True)
                elif upload_result.out:
                    click.echo(upload_result.out)
    else:
        click.echo("Skipping Codecov upload: coverage.xml not found")

    click.echo("All checks passed (coverage uploaded if configured).")


def _get_toml_module() -> ModuleType:
    global _TOML_MODULE
    if _TOML_MODULE is not None:
        return _TOML_MODULE

    try:
        import tomllib as module  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        try:
            import tomli as module  # type: ignore[import-not-found, assignment]
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError("tomllib/tomli modules are unavailable. Install the 'tomli' package for Python < 3.11.") from exc

    _TOML_MODULE = module
    return module


def _read_fail_under(pyproject: Path) -> int:
    try:
        toml_module = _get_toml_module()
        data = toml_module.loads(pyproject.read_text())
        return int(data["tool"]["coverage"]["report"]["fail_under"])
    except Exception:
        return 80


if __name__ == "__main__":
    main()
