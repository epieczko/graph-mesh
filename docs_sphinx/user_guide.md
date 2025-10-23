# User Guide

This guide covers common usage patterns and workflows for Graph-Mesh.

## Manifest Configuration

Manifests are YAML files that define pipeline execution. They specify data sources, converters, and matchers.

### Basic Manifest Structure

```yaml
name: my-pipeline
matchers:
  - logmap
  - aml
sources:
  - id: source1
    fetch:
      type: file
      path: schemas/schema1.xsd
    convert:
      type: xsd
  - id: source2
    fetch:
      type: file
      path: schemas/schema2.json
    convert:
      type: json
```

### Manifest Fields

#### Top Level

- **name** (required): Pipeline identifier
- **matchers** (required): List of matchers to execute (`logmap`, `aml`, `bertmap`)
- **sources** (required): Array of data source configurations

#### Source Configuration

- **id** (required): Unique identifier for the source
- **fetch** (required): Fetch configuration
  - **type**: `file` (local), `url` (remote), `git` (repository)
  - **path**: Path to source file
- **convert** (required): Conversion configuration
  - **type**: `xsd` or `json`
  - **namespace**: Custom namespace (optional)

### Example Manifests

#### Single XSD Source

```yaml
name: single-xsd-pipeline
matchers:
  - logmap
sources:
  - id: mortgage-schema
    fetch:
      type: file
      path: data_sources/mismo/mismo_2_4_schema.xsd
    convert:
      type: xsd
```

#### Multiple Sources with All Matchers

```yaml
name: multi-source-alignment
matchers:
  - logmap
  - aml
  - bertmap
sources:
  - id: financial-xsd
    fetch:
      type: file
      path: schemas/financial.xsd
    convert:
      type: xsd
  - id: legal-json
    fetch:
      type: file
      path: schemas/legal_schema.json
    convert:
      type: json
```

## Running the Pipeline

### Command Line

```bash
# Using Python module
python -m graph_mesh_orchestrator.pipeline data_sources/my_manifest.yaml

# Using installed command
graph-mesh data_sources/my_manifest.yaml
```

### Docker Compose

```bash
# Run with default manifest
docker compose up --build

# Run with custom manifest
docker compose run orchestrator python -m graph_mesh_orchestrator.pipeline /data_sources/custom.yaml
```

### Programmatic Usage

```python
from pathlib import Path
from graph_mesh_orchestrator.pipeline import orchestrate

# Run pipeline
artifacts = orchestrate(Path("data_sources/my_manifest.yaml"))

# Access results
print(f"Meta-ontology: {artifacts.meta_ontology}")
print(f"Converted graphs: {artifacts.converted_graphs}")
print(f"Mappings: {artifacts.mappings}")
print(f"Merged graph: {artifacts.merged_graph}")
```

## Working with Converters

### XSD to OWL

The XSD converter handles:
- Complex types → OWL classes
- Simple types → Datatype properties
- Elements → Object properties
- Attributes → Datatype properties
- Namespaces preserved

```python
from graph_mesh_ingest.xsd_to_owl import convert_xsd_to_owl

convert_xsd_to_owl(
    xsd_path="schemas/my_schema.xsd",
    output_path="output/my_ontology.owl"
)
```

### JSON Schema to OWL

The JSON Schema converter handles:
- Objects → OWL classes
- Properties → OWL properties
- Required fields → Cardinality restrictions
- Type constraints → Datatype restrictions

```python
from graph_mesh_ingest.json_to_owl import convert_json_schema_to_owl

convert_json_schema_to_owl(
    schema_path="schemas/my_schema.json",
    output_path="output/my_ontology.owl"
)
```

## Working with Matchers

### LogMap

Logic-based matcher with inconsistency repair.

**Strengths**:
- Precise alignments
- Handles inconsistencies
- Fast execution

**Best for**: Well-structured ontologies with formal semantics

### AML (AgreementMaker Light)

Hybrid matcher combining multiple similarity metrics.

**Strengths**:
- Balanced precision/recall
- Multiple matching strategies
- Good for diverse ontologies

**Best for**: General-purpose alignment tasks

### BERTMap

BERT-based semantic matcher using pre-trained language models.

**Strengths**:
- Semantic understanding
- Natural language labels
- Cross-domain matching

**Best for**: Ontologies with rich textual descriptions

### Matcher Selection Strategy

```yaml
# High precision needed → use LogMap
matchers:
  - logmap

# Balanced results → use AML + LogMap
matchers:
  - logmap
  - aml

# Maximum coverage → use all three
matchers:
  - logmap
  - aml
  - bertmap
```

## Analyzing Results

### Artifacts Directory Structure

After pipeline execution:

```
artifacts/
├── meta_ontology.ttl              # Base meta-ontology
├── source1_converted.ttl          # Converted source 1
├── source2_converted.ttl          # Converted source 2
├── logmap_mappings.sssom.tsv      # LogMap alignments
├── aml_mappings.sssom.tsv         # AML alignments
├── bertmap_mappings.sssom.tsv     # BERTMap alignments
└── merged_graph.ttl               # Final fused graph
```

### Reading SSSOM Mappings

```python
import pandas as pd

# Load mappings
mappings = pd.read_csv("artifacts/logmap_mappings.sssom.tsv", sep="\t")

# Analyze alignment quality
high_confidence = mappings[mappings["confidence"] > 0.9]
print(f"High confidence mappings: {len(high_confidence)}")

# Find specific mappings
entity_mappings = mappings[mappings["subject_label"].str.contains("Entity")]
```

### Querying the Merged Graph

```python
from rdflib import Graph

# Load merged graph
g = Graph()
g.parse("artifacts/merged_graph.ttl", format="turtle")

# SPARQL query
query = """
SELECT ?class ?label
WHERE {
    ?class a owl:Class .
    ?class rdfs:label ?label .
}
LIMIT 10
"""

results = g.query(query)
for row in results:
    print(f"{row.class}: {row.label}")
```

## Troubleshooting

### Common Issues

#### 1. Docker Socket Permission Denied

**Error**: `Permission denied while trying to connect to the Docker daemon socket`

**Solution**:
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

#### 2. Conversion Fails for XSD

**Error**: `Failed to parse XSD schema`

**Possible causes**:
- Invalid XML syntax
- Missing namespace declarations
- Unsupported XSD features

**Solution**: Validate XSD with `xmllint`:
```bash
xmllint --schema my_schema.xsd --noout
```

#### 3. Matcher Container Exits Immediately

**Error**: Matcher container exits with code 1

**Solution**: Check Docker logs:
```bash
docker compose logs logmap
```

#### 4. Out of Memory

**Error**: Container killed due to memory limits

**Solution**: Increase Docker memory:
```yaml
services:
  bertmap:
    image: graph-mesh/bertmap:latest
    deploy:
      resources:
        limits:
          memory: 4G
```

## Best Practices

1. **Start Small**: Test with simple schemas before scaling up
2. **Version Control**: Keep manifests in version control
3. **Incremental Alignment**: Add matchers progressively
4. **Validate Inputs**: Ensure schemas are valid before conversion
5. **Monitor Resources**: Watch memory usage for large ontologies
6. **Review Mappings**: Manually validate high-impact alignments
7. **Document Decisions**: Use comments in manifests to explain choices
