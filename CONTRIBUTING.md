# Contributing Guide

Thanks for helping improve lib_cli_exit_tools! This guide keeps changes small, safe, and easy to review.

## 1) Workflow at a Glance


## 2) Branches & Commits

- Branch names: 
- Commits: imperative, concise. Examples:

## 3) Coding Standards (Python)

- Follow the existing style; no sweeping refactors in unrelated code.

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
- If packaging drifts, run: `python tools/bump_version.py --sync-packaging`.
- CI enforces consistency on tags via a `packaging-consistency` job.

## 5) Tests & Style

- Run all checks: `make test` (ruff + pyright + pytest with coverage)
- Keep diffs focused; no unrelated refactors.

## 6) Docs

Checklist:

- [ ] Tests updated and passing (`make test`).
- [ ] Docs updated
- [ ] No generated artifacts committed
- [ ] Version bump: update only `pyproject.toml` and `CHANGELOG.md` (do not edit `src/lib_cli_exit_tools/__init__conf__.py`; version is read from installed metadata). After bump, tag the commit `vX.Y.Z`.

## 8) Security & Configuration

- No secrets in code or logs. Keep dependencies minimal.

Happy hacking!
