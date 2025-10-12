"""Let ``python -m lib_cli_exit_tools`` behave like the console script."""

from . import cli


def main() -> int:
    """Forward module execution to the Click entry point."""

    return cli.main()


if __name__ == "__main__":
    raise SystemExit(main())
