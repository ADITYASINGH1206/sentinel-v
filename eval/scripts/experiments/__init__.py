"""
SENTINEL-V Paper B Evaluation Harness Experiments (SPEC §15).
"""

import os
import sys
from pathlib import Path

# Set testing defaults to ensure offline / mock database compatibility
os.environ.setdefault("SV_DATABASE_URL", "sqlite+aiosqlite:///./test_dev.db")
os.environ.setdefault("SV_TESTING", "1")
os.environ.setdefault("SV_ENGINE_MODE", "mock")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
for pkg in [
    "packages/sv_core/src",
    "packages/sv_engine/src",
    "packages/sv_fusion/src",
    "packages/sv_receipts/src",
    "services/api/src",
    "services/monitor/src",
]:
    p_str = str(REPO_ROOT / pkg)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)
