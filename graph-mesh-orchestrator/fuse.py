import glob, rdflib
from rdflib import Graph
print("🔗  Fusing ontologies...")
g = Graph()
for f in glob.glob("output/*/*.owl"):
    print(f" + {f}")
    g.parse(f)
g.serialize("output/graph-mesh-merged.owl", format="xml")
print("✅  Fusion complete → output/graph-mesh-merged.owl")
