# Contributing Guide

Thanks for helping improve lib_cli_exit! This guide keeps changes small, safe, and easy to review.

## 1) Workflow at a Glance


## 2) Branches & Commits

- Branch names: 
- Commits: imperative, concise. Examples:

## 3) Coding Standards (Python)

- Follow the existing style; no sweeping refactors in unrelated code.

## 4) Build & Packaging

## 5) Tests & Style

- Run all tests: `make test`
- Coverage

## 6) Docs

Checklist:

- [ ] Tests updated and passing (`make test`).
- [ ] Docs updated
- [ ] No generated artifacts committed
- [ ] Version bump

## 8) Troubleshooting & Debug Logs

r Console: Tools → Developer Tools → Error Console.
- Toggle verbose logs at runtime:
  - Enable: `messenger.storage.local.set({ debug: true })`
  - Disable: `messenger.storage.local.set({ debug: false })`

## 9) Security & Configuration

- Keep `browser_specific_settings.gecko.id` stable to preserve the update channel.
- No secrets in code or logs. Keep dependencies minimal.

Happy hacking!
