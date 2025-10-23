# ADR-004: Modular Package Structure

**Status**: Accepted

**Date**: 2025-01

**Deciders**: Graph-Mesh Team

## Context

Graph-Mesh consists of multiple functional areas:
- Meta-ontology definitions and core utilities
- Schema-to-OWL conversion (XSD, JSON Schema)
- Ontology alignment orchestration
- Pipeline coordination and execution

We need to decide on a code organization strategy that:
- Promotes modularity and separation of concerns
- Allows independent development and testing
- Enables selective imports (don't import everything)
- Supports future extraction into separate packages
- Is familiar to Python developers
- Works well with static analysis tools

## Decision

We will organize Graph-Mesh as a **monorepo with multiple Python packages** using a flat namespace structure.

### Package Structure

```
graph-mesh/
├── graph_mesh_core/          # Meta-ontology and shared utilities
│   ├── __init__.py
│   └── meta_ontology.py
├── graph_mesh_ingest/        # Schema-to-OWL converters
│   ├── __init__.py
│   ├── xsd_to_owl.py
│   └── json_to_owl.py
├── graph_mesh_aligner/       # Matcher orchestration
│   ├── __init__.py
│   └── matchers.py
├── graph_mesh_orchestrator/  # Pipeline coordinator
│   ├── __init__.py
│   ├── pipeline.py
│   └── ingest.py
└── tests/                    # Test suite
```

### Key Decisions:

1. **Four Separate Packages**
   - `graph_mesh_core`: Foundation layer
   - `graph_mesh_ingest`: Conversion logic
   - `graph_mesh_aligner`: Alignment logic
   - `graph_mesh_orchestrator`: Top-level coordinator

2. **Flat Namespace (No Parent Package)**
   - NOT `graph_mesh.core`, `graph_mesh.ingest`, etc.
   - YES `graph_mesh_core`, `graph_mesh_ingest`, etc.
   - Avoids namespace package complexity

3. **Monorepo Approach**
   - All packages in single repository
   - Shared development workflow
   - Single version number (initially)

4. **Dependency Hierarchy**
   ```
   orchestrator → aligner → ingest → core
   ```
   - Core has no internal dependencies
   - Ingest depends only on core
   - Aligner depends on core (not ingest)
   - Orchestrator depends on all three

5. **Single setup.py/pyproject.toml**
   - One installable package: `graph-mesh`
   - Installs all four sub-packages
   - Can split later if needed

## Consequences

### Positive

- **Modularity**: Clear boundaries between functional areas
- **Testability**: Can test each package independently
- **Selective Imports**: Import only what you need
- **Code Navigation**: Easy to find relevant code
- **Parallel Development**: Teams can work on different packages
- **Clear Dependencies**: Dependency direction explicit
- **Future Flexibility**: Can extract packages later if needed
- **Tool Support**: Works well with IDEs, mypy, pylint

### Negative

- **Not True Separate Packages**: Still one installable package
- **Can't Version Independently**: All packages share version (for now)
- **Import Paths Longer**: `from graph_mesh_core...` vs `from graph_mesh.core...`
- **Duplication Risk**: Might duplicate utilities across packages

### Neutral

- **Monorepo**: Single repo for all code (good for small team, might need split later)
- **No Circular Dependencies**: Hierarchy prevents this (by design)

## Alternatives Considered

### 1. Single Flat Package

All code in single `graph_mesh/` package.

```
graph_mesh/
├── __init__.py
├── meta_ontology.py
├── xsd_to_owl.py
├── json_to_owl.py
├── matchers.py
└── pipeline.py
```

**Rejected because**:
- Poor separation of concerns
- Hard to navigate as codebase grows
- Difficult to test components independently
- Encourages tight coupling

### 2. Namespace Package

Use namespace package: `graph_mesh.core`, `graph_mesh.ingest`, etc.

```
graph_mesh/
├── core/
│   └── meta_ontology.py
├── ingest/
│   ├── xsd_to_owl.py
│   └── json_to_owl.py
```

**Rejected because**:
- Namespace packages are complex in Python
- Requires careful `__init__.py` management
- Potential import issues
- Doesn't play well with editable installs

### 3. Separate Repositories (Polyrepo)

Each package in its own git repository.

**Rejected because**:
- Too much overhead for current team size
- Complicates dependency management
- Harder to coordinate changes across packages
- Slows down development velocity
- Can migrate later if needed

### 4. Hierarchical Package Structure

Deep nesting: `graph_mesh.modules.ingest.converters.xsd`

**Rejected because**:
- Over-engineered for current complexity
- Longer import paths
- Harder to refactor

## Implementation Details

### Package Initialization

Each package has minimal `__init__.py`:

```python
# graph_mesh_core/__init__.py
"""Core meta-ontology definitions and shared utilities."""
from .meta_ontology import build_meta_graph, serialize_meta_graph

__all__ = ["build_meta_graph", "serialize_meta_graph"]
```

### Import Patterns

**Within same package**:
```python
# In graph_mesh_ingest/json_to_owl.py
from .xsd_to_owl import parse_namespace  # Relative import OK
```

**Cross-package**:
```python
# In graph_mesh_orchestrator/pipeline.py
from graph_mesh_core.meta_ontology import build_meta_graph
from graph_mesh_ingest.xsd_to_owl import convert_xsd_to_owl
from graph_mesh_aligner.matchers import run_alignment
```

**Avoid**:
```python
# DON'T DO THIS
from graph_mesh_orchestrator import *  # Star imports
import graph_mesh_core  # Importing package without submodule
```

### Dependency Management

Core has minimal dependencies:
```python
# graph_mesh_core dependencies
rdflib
owlready2
```

Each layer adds dependencies:
```python
# graph_mesh_ingest additional dependencies
xmlschema
# (inherits rdflib, owlready2 from core)

# graph_mesh_orchestrator additional dependencies
docker
pyyaml
pandas
sssom
```

### Testing Structure

Tests mirror package structure:

```
tests/
├── test_meta_ontology.py      # Tests graph_mesh_core
├── test_xsd_to_owl.py          # Tests graph_mesh_ingest
├── test_json_to_owl.py         # Tests graph_mesh_ingest
├── test_matchers.py            # Tests graph_mesh_aligner
└── test_orchestrator.py        # Tests graph_mesh_orchestrator
```

### Documentation Structure

Sphinx autodoc follows package structure:

```rst
API Reference
=============

Core Module
-----------
.. automodule:: graph_mesh_core.meta_ontology

Ingest Module
-------------
.. automodule:: graph_mesh_ingest.xsd_to_owl
.. automodule:: graph_mesh_ingest.json_to_owl
```

## Package Responsibilities

### graph_mesh_core

**Purpose**: Foundation layer, minimal dependencies

**Contains**:
- Meta-ontology definitions (7 core classes)
- Common RDF/OWL utilities
- Shared constants and namespaces

**Dependencies**: rdflib, owlready2

**Key Files**: `meta_ontology.py`

### graph_mesh_ingest

**Purpose**: Convert heterogeneous schemas to OWL

**Contains**:
- XSD to OWL converter
- JSON Schema to OWL converter
- Future: CSV, Protobuf, Avro converters

**Dependencies**: core + xmlschema

**Key Files**: `xsd_to_owl.py`, `json_to_owl.py`

### graph_mesh_aligner

**Purpose**: Orchestrate ontology matching

**Contains**:
- Matcher container wrappers
- SSSOM output generation
- Matcher lifecycle management

**Dependencies**: core + docker, sssom

**Key Files**: `matchers.py`

### graph_mesh_orchestrator

**Purpose**: End-to-end pipeline coordination

**Contains**:
- Pipeline orchestration logic
- Manifest parsing and validation
- Stage coordination (fetch, convert, align, fuse, validate)
- CLI interface

**Dependencies**: core + ingest + aligner + pyyaml, pandas

**Key Files**: `pipeline.py`, `ingest.py`

## Future Evolution

### Extracting Packages

If packages grow large or need independent versioning:

1. **Extract graph_mesh_core**
   - Move to separate repo
   - Publish to PyPI as `graph-mesh-core`
   - Other packages depend on it

2. **Extract graph_mesh_ingest**
   - Becomes `graph-mesh-converters`
   - Useful standalone for just conversion

3. **Extract graph_mesh_aligner**
   - Becomes `graph-mesh-matchers`
   - Can be used with other ontology tools

### Plugin System

Future: Allow external packages to register converters/matchers:

```python
# In external package
from graph_mesh_ingest import register_converter

@register_converter("protobuf")
def convert_protobuf_to_owl(path, output):
    ...
```

## Tools and Configuration

### Mypy Configuration

```toml
[tool.mypy]
mypy_path = "."
namespace_packages = false
explicit_package_bases = true
```

### Black/isort Configuration

```toml
[tool.isort]
profile = "black"
src_paths = ["graph_mesh_core", "graph_mesh_ingest", "graph_mesh_aligner", "graph_mesh_orchestrator"]
```

## References

- Python Packaging Guide: https://packaging.python.org/
- Monorepo Best Practices: https://monorepo.tools/
- PEP 420 (Namespace Packages): https://peps.python.org/pep-0420/

## Related ADRs

- [ADR-001: Container-Based Architecture](adr-001-container-based-architecture.md)
- [ADR-002: Manifest-Driven Pipeline](adr-002-manifest-driven-pipeline.md)
