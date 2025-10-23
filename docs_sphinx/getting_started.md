# Getting Started

This guide will help you get up and running with Graph-Mesh.

## Prerequisites

- Python 3.9 or higher
- Docker and Docker Compose (for containerized workflows)
- Git

## Installation

### From PyPI

```bash
pip install graph-mesh
```

### From Source

```bash
git clone https://github.com/epieczko/graph-mesh.git
cd graph-mesh
pip install -e .
```

### For Development

```bash
# Clone repository
git clone https://github.com/epieczko/graph-mesh.git
cd graph-mesh

# Install with development dependencies
pip install -e ".[dev,docs]"

# Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

## First Steps

### 1. Verify Installation

```bash
# Check that graph-mesh is installed
graph-mesh --help

# Verify Docker setup
docker compose version
```

### 2. Run Sample Pipeline

Graph-Mesh includes a sample manifest to demonstrate the pipeline:

```bash
# Using Python
python -m graph_mesh_orchestrator.pipeline data_sources/sample_manifest.yaml

# Using Docker
docker compose up --build
```

### 3. Inspect Output

After running the pipeline, check the `artifacts/` directory:

```bash
ls -lh artifacts/
```

You should see:
- `meta_ontology.ttl` - Base meta-ontology
- `*_converted.ttl` - Converted source ontologies
- `*_mappings.sssom.tsv` - SSSOM alignment mappings
- `merged_graph.ttl` - Final fused knowledge graph

## Creating Your First Manifest

A manifest defines the pipeline configuration:

```yaml
name: my-first-pipeline
matchers:
  - logmap
sources:
  - id: source1
    fetch:
      type: file
      path: schemas/my_schema.xsd
    convert:
      type: xsd
```

Save this as `data_sources/my_manifest.yaml` and run:

```bash
docker compose run orchestrator python -m graph_mesh_orchestrator.pipeline /data_sources/my_manifest.yaml
```

## Next Steps

- Read the [Architecture](architecture.md) guide to understand the system design
- Explore the [User Guide](user_guide.md) for detailed usage instructions
- Check the [API Reference](api_reference.rst) for programmatic access
- Review [Architecture Decision Records](adr/index.md) for design rationale
