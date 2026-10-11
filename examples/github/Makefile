SHELL := /usr/bin/env bash -o pipefail
.DEFAULT_GOAL := help

PACKAGE := example_app
IMAGE ?= example-app
# The template enforces its own minimum Copier version (`_min_copier_version`).
COPIER ?= uvx --from 'copier>=9.15.0' copier
COPIER_ARGS ?=

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*## "} /^##@/ {printf "\n%s\n", substr($$0, 5)} \
		/^[a-zA-Z0-9_-]+:.*## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

##@ Development

.PHONY: install
install: ## Create .venv and install the project with all dependency groups
	uv sync

.PHONY: pre-commit-install
pre-commit-install: ## Install git pre-commit hooks
	uv run pre-commit install

.PHONY: format
format: ## Apply safe lint fixes and format the code
	uv run ruff check --fix-only
	uv run ruff format

.PHONY: lint
lint: ## Run all checks: uv.lock, ruff, mypy, deptry
	uv lock --check
	uv run ruff format --check
	uv run ruff check
	uv run mypy
	uv run deptry .

.PHONY: test
test: ## Run tests with coverage (reports in ./reports)
	uv run pytest

# `uv audit` is a preview feature; the flag opts in and silences its warning.
.PHONY: audit
audit: ## Check locked runtime dependencies for known vulnerabilities
	uv audit --preview-features audit-command --locked --no-default-groups

.PHONY: run
run: ## Run the application
	uv run python -m $(PACKAGE)

.PHONY: update
update: ## Upgrade all dependencies in uv.lock
	uv lock --upgrade
	uv sync

.PHONY: clean
clean: ## Remove caches, reports and build artifacts
	rm -rf .mypy_cache .pytest_cache .ruff_cache reports build dist
	find . -path ./.venv -prune -o -name __pycache__ -type d -prune -exec rm -rf {} +

##@ Docker

.PHONY: docker-build
docker-build: ## Build the production image
	docker build --target production --tag $(IMAGE) .

.PHONY: up
up: ## Start the app with docker compose (development image)
	docker compose up --build

.PHONY: down
down: ## Stop docker compose services
	docker compose down

##@ Template

.PHONY: template-update
template-update: ## Update from the Copier template (pass e.g. COPIER_ARGS=--trust)
	$(COPIER) update --conflict inline --skip-answered $(COPIER_ARGS)
	@if git grep --untracked -lE '^(<<<<<<<|>>>>>>>)( |$$)' -- . ':!uv.lock'; then \
		echo "Resolve the conflicts in the files above, then run: uv lock && uv sync" >&2; \
		exit 1; \
	fi
	@if git grep --untracked -qE '^(<<<<<<<|>>>>>>>)( |$$)' -- uv.lock; then \
		git checkout HEAD -- uv.lock; \
	fi
	uv lock
	uv sync

.PHONY: template-check
template-check: ## Check whether a newer template version is available
	$(COPIER) check-update
