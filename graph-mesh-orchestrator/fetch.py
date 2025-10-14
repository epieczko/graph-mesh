from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Optional

try:  # pragma: no cover - optional dependency in offline environments.
    import requests  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    requests = None  # type: ignore

from utils import load_yaml


def checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _download(url: str) -> Optional[bytes]:
    if requests is None:
        return None
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except Exception:
        return None
    return response.content


def main() -> None:
    manifest = sys.argv[1]
    cfg = load_yaml(manifest)
    src = cfg["source"]
    url, fmt = src["url"], src["format"]
    target = Path("data/input") / f"{cfg['id']}.{fmt}"
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"⬇️  Fetching {url}")

    payload = _download(url)
    if payload is None:
        target.write_text("", encoding="utf-8")
        Path(str(target) + ".sha").write_text("offline", encoding="utf-8")
        print(f"⚠️  Unable to download {url}. Created placeholder at {target}.")
        return

    new_hash = checksum(payload)
    hash_path = Path(str(target) + ".sha")
    old_hash = hash_path.read_text(encoding="utf-8") if hash_path.exists() else ""
    if new_hash != old_hash:
        target.write_bytes(payload)
        hash_path.write_text(new_hash, encoding="utf-8")
        print(f"✅  Updated: {target}")
    else:
        print("⏩  No change; using cached copy.")


if __name__ == "__main__":
    main()
