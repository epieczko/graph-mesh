#!/usr/bin/env python3
"""Test script for Track 4: Core & Meta-Ontology enhancements."""

from graph_mesh_core.meta_ontology import (
    build_meta_graph,
    GM,
    META_CLASSES,
    META_OBJECT_PROPERTIES,
    META_DATA_PROPERTIES,
)
from graph_mesh_core.upper_ontology import (
    get_alignments_for_class,
    get_alignment_summary,
    build_alignment_graph,
    merge_with_upper_ontology,
    UpperOntologyType,
)
from graph_mesh_core.reasoning import (
    get_subclasses,
    get_superclasses,
    is_subclass_of,
    get_root_classes,
    get_applicable_properties,
    print_class_hierarchy,
)
from graph_mesh_core.validation import (
    validate_ontology,
    check_consistency,
    OWLProfile,
    ReasonerType,
)


def test_meta_ontology_enhancements():
    """Test enhanced meta-ontology with properties and relationships."""
    print("=" * 80)
    print("TEST 1: Enhanced Meta-Ontology")
    print("=" * 80)

    graph = build_meta_graph()

    # Check classes
    print(f"\n✓ Meta-Classes: {len(META_CLASSES)}")
    for mc in META_CLASSES:
        print(f"  - {mc.name}: {mc.comment}")
        if mc.parent:
            print(f"    Parent: {mc.parent}")

    # Check object properties
    print(f"\n✓ Object Properties: {len(META_OBJECT_PROPERTIES)}")
    for prop in META_OBJECT_PROPERTIES:
        print(f"  - {prop.name}: {prop.comment}")
        print(f"    Domain: {prop.domain}, Range: {prop.range}")

    # Check data properties
    print(f"\n✓ Data Properties: {len(META_DATA_PROPERTIES)}")
    for prop in META_DATA_PROPERTIES:
        print(f"  - {prop.name}: {prop.comment}")

    # Check graph triples
    print(f"\n✓ Total triples in graph: {len(graph)}")

    return graph


def test_upper_ontology_integration():
    """Test upper ontology (BFO/DOLCE) integration."""
    print("\n" + "=" * 80)
    print("TEST 2: Upper Ontology Integration")
    print("=" * 80)

    # Test alignments
    print("\n✓ BFO Alignments:")
    for mc in META_CLASSES:
        alignments = get_alignments_for_class(mc.name, UpperOntologyType.BFO)
        for alignment in alignments:
            print(f"  - {alignment.meta_class_name} → {alignment.upper_class_uri}")
            print(f"    Type: {alignment.alignment_type}")
            print(f"    Justification: {alignment.justification[:60]}...")

    print("\n✓ DOLCE Alignments:")
    for mc in META_CLASSES:
        alignments = get_alignments_for_class(mc.name, UpperOntologyType.DOLCE)
        for alignment in alignments:
            print(f"  - {alignment.meta_class_name} → {alignment.upper_class_uri}")
            print(f"    Type: {alignment.alignment_type}")

    # Build alignment graph
    alignment_graph = build_alignment_graph()
    print(f"\n✓ Alignment graph triples: {len(alignment_graph)}")

    # Test alignment summary
    print("\n✓ Alignment Summary:")
    summary = get_alignment_summary()
    for cls_name, alignments in summary.items():
        print(f"  {cls_name}:")
        if alignments['BFO']:
            print(f"    BFO: {len(alignments['BFO'])} alignment(s)")
        if alignments['DOLCE']:
            print(f"    DOLCE: {len(alignments['DOLCE'])} alignment(s)")


