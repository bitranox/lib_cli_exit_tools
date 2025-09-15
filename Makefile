SHELL := /bin/bash

# Config
PY ?= python3
PIP ?= pip
PKG ?= lib_cli_exit_tools
GIT_REF ?= v0.1.0
REMOTE ?= origin
NIX_FLAKE ?= packaging/nix
HATCHLING_VERSION ?= 1.25.0
BREW_FORMULA ?= packaging/brew/Formula/lib-cli-exit-tools.rb
CONDA_RECIPE ?= packaging/conda/recipe
FAIL_UNDER ?= 80
# Coverage mode: on|auto|off (default: on locally)
# - on   : always run coverage
# - auto : enable on CI or when CODECOV_TOKEN is set
# - off  : never run coverage
COVERAGE ?= on

.PHONY: help install dev test run clean build push release _bootstrap-dev

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
	@echo "[0/4] Sync packaging (conda/brew/nix) with pyproject"
	$(PY) tools/bump_version.py --sync-packaging
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

version-current: ## Print current version from pyproject.toml
	@grep -E '^version\s*=\s*"' pyproject.toml | sed -E 's/.*"([^"]+)".*/\1/'

bump: ## Bump version: VERSION=X.Y.Z or PART=major|minor|patch (default: patch); updates pyproject.toml and CHANGELOG.md
	@set -e; \
	if [ -n "$(VERSION)" ]; then \
	  $(PY) tools/bump_version.py --version "$(VERSION)"; \
	else \
	  $(PY) tools/bump_version.py --part "$(PART)"; \
	fi

bump-patch: ## Bump patch version (X.Y.Z -> X.Y.(Z+1))
	@PART=patch $(MAKE) bump

bump-minor: ## Bump minor version (X.Y.Z -> X.(Y+1).0)
	@PART=minor $(MAKE) bump

bump-major: ## Bump major version ((X+1).0.0)
	@PART=major $(MAKE) bump

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

push: ## Commit all changes once and push to GitHub (no CI monitoring)
	@echo "[push] Running local checks (make test)"
	$(MAKE) test
	@echo "[push] Sync packaging (conda/brew/nix) with pyproject before commit"
	$(PY) tools/bump_version.py --sync-packaging
	@echo "[push] Committing and pushing (single attempt)"
	@set -e; \
	BRANCH=$$(git rev-parse --abbrev-ref HEAD); \
	git add -A; \
	if git diff --cached --quiet; then \
	  echo "[push] Nothing to commit; pushing branch $$BRANCH"; \
	else \
	  git commit -m "chore: update"; \
	fi; \
	git push -u $(REMOTE) $$BRANCH || { echo "[push] git push failed"; exit 1; }

