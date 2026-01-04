.PHONY: help install dev test test-cov lint format typecheck clean build docker docs

PYTHON := uv run python
PYTEST := uv run pytest
RUFF := uv run ruff

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync --all-extras --dev

dev: ## Start development server
	$(PYTHON) -m ghoststorm.cli run --dev

test: ## Run tests
	$(PYTEST) tests/ -v --tb=short

test-cov: ## Run tests with coverage
	$(PYTEST) tests/ --cov=ghoststorm --cov-report=html --cov-report=term-missing -v

test-unit: ## Run unit tests only
	$(PYTEST) tests/unit/ -v

test-integration: ## Run integration tests
	$(PYTEST) tests/integration/ -v

test-e2e: ## Run E2E tests (mock mode)
	$(PYTEST) tests/e2e/ -m "not real" -v

lint: ## Run linter
	$(RUFF) check src/ tests/

format: ## Format code
	$(RUFF) format src/ tests/
	$(RUFF) check --fix src/ tests/

typecheck: ## Run type checker
	uv run mypy src/ghoststorm --ignore-missing-imports

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov/ .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build: ## Build package
	uv build

docker: ## Build Docker image
	docker build -t ghoststorm:latest .

docker-run: ## Run Docker container
	docker compose up -d

docker-stop: ## Stop Docker container
	docker compose down

docs: ## Build documentation
	uv run mkdocs build

docs-serve: ## Serve documentation locally
	uv run mkdocs serve

pre-commit: ## Run pre-commit hooks
	uv run pre-commit run --all-files

pre-commit-install: ## Install pre-commit hooks
	uv run pre-commit install

check: lint typecheck test ## Run all checks
