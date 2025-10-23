# ADR-003: SSSOM Mapping Format

**Status**: Accepted

**Date**: 2025-01

**Deciders**: Graph-Mesh Team

## Context

Graph-Mesh generates mappings between ontologies using various matchers (LogMap, AML, BERTMap). We need a standard format for representing these mappings that:

- Is interoperable with other ontology tools
- Supports rich metadata (confidence scores, provenance, relations)
- Is human-readable and machine-processable
- Can be validated and quality-checked
- Is extensible for custom fields
- Has good ecosystem support

Different matchers produce different output formats:
- LogMap: RDF alignment format
- AML: Custom XML/RDF
- BERTMap: TSV format

We need a unified format for downstream processing (fusion, validation, visualization).

## Decision

We will adopt **SSSOM (Simple Standard for Sharing Ontology Mappings)** as the canonical mapping format for Graph-Mesh.

### Key Decisions:

1. **SSSOM as Primary Format**
   - TSV-based format with controlled vocabulary
   - Rich metadata support
   - Growing ecosystem adoption
   - Python library (sssom-py) available

2. **Mapping Structure**
   ```
   subject_id | predicate_id | object_id | confidence | match_type
   ```

3. **Matcher Output Normalization**
   - Convert all matcher outputs to SSSOM
   - Preserve matcher-specific confidence scores
   - Add provenance metadata

4. **Required SSSOM Fields**
   - `subject_id`: Source ontology entity URI
   - `predicate_id`: Mapping relation (e.g., skos:exactMatch)
   - `object_id`: Target ontology entity URI
   - `confidence`: Numeric score (0.0-1.0)
   - `mapping_provider`: Which matcher produced this

5. **File Naming Convention**
   - `{matcher}_mappings.sssom.tsv`
   - Example: `logmap_mappings.sssom.tsv`

## Consequences

### Positive

- **Standardization**: Industry-standard format, interoperable with ROBOT, OntoPortal, etc.
- **Rich Metadata**: Supports confidence, provenance, justifications, relations
- **Tooling**: Python library (sssom-py) handles parsing, validation, conversion
- **Human-Readable**: TSV format easy to inspect with text editors/Excel
- **Extensible**: Can add custom columns for domain-specific needs
- **Validation**: Schema validation ensures data quality
- **Future-Proof**: Active development, growing adoption in ontology community

### Negative

- **Learning Curve**: Team needs to learn SSSOM specification
- **Conversion Overhead**: Must convert matcher outputs (adds processing step)
- **TSV Limitations**: Not ideal for very large mappings (millions of rows)
- **Dependency**: Adds sssom-py library dependency

### Neutral

- **Flat Structure**: TSV format is flat, not hierarchical (fine for mappings)
- **No Complex Relations**: Focuses on simple mappings (can extend if needed)

## Alternatives Considered

### 1. RDF Alignment Format

Use W3C Alignment API format (RDF/XML).

**Rejected because**:
- XML verbose and less human-readable
- Harder to process with standard tools (Excel, pandas)
- Not as widely adopted as SSSOM in recent years
- SSSOM can be converted to RDF if needed

### 2. Custom JSON Format

Design a custom JSON schema for mappings.

**Rejected because**:
- Reinventing the wheel
- No ecosystem support
- Not interoperable with other tools
- More work to maintain

### 3. Simple CSV

Use basic CSV with minimal fields.

**Rejected because**:
- No standardized vocabulary
- Limited metadata support
- No validation schema
- Not interoperable

### 4. Database Storage

Store mappings directly in a database (PostgreSQL, Neo4j).

**Rejected because**:
- Adds infrastructure dependency
- Harder to version control
- Not portable
- Can load SSSOM into DB later if needed

## Implementation Details

### SSSOM File Structure

```tsv
subject_id	predicate_id	object_id	confidence	mapping_provider	match_type
http://source.org/Entity	skos:exactMatch	http://target.org/Entity	0.95	logmap	manual
http://source.org/Agent	skos:closeMatch	http://target.org/Actor	0.78	bertmap	semantic
```

### Python Integration

