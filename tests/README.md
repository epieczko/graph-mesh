# Graph-Mesh Testing Infrastructure

This directory contains the comprehensive test suite for the Graph-Mesh project.

## Test Coverage

Current test coverage: **90.15%** (exceeds 70% requirement)

- `graph_mesh_core/meta_ontology.py`: 100%
- `graph_mesh_ingest/json_to_owl.py`: 100%
- `graph_mesh_orchestrator/pipeline.py`: 97.85%
- `graph_mesh_orchestrator/ingest.py`: 96.92%
- `graph_mesh_aligner/matchers.py`: 88.10%
- `graph_mesh_ingest/xsd_to_owl.py`: 81.82%

## Structure

```
tests/
├── conftest.py              # Shared fixtures and pytest configuration
├── unit/                    # Unit tests for individual modules
│   ├── test_xsd_to_owl.py  # XSD to OWL converter tests
│   ├── test_json_to_owl.py # JSON Schema to OWL converter tests
│   ├── test_meta_ontology.py # Meta-ontology tests
│   ├── test_ingest.py      # Ingest dispatcher tests
│   ├── test_matchers.py    # Matcher/alignment tests
│   └── test_property_based.py # Property-based tests with hypothesis
├── integration/             # Integration tests
│   └── test_pipeline.py    # Full pipeline integration tests
└── data/                    # Test data
    ├── xsd/                # Sample XSD schemas
    ├── json/               # Sample JSON schemas
    └── ontology/           # Sample ontologies
```

## Running Tests

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest tests/
```

### Run with Coverage

```bash
pytest tests/ --cov --cov-report=html
```

### Run Specific Test Categories

```bash
# Run only unit tests
pytest tests/unit/ -m unit

# Run only integration tests
pytest tests/integration/ -m integration

# Run XSD-related tests
pytest tests/ -m xsd

# Run JSON-related tests
pytest tests/ -m json

# Run property-based tests
pytest tests/ -m property

# Exclude slow tests
pytest tests/ -m "not slow"

# Exclude Docker-dependent tests
pytest tests/ -m "not docker"
```

### Run Specific Test Files

```bash
# Test XSD converter
pytest tests/unit/test_xsd_to_owl.py -v

# Test meta-ontology
pytest tests/unit/test_meta_ontology.py -v

# Test full pipeline
pytest tests/integration/test_pipeline.py -v
```

## Test Markers

Tests are organized using pytest markers:

- `unit`: Unit tests for individual components
- `integration`: Integration tests for full pipeline
- `xsd`: Tests related to XSD conversion
- `json`: Tests related to JSON Schema conversion
- `ontology`: Tests related to ontology operations
- `matcher`: Tests for alignment matchers
- `docker`: Tests that require Docker daemon
- `slow`: Tests that take significant time to run
- `property`: Property-based tests with hypothesis

## Fixtures

The `conftest.py` file provides numerous fixtures for testing:

### Path Fixtures
- `test_data_dir`: Path to test data directory
- `temp_dir`: Temporary directory for test artifacts
- `artifacts_dir`: Temporary artifacts directory structure

### XSD Fixtures
- `simple_xsd_content`: Simple XSD schema content
- `complex_xsd_content`: Complex nested XSD schema
- `simple_xsd_file`: Temporary simple XSD file
- `complex_xsd_file`: Temporary complex XSD file
- `multiple_xsd_files`: Multiple related XSD files

### JSON Schema Fixtures
- `simple_json_schema`: Simple JSON schema dict
- `complex_json_schema`: Complex nested JSON schema
- `simple_json_schema_file`: Temporary JSON schema file

### Ontology Fixtures
- `sample_ontology_graph`: Sample RDF graph
- `sample_ontology_file`: Temporary ontology file

### Pipeline Fixtures
- `simple_manifest_dict`: Simple pipeline manifest
- `simple_manifest_file`: Temporary manifest file
- `multi_source_manifest_dict`: Multi-source manifest

### Docker Mocking Fixtures
- `mock_docker_client`: Mocked Docker client for testing
- `mock_docker_unavailable`: Simulates Docker unavailability

### Utility Fixtures
- `rdf_graph_comparator`: Compare RDF graphs
- `assert_owl_class_exists`: Check OWL class existence

## Configuration Files

### pytest.ini
Configures pytest behavior:
- Test discovery patterns
- Coverage settings (70% minimum)
- Test markers
- Logging configuration
- Timeout settings (300s)

### .coveragerc
Configures coverage reporting:
- Source directories to measure
- Files to omit (tests, __pycache__, etc.)
- Branch coverage enabled
- HTML and XML report generation
- Exclude patterns for coverage calculation

## Test Statistics

- **Total Tests**: 160+ passing tests
- **Test Files**: 7 test modules
- **Fixtures**: 25+ reusable fixtures
- **Test Categories**: Unit, Integration, Property-based
- **Coverage Reports**: Terminal, HTML, XML

## Continuous Integration

The test suite is designed for CI/CD integration:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest tests/ --cov --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Writing New Tests

### Unit Test Template

```python
import pytest
from your_module import your_function

class TestYourFunction:
    @pytest.mark.unit
    def test_basic_functionality(self):
        """Test basic functionality."""
        result = your_function(input)
        assert result == expected

    @pytest.mark.unit
    def test_edge_case(self):
        """Test edge case handling."""
        with pytest.raises(ValueError):
            your_function(invalid_input)
```

### Using Fixtures

```python
@pytest.mark.unit
def test_with_fixture(simple_xsd_file, temp_dir):
    """Test using provided fixtures."""
    # simple_xsd_file and temp_dir are automatically provided
    result = process_file(simple_xsd_file, temp_dir)
    assert result.exists()
```

## Property-Based Testing

Tests use Hypothesis for property-based testing:

```python
from hypothesis import given, strategies as st

@pytest.mark.property
@given(st.text(min_size=1, max_size=100))
def test_property(text):
    """Test that property holds for all inputs."""
    result = safe_local(text)
    assert isinstance(result, str)
    assert len(result) > 0
```

## Troubleshooting

### Docker-Related Test Failures

If Docker tests fail:
```bash
# Skip Docker tests
pytest tests/ -m "not docker"
```

### Slow Test Execution

```bash
# Skip slow tests
pytest tests/ -m "not slow"
```

### Coverage Below Threshold

Check coverage report:
```bash
pytest tests/ --cov --cov-report=term-missing
```

The report shows which lines are missing coverage.

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure tests are marked appropriately
3. Add new fixtures to conftest.py if needed
4. Update this README with new test categories
5. Verify coverage remains above 70%

```bash
# Before committing
pytest tests/ --cov
```
