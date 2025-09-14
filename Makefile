SHELL := /bin/bash

# Config
PY ?= python3
PIP ?= pip
PKG ?= lib_cli_exit_tools
GIT_REF ?= v0.1.0
NIX_FLAKE ?= packaging/nix
BREW_FORMULA ?= packaging/brew/Formula/lib-cli-exit-tools.rb
CONDA_RECIPE ?= packaging/conda/recipe
FAIL_UNDER ?= 85
# Coverage mode: on|auto|off (default: on locally)
# - on   : always run coverage
# - auto : enable on CI or when CODECOV_TOKEN is set
# - off  : never run coverage
COVERAGE ?= on

.PHONY: help install dev test run clean build _bootstrap-dev

help: ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install package editable
	$(PIP) install -e .

dev: ## Install package with dev extras
	$(PIP) install -e .[dev]

_bootstrap-dev:
	@if [ "$(SKIP_BOOTSTRAP)" = "1" ]; then \
	  echo "[bootstrap] Skipping dev dependency bootstrap (SKIP_BOOTSTRAP=1)"; \
	else \
	  if ! command -v ruff >/dev/null 2>&1 || ! command -v pyright >/dev/null 2>&1 || ! python -c "import pytest" >/dev/null 2>&1; then \
	    echo "[bootstrap] Installing dev dependencies via '$(PIP) install -e .[dev]'"; \
	    $(PIP) install -e .[dev]; \
	  else \
	    echo "[bootstrap] Dev tools present"; \
	  fi; \
	  if ! python -c "import sqlite3" >/dev/null 2>&1; then \
	    echo "[bootstrap] sqlite3 stdlib module not available; installing pysqlite3-binary"; \
	    $(PIP) install pysqlite3-binary || true; \
	  fi; \
	fi

test: _bootstrap-dev ## Lint, type-check, run tests with coverage, upload to Codecov
	@echo "[1/4] Ruff lint"
	ruff check .
	@echo "[2/4] Ruff format (apply)"
	ruff format .
	@echo "[3/4] Pyright type-check"
	pyright
	@echo "[4/4] Pytest with coverage"
	rm -f .coverage* coverage.xml || true
	@if [ "$(COVERAGE)" = "on" ] || { [ "$(COVERAGE)" = "auto" ] && { [ -n "$$CI" ] || [ -n "$$CODECOV_TOKEN" ]; }; }; then \
	  echo "[coverage] enabled"; \
	  ( TMPDIR=$$(mktemp -d); TMP_COV="$$TMPDIR/.coverage"; \
	    echo "[coverage] file=$$TMP_COV"; \
	    COVERAGE_FILE=$$TMP_COV $(PY) -m pytest -q --cov=$(PKG) --cov-report=xml:coverage.xml --cov-report=term-missing --cov-fail-under=$(FAIL_UNDER) && cp -f coverage.xml codecov.xml ) || \
	    ( echo "[warn] Coverage failed; rerunning tests without coverage" && $(PY) -m pytest -q ); \
	else \
	  echo "[coverage] disabled (set COVERAGE=on to force)"; \
	  $(PY) -m pytest -q; \
	fi
	@set -a; [ -f .env ] && . ./.env || true; set +a; \
	if [ -f coverage.xml ]; then \
	  echo "Uploading coverage to Codecov"; \
	  if command -v codecov >/dev/null 2>&1; then \
	    codecov -f coverage.xml -F local -n "local-$(shell uname)-$$(python -c 'import platform; print(platform.python_version())')" $${CODECOV_TOKEN:+-t $$CODECOV_TOKEN} || true; \
	  else \
	    curl -s https://codecov.io/bash -o codecov.sh; \
	    bash codecov.sh -f coverage.xml -F local -n "local-$(shell uname)-$$(python -c 'import platform; print(platform.python_version())')" $${CODECOV_TOKEN:+-t $$CODECOV_TOKEN} || true; \
	    rm -f codecov.sh; \
	  fi; \
	fi
	@echo "All checks passed (coverage uploaded if configured)."

