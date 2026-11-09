"""Install pygame into the project venv without pip (pip needs mkdtemp, which the sandbox blocks)."""
import json
import pathlib
import sys
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
SITE = ROOT / ".venv" / "Lib" / "site-packages"
CACHE = ROOT / ".tmp"
CACHE.mkdir(parents=True, exist_ok=True)

TAG = "cp312-cp312-win_amd64"
VERSION = "2.6.1"

if not SITE.is_dir():
    sys.exit(f"venv site-packages missing: {SITE}")

# 1) locate the wheel on the index
wheel_url = None
try:
    meta = json.load(urllib.request.urlopen(
        f"https://pypi.org/pypi/pygame/{VERSION}/json", timeout=60))
    for item in meta["urls"]:
        if item["filename"].endswith(f"{TAG}.whl"):
            wheel_url = item["url"]
            break
except Exception as exc:  # noqa: BLE001
    print("pypi json failed:", exc)

if wheel_url is None:
    html = urllib.request.urlopen(
        "https://mirrors.aliyun.com/pypi/simple/pygame/", timeout=60).read().decode()
    for line in html.splitlines():
        if f"{VERSION}-{TAG}.whl" in line:
            wheel_url = line.split('href="')[1].split('"')[0]
            if wheel_url.startswith("../../"):
                wheel_url = "https://mirrors.aliyun.com/pypi/" + wheel_url[6:]
            break

if wheel_url is None:
    sys.exit("wheel not found on index")

print("wheel:", wheel_url)

# 2) download
wheel_path = CACHE / wheel_url.rsplit("/", 1)[-1]
if not wheel_path.exists() or wheel_path.stat().st_size < 1_000_000:
    with urllib.request.urlopen(wheel_url, timeout=300) as resp:
        data = resp.read()
    wheel_path.write_bytes(data)
print("downloaded:", wheel_path.stat().st_size, "bytes")

# 3) extract straight into site-packages (no mkdtemp involved)
with zipfile.ZipFile(wheel_path) as zf:
    names = zf.namelist()
    zf.extractall(SITE)
print("extracted", len(names), "files ->", SITE)

# 4) verify
sys.path.insert(0, str(SITE))
import pygame  # noqa: E402

print("pygame", pygame.version.ver, "import OK")