```python
import sssom
import pandas as pd

# Read SSSOM file
msdf = sssom.parse("logmap_mappings.sssom.tsv")

# Access as DataFrame
df = msdf.df
high_conf = df[df["confidence"] > 0.9]

# Write SSSOM file
sssom.write_sssom_dataframe(msdf, "output.sssom.tsv")
```

### Matcher Output Conversion

Each matcher wrapper converts to SSSOM:

```python
def logmap_to_sssom(logmap_output: Path) -> pd.DataFrame:
    """Convert LogMap RDF output to SSSOM DataFrame."""
    # Parse LogMap RDF
    # Extract mappings
    # Convert to SSSOM schema
    return sssom_df
```

### Mapping Relations

Use SKOS vocabulary for predicate types:
- `skos:exactMatch`: Entities are equivalent
- `skos:closeMatch`: Entities are very similar
- `skos:broadMatch`: Subject is broader than object
- `skos:narrowMatch`: Subject is narrower than object
- `skos:relatedMatch`: Entities are related

### Confidence Scores

Normalize all confidence scores to 0.0-1.0 range:
- LogMap: Already 0.0-1.0
- AML: May need normalization
- BERTMap: BERT similarity scores → confidence

### Provenance Tracking

Include metadata for traceability:
- `mapping_provider`: Which tool generated mapping
- `mapping_date`: When mapping was created
- `mapping_source`: Pipeline run identifier
- `comment`: Additional notes

### Quality Validation

Use SSSOM validator:

```python
from sssom.validation import validate

# Validate SSSOM file
errors = validate("mappings.sssom.tsv")
if errors:
    print("Validation errors:", errors)
```

## SSSOM Metadata

SSSOM files include optional metadata block:

```yaml
# SSSOM Metadata
creator_id: graph-mesh
mapping_date: 2025-01-15
license: https://creativecommons.org/publicdomain/zero/1.0/
mapping_set_description: |
  Ontology mappings generated by Graph-Mesh pipeline
  using LogMap, AML, and BERTMap matchers.
```

## Integration with Pipeline

### Stage 3: Align

Matchers produce SSSOM files in artifacts directory:

```
artifacts/
├── logmap_mappings.sssom.tsv
├── aml_mappings.sssom.tsv
└── bertmap_mappings.sssom.tsv
```

### Stage 4: Fuse

Fusion stage reads SSSOM mappings:

```python
def fuse_graphs(source_graphs, mappings):
    """Merge graphs using SSSOM mappings."""
    for mapping_file in mappings:
        msdf = sssom.parse(mapping_file)
        apply_mappings_to_graph(source_graphs, msdf)
```

### Aggregating Multiple Matchers

Combine mappings from multiple matchers:

```python
# Read all SSSOM files
all_mappings = []
for matcher in ["logmap", "aml", "bertmap"]:
    msdf = sssom.parse(f"{matcher}_mappings.sssom.tsv")
    all_mappings.append(msdf.df)

# Concatenate
combined = pd.concat(all_mappings)

# Deduplicate (keep highest confidence)
deduplicated = combined.sort_values("confidence", ascending=False).drop_duplicates(
    subset=["subject_id", "object_id"], keep="first"
)
```

## Future Enhancements

1. **Mapping Composition**: Compose mappings transitively
2. **Conflict Resolution**: Resolve contradictory mappings from different matchers
3. **Reasoning**: Use OWL reasoning to infer additional mappings
4. **Visualization**: Generate mapping visualizations from SSSOM
5. **Versioning**: Track mapping evolution over time
6. **SSSOM/RDF**: Export to RDF alignment format for compatibility

## References

- SSSOM Specification: https://mapping-commons.github.io/sssom/
- sssom-py Library: https://github.com/mapping-commons/sssom-py
- SKOS Mapping Properties: https://www.w3.org/TR/skos-reference/#mapping

## Related ADRs

- [ADR-005: Multi-Matcher Strategy](adr-005-multi-matcher-strategy.md)
- [ADR-001: Container-Based Architecture](adr-001-container-based-architecture.md)
