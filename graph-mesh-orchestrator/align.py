from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from shutil import which

from utils import load_yaml


def _run(command: str) -> None:
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"⚠️  Command failed during dry-run: {command}")


def main() -> None:
    cfg = load_yaml(sys.argv[1])
    sid = cfg["id"]
    out = Path("output") / sid
    out.mkdir(parents=True, exist_ok=True)
    print(f"🧠  Aligning {sid}")

    if which("docker") is None:
        print("⚠️  Docker is unavailable; skipping matcher containers.")
    else:
        for tool in cfg.get("alignment", {}).get("matchers", []):
            _run(f"docker compose run {tool}")

    fuse_script = Path("graph-mesh-orchestrator/fuse_mappings.py")
    if fuse_script.exists():
        _run(f"python {fuse_script} {sid}")
    else:
        print("ℹ️  No fuse_mappings.py script found; skipping matcher fusion.")

    print(f"✅  Alignment complete for {sid}")


if __name__ == "__main__":
    main()
