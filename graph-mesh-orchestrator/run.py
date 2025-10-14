import os, yaml, subprocess, glob, sys
from pathlib import Path

def run_step(name, cmd):
    print(f"🚀  Running step: {name}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌  Step failed: {name}")
        sys.exit(result.returncode)
    print(f"✅  Step complete: {name}\n")

def main():
    manifests = glob.glob("data_sources/*.yaml")
    for manifest in manifests:
        print(f"📘 Loading manifest: {manifest}")
        with open(manifest) as f:
            cfg = yaml.safe_load(f)
        sid = cfg["id"]
        src = cfg["source"]
        out_dir = Path("output") / sid
        out_dir.mkdir(parents=True, exist_ok=True)

        if src.get("url"):
            run_step("fetch", f"python graph-mesh-orchestrator/fetch.py {manifest}")
        run_step("convert", f"python graph-mesh-orchestrator/convert.py {manifest}")
        run_step("align", f"python graph-mesh-orchestrator/align.py {manifest}")
        run_step("fuse", f"python graph-mesh-orchestrator/fuse.py {manifest}")
        run_step("validate", f"python graph-mesh-orchestrator/validate.py {manifest}")

    print("🏁  Graph-Mesh pipeline complete.")

if __name__ == "__main__":
    main()
