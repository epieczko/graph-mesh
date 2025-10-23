# ADR-002: Manifest-Driven Pipeline Configuration

**Status**: Accepted

**Date**: 2025-01

**Deciders**: Graph-Mesh Team

## Context

Users need to configure Graph-Mesh pipelines specifying:
- Which data sources to process
- How to fetch each source (local file, URL, git repo)
- Which converter to use (XSD, JSON Schema)
- Which matchers to run (LogMap, AML, BERTMap)
- Pipeline metadata (name, description)

We need a configuration approach that is:
- Declarative and human-readable
- Version-controllable
- Easy to validate
- Extensible for new sources/matchers
- Shareable across teams

## Decision

We will use **YAML manifest files** as the primary configuration mechanism for pipeline execution.

### Manifest Structure

```yaml
name: pipeline-name
matchers:
  - logmap
  - aml
sources:
  - id: source-id
    fetch:
      type: file
      path: path/to/schema.xsd
    convert:
      type: xsd
      namespace: http://example.org/ns
```

### Key Decisions:

1. **YAML as Format**
   - Human-readable and writable
   - Native Python support (PyYAML)
   - Wide ecosystem support
   - Comments allowed

2. **Top-Level Fields**
   - `name`: Pipeline identifier (required)
   - `matchers`: List of matchers to execute (required)
   - `sources`: Array of source configurations (required)

3. **Source Configuration**
   - `id`: Unique source identifier
   - `fetch`: How to retrieve the source
   - `convert`: How to convert to OWL

4. **Extensibility Points**
   - New fetch types via registry pattern
   - New convert types via registry pattern
   - Custom matcher configurations (future)

5. **Validation**
   - Schema validation on load
   - Fail-fast on invalid manifests
   - Clear error messages

## Consequences

### Positive

- **Declarative**: Separates "what" from "how"
- **Readable**: Non-developers can understand and modify
- **Versionable**: YAML files work well with git
- **Shareable**: Easy to share pipeline configurations
- **Reproducible**: Same manifest = same pipeline execution
- **Testable**: Can test with sample manifests
- **Documentation**: Manifests serve as documentation
- **Extensible**: Easy to add new fields without breaking existing manifests

### Negative

- **Validation Complexity**: Need to validate manifest structure
- **Limited Logic**: Can't express complex conditionals (by design)
- **Version Management**: Need strategy for manifest format evolution
- **YAML Pitfalls**: YAML has gotchas (indentation, special characters)

### Neutral

- **Single File**: All configuration in one file (could split for large pipelines)
- **No Templating**: No variable substitution yet (can add later)
- **Static Configuration**: No runtime parameter changes

## Alternatives Considered

### 1. Command-Line Arguments

Pass all configuration via CLI flags.

**Rejected because**:
- Gets unwieldy with multiple sources
- Hard to share and version
- Poor for complex configurations
- Not human-readable at scale

### 2. Python Configuration Files

Use Python files for configuration (like Django settings).

**Rejected because**:
- Requires Python knowledge
- Security risk (arbitrary code execution)
- Harder to parse and validate
- Not declarative

### 3. JSON Configuration

Use JSON instead of YAML.

**Rejected because**:
- No comments support
- More verbose (quotes, commas)
- Less human-friendly
- YAML is superset of JSON (can support both)

### 4. TOML Configuration

Use TOML format.

**Rejected because**:
- Less familiar in data science community
- More verbose for nested structures
- YAML more established in ML/data pipelines

### 5. Database-Backed Configuration

Store configurations in database.

**Rejected because**:
- Adds infrastructure dependency
- Harder to version control
- Overkill for current needs
- Can migrate later if needed

## Implementation Details

### Manifest Loading

```python
from pathlib import Path
import yaml
from dataclasses import dataclass

@dataclass
class PipelineManifest:
    name: str
    matchers: list[str]
    sources: list[SourceConfig]

def load_manifest(path: Path) -> PipelineManifest:
    with open(path) as f:
        data = yaml.safe_load(f)
    # Validate and construct dataclass
    return PipelineManifest(**data)
```

### Validation Strategy

1. **Schema Validation**: Use schema validator (future: JSON Schema)
2. **Type Checking**: Leverage Python type hints and dataclasses
3. **Business Logic Validation**: Check source IDs unique, matchers valid, etc.

### Extensibility Pattern

```python
# Registry for fetch types
FETCH_HANDLERS = {
    "file": fetch_from_file,
    "url": fetch_from_url,
    "git": fetch_from_git,
}

# Registry for converters
CONVERTERS = {
    "xsd": convert_xsd_to_owl,
    "json": convert_json_schema_to_owl,
}
```

### Error Handling

- **Parse Errors**: Show line numbers and context
- **Validation Errors**: List all validation failures, not just first
- **Execution Errors**: Track which source/step failed

### Manifest Evolution

**Version Strategy**:
- No version field initially (all manifests v1 implicitly)
- Add version field when breaking changes needed
- Maintain backwards compatibility where possible
- Provide migration tools for major version changes

**Deprecation Process**:
1. Announce deprecation in docs
2. Add deprecation warnings in code
3. Support old + new format for 2 releases
4. Remove deprecated format

## Example Manifests

### Simple Single-Source

```yaml
name: simple-pipeline
matchers:
  - logmap
sources:
  - id: mortgage
    fetch:
      type: file
      path: schemas/mortgage.xsd
    convert:
      type: xsd
```

### Multi-Source with All Matchers

```yaml
name: financial-integration
matchers:
  - logmap
  - aml
  - bertmap
sources:
  - id: mismo
    fetch:
      type: file
      path: mismo/mismo_2_4_schema.xsd
    convert:
      type: xsd
      namespace: http://www.mismo.org/residential/2009/schemas
  - id: acord
    fetch:
      type: url
      url: https://example.org/acord_schema.xsd
    convert:
      type: xsd
```

## Future Enhancements

1. **Variable Substitution**: `${ENV_VAR}` support
2. **Includes**: Import common configuration snippets
3. **Profiles**: Development vs. production configurations
4. **Conditional Execution**: Run matchers based on conditions
5. **Parallel Sources**: Explicit parallel/sequential control
6. **Matcher Parameters**: Pass custom parameters to matchers

## References

- YAML Specification: https://yaml.org/spec/
- PyYAML Documentation: https://pyyaml.org/
- The Twelve-Factor App (Config): https://12factor.net/config

## Related ADRs

- [ADR-001: Container-Based Architecture](adr-001-container-based-architecture.md)
- [ADR-005: Multi-Matcher Strategy](adr-005-multi-matcher-strategy.md)
