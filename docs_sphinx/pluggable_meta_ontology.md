# Pluggable Meta-Ontology System

Graph-Mesh supports pluggable meta-ontologies, allowing you to choose the semantic backbone that best fits your domain.

## Overview

The meta-ontology serves as the integration pivot point - external schemas are aligned to it, enabling cross-schema queries and reasoning.

```
Schema A (MISMO) ----→ Meta-Ontology ←---- Schema B (XBRL)
                             ↑
                             |
                       Schema C (HMDA)
```

## Available Providers

### 1. Generic (Default)

Simple 7-class ontology for domain-agnostic integration.

**Classes:** Entity, Agent, Contract, Event, Location, Regulation, Metric

**Use Cases:**
- Exploratory data integration
- Prototyping before selecting domain ontology
- Cross-domain projects

**Configuration:**
```yaml
meta_ontology:
  type: generic
```

**Python API:**
```python
from graph_mesh_core.providers.generic import GenericMetaOntology

provider = GenericMetaOntology()
graph = provider.build_graph()
```

---

### 2. FIBO (Financial)

Financial Industry Business Ontology - industry standard for financial services.

**Modules:**
- FND: Foundations (parties, agreements, accounting)
- BE: Business Entities
- FBC: Financial Business and Commerce
- LOAN: Loans and Mortgages
- SEC: Securities
- IND: Indicators and Indexes
- DER: Derivatives

**Use Cases:**
- Banking and financial services
- Mortgage and lending systems
- Securities and derivatives trading
- Regulatory compliance (MISMO, XBRL, HMDA)

**Configuration:**
```yaml
meta_ontology:
  type: fibo
  options:
    modules:
      - FND    # Foundations
      - LOAN   # Loans
      - FBC    # Financial Business
    cache_dir: ./.fibo-cache
    use_cache: true
    version: latest
```

**Python API:**
```python
from graph_mesh_core.providers.fibo import FIBOMetaOntology

provider = FIBOMetaOntology(
    modules=["FND", "LOAN"],
    cache_dir="./.fibo-cache"
)
graph = provider.build_graph()
```

---

### 3. Custom

Load any OWL ontology from file or URL.

**Use Cases:**
- Domain-specific ontologies not provided as built-in
- Proprietary enterprise ontologies
- Research/specialized domains

**Configuration:**
```yaml
meta_ontology:
  type: custom
  options:
    source: "https://example.org/domain.owl"
    namespace: "https://example.org/domain#"
    name: "MyDomain"
    version: "1.0"
    format: "xml"  # Optional: turtle, xml, n3, etc.
```

**Python API:**
```python
from graph_mesh_core.providers.custom import CustomMetaOntology

provider = CustomMetaOntology(
    source="./my-ontology.ttl",
    namespace="https://my.org/onto#",
    name="MyOntology"
)
graph = provider.build_graph()
```

---

### 4. Composite

Combine multiple ontologies into unified meta-ontology.

**Use Cases:**
- FIBO + custom extensions
- Multi-domain projects
- Mixing generic and domain-specific concepts

**Python API (manifest not yet supported):**
```python
from graph_mesh_core.providers.fibo import FIBOMetaOntology
from graph_mesh_core.providers.custom import CustomMetaOntology
from graph_mesh_core.providers.composite import CompositeMetaOntology

fibo = FIBOMetaOntology(modules=["FND", "LOAN"])
custom = CustomMetaOntology(
    source="./extensions.ttl",
    namespace="https://my.org/ext#"
)

composite = CompositeMetaOntology(
    providers=[fibo, custom],
    name="FIBO+Extensions"
)

graph = composite.build_graph()
```

---

## Usage Examples

### Example 1: Financial Services (FIBO)

```yaml
# data_sources/riskexec_financial.yaml
name: riskexec-financial
meta_ontology:
  type: fibo
  options:
    modules: [FND, LOAN, FBC]

sources:
  - id: mismo
    fetch:
      type: local
      path: data_sources/mismo/MISMO_3.6.2.xsd
    convert:
      type: xsd
```

### Example 2: Generic Exploration

```yaml
# data_sources/exploration.yaml
name: quick-exploration
meta_ontology:
  type: generic

sources:
  - id: sample
    fetch:
      type: local
      path: data_sources/schemas/sample.xsd
    convert:
      type: xsd
```

### Example 3: Healthcare (Custom)

```yaml
# data_sources/healthcare.yaml
name: healthcare-integration
meta_ontology:
  type: custom
  options:
    source: "https://www.hl7.org/fhir/fhir.ttl"
    namespace: "http://hl7.org/fhir/"
    name: "FHIR"

sources:
  - id: epic-emr
    fetch:
      type: local
      path: data_sources/epic/schema.json
    convert:
      type: json
```

---

## Creating Custom Providers

