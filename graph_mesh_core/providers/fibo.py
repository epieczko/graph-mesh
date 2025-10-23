"""FIBO (Financial Industry Business Ontology) meta-ontology provider.

This provider loads FIBO ontology modules as the semantic backbone for
financial services schema integration.
"""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path
from typing import Optional

from rdflib import Graph, Namespace, URIRef, RDF, OWL, RDFS

from graph_mesh_core.meta_ontology_base import (
    MetaOntologyInfo,
    MetaOntologyProvider,
)

LOGGER = logging.getLogger(__name__)

# FIBO namespace base
FIBO_BASE = "https://spec.edmcouncil.org/fibo/ontology/"

# FIBO module information
FIBO_MODULES = {
    "FND": {
        "name": "Foundations",
        "description": "Core concepts: Parties, Agreements, Accounting, Law",
        "url": f"{FIBO_BASE}FND/FND.rdf",
    },
    "BE": {
        "name": "Business Entities",
        "description": "Organizations, Corporations, Legal Entities",
        "url": f"{FIBO_BASE}BE/BE.rdf",
    },
    "FBC": {
        "name": "Financial Business and Commerce",
        "description": "Financial Services, Banking, Products",
        "url": f"{FIBO_BASE}FBC/FBC.rdf",
    },
    "LOAN": {
        "name": "Loans",
        "description": "Loan products, Mortgages, Credit Facilities",
        "url": f"{FIBO_BASE}LOAN/LOAN.rdf",
    },
    "SEC": {
        "name": "Securities",
        "description": "Equity, Debt, Derivatives",
        "url": f"{FIBO_BASE}SEC/SEC.rdf",
    },
    "IND": {
        "name": "Indicators and Indexes",
        "description": "Economic Indicators, Market Indices, Interest Rates",
        "url": f"{FIBO_BASE}IND/IND.rdf",
    },
    "DER": {
        "name": "Derivatives",
        "description": "Derivatives, Options, Swaps",
        "url": f"{FIBO_BASE}DER/DER.rdf",
    },
}


