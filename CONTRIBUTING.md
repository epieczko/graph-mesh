# Contributing to Graph-Mesh

Thank you for your interest in contributing to Graph-Mesh! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## Getting Started

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Git

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/graph-mesh.git
   cd graph-mesh
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   make install
   # or
   pip install -e ".[dev,docs]"
   ```

4. **Install Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions or fixes

### 2. Make Changes

- Write clean, readable code
- Follow existing code style
- Add tests for new functionality
- Update documentation as needed

### 3. Run Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_xsd_to_owl.py
```

### 4. Check Code Quality

```bash
# Run all checks
make lint

# Format code
make format
```

### 5. Commit Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "Add feature: XYZ

- Detailed description of changes
- Why the change was needed
- Any breaking changes"
```

Commit message guidelines:
- Use present tense ("Add feature" not "Added feature")
- First line should be concise (< 72 characters)
- Provide detailed description in body if needed
- Reference issues: "Fixes #123" or "Relates to #456"

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Pull Request Guidelines

### PR Title

Use descriptive titles:
- ✅ "Add support for Protobuf schema conversion"
- ✅ "Fix memory leak in LogMap container"
- ❌ "Update code"
- ❌ "Fix bug"

### PR Description

Include:
1. **What**: What changes were made
2. **Why**: Why these changes were needed
3. **How**: How the changes work
4. **Testing**: How you tested the changes
5. **Screenshots**: If UI changes (not applicable here)

Example:
```markdown
## Summary
Adds support for converting Protobuf schemas to OWL ontologies.

## Motivation
Users requested support for Protobuf schemas (#123).

## Changes
- Added `protobuf_to_owl.py` converter
- Updated manifest schema to accept `type: protobuf`
- Added tests for Protobuf conversion
- Updated documentation

## Testing
- Unit tests: `test_protobuf_to_owl.py`
- Integration test with sample Protobuf schema
- All existing tests pass

## Related Issues
Closes #123
```

### PR Checklist

Before submitting, ensure:
- [ ] Tests pass (`make test`)
- [ ] Code is formatted (`make format`)
- [ ] Linting passes (`make lint`)
- [ ] Documentation updated (if needed)
- [ ] Changelog updated (if significant change)
- [ ] Commit messages are clear
- [ ] PR description is complete

## Code Style

### Python Style

We follow [PEP 8](https://peps.python.org/pep-0008/) with some modifications:

- **Line Length**: 100 characters (Black default)
- **Quotes**: Double quotes preferred
- **Imports**: Sorted with isort
- **Type Hints**: Use where beneficial

### Docstrings

Use Google-style docstrings:

```python
def convert_xsd_to_owl(xsd_path: str, output_path: str) -> None:
    """Convert XSD schema to OWL ontology.

    Args:
        xsd_path: Path to input XSD file.
        output_path: Path for output OWL file.

    Returns:
        None

    Raises:
        ValueError: If XSD file is invalid.
        IOError: If file operations fail.

    Example:
        >>> convert_xsd_to_owl("schema.xsd", "ontology.owl")
    """
    pass
```

### Testing

- Write tests for all new functionality
- Aim for high test coverage (> 80%)
- Use descriptive test names
- Follow AAA pattern: Arrange, Act, Assert

```python
def test_xsd_conversion_preserves_namespace(self, temp_dir):
    """Test that XSD namespace is preserved in OWL output."""
    # Arrange
    xsd_path = self.create_xsd_with_namespace(temp_dir)
    output_path = temp_dir / "output.owl"

    # Act
    convert_xsd_to_owl(str(xsd_path), str(output_path))

    # Assert
    graph = Graph()
    graph.parse(str(output_path))
    assert "http://example.org/ns" in [str(ns) for _, ns in graph.namespaces()]
```

## Documentation

### Code Documentation

- Document all public APIs
- Include examples in docstrings
- Keep comments concise and relevant

### User Documentation

When adding features, update:
- `docs_sphinx/user_guide.md` - User-facing documentation
- `docs_sphinx/api_reference.rst` - API reference
- `README.md` - If user-facing changes
- ADRs - If architectural decision

### Building Documentation

```bash
make docs
# View at docs_sphinx/_build/html/index.html

# Serve locally
make docs-serve
# View at http://localhost:8000
```

## Adding New Features

### New Converter

1. Create `graph_mesh_ingest/<format>_to_owl.py`
2. Implement `convert_<format>_to_owl(input_path, output_path)`
3. Register in `graph_mesh_orchestrator/ingest.py`
4. Add tests in `tests/test_<format>_to_owl.py`
5. Update documentation

### New Matcher

1. Create Dockerfile in `docker/<matcher>/`
2. Add service to `docker-compose.yaml`
3. Register in `graph_mesh_aligner/matchers.py`
4. Ensure output is SSSOM format
5. Add documentation

### New Pipeline Stage

1. Add stage function in `graph_mesh_orchestrator/pipeline.py`
2. Update `orchestrate()` to call new stage
3. Add tests
4. Update architecture documentation
5. Consider writing an ADR

## Reporting Issues

### Bug Reports

Include:
- **Description**: What happened vs. what you expected
- **Steps to Reproduce**: Detailed steps
- **Environment**: OS, Python version, Docker version
- **Logs**: Relevant error messages or logs
- **Screenshots**: If applicable

### Feature Requests

Include:
- **Use Case**: Why this feature is needed
- **Proposed Solution**: How you envision it working
- **Alternatives**: Other approaches considered
- **Examples**: Example usage or similar features in other tools

## Review Process

1. **Automated Checks**: CI runs tests, linting, etc.
2. **Code Review**: Maintainer reviews code
3. **Revisions**: Address feedback
4. **Approval**: Maintainer approves
5. **Merge**: PR merged to main branch

### Review Timeline

- We aim to respond to PRs within 3-5 business days
- Complex PRs may take longer
- Ping maintainers if no response after 7 days

## Release Process

Releases follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: Backwards-compatible features
- **PATCH**: Backwards-compatible bug fixes

Maintainers handle releases. Contributors don't need to worry about versioning.

## Questions?

- **Documentation**: https://graph-mesh.readthedocs.io
- **Issues**: https://github.com/epieczko/graph-mesh/issues
- **Discussions**: https://github.com/epieczko/graph-mesh/discussions

Thank you for contributing! 🎉
