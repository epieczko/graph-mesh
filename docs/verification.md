# Verification Checklist

To confirm the Graph-Mesh Phase 2 pipeline is ready for dry-run execution, perform the following checks from the repository root:

1. **Validate repository layout**
   ```bash
   tree -L 2 | grep -E "graph-mesh-(core|aligner|converters|orchestrator)|data_sources|docker-compose.yml|requirements.txt"
   ```
   If the `tree` utility is not available in your environment, install it (e.g., `apt-get install tree`) or inspect the directory manually with `find`.

2. **Ensure required Python dependencies are declared**
   ```bash
   grep -E "rdflib|owlready2|sssom|pandas|tqdm|pyyaml" requirements.txt
   ```

3. **Run the orchestrator against the demo manifest**
   ```bash
   python graph-mesh-orchestrator/run.py --manifest data_sources/demo.yaml
   ```
   The dry-run will create placeholder artifacts under `data/` and `output/` to mimic a successful pipeline execution.

4. **Confirm CI references the orchestrator container**
   ```bash
   grep -A5 "Graph-Mesh Build" .github/workflows/graph-mesh.yml
   ```

These commands mirror the automated verification workflow and can help troubleshoot issues locally before pushing changes.
