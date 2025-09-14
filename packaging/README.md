# Packaging Skeletons

This directory contains starter files for common package managers. They are intentionally minimal and contain placeholders you must fill (version/sha256, maintainers).

## Conda (packaging/conda/recipe)

- `meta.yaml` uses GitHub release tarballs. Update `version` and `sha256` for each release.
- Build locally (example):
  ```bash
  conda build packaging/conda/recipe
  ```
- Consider submitting to conda-forge via a feedstock.

## Homebrew (packaging/brew/Formula)

- `lib-cli-exit-tools.rb` is a template. Fill `sha256` for the source tarball and the vendored `click` resource.
- Build locally:
  ```bash
  make build       # attempts Homebrew build; auto-installs if missing
  lib_cli_exit_tools --version
  ```
  Additional helpers:
  ```bash
  make brew-uninstall
  make brew-audit    # will fail until sha256 placeholders are filled
  ```

## Nix (packaging/nix)

- `flake.nix` builds from the working tree for local development.
- For reproducible releases, swap `src = ./.;` for a `fetchFromGitHub` stanza with `rev` and `sha256`.
- Example:
  ```bash
  make build       # attempts Nix build; auto-installs if missing
  make nix-run
  ```
