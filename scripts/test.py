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
def main(coverage: str) -> None:
    bootstrap_dev()

    click.echo("[0/4] Sync packaging (conda/brew/nix) with pyproject")
    sync_packaging()

    click.echo("[1/4] Ruff lint")
    run(["ruff", "check", "."])  # type: ignore[list-item]

    click.echo("[2/4] Ruff format (apply)")
    run(["ruff", "format", "."])  # type: ignore[list-item]

    click.echo("[3/4] Pyright type-check")
    run(["pyright"])  # type: ignore[list-item]

    click.echo("[4/4] Pytest with coverage")
    # remove old coverage
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
            run(
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
        run(["python", "-m", "pytest", "-q"])  # type: ignore[list-item]

    # Upload coverage to Codecov if present
    if Path("coverage.xml").exists():
        click.echo("Uploading coverage to Codecov")
        if cmd_exists("codecov"):
            version = run(["python", "-c", "import platform; print(platform.python_version())"]).out.strip()
            run(["codecov", "-f", "coverage.xml", "-F", "local", "-n", f"local-$(uname)-{version}"], check=False)
        else:
            # fallback bash uploader
            run(
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
