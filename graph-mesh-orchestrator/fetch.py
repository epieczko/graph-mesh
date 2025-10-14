import requests, yaml, hashlib, sys, os
from pathlib import Path

def checksum(data): return hashlib.sha256(data).hexdigest()

manifest = sys.argv[1]
cfg = yaml.safe_load(open(manifest))
src = cfg["source"]
url, fmt = src["url"], src["format"]
target = Path("data/input") / f"{cfg['id']}.{fmt}"
target.parent.mkdir(parents=True, exist_ok=True)
print(f"⬇️  Fetching {url}")
r = requests.get(url)
data = r.content
new_hash = checksum(data)
old_hash = Path(str(target) + ".sha").read_text() if Path(str(target) + ".sha").exists() else ""
if new_hash != old_hash:
    target.write_bytes(data)
    Path(str(target) + ".sha").write_text(new_hash)
    print(f"✅  Updated: {target}")
else:
    print("⏩  No change; using cached copy.")
