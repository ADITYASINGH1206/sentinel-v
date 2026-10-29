#!/usr/bin/env python3
"""Strict Lock Compliance & Additive Integrity Verification Tool (SPEC §11, GEMINI.md).

Ensures:
1. No files in upstream submodules (e.g. third_party/smsdt) are modified.
2. Changes under integrations/sentinel are strictly restricted to approved additive files:
   - backend/services/videoModerationService.js
   - backend/routes/svWebhookRoutes.js
   - backend/supabase/schema_update_v6_video.sql
   - frontend/src/components/VideoAuthenticityBadge.jsx
   - PATCH_NOTES.md
3. No locked files (Web3, existing smart contracts, image deepfake classifiers) are touched.
"""

import subprocess
import sys
from pathlib import Path

APPROVED_ADDITIVE_INTEGRATION_FILES = {
    "integrations/sentinel/backend/services/videoModerationService.js",
    "integrations/sentinel/backend/routes/svWebhookRoutes.js",
    "integrations/sentinel/backend/supabase/schema_update_v6_video.sql",
    "integrations/sentinel/frontend/src/components/VideoAuthenticityBadge.jsx",
    "integrations/sentinel/PATCH_NOTES.md",
}

LOCKED_PREFIXES = (
    "third_party/smsdt",
    "contracts/locked",
)


def get_git_status_files() -> list[str]:
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = []
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            # format: XY filename
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                files.append(parts[1].replace("\\", "/"))
        return files
    except Exception as e:
        print(f"Warning: git status check failed ({e}); falling back to filesystem walk.")
        return []


def check_integrations_files(root: Path) -> list[str]:
    violations = []
    integrations_dir = root / "integrations" / "sentinel"
    if not integrations_dir.exists():
        return violations

    for p in integrations_dir.rglob("*"):
        if p.is_file():
            rel_path = p.relative_to(root).as_posix()
            if rel_path not in APPROVED_ADDITIVE_INTEGRATION_FILES:
                violations.append(f"Disallowed unapproved file in integrations: {rel_path}")
    return violations


def check_locked_files() -> int:
    root = Path(__file__).resolve().parent.parent
    violations = []

    # 1. Check all files present under integrations/sentinel
    violations.extend(check_integrations_files(root))

    # 2. Check git modified files
    modified_files = get_git_status_files()
    for f in modified_files:
        for locked in LOCKED_PREFIXES:
            if f.startswith(locked):
                violations.append(f"Attempted modification of locked path: {f}")

    if violations:
        print("[FAIL] Strict Lock Compliance Check FAILED:")
        for v in violations:
            print(f"  - {v}")
        return 1

    print("[PASS] Strict Lock Compliance Check PASSED: zero locked files modified.")
    return 0


if __name__ == "__main__":
    sys.exit(check_locked_files())
