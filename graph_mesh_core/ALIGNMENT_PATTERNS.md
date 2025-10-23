# Ontology Alignment Patterns for Graph-Mesh

This document describes the alignment patterns used in Graph-Mesh to integrate domain-specific ontologies with standard upper ontologies (BFO and DOLCE).

## Table of Contents

1. [Overview](#overview)
2. [Upper Ontologies](#upper-ontologies)
3. [Alignment Strategy](#alignment-strategy)
4. [Meta-Ontology to BFO Mappings](#meta-ontology-to-bfo-mappings)
5. [Meta-Ontology to DOLCE Mappings](#meta-ontology-to-dolce-mappings)
6. [Usage Examples](#usage-examples)
7. [Best Practices](#best-practices)

## Overview

Graph-Mesh provides a meta-ontology that serves as a semantic backbone for integrating heterogeneous domain schemas. To enable interoperability with existing semantic web resources, we align our meta-ontology with two prominent upper ontologies:

- **BFO (Basic Formal Ontology)**: A top-level ontology designed for scientific domains
- **DOLCE (Descriptive Ontology for Linguistic and Cognitive Engineering)**: An ontology focused on cognitive and linguistic aspects

## Upper Ontologies

### BFO (Basic Formal Ontology)

BFO is a small, upper-level ontology designed for use in supporting information retrieval, analysis, and integration in scientific and other domains.

**Key Concepts:**
- **Entity (BFO_0000001)**: The root of all entities
- **Continuant (BFO_0000002)**: Entities that persist through time (objects, qualities)
- **Occurrent (BFO_0000003)**: Entities that happen or occur in time (processes, events)
- **Independent Continuant (BFO_0000004)**: Objects that exist independently
- **Generically Dependent Continuant (BFO_0000031)**: Information content entities

**Resources:**
- Website: https://basic-formal-ontology.org/
- OBO: http://purl.obolibrary.org/obo/bfo.owl

### DOLCE (Descriptive Ontology for Linguistic and Cognitive Engineering)

DOLCE is an ontology that focuses on modeling cognitive categories underlying natural language and human common sense.

**Key Concepts:**
- **Particular**: Concrete entities (individuals)
- **Endurant**: Entities that persist through time with all their parts
- **Perdurant**: Events and processes
- **Quality**: Properties of endurants
- **Agentive Physical Object**: Objects capable of agency
- **Social Object**: Institutional/normative entities

**Resources:**
- Website: http://www.loa.istc.cnr.it/dolce/overview.html

## Alignment Strategy

Graph-Mesh uses **SKOS mapping properties** to express alignments:

- **skos:exactMatch**: The two concepts are equivalent
- **skos:closeMatch**: The concepts are closely related but not identical
- **skos:broadMatch**: The upper ontology concept is broader/more general
- **skos:narrowMatch**: The upper ontology concept is more specific

Each alignment includes:
1. Source meta-class
2. Target upper ontology concept
3. Mapping relation type (exactMatch, closeMatch, etc.)
4. Textual justification explaining the alignment

## Meta-Ontology to BFO Mappings

| Meta-Class | BFO Concept | Relation | Justification |
|------------|-------------|----------|---------------|
| Entity | BFO:Entity (BFO_0000001) | broadMatch | Graph-Mesh Entity is a broad category aligned with BFO's root Entity |
| Agent | BFO:Independent Continuant (BFO_0000004) | closeMatch | Agents are independent continuants that can act and persist through time |
| Event | BFO:Occurrent (BFO_0000003) | exactMatch | Events are occurrents - things that happen in time |
| Location | BFO:Site (BFO_0000029) | closeMatch | Locations align with BFO's Site concept - spatial regions |
| Contract | BFO:Generically Dependent Continuant (BFO_0000031) | closeMatch | Contracts are information artifacts |
| Regulation | BFO:Generically Dependent Continuant (BFO_0000031) | closeMatch | Regulations are information artifacts |
| Metric | BFO:Generically Dependent Continuant (BFO_0000031) | closeMatch | Metrics are information content |

### BFO Alignment Rationale

**Entity → BFO:Entity (broadMatch)**
- Graph-Mesh's Entity is a top-level category designed to be domain-agnostic
- It encompasses both continuants and occurrents
- broadMatch indicates that BFO:Entity is a broader categorization

**Agent → BFO:Independent Continuant (closeMatch)**
- Agents in Graph-Mesh can be people, organizations, or systems
- They persist through time and exist independently
- Close but not exact due to Graph-Mesh's focus on active capability

**Event → BFO:Occurrent (exactMatch)**
- Direct correspondence: both represent temporal occurrences
- Events have temporal parts and happen in time

**Location → BFO:Site (closeMatch)**
- BFO:Site represents spatial regions at which processes occur
- Graph-Mesh Location includes jurisdictional/administrative aspects

**Contract, Regulation, Metric → BFO:Generically Dependent Continuant (closeMatch)**
- These are information entities that depend on physical bearers
- They represent different types of normative/measurement content

## Meta-Ontology to DOLCE Mappings

| Meta-Class | DOLCE Concept | Relation | Justification |
|------------|---------------|----------|---------------|
| Entity | DOLCE:Particular | broadMatch | Graph-Mesh Entity corresponds to DOLCE's particular (concrete entity) |
| Agent | DOLCE:Agentive Physical Object | exactMatch | Agents are agentive physical objects capable of intentional action |
| Event | DOLCE:Perdurant | exactMatch | Events are perdurants - things that happen over time |
| Location | DOLCE:Physical Region | closeMatch | Locations correspond to physical regions in DOLCE |
| Contract | DOLCE:Social Object | exactMatch | Contracts are social objects - agreements with normative force |
| Regulation | DOLCE:Social Object | exactMatch | Regulations are social objects with normative/prescriptive content |
| Metric | DOLCE:Quality | closeMatch | Metrics represent qualities or measurements of entities |

### DOLCE Alignment Rationale

**Entity → DOLCE:Particular (broadMatch)**
- DOLCE:Particular represents concrete, specific entities
- Graph-Mesh Entity is more abstract and includes various categories

**Agent → DOLCE:Agentive Physical Object (exactMatch)**
- Strong alignment: both represent entities capable of intentional action
- DOLCE's notion of agency matches Graph-Mesh's agent concept

**Event → DOLCE:Perdurant (exactMatch)**
- Direct correspondence: both represent occurrences in time
- Perdurants have temporal parts, just like Graph-Mesh events

**Location → DOLCE:Physical Region (closeMatch)**
- Spatial regions in DOLCE correspond to locations
- Graph-Mesh includes non-physical locations (jurisdictions)

**Contract, Regulation → DOLCE:Social Object (exactMatch)**
- Excellent match: social objects in DOLCE have normative/institutional nature
- Contracts and regulations are paradigmatic social objects

**Metric → DOLCE:Quality (closeMatch)**
- Qualities in DOLCE are properties of endurants
- Metrics measure or quantify these qualities

## Usage Examples

### Example 1: Building an Aligned Ontology

```python
from graph_mesh_core.meta_ontology import build_meta_graph
from graph_mesh_core.upper_ontology import (
    merge_with_upper_ontology,
    UpperOntologyType
)

# Build base meta-ontology
graph = build_meta_graph()

# Add BFO alignments
graph = merge_with_upper_ontology(graph, UpperOntologyType.BFO)

# Serialize with alignments
graph.serialize("meta_ontology_with_bfo.ttl", format="turtle")
```

### Example 2: Querying Alignments

```python
from graph_mesh_core.upper_ontology import (
    get_alignments_for_class,
    get_alignment_summary,
    UpperOntologyType
)

# Get all alignments for the Agent class
agent_alignments = get_alignments_for_class("Agent")

for alignment in agent_alignments:
    print(f"{alignment.meta_class_name} → {alignment.upper_class_uri}")
    print(f"  Type: {alignment.alignment_type}")
    print(f"  Justification: {alignment.justification}\n")

# Get summary of all alignments
summary = get_alignment_summary()
for meta_class, alignments in summary.items():
    print(f"{meta_class}:")
    print(f"  BFO: {alignments['BFO']}")
    print(f"  DOLCE: {alignments['DOLCE']}\n")
```

### Example 3: Validation with Alignment

```python
from graph_mesh_core.meta_ontology import build_meta_graph
from graph_mesh_core.upper_ontology import build_alignment_graph
from graph_mesh_core.validation import validate_ontology, OWLProfile

# Build ontology with alignments
graph = build_meta_graph()
alignment_graph = build_alignment_graph()

# Merge graphs
for triple in alignment_graph:
    graph.add(triple)

# Validate
result = validate_ontology(graph, profile=OWLProfile.DL)

if result.is_valid:
    print("Ontology is valid!")
else:
    print("Validation errors:")
    for error in result.errors:
        print(f"  - {error.message}")
```

### Example 4: Reasoning with Alignments

```python
from graph_mesh_core.meta_ontology import build_meta_graph, GM
from graph_mesh_core.reasoning import (
    is_subclass_of,
    get_superclasses,
    print_class_hierarchy
)

graph = build_meta_graph()

# Check subsumption
from rdflib import URIRef

agent_uri = GM["Agent"]
entity_uri = GM["Entity"]

if is_subclass_of(graph, agent_uri, entity_uri):
    print("Agent is a subclass of Entity")

# Get all superclasses of Agent
superclasses = get_superclasses(graph, agent_uri)
print(f"Agent superclasses: {superclasses}")

# Print hierarchy
print("\nClass Hierarchy:")
print(print_class_hierarchy(graph, namespace=GM))
```

## Best Practices

### 1. Use Appropriate Mapping Relations

- **exactMatch**: Only when concepts are truly equivalent in meaning and scope
- **closeMatch**: When concepts are very similar but have slight differences
- **broadMatch/narrowMatch**: When there's a clear generalization/specialization relationship

### 2. Document Alignments

Always provide clear justifications for alignments:
- Explain semantic similarities
- Note any differences or caveats
- Reference definitions from both ontologies

### 3. Validate After Alignment

```python
from graph_mesh_core.validation import validate_ontology

result = validate_ontology(aligned_graph)
if not result.is_valid:
    # Handle validation errors
    pass
```

### 4. Consider Multiple Upper Ontologies

Different upper ontologies serve different purposes:
- Use **BFO** for scientific/biomedical domains
- Use **DOLCE** for cognitive/linguistic applications
- Can align with both for maximum interoperability

### 5. Maintain Alignment Metadata

Track:
- Who created the alignment
- When it was created
- Confidence level
- Sources/references used

### 6. Test Reasoning

After adding alignments, test that:
- Inferences are correct
- No inconsistencies are introduced
- Query performance is acceptable

```python
from graph_mesh_core.validation import check_consistency

consistency = check_consistency(aligned_graph)
if not consistency.is_consistent:
    print("Inconsistency detected!")
```

### 7. Update Alignments

Upper ontologies evolve:
- Monitor for new versions
- Review and update alignments periodically
- Document changes

## Advanced Patterns

### Pattern 1: Multi-Inheritance Alignment

When a meta-class aligns with multiple upper ontology concepts:

```python
AlignmentMapping(
    "Event",
    UpperOntologyType.BFO,
    "http://purl.obolibrary.org/obo/BFO_0000003",  # Occurrent
    "exactMatch",
    "Primary alignment: Events are occurrents"
)

# Could also relate to Process if needed
```

### Pattern 2: Context-Dependent Alignment

Different domains may require different interpretations:

```python
# In biomedical context
align_to_bfo(domain_ontology)

# In legal/administrative context
align_to_dolce(domain_ontology)
```

### Pattern 3: Hierarchical Alignment Propagation

When aligning class hierarchies:
1. Align top-level classes first
2. Ensure child alignments are consistent with parent alignments
3. Validate that alignment doesn't violate subsumption

### Pattern 4: Property Alignment

Align meta-properties to upper ontology relations:

```python
# Example: participatesIn could align to BFO:participates_in
# This is future work for Graph-Mesh
```

## References

1. **BFO 2.0 Specification**: https://basic-formal-ontology.org/bfo-2-reference.pdf
2. **DOLCE Documentation**: http://www.loa.istc.cnr.it/dolce/dolce-owl/
3. **SKOS Reference**: https://www.w3.org/TR/skos-reference/
4. **Ontology Alignment Evaluation Initiative**: http://oaei.ontologymatching.org/

## Future Work

- Align meta-properties to upper ontology relations
- Add alignments to other upper ontologies (SUMO, Cyc)
- Automated alignment suggestion using ML
- Confidence scoring for alignments
- Provenance tracking for alignment decisions
