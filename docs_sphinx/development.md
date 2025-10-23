# Development Guide

This guide covers development workflows, testing, and contribution guidelines.

## Development Setup

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Git

### Environment Setup

```bash
# Clone repository
git clone https://github.com/epieczko/graph-mesh.git
cd graph-mesh

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev,docs]"

# Install pre-commit hooks
pre-commit install
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_meta_ontology.py

# Run specific test
pytest tests/test_xsd_to_owl.py::TestXSDToOWL::test_convert_simple_xsd

# Run tests by marker
pytest -m unit
pytest -m integration
```

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── fixtures/                # Test data
│   ├── sample.xsd
│   └── sample_json_schema.json
├── test_meta_ontology.py    # Core module tests
├── test_xsd_to_owl.py       # XSD converter tests
├── test_json_to_owl.py      # JSON converter tests
└── test_orchestrator.py     # Pipeline tests
```

### Writing Tests

```python
import pytest
from graph_mesh_ingest.xsd_to_owl import convert_xsd_to_owl

class TestMyFeature:
    """Test suite for my feature."""

    def test_basic_functionality(self, temp_dir):
        """Test basic functionality."""
        # Arrange
        input_file = temp_dir / "input.xsd"
        output_file = temp_dir / "output.owl"

        # Act
        convert_xsd_to_owl(str(input_file), str(output_file))

        # Assert
        assert output_file.exists()
```

### Fixtures

Use shared fixtures from `conftest.py`:

```python
def test_with_fixtures(temp_dir, sample_xsd_path, fixtures_dir):
    """Test using shared fixtures."""
    # temp_dir: Temporary directory for test artifacts
    # sample_xsd_path: Path to sample XSD file
    # fixtures_dir: Path to fixtures directory
    pass
```

## Code Quality

### Formatting

```bash
# Format code with Black
black graph_mesh_* tests/

# Sort imports with isort
isort graph_mesh_* tests/

# Check formatting without changes
black --check graph_mesh_*
```

### Linting

```bash
# Run flake8
flake8 graph_mesh_* tests/ --max-line-length=100

# Run mypy for type checking
mypy graph_mesh_core/ graph_mesh_ingest/ graph_mesh_aligner/ graph_mesh_orchestrator/
```

### Pre-commit Hooks

Pre-commit hooks automatically run checks before commits:

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

Configuration in `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
```

## Documentation

### Building Sphinx Docs

```bash
# Install documentation dependencies
pip install -e ".[docs]"

# Build HTML documentation
cd docs_sphinx
make html

# View documentation
open _build/html/index.html  # macOS
xdg-open _build/html/index.html  # Linux
```

### Writing Documentation

#### Docstrings

Use Google-style docstrings:

```python
def convert_xsd_to_owl(xsd_path: str, output_path: str) -> None:
    """Convert XSD schema to OWL ontology.

    Args:
        xsd_path: Path to input XSD file
        output_path: Path for output OWL file

    Returns:
        None

    Raises:
        ValueError: If XSD file is invalid
        IOError: If file operations fail

    Example:
        >>> convert_xsd_to_owl("schema.xsd", "ontology.owl")
    """
    pass
```

#### Markdown Files

Documentation uses MyST for Markdown in Sphinx:

```markdown
# My Feature

This is a description.

## Usage

```python
from graph_mesh_core import my_feature

my_feature.do_something()
```

## See Also

- {doc}`related_topic`
- {ref}`reference-section`
```
```

## Docker Development

### Building Images

```bash
# Build all images
docker compose build

# Build specific image
docker compose build orchestrator

# Rebuild without cache
docker compose build --no-cache
```

### Testing Containers

```bash
# Run specific service
docker compose run orchestrator bash

# View logs
docker compose logs -f orchestrator

# Clean up
docker compose down -v
```

### Adding New Matcher

1. Create Dockerfile in `docker/<matcher_name>/`
2. Add service to `docker-compose.yaml`
3. Implement wrapper in `graph_mesh_aligner/matchers.py`
4. Update documentation

## CI/CD

### GitHub Actions Workflows

- **test.yml**: Runs tests on Python 3.9, 3.10, 3.11
- **validate.yml**: OWL validation checks
- **graph-mesh.yml**: Full pipeline execution
- **release.yml**: Semantic versioning and releases

### Running Workflows Locally

```bash
# Install act (GitHub Actions local runner)
brew install act  # macOS

# Run test workflow
act -j test
```

## Release Process

### Creating a Release

1. Update version in `setup.py` and `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create and push tag:

```bash
git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin v0.2.0
```

4. GitHub Actions automatically:
   - Builds Python package
   - Creates Docker images with version tags
   - Generates GitHub release

### Versioning

Follow Semantic Versioning (SemVer):

- **MAJOR**: Incompatible API changes
- **MINOR**: Backwards-compatible features
- **PATCH**: Backwards-compatible bug fixes

## Contributing

### Contribution Workflow

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes and add tests
4. Run test suite: `pytest`
5. Run code quality checks: `black`, `flake8`, `mypy`
6. Commit changes: `git commit -m "Add my feature"`
7. Push to branch: `git push origin feature/my-feature`
8. Open pull request

### Pull Request Guidelines

- **Title**: Clear, concise description
- **Description**: Explain motivation and changes
- **Tests**: Include tests for new functionality
- **Documentation**: Update docs as needed
- **Code Quality**: Pass all CI checks

### Code Review Process

1. Automated CI checks must pass
2. At least one approving review required
3. No unresolved conversations
4. Branch up to date with main

## Architecture Decision Records

See [ADRs](adr/index.md) for architectural decisions and rationale.

## Getting Help

- **Issues**: https://github.com/epieczko/graph-mesh/issues
- **Discussions**: https://github.com/epieczko/graph-mesh/discussions
- **Documentation**: https://graph-mesh.readthedocs.io
