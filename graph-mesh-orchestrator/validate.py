from owlready2 import get_ontology, sync_reasoner_pellet
print("🧮  Validating merged ontology...")
onto = get_ontology("output/graph-mesh-merged.owl").load()
with onto:
    sync_reasoner_pellet()
print("✅  Validation successful.")
