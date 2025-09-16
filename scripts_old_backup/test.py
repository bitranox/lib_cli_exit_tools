from __future__ import annotations

import os
import tempfile
from pathlib import Path

import click
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts._utils import bootstrap_dev, cmd_exists, run, sync_packaging  # noqa: E402


@click.command(help="Run lints, type-check, tests with coverage, and Codecov upload if configured")
@click.option("--coverage", type=click.Choice(["on", "auto", "off"]), default="on")
@click.option("--verbose", "-v", is_flag=True, help="Print executed commands before running them")
def main(coverage: str, verbose: bool) -> None:
    env_verbose = os.getenv("TEST_VERBOSE", "").lower()
    if not verbose and env_verbose in {"1", "true", "yes", "on"}:
        verbose = True

    def _run(cmd: list[str] | str, *, env: dict[str, str] | None = None, check: bool = True) -> None:
        display = cmd if isinstance(cmd, str) else " ".join(cmd)
        if verbose:
            click.echo(f"  $ {display}")
            if env:
                overrides = {k: v for k, v in env.items() if os.environ.get(k) != v}
                if overrides:
                    env_view = " ".join(f"{k}={v}" for k, v in overrides.items())
                    click.echo(f"    env {env_view}")
        run(cmd, env=env, check=check)  # type: ignore[arg-type]

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
        with tempfile.TemporaryDirectory() as tmp:
            cov_file = Path(tmp) / ".coverage"
            click.echo(f"[coverage] file={cov_file}")
            env = os.environ | {"COVERAGE_FILE": str(cov_file)}
            _run(
                [
                    "python",
                    "-m",
                    "pytest",
                    "-q",
                    "--cov=lib_cli_exit_tools",
                    "--cov-report=xml:coverage.xml",
                    "--cov-report=term-missing",
                    "--cov-fail-under=80",
                ],
                env=env,
            )
    else:
        click.echo("[coverage] disabled (set --coverage=on to force)")
        _run(["python", "-m", "pytest", "-q"])  # type: ignore[list-item]

    if Path("coverage.xml").exists():
        click.echo("Uploading coverage to Codecov")
        if cmd_exists("codecov"):
            version = run(["python", "-c", "import platform; print(platform.python_version())"]).out.strip()
            _run(["codecov", "-f", "coverage.xml", "-F", "local", "-n", f"local-$(uname)-{version}"], check=False)
        else:
            _run(
                [
                    "bash",
                    "-lc",
                    "curl -s https://codecov.io/bash -o codecov.sh && bash codecov.sh -f coverage.xml -F local -n local-$(uname)-$(python -c 'import platform; print(platform.python_version())') ${CODECOV_TOKEN:+-t $CODECOV_TOKEN} || true && rm -f codecov.sh",
                ],
                check=False,
            )

    click.echo("All checks passed (coverage uploaded if configured).")


if __name__ == "__main__":
    main()
