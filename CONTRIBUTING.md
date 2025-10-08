# Contributing Guide

Thanks for helping improve lib_cli_exit_tools! This guide keeps changes small, safe, and easy to review.

## 1) Workflow at a Glance

1. Fork and clone the repository; ensure you are on the latest `main` before starting work.
2. Create a feature branch (see naming rules below) and keep the scope of your change tight.
3. Implement the change, updating or adding tests and documentation alongside the code.
4. Run `make test` locally; this executes formatting, linting, typing, security scanners, and pytest with coverage.
5. Open a pull request that references any related issues and summarizes user-visible impact.

## 2) Branches & Commits

- Branch names: `feature/<short-description>`, `fix/<bug-id>`, or `chore/<task>` (lowercase, hyphen separated).
- Commits: imperative, concise, and self-contained (e.g., `Add traceback CLI regression test`). Avoid mixing unrelated changes.

## 3) Coding Standards (Python)

- Follow the clean architecture layering already in place (`core`, `application`, `adapters`, `cli`).
- Honour the documented system prompts: small functions, type hints throughout, and doctests that explain intent.
- No sweeping refactors in unrelated modules; keep pull requests reviewable.

## 4) Build & Packaging

### Packaging Sync (Conda/Brew/Nix)

- Sync is automatic on common workflows:
  - `make test` and `make push` run a sync step that aligns packaging files under `packaging/` with `pyproject.toml`.
  - `make bump` also updates packaging files when bumping the version.
- What gets synced from `pyproject.toml`:
  - Version and minimum Python (`requires-python`).
  - Runtime dependencies (from `[project].dependencies`).
    - Conda: rewrites `requirements: run` with `python >=X.Y` plus all deps (exact `==` pins kept; ranges copied as-is).
    - Homebrew: ensures a `resource "<dep>"` for each dep; if pinned, uses that version; otherwise pins to the latest PyPI release, updating `url` + `sha256`.
    - Nix: updates the package version, `pkgs.pythonXYZPackages`/`pkgs.pythonXYZ` to match the min Python, and `propagatedBuildInputs` to include all deps as `pypkgs.<name>`.
- Network note: Homebrew resource updates fetch PyPI metadata; if offline, those updates may be skipped.
- If packaging drifts, run: `python scripts/bump_version.py --sync-packaging`.
- CI enforces consistency on tags via a `packaging-consistency` job.

## 5) Tests & Style

- Always run `make test` before submitting. This covers Ruff (lint + format), import-linter, Pyright, Bandit, pip-audit, and pytest with coverage.
- Add or update tests whenever behaviour changes; prefer focused unit tests and regression coverage in `tests/`.
- Keep diffs focused; unrelated refactors should be a separate pull request.

## 6) Docs

Checklist:

- [ ] Tests updated and passing (`make test`).
- [ ] Docs updated (README, system design, and inline docstrings where applicable).
- [ ] No generated artifacts committed.
- [ ] Version bump: update only `pyproject.toml` and `CHANGELOG.md` (do not edit `src/lib_cli_exit_tools/__init__conf__.py`; version is read from installed metadata). After bump, tag the commit `vX.Y.Z`.

## 7) Security & Configuration

- No secrets in code or logs. Keep dependencies minimal.

Happy hacking!
