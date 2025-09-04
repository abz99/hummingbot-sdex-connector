# Stellar Hummingbot Connector v3 - Development Makefile

.PHONY: help install install-dev install-security install-performance
.PHONY: format lint type-check test test-unit test-integration test-e2e test-security
.PHONY: coverage clean build docs pre-commit setup-dev
.PHONY: docker-build docker-run docker-test stellar-setup

# Default target
help: ## Show this help message
	@echo "Stellar Hummingbot Connector v3 Development Commands"
	@echo "=================================================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Installation targets
install: ## Install production dependencies
	pip install -e .

install-dev: ## Install development dependencies
	pip install -e ".[dev,test]"

install-security: ## Install security dependencies
	pip install -e ".[security]"

install-performance: ## Install performance dependencies  
	pip install -e ".[performance]"

install-all: ## Install all dependencies
	pip install -e ".[dev,test,security,performance]"

# Development setup
setup-dev: install-dev ## Setup complete development environment
	pre-commit install
	pre-commit install --hook-type commit-msg
	mkdir -p reports logs
	@echo "Development environment setup complete!"

# Code formatting and linting
format: ## Format code with black and isort
	black hummingbot tests
	isort hummingbot tests

lint: ## Run flake8 linting
	flake8 hummingbot tests

type-check: ## Run mypy type checking
	mypy hummingbot

check-all: format lint type-check ## Run all code quality checks

# Testing targets
test: ## Run all tests
	pytest

test-unit: ## Run unit tests only
	pytest -m "unit" --cov-report=term-missing

test-integration: ## Run integration tests only
	pytest -m "integration" --maxfail=1

test-e2e: ## Run end-to-end tests only
	pytest -m "e2e" --maxfail=1

test-security: ## Run security tests only
	pytest -m "security"

test-performance: ## Run performance tests only
	pytest -m "performance" --durations=0

test-stellar: ## Run Stellar network tests
	pytest -m "stellar"

test-parallel: ## Run tests in parallel
	pytest -n auto

test-watch: ## Run tests in watch mode
	pytest-watch -- --cov=hummingbot

# Coverage reporting
coverage: ## Generate coverage report
	pytest --cov=hummingbot --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/"

coverage-xml: ## Generate XML coverage report
	pytest --cov=hummingbot --cov-report=xml

# Security scanning
security-scan: ## Run security scans
	bandit -r hummingbot -f json -o reports/bandit-report.json
	safety check --json --output reports/safety-report.json || true

# Clean targets
clean: ## Clean build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf reports/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-logs: ## Clean log files
	rm -rf logs/*.log

# Build targets
build: clean ## Build package
	python -m build

build-wheel: clean ## Build wheel only
	python -m build --wheel

# Documentation
docs: ## Build documentation
	@echo "Building documentation..."
	# Add sphinx-build command when docs are setup

docs-serve: ## Serve documentation locally
	@echo "Serving documentation..."
	# Add sphinx-serve command when docs are setup

# Pre-commit hooks
pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

pre-commit-update: ## Update pre-commit hooks
	pre-commit autoupdate

# Docker targets
docker-build: ## Build Docker image
	docker build -t stellar-hummingbot-connector-v3:latest .

docker-run: ## Run Docker container
	docker run -it --rm stellar-hummingbot-connector-v3:latest

docker-test: ## Run tests in Docker
	docker run --rm stellar-hummingbot-connector-v3:latest pytest

# Stellar network setup
stellar-setup: ## Setup Stellar testnet accounts
	@echo "Setting up Stellar testnet accounts..."
	python scripts/setup_stellar_accounts.py

stellar-fund: ## Fund Stellar testnet accounts
	@echo "Funding Stellar testnet accounts..."
	python scripts/fund_accounts.py

# Performance profiling
profile: ## Profile application performance
	python -m cProfile -o reports/profile.stats scripts/performance_test.py
	@echo "Profile saved to reports/profile.stats"

profile-view: ## View performance profile
	python -c "import pstats; p = pstats.Stats('reports/profile.stats'); p.sort_stats('cumulative').print_stats(20)"

# Monitoring and observability
metrics-start: ## Start metrics collection
	@echo "Starting Prometheus metrics server..."
	python scripts/start_metrics.py

health-check: ## Run health checks
	python scripts/health_check.py

# Database and migrations (if needed)
db-init: ## Initialize database
	@echo "Initializing database..."
	# Add database initialization commands

db-migrate: ## Run database migrations
	@echo "Running database migrations..."
	# Add migration commands

# Environment management
env-create: ## Create virtual environment
	python3.11 -m venv .venv
	@echo "Virtual environment created. Activate with: source .venv/bin/activate"

env-requirements: ## Generate requirements.txt
	pip-compile pyproject.toml --output-file requirements.txt
	pip-compile pyproject.toml --extra dev --output-file requirements-dev.txt

# CI/CD helpers
ci-install: ## Install dependencies for CI
	pip install --upgrade pip setuptools wheel
	pip install -e ".[dev,test,security]"

ci-test: ## Run tests for CI
	pytest --cov=hummingbot --cov-report=xml --junitxml=reports/junit.xml

ci-lint: ## Run linting for CI
	flake8 hummingbot tests --format=junit-xml --output-file=reports/flake8.xml

# Release management
version: ## Show current version
	@python -c "from hummingbot.connector.exchange.stellar._version import __version__; print(__version__)"

release-patch: ## Create patch release
	@echo "Creating patch release..."
	# Add release automation

release-minor: ## Create minor release
	@echo "Creating minor release..."
	# Add release automation

release-major: ## Create major release
	@echo "Creating major release..."
	# Add release automation

# Utilities
todo: ## Show TODO comments in code
	@echo "TODO items found:"
	@grep -r "TODO\|FIXME\|XXX" hummingbot/ --exclude-dir=__pycache__ || echo "No TODO items found"

lines: ## Count lines of code
	@find hummingbot -name "*.py" | xargs wc -l | tail -1

deps-outdated: ## Check for outdated dependencies
	pip list --outdated

deps-update: ## Update dependencies
	pip-compile --upgrade pyproject.toml
	pip-compile --upgrade pyproject.toml --extra dev --output-file requirements-dev.txt