You can register your own providers:

```python
from graph_mesh_core.meta_ontology_base import MetaOntologyProvider, MetaOntologyInfo
from graph_mesh_core.meta_ontology_registry import MetaOntologyRegistry
from rdflib import Graph, Namespace, URIRef

class MyCustomProvider(MetaOntologyProvider):
    def get_info(self) -> MetaOntologyInfo:
        return MetaOntologyInfo(
            name="MyProvider",
            version="1.0",
            namespace="https://my.org/onto#",
            description="My custom ontology"
        )

    def build_graph(self) -> Graph:
        graph = Graph()
        # Build your ontology
        return graph

    def get_alignment_targets(self) -> list[URIRef]:
        # Return alignable classes
        return []

    def get_namespace(self) -> Namespace:
        return Namespace("https://my.org/onto#")

# Register it
MetaOntologyRegistry.register("myprovider", MyCustomProvider)

# Use in manifest
meta_ontology:
  type: myprovider
  options:
    # Your options
```

---

## Provider Interface

All providers implement:

```python
class MetaOntologyProvider(ABC):
    @abstractmethod
    def get_info(self) -> MetaOntologyInfo:
        """Return metadata about this ontology."""
        pass

    @abstractmethod
    def build_graph(self) -> Graph:
        """Build and return the RDF graph."""
        pass

    @abstractmethod
    def get_alignment_targets(self) -> list[URIRef]:
        """Return classes available for alignment."""
        pass

    @abstractmethod
    def get_namespace(self) -> Namespace:
        """Return the primary namespace."""
        pass

    def validate_alignment(self, source_uri: URIRef, target_uri: URIRef) -> bool:
        """Validate if an alignment is semantically valid."""
        return True  # Optional override
```

---

## Provider Selection Guide

| Domain | Recommended Provider | Rationale |
|--------|---------------------|-----------|
| Financial Services | **FIBO** | Industry standard, 1500+ financial concepts |
| Healthcare | **Custom** (FHIR/SNOMED) | Medical terminology standards |
| Manufacturing | **Custom** (ISA-95) | Industrial automation |
| Legal/Compliance | **Custom** (LKIF) | Legal reasoning |
| Research/Generic | **Generic** | Simple, domain-agnostic |
| Multi-domain | **Composite** | Combine multiple ontologies |

---

## Performance Considerations

### FIBO

- **Size:** ~1500 classes, can be large
- **Loading:** First load downloads from EDM Council (cached afterward)
- **Recommendation:** Load only needed modules (FND + domain module)

```yaml
meta_ontology:
  type: fibo
  options:
    modules: [FND, LOAN]  # Only 2 modules instead of all 7
    cache_dir: ./cache
    use_cache: true       # Reuse cached files
```

### Generic

- **Size:** 7 classes, very small
- **Loading:** Instant, no downloads
- **Recommendation:** Default for quick prototyping

### Custom

- **Size:** Varies
- **Loading:** Depends on source (local vs URL)
- **Recommendation:** Cache files locally for repeated use

---

## Migration Guide

### From Fixed Generic to Pluggable

**Old code (still works):**
```python
from graph_mesh_core.meta_ontology import build_meta_graph
graph = build_meta_graph()
```

**New code (recommended):**
```python
from graph_mesh_core.meta_ontology_registry import MetaOntologyRegistry
provider = MetaOntologyRegistry.create({"type": "generic"})
graph = provider.build_graph()
```

**Manifest (backward compatible):**
```yaml
# Old manifests without meta_ontology field default to generic
name: my-pipeline
sources:
  - id: source1
    ...

# New manifests specify meta-ontology explicitly
name: my-pipeline
meta_ontology:
  type: fibo
  options: ...
sources:
  - id: source1
    ...
```

---

## FAQ

### Can I use multiple meta-ontologies in one pipeline?

Not directly in manifest, but via Python API using CompositeMetaOntology.

### Does changing meta-ontology affect existing mappings?

Yes - alignments are specific to the meta-ontology. Switching ontologies requires re-running alignment.

### Can I extend FIBO with custom concepts?

Yes, use CompositeMetaOntology to combine FIBO + custom provider.

### How do I know which FIBO modules to load?

Start with FND (foundations) + your domain module (LOAN for mortgages, SEC for securities, etc.).

### Is there a performance cost to pluggable ontologies?

Minimal. Provider overhead is small. FIBO is large but cached after first load.

---

## References

- [FIBO Ontology](https://spec.edmcouncil.org/fibo/)
- [OWL 2 Specification](https://www.w3.org/TR/owl2-overview/)
- [RDFLib Documentation](https://rdflib.readthedocs.io/)
- [ADR-006: Pluggable Meta-Ontology Architecture](./adr/adr-006-pluggable-meta-ontology.md)
