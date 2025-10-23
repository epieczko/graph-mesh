# Architecture

Graph-Mesh is built as a modular, container-based platform for ontology alignment and knowledge graph fusion.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Orchestrator                            │
│  (Pipeline Coordinator & Execution Engine)                  │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Ingest     │  │   Aligner    │  │     Core     │
│  Converters  │  │   Matchers   │  │ Meta-Ontology│
└──────────────┘  └──────────────┘  └──────────────┘
```

## Components

### 1. Core (`graph_mesh_core`)

**Purpose**: Foundation layer providing meta-ontology and shared utilities

**Key Files**:
- `meta_ontology.py`: Defines 7 core meta-classes (Entity, Agent, Contract, Event, Location, Regulation, Metric)

**Responsibilities**:
- Meta-ontology graph construction
- Common RDF/OWL utilities
- Namespace management

### 2. Ingest (`graph_mesh_ingest`)

**Purpose**: Convert heterogeneous schemas to OWL ontologies

**Supported Formats**:
- XSD (XML Schema)
- JSON Schema

**Key Files**:
- `xsd_to_owl.py`: Namespace-aware XSD conversion with deep traversal
- `json_to_owl.py`: JSON Schema to OWL mapping

**Conversion Strategy**:
- Preserve source namespaces
- Map primitive types to XSD datatypes
- Convert complex types to OWL classes
- Transform elements/properties to OWL properties

### 3. Aligner (`graph_mesh_aligner`)

**Purpose**: Orchestrate ontology matching using containerized matchers

**Supported Matchers**:
- **LogMap**: Logic-based matcher with inconsistency repair
- **AML**: Agreementmaker Light - hybrid matcher
- **BERTMap**: BERT-based semantic matcher

**Key Files**:
- `matchers.py`: Container-based matcher wrapper

**Output Format**: SSSOM (Simple Standard for Sharing Ontology Mappings)

### 4. Orchestrator (`graph_mesh_orchestrator`)

**Purpose**: Coordinate end-to-end pipeline execution

**Key Files**:
- `pipeline.py`: Main orchestration logic and CLI
- `ingest.py`: Ingest stage coordination

**Pipeline Stages**:

#### Stage 1: Fetch
Retrieve source schemas from:
- Local file system
- Remote URLs (future)
- Git repositories (future)

#### Stage 2: Convert
Transform schemas to OWL using registered converters

#### Stage 3: Align
Execute matchers to find correspondences between ontologies

#### Stage 4: Fuse
Merge ontologies using alignment mappings

#### Stage 5: Validate
Verify output consistency (future enhancement)

## Data Flow

```
Manifest (YAML)
    │
    ▼
┌──────────────┐
│   Fetch      │ → Raw schemas (XSD, JSON)
└──────────────┘
    │
    ▼
┌──────────────┐
│  Convert     │ → Individual OWL graphs
└──────────────┘
    │
    ▼
┌──────────────┐
│   Align      │ → SSSOM mappings
└──────────────┘
    │
    ▼
┌──────────────┐
│    Fuse      │ → Merged knowledge graph
└──────────────┘
    │
    ▼
┌──────────────┐
│  Validate    │ → Validated ontology
└──────────────┘
```

## Container Architecture

Each matcher runs in an isolated Docker container:

```yaml
services:
  logmap:
    image: graph-mesh/logmap
    volumes:
      - ./artifacts:/artifacts

  orchestrator:
    image: graph-mesh/orchestrator
    depends_on:
      - logmap
      - aml
      - bertmap
    volumes:
      - ./artifacts:/artifacts
      - /var/run/docker.sock:/var/run/docker.sock
```

The orchestrator communicates with matchers via:
- Shared volume (`artifacts/`)
- Docker API (for lifecycle management)

## Design Principles

1. **Modularity**: Clear separation of concerns between components
2. **Extensibility**: Plugin architecture for converters and matchers
3. **Reproducibility**: Full containerization with version pinning
4. **Declarative Configuration**: YAML manifests for pipeline definition
5. **Standard Formats**: Use of W3C standards (OWL, RDF) and SSSOM

## Technology Stack

- **Language**: Python 3.9+
- **RDF/OWL**: RDFLib, OWLReady2
- **Schema Parsing**: xmlschema (XSD), JSON Schema validators
- **Containerization**: Docker, Docker Compose
- **Mapping Format**: SSSOM (sssom-py)
- **Data Manipulation**: Pandas

## Scalability Considerations

- **Parallel Matching**: Multiple matchers execute concurrently
- **Streaming Processing**: Large graphs processed incrementally (future)
- **Distributed Execution**: Kubernetes support (future)
- **Caching**: Intermediate results cached for reuse (future)
