# Development of the template itself (generated projects get template/Makefile.jinja).
SHELL := /usr/bin/env bash -o pipefail
.DEFAULT_GOAL := help

# Python code of this repository (template/ and examples/ are checked in generated projects).
CODE := tests

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: install
install: ## Create .venv with the dev dependencies
	uv sync

.PHONY: pre-commit-install
pre-commit-install: ## Install git pre-commit hooks
	uv run pre-commit install

.PHONY: format
format: ## Apply safe ruff fixes and format the code
	uv run ruff check --fix-only $(CODE)
	uv run ruff format $(CODE)

.PHONY: lint
lint: ## uv lock --check, ruff format --check, ruff check, mypy
	uv lock --check
	uv run ruff format --check $(CODE)
	uv run ruff check --no-fix $(CODE)
	uv run mypy $(CODE)

.PHONY: test
test: ## Template tests without Docker (render matrix, update, generated projects)
	uv run pytest -m "not e2e"

.PHONY: test-e2e
test-e2e: ## End-to-end tests (Docker; act and gitlab-ci-local when installed)
	uv run pytest -m e2e

.PHONY: examples
examples: ## Re-render examples/ after changing template/ (checked by tests/test_examples.py)
	uv run python -m tests.examples

.PHONY: update
update: ## Upgrade the dev dependencies in uv.lock
	uv lock --upgrade

.PHONY: clean
clean: ## Remove caches and reports
	rm -rf reports .mypy_cache .pytest_cache .ruff_cache
	find . -path ./.venv -prune -o -name __pycache__ -type d -exec rm -rf {} +
