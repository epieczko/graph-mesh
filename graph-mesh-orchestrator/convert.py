import yaml, subprocess, sys
cfg = yaml.safe_load(open(sys.argv[1]))
sid = cfg["id"]
conv = cfg.get("converter", {})
img = conv.get("docker_image", "default-converter")
print(f"🧩  Converting {sid} using {img}")
subprocess.run(f"docker run --rm -v $(pwd)/data:/app/data {img}", shell=True, check=True)
