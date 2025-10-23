Graph-Mesh Documentation
========================

**Graph-Mesh** is a multi-source ontology alignment and knowledge graph fusion platform
that orchestrates the conversion, alignment, and fusion of heterogeneous data sources
into a unified knowledge graph.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   getting_started
   architecture
   user_guide
   api_reference
   development
   adr/index

Features
--------

* **Multi-Format Ingestion**: Convert XSD schemas and JSON schemas to OWL ontologies
* **Ontology Alignment**: Integrate multiple matchers (LogMap, AML, BERTMap)
* **Knowledge Graph Fusion**: Merge aligned ontologies into unified graphs
* **Container-Based Architecture**: Fully dockerized for reproducibility
* **Manifest-Driven Pipeline**: Declarative YAML configuration
* **Extensible Design**: Plugin architecture for custom converters and matchers

Quick Start
-----------

Installation
~~~~~~~~~~~~

.. code-block:: bash

   # Install from PyPI
   pip install graph-mesh

   # Or install from source
   git clone https://github.com/epieczko/graph-mesh.git
   cd graph-mesh
   pip install -e .

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from graph_mesh_orchestrator.pipeline import orchestrate

   # Run pipeline with a manifest
   orchestrate("data_sources/sample_manifest.yaml")

Docker Usage
~~~~~~~~~~~~

.. code-block:: bash

   # Build and run full pipeline
   docker compose up --build

   # Run with custom manifest
   docker compose run orchestrator python -m graph_mesh_orchestrator.pipeline /data_sources/my_manifest.yaml

Architecture Overview
--------------------

Graph-Mesh consists of four main components:

1. **graph_mesh_core**: Meta-ontology definitions and core utilities
2. **graph_mesh_ingest**: Schema-to-OWL conversion (XSD, JSON Schema)
3. **graph_mesh_aligner**: Ontology matching orchestration
4. **graph_mesh_orchestrator**: Pipeline coordination and execution

The pipeline follows a 5-stage process:

1. **Fetch**: Retrieve source schemas from various locations
2. **Convert**: Transform schemas to OWL ontologies
3. **Align**: Execute matchers to find correspondences
4. **Fuse**: Merge ontologies using alignment mappings
5. **Validate**: Verify output consistency and completeness

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
