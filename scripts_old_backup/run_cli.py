from __future__ import annotations

import click


@click.command(help="Run lib_cli_exit_tools CLI (passes additional args)")
@click.argument("args", nargs=-1)
def main(args: tuple[str, ...]) -> None:
    __import__("lib_cli_exit_tools.__main__")
    from lib_cli_exit_tools.cli import main as cli_main

    code = cli_main(list(args) if args else ["--help"])  # returns int
    raise SystemExit(int(code))


if __name__ == "__main__":
    main()
