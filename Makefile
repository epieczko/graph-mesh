.PHONY: help install test lint format clean docker-build docker-up docs

help:
	@echo "Graph-Mesh Development Commands"
	@echo "================================"
	@echo "install         Install package and dependencies"
	@echo "test            Run test suite"
	@echo "test-cov        Run tests with coverage"
	@echo "lint            Run code quality checks"
	@echo "format          Format code with black and isort"
	@echo "clean           Remove build artifacts"
	@echo "docker-build    Build all Docker images"
	@echo "docker-up       Run full pipeline with Docker Compose"
	@echo "docs            Build Sphinx documentation"
	@echo "docs-serve      Build and serve documentation"

install:
	pip install -e ".[dev,docs]"

test:
	pytest

test-cov:
	pytest --cov --cov-report=html --cov-report=term

lint:
	black --check graph_mesh_* tests/
	isort --check-only graph_mesh_* tests/
	flake8 graph_mesh_* tests/ --max-line-length=100 --extend-ignore=E203,W503
	mypy graph_mesh_core/ graph_mesh_ingest/ graph_mesh_aligner/ graph_mesh_orchestrator/ || true

format:
	black graph_mesh_* tests/
	isort graph_mesh_* tests/

clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf htmlcov/ .coverage coverage.xml
	rm -rf .pytest_cache/ .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docker-build:
	docker compose build

docker-up:
	docker compose up --build

docs:
	cd docs_sphinx && make html

docs-serve: docs
	cd docs_sphinx/_build/html && python -m http.server 8000
