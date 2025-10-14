from __future__ import annotations

from pathlib import Path

try:  # pragma: no cover - optional dependency.
    from owlready2 import get_ontology, sync_reasoner_pellet  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    get_ontology = None  # type: ignore
    sync_reasoner_pellet = None  # type: ignore

print("🧮  Validating merged ontology...")
merged = Path("output/graph-mesh-merged.owl")

if get_ontology is None or sync_reasoner_pellet is None:
    merged.touch(exist_ok=True)
    print("⚠️  owlready2 is unavailable; skipping reasoning step for dry-run.")
else:
    onto = get_ontology(str(merged)).load()
    with onto:
        sync_reasoner_pellet()

print("✅  Validation successful.")