class FIBOMetaOntology(MetaOntologyProvider):
    """FIBO ontology provider for financial services integration.

    FIBO (Financial Industry Business Ontology) is the industry-standard ontology
    for financial services, maintained by the EDM Council. It contains ~1500 classes
    covering financial instruments, parties, contracts, regulations, and more.

    Args:
        modules: List of FIBO modules to load (default: ["FND", "LOAN"])
        cache_dir: Directory to cache downloaded FIBO files (default: ~/.graph-mesh/fibo)
        use_cache: Whether to use cached files if available (default: True)
        version: FIBO version tag (default: "latest")

    Available modules:
        - FND: Foundations (core concepts)
        - BE: Business Entities
        - FBC: Financial Business and Commerce
        - LOAN: Loans and Mortgages
        - SEC: Securities
        - IND: Indicators and Indexes
        - DER: Derivatives

    Example:
        >>> # Load only core and loan modules
        >>> provider = FIBOMetaOntology(modules=["FND", "LOAN"])
        >>> graph = provider.build_graph()
        >>>
        >>> # Load all modules
        >>> provider = FIBOMetaOntology(modules=list(FIBO_MODULES.keys()))
        >>> graph = provider.build_graph()
    """

    def __init__(
        self,
        modules: Optional[list[str]] = None,
        cache_dir: Optional[str] = None,
        use_cache: bool = True,
        version: str = "latest",
    ):
        """Initialize FIBO ontology provider.

        Args:
            modules: FIBO modules to load (default: FND, LOAN)
            cache_dir: Cache directory path
            use_cache: Use cached files
            version: FIBO version
        """
        self.modules = modules or ["FND", "LOAN"]
        self.version = version
        self.use_cache = use_cache

        # Validate modules
        invalid = set(self.modules) - set(FIBO_MODULES.keys())
        if invalid:
            raise ValueError(
                f"Invalid FIBO modules: {invalid}. "
                f"Valid modules: {list(FIBO_MODULES.keys())}"
            )

        # Set up cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path.home() / ".graph-mesh" / "fibo" / version

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._graph: Optional[Graph] = None
        self._namespace: Optional[Namespace] = None

        LOGGER.info(
            "Initialized FIBO provider with modules: %s (cache: %s)",
            ", ".join(self.modules),
            self.cache_dir,
        )

    def get_info(self) -> MetaOntologyInfo:
        """Return metadata about FIBO.

        Returns:
            MetaOntologyInfo with FIBO details.
        """
        modules_str = ", ".join([FIBO_MODULES[m]["name"] for m in self.modules])
        return MetaOntologyInfo(
            name="FIBO",
            version=self.version,
            namespace=FIBO_BASE,
            description=f"Financial Industry Business Ontology ({modules_str})",
            source_url="https://spec.edmcouncil.org/fibo/",
        )

    def _download_module(self, module: str) -> Path:
        """Download a FIBO module to cache.

        Args:
            module: Module code (e.g., "FND")

        Returns:
            Path to cached module file.
        """
        module_info = FIBO_MODULES[module]
        cache_file = self.cache_dir / f"{module}.rdf"

        if self.use_cache and cache_file.exists():
            LOGGER.debug("Using cached FIBO module: %s", module)
            return cache_file

        LOGGER.info("Downloading FIBO module: %s from %s", module, module_info["url"])

        try:
            # Download with timeout
            with urllib.request.urlopen(module_info["url"], timeout=60) as response:
                content = response.read()

            # Write to cache
            cache_file.write_bytes(content)
            LOGGER.info("Cached FIBO module: %s (%d bytes)", module, len(content))

            return cache_file

        except Exception as e:
            raise RuntimeError(
                f"Failed to download FIBO module {module} from {module_info['url']}: {e}"
            ) from e

    def build_graph(self) -> Graph:
        """Build the FIBO ontology graph.

        Downloads (if needed) and merges the specified FIBO modules into
        a single RDF graph.

        Returns:
            rdflib.Graph containing merged FIBO modules.

        Raises:
            RuntimeError: If modules cannot be loaded.
        """
        if self._graph is not None:
            return self._graph

        graph = Graph()
        graph.bind("fibo", Namespace(FIBO_BASE))

        for module in self.modules:
            try:
                module_file = self._download_module(module)
                LOGGER.info("Parsing FIBO module: %s", module)

                module_graph = Graph()
                module_graph.parse(str(module_file), format="xml")

                # Merge into main graph
                graph += module_graph

                LOGGER.info(
                    "Loaded FIBO %s: %d triples (total: %d)",
                    module,
                    len(module_graph),
                    len(graph),
                )

            except Exception as e:
                LOGGER.error("Failed to load FIBO module %s: %s", module, e)
                raise RuntimeError(f"Failed to load FIBO module {module}") from e

        self._graph = graph
        LOGGER.info("FIBO ontology loaded: %d total triples", len(graph))

        return graph

    def get_alignment_targets(self) -> list[URIRef]:
        """Return key FIBO classes for alignment.

        Returns most commonly-used FIBO classes rather than all 1500+.
        These are the primary concepts external schemas should align to.

        Returns:
            List of URIRefs for key FIBO classes.
        """
        graph = self.build_graph()

        # Get all OWL classes
        all_classes = []
        for subj in graph.subjects(RDF.type, OWL.Class):
            if isinstance(subj, URIRef) and FIBO_BASE in str(subj):
                all_classes.append(subj)

        # For large ontologies like FIBO, return top-level or key classes
        # TODO: Could implement filtering logic here to return only most important classes
        LOGGER.info("Found %d FIBO classes for alignment", len(all_classes))

        return all_classes

    def get_namespace(self) -> Namespace:
        """Return the FIBO namespace.

        Returns:
            rdflib.Namespace for FIBO base URI.
        """
        if self._namespace is None:
            self._namespace = Namespace(FIBO_BASE)
        return self._namespace

    def get_top_level_classes(self) -> list[URIRef]:
        """Return top-level FIBO classes.

        Returns:
            List of URIRefs for classes with no superclass.
        """
        graph = self.build_graph()
        all_classes = set(self.get_alignment_targets())

        # Find subclasses
        subclasses = set()
        for subj in graph.subjects(RDFS.subClassOf, None):
            if isinstance(subj, URIRef) and subj in all_classes:
                subclasses.add(subj)

        # Top-level = not subclasses
        top_level = [cls for cls in all_classes if cls not in subclasses]

        LOGGER.debug("Found %d top-level FIBO classes", len(top_level))
        return top_level

    def get_properties(self) -> list[URIRef]:
        """Return FIBO properties.

        Returns:
            List of URIRefs for FIBO properties.
        """
        graph = self.build_graph()
        properties = []

        for subj in graph.subjects(RDF.type, OWL.ObjectProperty):
            if isinstance(subj, URIRef) and FIBO_BASE in str(subj):
                properties.append(subj)

        for subj in graph.subjects(RDF.type, OWL.DatatypeProperty):
            if isinstance(subj, URIRef) and FIBO_BASE in str(subj) and subj not in properties:
                properties.append(subj)

        LOGGER.debug("Found %d FIBO properties", len(properties))
        return properties

    def get_description(self, concept_uri: URIRef) -> Optional[str]:
        """Get description for a FIBO concept.

        Args:
            concept_uri: URI of the FIBO concept

        Returns:
            Description from rdfs:comment or skos:definition, or None.
        """
        graph = self.build_graph()

        # Try rdfs:comment
        for comment in graph.objects(concept_uri, RDFS.comment):
            if comment:
                return str(comment)

        # Try skos:definition (FIBO uses SKOS extensively)
        SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
        for definition in graph.objects(concept_uri, SKOS.definition):
            if definition:
                return str(definition)

        # Try rdfs:label as fallback
        for label in graph.objects(concept_uri, RDFS.label):
            if label:
                return str(label)

        return None

    def validate_alignment(self, source_uri: URIRef, target_uri: URIRef) -> bool:
        """Validate if an alignment to FIBO is semantically valid.

        Basic validation: check that target exists in FIBO graph.

        Args:
            source_uri: External schema concept
            target_uri: FIBO concept

        Returns:
            True if target_uri exists in FIBO, False otherwise.
        """
        graph = self.build_graph()

        # Check if target exists in graph
        if (target_uri, None, None) not in graph:
            LOGGER.warning(
                "Alignment target %s not found in FIBO", target_uri
            )
            return False

        return True
