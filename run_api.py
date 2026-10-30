import os
import sys
from pathlib import Path

# Repo root directory
ROOT = Path(__file__).resolve().parent

# Add all packages and services to sys.path using absolute paths
package_dirs = [
    ROOT / "packages" / "sv_core" / "src",
    ROOT / "packages" / "sv_engine" / "src",
    ROOT / "packages" / "sv_fusion" / "src",
    ROOT / "packages" / "sv_receipts" / "src",
    ROOT / "services" / "api" / "src",
    ROOT / "services" / "workers" / "src",
    ROOT / "services" / "monitor" / "src",
    ROOT / "third_party" / "smsdt",
    ROOT,
]

for p in package_dirs:
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

# Set PYTHONPATH environment variable with absolute paths so uvicorn reloader subprocesses inherit it
abs_pypath = os.pathsep.join(str(p) for p in package_dirs)
if "PYTHONPATH" in os.environ:
    os.environ["PYTHONPATH"] = abs_pypath + os.pathsep + os.environ["PYTHONPATH"]
else:
    os.environ["PYTHONPATH"] = abs_pypath

os.environ.setdefault("SV_DATABASE_URL", f"sqlite+aiosqlite:///{ROOT / 'test_dev.db'}")
os.environ.setdefault("SV_ENGINE_MODE", "real")

if __name__ == "__main__":
    import uvicorn

    print(f"Starting SENTINEL-V API on http://127.0.0.1:8080 (ENGINE_MODE: {os.environ.get('SV_ENGINE_MODE')})...")
    reload = os.environ.get("SV_RELOAD", "false").lower() == "true"
    uvicorn.run("sv_api.main:app", host="127.0.0.1", port=8080, reload=reload)