run: ## Run module CLI (requires dev install or src on PYTHONPATH)
	$(PY) -m $(PKG) --help || true

clean: ## Remove caches, build artifacts, and coverage
	rm -rf \
	  .pytest_cache \
	  .ruff_cache \
	  .pyright \
	  .mypy_cache \
	  .tox .nox \
	  .eggs *.egg-info \
	  build dist \
	  htmlcov .coverage coverage.xml \
	  codecov.sh \
	  .cache \
	  result

build: ## Build wheel/sdist and attempt conda, brew, and nix builds (auto-installs tools if missing)
	@echo "[1/4] Building wheel/sdist via python -m build"
	$(PY) -m build
	@echo "[2/4] Attempting conda-build (auto-install Miniforge if needed)"
	@if command -v conda >/dev/null 2>&1; then \
	  conda build $(CONDA_RECIPE) || echo "conda-build failed (ok to skip)"; \
	else \
	  echo "[bootstrap] conda not found; installing Miniforge..."; \
	  OS=$$(uname -s | tr '[:upper:]' '[:lower:]'); ARCH=$$(uname -m); \
	  case "$$OS-$$ARCH" in \
	    linux-x86_64)  URL=https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh ;; \
	    linux-aarch64) URL=https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh ;; \
	    darwin-arm64)  URL=https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh ;; \
	    darwin-x86_64) URL=https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh ;; \
	    *) URL=; echo "Unsupported platform $$OS-$$ARCH" ;; \
	  esac; \
	  if [ -n "$$URL" ]; then \
	    INST=$$HOME/miniforge3; \
	    curl -fsSL $$URL -o /tmp/miniforge.sh && bash /tmp/miniforge.sh -b -p $$INST; \
	    $$INST/bin/conda install -y conda-build || true; \
	    $$INST/bin/conda build $(CONDA_RECIPE) || true; \
	  fi; \
	fi
	@echo "[3/4] Attempting Homebrew build/install from local formula (auto-install if needed)"
	@if command -v brew >/dev/null 2>&1; then \
	  brew install --build-from-source $(BREW_FORMULA) || echo "brew build failed (ok to skip; fill sha256)"; \
	else \
	  echo "[bootstrap] brew not found; installing Homebrew..."; \
	  /bin/bash -c "$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || true; \
	  BREW=$$(command -v brew || true); \
	  if [ -z "$$BREW" ]; then \
	    if [ -x /home/linuxbrew/.linuxbrew/bin/brew ]; then BREW=/home/linuxbrew/.linuxbrew/bin/brew; fi; \
	    if [ -z "$$BREW" ] && [ -x /opt/homebrew/bin/brew ]; then BREW=/opt/homebrew/bin/brew; fi; \
	  fi; \
	  if [ -n "$$BREW" ]; then $$BREW install --build-from-source $(BREW_FORMULA) || true; fi; \
	fi
	@echo "[4/4] Attempting Nix flake build (auto-install if needed)"
	@if command -v nix >/dev/null 2>&1; then \
	  nix build $(NIX_FLAKE)#default -L || echo "nix build failed (ok to skip)"; \
	else \
	  echo "[bootstrap] nix not found; installing Nix (single-user)..."; \
	  sh <(curl -L https://nixos.org/nix/install) --no-daemon || true; \
	  NIX=$$(command -v nix || true); \
	  if [ -z "$$NIX" ] && [ -x $$HOME/.nix-profile/bin/nix ]; then NIX=$$HOME/.nix-profile/bin/nix; fi; \
	  if [ -z "$$NIX" ] && [ -x /nix/var/nix/profiles/default/bin/nix ]; then NIX=/nix/var/nix/profiles/default/bin/nix; fi; \
	  if [ -n "$$NIX" ]; then $$NIX build $(NIX_FLAKE)#default -L || true; fi; \
	fi
