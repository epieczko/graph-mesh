import yaml, subprocess, sys, os
from pathlib import Path
cfg = yaml.safe_load(open(sys.argv[1]))
sid = cfg["id"]
out = Path("output") / sid
out.mkdir(parents=True, exist_ok=True)
print(f"🧠  Aligning {sid}")
for tool in cfg["alignment"]["matchers"]:
    subprocess.run(f"docker compose run {tool}", shell=True, check=True)
subprocess.run(f"python graph-mesh-orchestrator/fuse_mappings.py {sid}", shell=True, check=True)
print(f"✅  Alignment complete for {sid}")
