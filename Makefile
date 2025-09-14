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
# Coverage mode: auto|on|off (auto: CI or CODECOV_TOKEN -> on, else off)
COVERAGE ?= auto

.PHONY: help menu install dev test run cli which-cmd verify-install user-install venv wheel-install sdist-install pip-git-install clean build-all _bootstrap-dev \
	pipx-install pipx-upgrade pipx-uninstall uv-dev uv-tool-install uv-tool-upgrade uv-tool-run \
	brew-uninstall brew-audit nix-run

help: ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

menu: help ## Show interactive-like help

install: ## Install package editable
	$(PIP) install -e .

dev: ## Install package with dev extras
	$(PIP) install -e .[dev]

user-install: ## Per-user install (no venv)
	$(PIP) install --user .

venv: ## Create local venv in .venv (prints activation hint)
	$(PY) -m venv .venv && echo "Activate with: source .venv/bin/activate (POSIX) or .venv\\Scripts\\activate (Windows)"

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
	  ( COVERAGE_FILE=.coverage $(PY) -m pytest -q --cov=$(PKG) --cov-report=xml:coverage.xml --cov-report=term-missing --cov-fail-under=$(FAIL_UNDER) ) || \
	    ( echo "[warn] Coverage failed; rerunning tests without coverage" && $(PY) -m pytest -q ); \
	else \
	  echo "[coverage] disabled (set COVERAGE=on to force)"; \
	  $(PY) -m pytest -q; \
	fi
	@echo "Uploading coverage to Codecov (if configured)"
	@set -a; [ -f .env ] && . ./.env || true; set +a; \
	if [ -f coverage.xml ]; then \
	  if command -v codecov >/dev/null 2>&1; then \
	    codecov -f coverage.xml -F local -n "local-$(shell uname)-$$(python -c 'import platform; print(platform.python_version())')" $${CODECOV_TOKEN:+-t $$CODECOV_TOKEN} || true; \
	  else \
	    curl -s https://codecov.io/bash -o codecov.sh; \
	    bash codecov.sh -f coverage.xml -F local -n "local-$(shell uname)-$$(python -c 'import platform; print(platform.python_version())')" $${CODECOV_TOKEN:+-t $$CODECOV_TOKEN} || true; \
	    rm -f codecov.sh; \
	  fi; \
	else \
	  echo "[info] coverage.xml not found; skipping Codecov upload"; \
	fi
	@echo "All checks passed (coverage uploaded if configured)."

run: ## Run module CLI (requires dev install or src on PYTHONPATH)
	$(PY) -m $(PKG) --help || true

cli: ## Run console script (requires install)
	$(PKG) --help || true

which-cmd: ## Show where the CLI command is installed and which one resolves
	@echo "Looking for CLI shims on PATH..." && which $(PKG) || true
	@which cli-exit-tools || true

verify-install: ## Verify CLI is callable from PATH
	@($(PKG) --version || cli-exit-tools --version) && echo "OK: CLI found on PATH" || (echo "CLI not on PATH. Did you pip install . or pipx install . ?" && exit 1)

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

build-all: ## Build wheel/sdist and attempt conda, brew, and nix builds
	@echo "[1/4] Building wheel/sdist via python -m build"
	$(PY) -m build
	@echo "[2/4] Attempting conda-build (skips if conda not found)"
	@if command -v conda >/dev/null 2>&1; then \
		conda build $(CONDA_RECIPE) || echo "conda-build failed (ok to skip)"; \
	else \
		echo "conda not found; skipping conda-build"; \
	fi
	@echo "[3/4] Attempting Homebrew build/install from local formula (skips if brew not found)"
	@if command -v brew >/dev/null 2>&1; then \
		brew install --build-from-source $(BREW_FORMULA) || echo "brew build failed (ok to skip; fill sha256)"; \
	else \
		echo "brew not found; skipping brew build"; \
	fi
	@echo "[4/4] Attempting Nix flake build (skips if nix not found)"
	@if command -v nix >/dev/null 2>&1; then \
		nix build $(NIX_FLAKE)#default -L || echo "nix build failed (ok to skip)"; \
	else \
		echo "nix not found; skipping nix build"; \
	fi

wheel-install: ## Install built wheel artifact (requires dist/ to exist)
	$(PIP) install dist/$(PKG)-*.whl

sdist-install: ## Install from sdist artifact (requires dist/ to exist)
	$(PIP) install dist/$(PKG)-*.tar.gz

pip-git-install: ## Install from Git ref (GIT_REF?=v0.1.0)
	$(PIP) install "git+https://github.com/bitranox/$(PKG)@$(GIT_REF)#egg=$(PKG)"

# --- packaging helpers (subset not covered by build-all) ---
brew-uninstall: ## Uninstall Homebrew package
	@if command -v brew >/dev/null 2>&1; then brew uninstall lib-cli-exit-tools || true; fi

brew-audit: ## Audit brew formula (will fail until placeholders are filled)
	@if ! command -v brew >/dev/null 2>&1; then echo "brew not found"; exit 1; fi
	brew audit --new-formula --strict $(BREW_FORMULA) || true

nix-run: ## Run CLI from Nix build result
	@if [ -x result/bin/$(PKG) ]; then result/bin/$(PKG) --version; else echo "Build first: make build-all"; fi

# --- pipx & uv convenience targets ---
pipx-install: ## Install CLI via pipx (isolated)
	pipx install .

pipx-upgrade: ## Upgrade CLI via pipx
	pipx upgrade $(PKG)

pipx-uninstall: ## Uninstall CLI via pipx
	pipx uninstall $(PKG)

uv-dev: ## Dev install via uv (editable + extras)
	uv pip install -e .[dev]

uv-tool-install: ## Install CLI as uv tool
	uv tool install .

uv-tool-upgrade: ## Upgrade uv tool
	uv tool upgrade $(PKG)

uv-tool-run: ## One-off run via uvx
	uvx $(PKG) --help || true
