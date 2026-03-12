# Makefile for Backlog API MCP Server
# Provides convenient commands for development and linting

.PHONY: help install install-dev lint lint-fix format type-check security test clean docker-lint

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  lint         - Run all linting checks (ruff + mypy + bandit)"
	@echo "  lint-fix     - Run linting with auto-fix"
	@echo "  format       - Format code with ruff"
	@echo "  type-check   - Run type checking with mypy"
	@echo "  security     - Run security checks with bandit"
	@echo "  test         - Run tests"
	@echo "  clean        - Clean cache files"
	@echo "  docker-lint  - Run linting in Docker container"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt
	pre-commit install

# Linting commands
lint: format type-check security
	@echo "✅ All linting checks completed"

lint-fix:
	ruff check --fix src/
	ruff format src/
	@echo "✅ Auto-fix completed"

format:
	@echo "🔧 Formatting code..."
	ruff format src/
	@echo "✅ Code formatting completed"

type-check:
	@echo "🔍 Type checking..."
	mypy src/
	@echo "✅ Type checking completed"

security:
	@echo "🔒 Security checking..."
	bandit -r src/ -f json -o bandit-report.json || bandit -r src/
	@echo "✅ Security checking completed"

# Testing
test:
	@echo "🧪 Running tests..."
	pytest tests/ -v
	@echo "✅ Tests completed"

# Cleanup
clean:
	@echo "🧹 Cleaning cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -f bandit-report.json 2>/dev/null || true
	@echo "✅ Cleanup completed"

# Docker-based linting (for CI/CD or isolated environments)
docker-lint:
	@echo "🐳 Running linting in Docker..."
	docker run --rm -v $(PWD):/app -w /app python:3.11-slim bash -c "\
		pip install -r requirements-dev.txt && \
		ruff check src/ && \
		ruff format --check src/ && \
		mypy src/ && \
		bandit -r src/"
	@echo "✅ Docker linting completed"

# Quick commands for Agent Hook integration
quick-lint:
	@echo "⚡ Quick lint check..."
	ruff check src/ --quiet
	@echo "✅ Quick lint completed"

quick-format:
	@echo "⚡ Quick format..."
	ruff format src/ --quiet
	@echo "✅ Quick format completed"

# Pre-commit simulation
pre-commit-all:
	@echo "🔄 Running pre-commit on all files..."
	pre-commit run --all-files
	@echo "✅ Pre-commit checks completed"