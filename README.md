# Graph-Mesh

Graph-Mesh is a federated semantic integration platform that continuously
fetches, ingests, aligns, and validates heterogeneous schemas into a unified
knowledge mesh. The repository is organized as a modular monorepo to support a
composable ontology CI/CD workflow.

## Repository Layout

```
├── autoschema/                 # Future AutoSchemaKG ingestion adapters
├── data_sources/               # Declarative YAML manifests and raw schemas
├── docker/                     # Container build contexts for matchers & orchestrator
├── docker-compose.yaml         # End-to-end pipeline orchestration
├── docs/                       # Architecture and usage documentation
├── graph_mesh_core/            # Meta-ontology definitions and reasoning utils
├── graph_mesh_ingest/          # Schema ingestion and conversion utilities
├── graph_mesh_aligner/         # Containerized matcher wrappers (LogMap, AML, BERTMap)
├── graph_mesh_orchestrator/    # Pipeline entry point
└── README.md
```

## Quickstart

1. **Configure data sources** by creating YAML manifests under `data_sources/`.
   A sample manifest (`sample_manifest.yaml`) demonstrates how to ingest a local
   XSD schema.
2. **Build matcher containers** and run the pipeline via Docker Compose:

   ```bash
   docker compose build
   docker compose run orchestrator /data_sources/sample_manifest.yaml
   ```

   Artifacts (meta-ontology, converted graphs, SSSOM mappings, merged ontology)
   will be emitted to the `artifacts/` directory.

3. **Inspect results** using your preferred triple store or RDF tooling. The
   orchestrator also exposes SSSOM mapping tables suitable for downstream
   analytics.

## Declarative Manifests

Each manifest describes a set of sources to ingest:

```yaml
name: finance-mesh
matchers:
  - LogMap
  - AML
sources:
  - id: regulatory-xsd
    fetch:
      type: local
      path: data_sources/schemas/regulatory.xsd
    convert:
      type: xsd
```

Additional fetch types (HTTP, S3, Git) and ingest converters (JSON Schema, CSV, SQL) can
be registered without modifying the orchestrator. The goal is to make Graph-Mesh
fully domain-agnostic and easily extendable.
