from __future__ import annotations

import subprocess
import sys
from shutil import which

from utils import load_yaml


def main() -> None:
    cfg = load_yaml(sys.argv[1])
    sid = cfg["id"]
    conv = cfg.get("converter", {})
    img = conv.get("docker_image", "default-converter")
    print(f"🧩  Converting {sid} using {img}")

    if which("docker") is None:
        print("⚠️  Docker is unavailable; skipping container execution for dry-run.")
        return

    result = subprocess.run(
        f"docker run --rm -v $(pwd)/data:/app/data {img}", shell=True
    )
    if result.returncode != 0:
        print("⚠️  Converter container exited with a non-zero status during dry-run.")


if __name__ == "__main__":
    main()
