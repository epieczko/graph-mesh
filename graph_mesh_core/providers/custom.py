"""Custom meta-ontology provider for loading arbitrary ontologies.

This provider allows loading any OWL ontology from a file or URL as the
meta-ontology for Graph-Mesh alignment.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from rdflib import Graph, Namespace, URIRef, RDF, OWL, RDFS

from graph_mesh_core.meta_ontology_base import (
    MetaOntologyInfo,
    MetaOntologyProvider,
)

LOGGER = logging.getLogger(__name__)


class CustomMetaOntology(MetaOntologyProvider):
    """Load a custom ontology from file or URL.

    This provider enables using any existing OWL ontology as the meta-ontology
    for schema alignment. Useful for domain-specific ontologies not provided
    as built-in providers.

    Args:
        source: Path to ontology file or HTTP(S) URL
        namespace: Base namespace URI for the ontology
        name: Optional human-readable name (default: derived from source)
        version: Optional version string (default: "custom")
        format: RDF serialization format (default: auto-detect)

    Example:
        >>> provider = CustomMetaOntology(
        ...     source="https://example.org/domain.owl",
        ...     namespace="https://example.org/domain#"
        ... )
        >>> graph = provider.build_graph()
    """

    def __init__(
        self,
        source: str,
        namespace: str,
        name: Optional[str] = None,
        version: str = "custom",
        format: Optional[str] = None,
    ):
        """Initialize custom ontology provider.

        Args:
            source: Path or URL to ontology file
            namespace: Base namespace URI
            name: Human-readable name (default: filename/URL)
            version: Version string
            format: RDF format (turtle, xml, n3, etc.) or None for auto-detect
        """
        self.source = source
        self.namespace_str = namespace
        self.name_str = name or self._derive_name(source)
        self.version_str = version
        self.format = format
        self._graph: Optional[Graph] = None
        self._namespace: Optional[Namespace] = None

    def _derive_name(self, source: str) -> str:
        """Derive a name from the source path/URL."""
        if source.startswith(("http://", "https://")):
            # Extract filename from URL
            return source.rstrip("/").split("/")[-1].replace(".owl", "").replace(".ttl", "")
        else:
            # Extract filename from path
            return Path(source).stem

    def get_info(self) -> MetaOntologyInfo:
        """Return metadata about the custom ontology.

        Returns:
            MetaOntologyInfo with name, version, namespace, and description.
        """
        description = f"Custom ontology loaded from {self.source}"
        return MetaOntologyInfo(
            name=self.name_str,
            version=self.version_str,
            namespace=self.namespace_str,
            description=description,
            source_url=self.source if self.source.startswith("http") else None,
        )

    def build_graph(self) -> Graph:
        """Load and return the ontology graph.

        Returns:
            rdflib.Graph loaded from the source.

        Raises:
            RuntimeError: If the ontology cannot be loaded.
        """
        if self._graph is not None:
            return self._graph

        graph = Graph()

        try:
            if self.source.startswith(("http://", "https://")):
                LOGGER.info("Loading custom ontology from URL: %s", self.source)
                graph.parse(self.source, format=self.format)
            else:
                source_path = Path(self.source)
                if not source_path.exists():
                    raise FileNotFoundError(f"Ontology file not found: {self.source}")

                LOGGER.info("Loading custom ontology from file: %s", self.source)
                graph.parse(str(source_path), format=self.format)

            LOGGER.info(
                "Loaded custom ontology: %d triples",
                len(graph)
            )

            self._graph = graph
            return graph

        except Exception as e:
            raise RuntimeError(
                f"Failed to load custom ontology from {self.source}: {e}"
            ) from e

    def get_alignment_targets(self) -> list[URIRef]:
        """Return list of OWL classes in the ontology.

        Extracts all classes (owl:Class) from the loaded ontology.

        Returns:
            List of URIRefs for all classes in the ontology.
        """
        graph = self.build_graph()

        # Find all OWL classes
        classes = []
        for subj in graph.subjects(RDF.type, OWL.Class):
            if isinstance(subj, URIRef):
                classes.append(subj)

        # Also check for RDFS classes
        for subj in graph.subjects(RDF.type, RDFS.Class):
            if isinstance(subj, URIRef) and subj not in classes:
                classes.append(subj)

        LOGGER.debug("Found %d alignment target classes", len(classes))
        return classes

    def get_namespace(self) -> Namespace:
        """Return the namespace for this ontology.

        Returns:
            rdflib.Namespace for the configured namespace URI.
        """
        if self._namespace is None:
            self._namespace = Namespace(self.namespace_str)
        return self._namespace

    def get_top_level_classes(self) -> list[URIRef]:
        """Return classes with no superclass (except owl:Thing).

        Returns:
            List of URIRefs for top-level classes.
        """
        graph = self.build_graph()
        all_classes = set(self.get_alignment_targets())

        # Find classes that are subclasses of something
        subclasses = set()
        for subj in graph.subjects(RDFS.subClassOf, None):
            if isinstance(subj, URIRef) and subj in all_classes:
                subclasses.add(subj)

        # Top-level classes are those not in subclasses set
        top_level = [cls for cls in all_classes if cls not in subclasses]

        LOGGER.debug("Found %d top-level classes", len(top_level))
        return top_level

    def get_properties(self) -> list[URIRef]:
        """Return all properties in the ontology.

        Returns:
            List of URIRefs for OWL properties.
        """
        graph = self.build_graph()
        properties = []

        # Object properties
        for subj in graph.subjects(RDF.type, OWL.ObjectProperty):
            if isinstance(subj, URIRef):
                properties.append(subj)

        # Datatype properties
        for subj in graph.subjects(RDF.type, OWL.DatatypeProperty):
            if isinstance(subj, URIRef) and subj not in properties:
                properties.append(subj)

        LOGGER.debug("Found %d properties", len(properties))
        return properties

    def get_description(self, concept_uri: URIRef) -> Optional[str]:
        """Get description for a concept from rdfs:comment.

        Args:
            concept_uri: URI of the concept

        Returns:
            Description string from rdfs:comment, or None if not found.
        """
        graph = self.build_graph()

        # Try rdfs:comment
        for comment in graph.objects(concept_uri, RDFS.comment):
            if comment:
                return str(comment)

        # Try rdfs:label as fallback
        for label in graph.objects(concept_uri, RDFS.label):
            if label:
                return str(label)

        return None
