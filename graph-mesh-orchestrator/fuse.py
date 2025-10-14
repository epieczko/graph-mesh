from __future__ import annotations

import glob
from pathlib import Path

try:  # pragma: no cover - optional dependency.
    from rdflib import Graph  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    Graph = None  # type: ignore


print("🔗  Fusing ontologies...")
out_path = Path("output/graph-mesh-merged.owl")
out_path.parent.mkdir(parents=True, exist_ok=True)

if Graph is None:
    out_path.write_text("<!-- Placeholder graph generated during dry-run -->\n", encoding="utf-8")
    print(f"⚠️  rdflib is unavailable; wrote placeholder graph to {out_path}.")
else:
    graph = Graph()
    sources = sorted(glob.glob("output/*/*.owl"))
    if not sources:
        print("ℹ️  No ontology artifacts found; creating empty merged graph.")
    for src in sources:
        print(f" + {src}")
        graph.parse(src)
    graph.serialize(out_path, format="xml")

print(f"✅  Fusion complete → {out_path}")
