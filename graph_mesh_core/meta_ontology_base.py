"""Abstract base classes and interfaces for pluggable meta-ontology providers.

This module defines the contract that all meta-ontology providers must implement,
enabling Graph-Mesh to work with different domain ontologies (FIBO, SNOMED, custom, etc.)
while maintaining a consistent interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from rdflib import Graph, Namespace, URIRef


@dataclass(frozen=True)
class MetaOntologyInfo:
    """Metadata about a meta-ontology provider.

    Attributes:
        name: Human-readable name of the ontology (e.g., "FIBO", "Generic")
        version: Version string (e.g., "1.0", "Q4-2024")
        namespace: Base namespace URI for the ontology
        description: Brief description of the ontology's purpose and scope
        source_url: Optional URL to the ontology source or documentation
    """

    name: str
    version: str
    namespace: str
    description: str
    source_url: Optional[str] = None


class MetaOntologyProvider(ABC):
    """Abstract interface for pluggable meta-ontology providers.

    A meta-ontology provider serves as a semantic backbone for aligning
    heterogeneous schemas. Different domains benefit from different meta-ontologies:

    - Financial services: FIBO (Financial Industry Business Ontology)
    - Healthcare: SNOMED CT, HL7 FHIR
    - Manufacturing: ISA-95, DEXPI
    - Generic: Simple domain-agnostic ontology

    Implementations must provide:
    1. Ontology metadata (name, version, namespace)
    2. RDF graph construction
    3. Alignment targets (classes/concepts available for mapping)
    4. Namespace access
    5. Alignment validation logic

    Example:
        >>> from graph_mesh_core.meta_ontology_registry import MetaOntologyRegistry
        >>> provider = MetaOntologyRegistry.create({"type": "fibo", "options": {"modules": ["FND"]}})
        >>> graph = provider.build_graph()
        >>> info = provider.get_info()
        >>> print(f"Using {info.name} v{info.version}")
    """

    @abstractmethod
    def get_info(self) -> MetaOntologyInfo:
        """Return metadata about this meta-ontology.

        Returns:
            MetaOntologyInfo containing name, version, namespace, description, and optional source URL.
        """
        pass

    @abstractmethod
    def build_graph(self) -> Graph:
        """Build and return the complete RDF graph for this meta-ontology.

        This method should construct the ontology graph including:
        - Class definitions (owl:Class)
        - Property definitions (owl:ObjectProperty, owl:DatatypeProperty)
        - Class hierarchies (rdfs:subClassOf)
        - Property hierarchies (rdfs:subPropertyOf)
        - Annotations (rdfs:label, rdfs:comment, etc.)

        The graph should be fully constructed and ready for use in alignment.

        Returns:
            rdflib.Graph containing the complete ontology.

        Raises:
            RuntimeError: If the ontology cannot be constructed (e.g., remote source unavailable).
        """
        pass

    @abstractmethod
    def get_alignment_targets(self) -> list[URIRef]:
        """Return list of key classes/concepts available for alignment.

        These are the primary concepts that external schemas should align to.
        For large ontologies (e.g., FIBO with 1500+ classes), this returns
        the most important/commonly-used classes rather than exhaustive listing.

        Returns:
            List of URIRefs representing alignable concepts.

        Example:
            For FIBO, might return:
            [
                URIRef("https://spec.edmcouncil.org/fibo/ontology/LOAN/.../Loan"),
                URIRef("https://spec.edmcouncil.org/fibo/ontology/FND/.../Contract"),
                ...
            ]
        """
        pass

    @abstractmethod
    def get_namespace(self) -> Namespace:
        """Return the primary namespace for this ontology.

        Returns:
            rdflib.Namespace that can be used for URI construction.

        Example:
            >>> ns = provider.get_namespace()
            >>> loan_concept = ns["Loan"]  # Creates URIRef
        """
        pass

    def validate_alignment(self, source_uri: URIRef, target_uri: URIRef) -> bool:
        """Validate if an alignment to this ontology is semantically valid.

        Optional method that providers can override to implement domain-specific
        validation logic. Default implementation always returns True.

        Args:
            source_uri: URI of the concept being aligned (from external schema)
            target_uri: URI of the target concept in this meta-ontology

        Returns:
            True if the alignment is valid, False otherwise.

        Example:
            A FIBO provider might reject alignments where source_uri is a datatype
            property but target_uri is a class.
        """
        return True

    def get_top_level_classes(self) -> list[URIRef]:
        """Return top-level classes in the ontology hierarchy.

        Optional convenience method for providers to expose root concepts.
        Default implementation returns empty list.

        Returns:
            List of URIRefs representing top-level classes (no parent except owl:Thing).
        """
        return []

    def get_properties(self) -> list[URIRef]:
        """Return list of properties defined in this ontology.

        Optional convenience method for providers to expose properties.
        Default implementation returns empty list.

        Returns:
            List of URIRefs representing object and datatype properties.
        """
        return []

    def get_description(self, concept_uri: URIRef) -> Optional[str]:
        """Return human-readable description for a concept.

        Optional convenience method for providers to expose concept descriptions.
        Default implementation returns None.

        Args:
            concept_uri: URI of the concept to describe

        Returns:
            Description string (typically from rdfs:comment), or None if unavailable.
        """
        return None
