from __future__ import annotations

import click
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts._utils import git_branch, run, sync_packaging  # noqa: E402


@click.command(help="Run tests, sync packaging, commit changes if any, and push current branch")
@click.option("--remote", default="origin", show_default=True)
def main(remote: str) -> None:
    click.echo("[push] Running local checks (scripts/test.py)")
    run(["python", "scripts/test.py"])  # type: ignore[list-item]

    click.echo("[push] Sync packaging with pyproject before commit")
    sync_packaging()

    click.echo("[push] Committing and pushing (single attempt)")
    run(["git", "add", "-A"])  # stage all
    # Commit only if there are staged diffs
    staged = run(["bash", "-lc", "! git diff --cached --quiet"], check=False)
    if staged.code == 0:
        run(["git", "commit", "-m", "chore: update"])  # type: ignore[list-item]
    else:
        click.echo("[push] Nothing to commit; pushing branch")
    branch = git_branch()
    run(["git", "push", "-u", remote, branch])  # type: ignore[list-item]


if __name__ == "__main__":
    main()
