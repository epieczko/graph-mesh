"""Upper ontology integration for Graph-Mesh.

This module provides integration with standard upper ontologies:
- BFO (Basic Formal Ontology): https://basic-formal-ontology.org/
- DOLCE (Descriptive Ontology for Linguistic and Cognitive Engineering)

It defines alignment mappings between the Graph-Mesh meta-ontology and these
upper ontologies to enable semantic interoperability and reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

from rdflib import Graph, Literal, Namespace, OWL, RDF, RDFS, URIRef

from .meta_ontology import GM, META_CLASSES


# BFO Namespace (Basic Formal Ontology)
BFO = Namespace("http://purl.obolibrary.org/obo/")

# DOLCE Namespace
DOLCE = Namespace("http://www.loa.istc.cnr.it/dolce/dolce-owl/")


class UpperOntologyType(Enum):
    """Enumeration of supported upper ontologies."""
    BFO = "BFO"
    DOLCE = "DOLCE"


@dataclass(frozen=True)
class AlignmentMapping:
    """Represents an alignment between a meta-class and an upper ontology concept."""

    meta_class_name: str
    upper_ontology: UpperOntologyType
    upper_class_uri: str
    alignment_type: str  # "exactMatch", "closeMatch", "broadMatch", "narrowMatch"
    justification: str


# BFO Core Concepts:
# - BFO_0000001: Entity (root)
# - BFO_0000002: Continuant (things that persist through time)
# - BFO_0000003: Occurrent (things that happen/occur)
# - BFO_0000004: Independent Continuant
# - BFO_0000015: Process
# - BFO_0000023: Role
# - BFO_0000029: Site (spatial region)
# - BFO_0000031: Generically Dependent Continuant

BFO_ALIGNMENTS: tuple[AlignmentMapping, ...] = (
    AlignmentMapping(
        "Entity",
        UpperOntologyType.BFO,
        "http://purl.obolibrary.org/obo/BFO_0000001",
        "broadMatch",
        "Graph-Mesh Entity is a broad category aligned with BFO's root Entity"
    ),
    AlignmentMapping(
        "Agent",
        UpperOntologyType.BFO,
        "http://purl.obolibrary.org/obo/BFO_0000004",
        "closeMatch",
        "Agents are independent continuants that can act and persist through time"
    ),
    AlignmentMapping(
        "Event",
        UpperOntologyType.BFO,
        "http://purl.obolibrary.org/obo/BFO_0000003",
        "exactMatch",
        "Events are occurrents - things that happen in time"
    ),
    AlignmentMapping(
        "Location",
        UpperOntologyType.BFO,
        "http://purl.obolibrary.org/obo/BFO_0000029",
        "closeMatch",
        "Locations align with BFO's Site concept - spatial regions"
    ),
    AlignmentMapping(
        "Contract",
        UpperOntologyType.BFO,
        "http://purl.obolibrary.org/obo/BFO_0000031",
        "closeMatch",
        "Contracts are generically dependent continuants - information artifacts"
    ),
    AlignmentMapping(
        "Regulation",
        UpperOntologyType.BFO,
        "http://purl.obolibrary.org/obo/BFO_0000031",
        "closeMatch",
        "Regulations are generically dependent continuants - information artifacts"
    ),
    AlignmentMapping(
        "Metric",
        UpperOntologyType.BFO,
        "http://purl.obolibrary.org/obo/BFO_0000031",
        "closeMatch",
        "Metrics are generically dependent continuants - information content"
    ),
)


# DOLCE Core Concepts:
# - endurant: entities that persist through time with all their parts
# - perdurant: events, happenings
# - quality: properties of endurants
# - abstract: information objects, social objects
# - physical-endurant: physical objects
# - social-object: contracts, regulations, etc.
# - agentive-physical-object: agents

DOLCE_ALIGNMENTS: tuple[AlignmentMapping, ...] = (
    AlignmentMapping(
        "Entity",
        UpperOntologyType.DOLCE,
        "http://www.loa.istc.cnr.it/dolce/dolce-owl/particular",
        "broadMatch",
        "Graph-Mesh Entity corresponds to DOLCE's particular (concrete entity)"
    ),
    AlignmentMapping(
        "Agent",
        UpperOntologyType.DOLCE,
        "http://www.loa.istc.cnr.it/dolce/dolce-owl/agentive-physical-object",
        "exactMatch",
        "Agents are agentive physical objects capable of intentional action"
    ),
    AlignmentMapping(
        "Event",
        UpperOntologyType.DOLCE,
        "http://www.loa.istc.cnr.it/dolce/dolce-owl/perdurant",
        "exactMatch",
        "Events are perdurants - things that happen over time"
    ),
    AlignmentMapping(
        "Location",
        UpperOntologyType.DOLCE,
        "http://www.loa.istc.cnr.it/dolce/dolce-owl/physical-region",
        "closeMatch",
        "Locations correspond to physical regions in DOLCE"
    ),
    AlignmentMapping(
        "Contract",
        UpperOntologyType.DOLCE,
        "http://www.loa.istc.cnr.it/dolce/dolce-owl/social-object",
        "exactMatch",
        "Contracts are social objects - agreements with normative force"
    ),
    AlignmentMapping(
        "Regulation",
        UpperOntologyType.DOLCE,
        "http://www.loa.istc.cnr.it/dolce/dolce-owl/social-object",
        "exactMatch",
        "Regulations are social objects with normative/prescriptive content"
    ),
    AlignmentMapping(
        "Metric",
        UpperOntologyType.DOLCE,
        "http://www.loa.istc.cnr.it/dolce/dolce-owl/quality",
        "closeMatch",
        "Metrics represent qualities or measurements of entities"
    ),
)


def get_alignments_for_class(
    class_name: str,
    upper_ontology: UpperOntologyType | None = None
) -> List[AlignmentMapping]:
    """Get all alignment mappings for a given meta-class.

    Args:
        class_name: Name of the meta-class
        upper_ontology: Optional filter by upper ontology type

    Returns:
        List of alignment mappings
    """
    all_alignments = list(BFO_ALIGNMENTS) + list(DOLCE_ALIGNMENTS)

    results = [a for a in all_alignments if a.meta_class_name == class_name]

    if upper_ontology:
        results = [a for a in results if a.upper_ontology == upper_ontology]

    return results


def get_alignment_summary() -> Dict[str, Dict[str, List[str]]]:
    """Get a summary of all alignments organized by meta-class.

    Returns:
        Dictionary mapping meta-class names to their upper ontology alignments
    """
    summary: Dict[str, Dict[str, List[str]]] = {}

    for meta_class in META_CLASSES:
        alignments = get_alignments_for_class(meta_class.name)
        summary[meta_class.name] = {
            "BFO": [a.upper_class_uri for a in alignments if a.upper_ontology == UpperOntologyType.BFO],
            "DOLCE": [a.upper_class_uri for a in alignments if a.upper_ontology == UpperOntologyType.DOLCE],
        }

    return summary


def build_alignment_graph() -> Graph:
    """Create an RDF graph with alignment mappings using SKOS vocabulary.

    Returns:
        RDF Graph containing alignment mappings
    """
    graph = Graph()
    graph.bind("gm", GM)
    graph.bind("bfo", BFO)
    graph.bind("dolce", DOLCE)
    graph.bind("skos", Namespace("http://www.w3.org/2004/02/skos/core#"))

    SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

    # Add all alignments as SKOS mapping relations
    for alignment in list(BFO_ALIGNMENTS) + list(DOLCE_ALIGNMENTS):
        source_uri = GM[alignment.meta_class_name]
        target_uri = URIRef(alignment.upper_class_uri)

        # Map alignment type to SKOS properties
        skos_property = {
            "exactMatch": SKOS.exactMatch,
            "closeMatch": SKOS.closeMatch,
            "broadMatch": SKOS.broadMatch,
            "narrowMatch": SKOS.narrowMatch,
        }.get(alignment.alignment_type, SKOS.relatedMatch)

        graph.add((source_uri, skos_property, target_uri))

        # Add annotation with justification
        # Create a blank node for the alignment annotation
        alignment_node = URIRef(f"{GM}{alignment.meta_class_name}_to_{alignment.upper_ontology.value}_alignment")
        graph.add((alignment_node, RDF.type, OWL.Axiom))
        graph.add((alignment_node, OWL.annotatedSource, source_uri))
        graph.add((alignment_node, OWL.annotatedProperty, skos_property))
        graph.add((alignment_node, OWL.annotatedTarget, target_uri))
        graph.add((alignment_node, RDFS.comment, Literal(alignment.justification)))

    return graph


def merge_with_upper_ontology(
    base_graph: Graph,
    upper_ontology: UpperOntologyType
) -> Graph:
    """Merge the base graph with upper ontology alignments.

    Args:
        base_graph: The base RDF graph (e.g., from build_meta_graph)
        upper_ontology: Which upper ontology to align with

    Returns:
        Merged graph with alignment assertions
    """
    alignment_graph = build_alignment_graph()

    # Filter alignments for the specified upper ontology
    for s, p, o in alignment_graph:
        # Only include alignments to the specified upper ontology
        if upper_ontology == UpperOntologyType.BFO and "obolibrary.org" in str(o):
            base_graph.add((s, p, o))
        elif upper_ontology == UpperOntologyType.DOLCE and "loa.istc.cnr.it" in str(o):
            base_graph.add((s, p, o))

    return base_graph