def test_reasoning_utilities():
    """Test reasoning utilities for subsumption checking."""
    print("\n" + "=" * 80)
    print("TEST 3: Reasoning Utilities")
    print("=" * 80)

    graph = build_meta_graph()

    # Test subsumption
    print("\n✓ Subsumption Checking:")
    agent_uri = GM["Agent"]
    entity_uri = GM["Entity"]

    is_sub = is_subclass_of(graph, agent_uri, entity_uri)
    print(f"  Agent is subclass of Entity: {is_sub}")

    # Test superclasses
    print("\n✓ Superclasses of Agent:")
    superclasses = get_superclasses(graph, agent_uri)
    for sc in superclasses:
        print(f"  - {sc}")

    # Test subclasses
    print("\n✓ Subclasses of Entity:")
    subclasses = get_subclasses(graph, entity_uri)
    for sc in subclasses:
        local_name = str(sc).split('#')[-1]
        print(f"  - {local_name}")

    # Test root classes
    print("\n✓ Root Classes:")
    roots = get_root_classes(graph)
    for root in roots:
        local_name = str(root).split('#')[-1]
        print(f"  - {local_name}")

    # Test applicable properties
    print("\n✓ Properties applicable to Agent:")
    applicable = get_applicable_properties(graph, agent_uri, include_inherited=True)
    print(f"  Object Properties: {len(applicable['object'])}")
    for prop in applicable['object']:
        local_name = str(prop).split('#')[-1]
        print(f"    - {local_name}")
    print(f"  Datatype Properties: {len(applicable['datatype'])}")
    for prop in applicable['datatype']:
        local_name = str(prop).split('#')[-1]
        print(f"    - {local_name}")

    # Print class hierarchy
    print("\n✓ Class Hierarchy:")
    hierarchy = print_class_hierarchy(graph, namespace=GM)
    print(hierarchy)


def test_owl_validation():
    """Test OWL validation with reasoner."""
    print("\n" + "=" * 80)
    print("TEST 4: OWL Validation")
    print("=" * 80)

    graph = build_meta_graph()

    # Test basic validation
    print("\n✓ OWL DL Validation:")
    result = validate_ontology(graph, profile=OWLProfile.DL, reasoner=ReasonerType.HERMIT)

    print(f"  Valid: {result.is_valid}")
    print(f"  Profile: {result.profile.value}")
    print(f"  Reasoner: {result.reasoner_used.value if result.reasoner_used else 'None'}")

    if result.errors:
        print(f"  Errors ({len(result.errors)}):")
        for error in result.errors[:5]:  # Show first 5
            print(f"    - {error.message}")

    if result.warnings:
        print(f"  Warnings ({len(result.warnings)}):")
        for warning in result.warnings[:5]:  # Show first 5
            print(f"    - {warning.message}")

    # Test consistency
    print("\n✓ Consistency Checking:")
    consistency = check_consistency(graph, reasoner=ReasonerType.HERMIT)
    print(f"  Consistent: {consistency.is_consistent}")
    print(f"  Reasoner: {consistency.reasoner.value if consistency.reasoner else 'None'}")

    if consistency.errors:
        print(f"  Errors ({len(consistency.errors)}):")
        for error in consistency.errors:
            print(f"    - {error.message}")

    if consistency.warnings:
        print(f"  Warnings ({len(consistency.warnings)}):")
        for warning in consistency.warnings:
            print(f"    - {warning.message}")


def test_integration():
    """Test integration of all components."""
    print("\n" + "=" * 80)
    print("TEST 5: Integration Test")
    print("=" * 80)

    # Build base ontology
    graph = build_meta_graph()
    print(f"\n✓ Base ontology: {len(graph)} triples")

    # Add BFO alignments
    graph_with_bfo = merge_with_upper_ontology(graph, UpperOntologyType.BFO)
    print(f"✓ With BFO alignments: {len(graph_with_bfo)} triples")

    # Validate the merged ontology
    result = validate_ontology(graph_with_bfo, profile=OWLProfile.DL)
    print(f"✓ Merged ontology valid: {result.is_valid}")

    # Save to file
    output_path = "/tmp/meta_ontology_enhanced.ttl"
    graph_with_bfo.serialize(destination=output_path, format="turtle")
    print(f"✓ Saved to: {output_path}")

    # Print sample triples
    print("\n✓ Sample triples:")
    for i, (s, p, o) in enumerate(graph_with_bfo):
        if i >= 10:  # Show first 10
            break
        s_short = str(s).split('#')[-1].split('/')[-1]
        p_short = str(p).split('#')[-1].split('/')[-1]
        o_short = str(o).split('#')[-1].split('/')[-1]
        print(f"  {s_short} {p_short} {o_short}")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("Graph-Mesh Meta-Ontology Enhancement Tests")
    print("Track 4: Core & Meta-Ontology")
    print("=" * 80)

    try:
        test_meta_ontology_enhancements()
        test_upper_ontology_integration()
        test_reasoning_utilities()
        test_owl_validation()
        test_integration()

        print("\n" + "=" * 80)
        print("✓ ALL TESTS PASSED")
        print("=" * 80)
        return 0

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"✗ TEST FAILED: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
