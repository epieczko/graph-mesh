# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Complete CI/CD infrastructure with GitHub Actions
  - Automated testing workflow for Python 3.9, 3.10, 3.11
  - OWL validation workflow
  - Release automation workflow with semantic versioning
  - Documentation building workflow
- Comprehensive test suite
  - Unit tests for meta-ontology, XSD/JSON converters, orchestrator
  - Pytest configuration with coverage reporting
  - Test fixtures and shared conftest
- Ontmalizer Docker container for XSD to OWL conversion
- Complete Sphinx documentation structure
  - Getting Started guide
  - Architecture documentation
  - User Guide with examples
  - API Reference
  - Development guide
- Architecture Decision Records (ADRs)
  - ADR-001: Container-Based Architecture
  - ADR-002: Manifest-Driven Pipeline
  - ADR-003: SSSOM Mapping Format
  - ADR-004: Modular Package Structure
  - ADR-005: Multi-Matcher Strategy
- Python package structure
  - setup.py for package installation
  - pyproject.toml with tool configurations
  - CLI entry point: `graph-mesh` command
- Code quality tooling
  - Black formatter configuration
  - isort import sorting
  - flake8 linting
  - mypy type checking
  - pre-commit hooks
- Makefile for common development tasks
- CONTRIBUTING.md with contributor guidelines

### Changed
- Enhanced docker-compose.yaml with Ontmalizer service
- Updated GitHub Actions workflows for better pipeline execution
- Improved requirements.txt with testing and documentation dependencies

### Infrastructure
- Docker images with semantic versioning
- Parallel Docker builds in CI
- Artifact retention and upload
- Code coverage tracking
- OWL validation in CI pipeline

## [0.1.0] - 2025-01 (Initial)

### Added
- Core meta-ontology with 7 base classes
- XSD to OWL converter with namespace awareness
- JSON Schema to OWL converter
- Container-based matchers (LogMap, AML, BERTMap)
- Manifest-driven pipeline orchestration
- SSSOM mapping format support
- Docker Compose orchestration
- Basic documentation

[Unreleased]: https://github.com/epieczko/graph-mesh/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/epieczko/graph-mesh/releases/tag/v0.1.0
