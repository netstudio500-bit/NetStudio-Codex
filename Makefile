.PHONY: help install dev test lint format clean run docs

.DEFAULT_GOAL := help

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -e .

dev:  ## Install development dependencies
	pip install -e ".[dev]"
	pre-commit install

test:  ## Run tests
	pytest tests/ -v

test-cov:  ## Run tests with coverage
	pytest tests/ -v --cov=netstudio --cov-report=html

test-unit:  ## Run unit tests only
	pytest tests/unit/ -v

lint:  ## Run linters
	black --check netstudio/ tests/
	isort --check-only netstudio/ tests/
	flake8 netstudio/ tests/
	mypy netstudio/

format:  ## Format code
	black netstudio/ tests/
	isort netstudio/ tests/

clean:  ## Clean up build artifacts
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +

run:  ## Run the application
	python -m netstudio.main

run-debug:  ## Run with debug mode
	python -m netstudio.main --debug

docs:  ## Build documentation
	mkdocs build

docs-serve:  ## Serve documentation locally
	mkdocs serve