build: ## Build wheel/sdist and attempt conda, brew, and nix builds (auto-installs tools if missing)
	@echo "[1/4] Building wheel/sdist via python -m build"
	$(PY) -m build
	@echo "[2/4] Attempting conda-build (auto-install Miniforge if needed)"
	@if command -v conda >/dev/null 2>&1; then \
	  CONDA_USE_LOCAL=1 conda build $(CONDA_RECIPE) || echo "conda-build failed (ok to skip)"; \
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
	    CONDA_USE_LOCAL=1 $$INST/bin/conda build $(CONDA_RECIPE) || true; \
	  fi; \
	fi
	@echo "[3/4] Attempting Homebrew build/install from local formula (auto-install if needed)"
	@OS=$$(uname -s | tr '[:upper:]' '[:lower:]'); \
	if [ "$$OS" != "darwin" ]; then \
	  echo "[brew] skipping: Homebrew formula build requires macOS and a tap. See packaging/brew/Formula/ and https://docs.brew.sh."; \
	else \
	  if command -v brew >/dev/null 2>&1; then \
	    brew install --build-from-source $(BREW_FORMULA) || echo "brew build failed (ok to skip; move formula into a tap to test)"; \
	  else \
	    echo "[bootstrap] brew not found; installing Homebrew..."; \
	    /bin/bash -c "$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || true; \

	    BREW=$$(command -v brew || true); \
	    if [ -z "$$BREW" ] && [ -x /opt/homebrew/bin/brew ]; then BREW=/opt/homebrew/bin/brew; fi; \
	    if [ -n "$$BREW" ]; then $$BREW install --build-from-source $(BREW_FORMULA) || true; fi; \
	  fi; \
	fi
	@echo "[4/4] Attempting Nix flake build (auto-install if needed)"
	@# Inline: update vendored hatchling SRI hash (if needed) before nix build
	@set -e; \
	HV=$${HATCHLING_VERSION:-1.25.0}; \
	TMP=$$(mktemp -d); \
	echo "[nix] Prefetching hatchling $$HV wheel"; \
	$(PIP) download "hatchling==$$HV" --only-binary=:all: --no-deps -d "$$TMP" >/dev/null 2>&1 || true; \
	WHEEL=$$(ls -1 "$$TMP"/hatchling-$$HV-*.whl 2>/dev/null | head -n1); \
		if [ -n "$$WHEEL" ]; then \
		  SRI=$$($(PY) -c "import base64,hashlib,sys,pathlib; p=sys.argv[1]; h=hashlib.sha256(pathlib.Path(p).read_bytes()).digest(); print('sha256-'+base64.b64encode(h).decode('ascii'))" "$$WHEEL"); \
	  sed -i.bak -E "s|hash = \"sha256-[A-Za-z0-9+/=]+\";|hash = \"$${SRI}\";|" packaging/nix/flake.nix; \
	  rm -f packaging/nix/flake.nix.bak; \
	  echo "[nix] Updated hatchling hash in packaging/nix/flake.nix"; \
	fi; \
	rm -rf "$$TMP";
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

release: ## Create and push tag vX.Y.Z from pyproject, then sync packaging and commit
	@set -euo pipefail; IFS=$$'\n\t'; \
	VERSION=$$(grep -E '^version\s*=\s*"' pyproject.toml | sed -E 's/.*"([^"]+)".*/\1/'); \
	echo "[release] Target version $$VERSION"; \
	# Ensure clean working tree
	if ! git diff --quiet || ! git diff --cached --quiet; then \
	  echo "[release] Working tree not clean. Commit or stash changes first."; exit 1; \
	fi; \
	# Run verification
	$(MAKE) test; \
	BRANCH=$$(git rev-parse --abbrev-ref HEAD); \
	echo "[release] Pushing branch $$BRANCH to $(REMOTE)"; \
	git push $(REMOTE) $$BRANCH; \
	# Create tag if missing
	if git rev-parse -q --verify "refs/tags/v$$VERSION" >/dev/null; then \
	  echo "[release] Tag v$$VERSION already exists locally"; \
	else \
	  git tag -a "v$$VERSION" -m "Release v$$VERSION"; \
	fi; \
	echo "[release] Pushing tag v$$VERSION"; \
	git push $(REMOTE) "v$$VERSION"; \
	# Try to sync packaging (tarball hashes) a few times to tolerate propagation delay
	for i in 1 2 3 4 5; do \
	  echo "[release] Sync packaging attempt $$i"; \
	  $(PY) tools/bump_version.py --sync-packaging || true; \
	  if ! grep -R "<fill-me>" -n packaging >/dev/null 2>&1; then \
	    break; \
	  fi; \
	  sleep 3; \
	done; \
	# Commit packaging changes, if any
	if ! git diff --quiet packaging; then \
	  git add packaging; \
	  git commit -m "chore(packaging): sync for v$$VERSION"; \
	  git push $(REMOTE) $$BRANCH; \
	else \
	  echo "[release] No packaging changes to commit"; \
	fi; \
	echo "[release] Done: v$$VERSION tagged and pushed."
