# Contributing Guide

Thanks for helping improve lib_cli_exit_tools! This guide keeps changes small, safe, and easy to review.

## 1) Workflow at a Glance


## 2) Branches & Commits

- Branch names: 
- Commits: imperative, concise. Examples:

## 3) Coding Standards (Python)

- Follow the existing style; no sweeping refactors in unrelated code.

## 4) Build & Packaging

## 5) Tests & Style

- Run all checks: `make test` (ruff + pyright + pytest with coverage)
- Keep diffs focused; no unrelated refactors.

## 6) Docs

Checklist:

- [ ] Tests updated and passing (`make test`).
- [ ] Docs updated
- [ ] No generated artifacts committed
- [ ] Version bump (CHANGELOG.md, __init__conf__.py, pyproject.toml)

## 8) Security & Configuration

- No secrets in code or logs. Keep dependencies minimal.

Happy hacking!
