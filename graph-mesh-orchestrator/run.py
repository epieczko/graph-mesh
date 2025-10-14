import argparse
import glob
import subprocess
import sys
from pathlib import Path

from utils import load_yaml


def run_step(name: str, cmd: str) -> None:
    print(f"🚀  Running step: {name}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌  Step failed: {name}")
        sys.exit(result.returncode)
    print(f"✅  Step complete: {name}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Graph-Mesh pipeline")
    parser.add_argument(
        "--manifest",
        dest="manifests",
        action="append",
        help="Specific manifest file(s) to execute",
    )
    args = parser.parse_args()

    manifests = args.manifests if args.manifests else sorted(glob.glob("data_sources/*.yaml"))

    for manifest in manifests:
        print(f"📘 Loading manifest: {manifest}")
        cfg = load_yaml(manifest)
        if "id" not in cfg or "source" not in cfg:
            print(f"⚠️  Manifest {manifest} is missing required keys; skipping.")
            continue

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
