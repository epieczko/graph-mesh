"""Composite meta-ontology provider for combining multiple ontologies.

This provider allows merging multiple meta-ontology providers into a single
unified ontology graph.
"""

from __future__ import annotations

import logging
from typing import Optional

from rdflib import Graph, Namespace, URIRef

from graph_mesh_core.meta_ontology_base import (
    MetaOntologyInfo,
    MetaOntologyProvider,
)

LOGGER = logging.getLogger(__name__)


class CompositeMetaOntology(MetaOntologyProvider):
    """Combine multiple meta-ontology providers.

    This provider merges graphs from multiple providers into a single unified
    meta-ontology. Useful for:
    - Combining domain ontologies (e.g., FIBO + custom extensions)
    - Mixing generic and domain-specific concepts
    - Multi-domain projects requiring multiple semantic backbones

    Args:
        providers: List of MetaOntologyProvider instances to combine
        name: Optional custom name for the composite ontology
        namespace: Optional custom namespace (default: first provider's namespace)

    Example:
        >>> from graph_mesh_core.providers.generic import GenericMetaOntology
        >>> from graph_mesh_core.providers.fibo import FIBOMetaOntology
        >>>
        >>> generic = GenericMetaOntology()
        >>> fibo = FIBOMetaOntology(modules=["FND"])
        >>>
        >>> composite = CompositeMetaOntology(
        ...     providers=[fibo, generic],
        ...     name="FIBO+Generic"
        ... )
        >>> graph = composite.build_graph()
    """

    def __init__(
        self,
        providers: list[MetaOntologyProvider],
        name: Optional[str] = None,
        namespace: Optional[str] = None,
    ):
        """Initialize composite provider.

        Args:
            providers: List of providers to combine (at least 1 required)
            name: Custom name for composite ontology
            namespace: Custom namespace URI

        Raises:
            ValueError: If providers list is empty
        """
        if not providers:
            raise ValueError("At least one provider must be specified for composite ontology")

        self.providers = providers
        self.name_str = name
        self.namespace_str = namespace

        # Use first provider's namespace if not specified
        if self.namespace_str is None:
            first_provider_info = self.providers[0].get_info()
            self.namespace_str = first_provider_info.namespace

        self._graph: Optional[Graph] = None
        self._namespace: Optional[Namespace] = None

        LOGGER.info(
            "Initialized composite ontology with %d providers",
            len(self.providers)
        )

    def get_info(self) -> MetaOntologyInfo:
        """Return metadata about the composite ontology.

        Returns:
            MetaOntologyInfo combining info from all providers.
        """
        if self.name_str:
            name = self.name_str
        else:
            # Construct name from providers
            provider_names = [p.get_info().name for p in self.providers]
            name = " + ".join(provider_names)

        # Combine descriptions
        descriptions = []
        for provider in self.providers:
            info = provider.get_info()
            descriptions.append(f"{info.name}: {info.description}")

        combined_description = "; ".join(descriptions)

        # Use latest version from providers
        versions = [p.get_info().version for p in self.providers]
        version = f"composite-{'-'.join(versions)}"

        return MetaOntologyInfo(
            name=name,
            version=version,
            namespace=self.namespace_str,
            description=f"Composite ontology combining: {combined_description}",
            source_url=None,
        )

    def build_graph(self) -> Graph:
        """Build the composite graph by merging all provider graphs.

        Returns:
            rdflib.Graph containing merged ontologies from all providers.

        Raises:
            RuntimeError: If any provider fails to build its graph.
        """
        if self._graph is not None:
            return self._graph

        LOGGER.info("Building composite graph from %d providers", len(self.providers))

        combined = Graph()

        for i, provider in enumerate(self.providers, 1):
            try:
                provider_info = provider.get_info()
                LOGGER.info(
                    "Merging provider %d/%d: %s",
                    i,
                    len(self.providers),
                    provider_info.name
                )

                provider_graph = provider.build_graph()
                triples_before = len(combined)

                # Merge graphs
                combined += provider_graph

                triples_added = len(combined) - triples_before
                LOGGER.info(
                    "Merged %s: added %d triples (total: %d)",
                    provider_info.name,
                    triples_added,
                    len(combined)
                )

            except Exception as e:
                provider_info = provider.get_info()
                LOGGER.error(
                    "Failed to merge provider %s: %s",
                    provider_info.name,
                    e
                )
                raise RuntimeError(
                    f"Failed to build graph from provider {provider_info.name}"
                ) from e

        self._graph = combined
        LOGGER.info("Composite graph complete: %d total triples", len(combined))

        return combined

    def get_alignment_targets(self) -> list[URIRef]:
        """Return alignment targets from all providers.

        Combines and deduplicates alignment targets from all constituent providers.

        Returns:
            List of URIRefs from all providers (deduplicated).
        """
        all_targets = []
        seen = set()

        for provider in self.providers:
            provider_info = provider.get_info()
            targets = provider.get_alignment_targets()

            for target in targets:
                if target not in seen:
                    all_targets.append(target)
                    seen.add(target)

            LOGGER.debug(
                "Provider %s contributed %d unique targets",
                provider_info.name,
                len([t for t in targets if t in seen])
            )

        LOGGER.info(
            "Composite ontology has %d total alignment targets",
            len(all_targets)
        )

        return all_targets

    def get_namespace(self) -> Namespace:
        """Return the namespace for this composite ontology.

        Returns:
            rdflib.Namespace for the configured namespace URI.
        """
        if self._namespace is None:
            self._namespace = Namespace(self.namespace_str)
        return self._namespace

    def get_top_level_classes(self) -> list[URIRef]:
        """Return top-level classes from all providers.

        Returns:
            List of URIRefs for top-level classes (deduplicated).
        """
        all_classes = []
        seen = set()

        for provider in self.providers:
            classes = provider.get_top_level_classes()
            for cls in classes:
                if cls not in seen:
                    all_classes.append(cls)
                    seen.add(cls)

        return all_classes

    def get_properties(self) -> list[URIRef]:
        """Return properties from all providers.

        Returns:
            List of URIRefs for properties (deduplicated).
        """
        all_properties = []
        seen = set()

        for provider in self.providers:
            properties = provider.get_properties()
            for prop in properties:
                if prop not in seen:
                    all_properties.append(prop)
                    seen.add(prop)

        return all_properties

    def get_description(self, concept_uri: URIRef) -> Optional[str]:
        """Get description for a concept from any provider.

        Checks all providers in order until a description is found.

        Args:
            concept_uri: URI of the concept

        Returns:
            Description from first provider that has one, or None.
        """
        for provider in self.providers:
            description = provider.get_description(concept_uri)
            if description:
                return description

        return None

    def validate_alignment(self, source_uri: URIRef, target_uri: URIRef) -> bool:
        """Validate alignment against any provider.

        Alignment is valid if any constituent provider validates it.

        Args:
            source_uri: External schema concept
            target_uri: Target concept in composite ontology

        Returns:
            True if any provider validates the alignment, False otherwise.
        """
        for provider in self.providers:
            if provider.validate_alignment(source_uri, target_uri):
                return True

        return False
