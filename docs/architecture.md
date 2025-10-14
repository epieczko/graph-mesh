# Graph-Mesh Architecture

Graph-Mesh is structured as a modular monorepo to support a federated ontology
integration pipeline. The repository is split into four Python sub-packages and
supporting configuration directories:

- `graph-mesh-core`: meta-ontology definitions and shared reasoning utilities.
- `graph-mesh-converters`: conversion templates for XSD, JSON Schema, CSV, and
  other structured sources. The initial scaffold provides an XSD placeholder
  that can be expanded with additional converters.
- `graph-mesh-aligner`: orchestration of LogMap, AML, and BERTMap matchers via
  containerized runners.
- `graph-mesh-orchestrator`: the high-level pipeline that ties fetching,
  conversion, alignment, fusion, and validation together.
- `data_sources`: declarative YAML manifests describing how to ingest new
  schemas along with sample schema assets.
- `docker`: container definitions for the external matcher engines.
- `autoschema`: reserved for future AutoSchemaKG integrations.

The orchestrator consumes manifests to drive the end-to-end process:

1. **Fetch** schema assets from local or remote storage.
2. **Convert** them into OWL/RDF via configured converters.
3. **Align** against the meta-ontology using containerized matchers.
4. **Fuse** converted graphs into a unified mesh.
5. **Validate** and expose artifacts (merged ontology, SSSOM mappings, logs).

Docker Compose coordinates the containers so that the entire pipeline can be
executed with a single command. Artifacts are stored in the `artifacts/` folder
and can be uploaded as CI outputs or loaded into a local triplestore.
