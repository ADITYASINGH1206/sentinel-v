#!/usr/bin/env python3
"""SENTINEL-V Gemini AI PR Reviewer.

Reviews pull request diffs against SENTINEL-V SPEC and AGENTS.md rules using Google Gemini API.
Runs in GitHub Actions with zero external Python dependencies.
Idempotently updates existing review comments to avoid duplicates.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

# Files to exclude from diff review to save token context
EXCLUDE_EXTENSIONS = (
    ".lock",
    "-lock.json",
    ".min.js",
    ".min.css",
    ".map",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".npz",
    ".npy",
    ".pt",
    ".safetensors",
    ".parquet",
)

PROMPT_TEMPLATE = """You are an expert senior software architect, deepfake forensics engineer, and security auditor evaluating a Pull Request for SENTINEL-V.
SENTINEL-V is a calibrated, auditable video deepfake screening platform built on top of the S-MSDT detector family.

Review the following Pull Request diff thoroughly against our project specifications and standards.

### CRITICAL PROJECT RULES (From AGENTS.md & SPEC.md):
1. **Never Invent Results:** Any metric, performance number, calibration coefficient, or screening verdict shown in UI or documentation must come from generated data files (`eval/results/*.csv`, bundle `calibration.json` / `operating_points.json`) or DB rows. Never hardcode or invent results; use `null` or `—`.
2. **Locked Core Rule:** Core SENTINEL platform files (contracts, Web3, base video and image deepfake code) are locked. Integration code in `integrations/sentinel/` must be strictly additive.
3. **Submodule Rule:** Upstream S-MSDT in `third_party/smsdt` must NEVER be modified in-place.
4. **Forbidden Copy Rule:** UI strings and API error responses must NEVER use bare "FAKE", "REAL", "100%", "guaranteed", or "AI-certified". The mandatory screening disclaimer ("Screening aid — not proof. Human review required for consequential action.") must accompany verdicts.
5. **Calibrated Probabilities & Decisions:** Finalization must use calibrated thresholds and proper Platt scaling rather than uncalibrated synthetic scores.
6. **Test Coverage & Parity:** All new logic and bug fixes must have accompanying unit or integration tests (`pytest -v -m "not gpu"`).
7. **Security & Sandboxing:** Check for SSRF risks, unsafe subshell executions, secret leakage, or unvalidated inputs.

---

### PR METADATA:
- **PR Number:** #{pr_number}
- **Title:** {pr_title}
- **Author:** @{pr_author}

---

### CODE DIFF:
```diff
{diff_content}
```

---

### REQUIRED OUTPUT FORMAT:
Produce a comprehensive, highly readable GitHub Markdown review following this exact structure:

<!-- sentinel-v-pr-review -->
## 🤖 SENTINEL-V DeepForensics AI Review

| Status | Target PR | Author | Review Engine |
| :--- | :--- | :--- | :--- |
| **[VERDICT_BADGE: ✅ APPROVE | ⚠️ COMMENT | ❌ REQUEST CHANGES]** | #{pr_number} - {pr_title} | @{pr_author} | Google Gemini DeepForensics |

---

### 📋 1. Executive Summary
(Provide a clear 2-4 sentence architectural summary of what this PR introduces, changed components, and overall system impact)

---

### 🛡️ 2. Specification & Policy Compliance Checklist

| Rule / Invariant | Status | Details / Audit Finding |
| :--- | :---: | :--- |
| **No Hardcoded / Invented Results** | [✅ Pass | ⚠️ Warning | ❌ Fail] | (Details) |
| **Locked Core Untouched (Additive Only)** | [✅ Pass | ⚠️ Warning | ❌ Fail] | (Details) |
| **Upstream Submodule Purity (`smsdt`)** | [✅ Pass | ⚠️ Warning | ❌ Fail] | (Details) |
| **Forbidden Copy Compliance** | [✅ Pass | ⚠️ Warning | ❌ Fail] | (Details) |
| **Unit & Integration Test Coverage** | [✅ Pass | ⚠️ Warning | ❌ Fail] | (Details) |
| **Security, Secrets & Sandboxing** | [✅ Pass | ⚠️ Warning | ❌ Fail] | (Details) |

---

### 🔍 3. Deep Forensic Findings & Vulnerability Analysis
(Group findings clearly by severity with exact file paths, line references, explanation, and code fixes):

#### 🔴 [BLOCKING] Issues (Must resolve before merge)
(List each blocking flaw with path and code suggestion. If none, state "None detected.")

#### 🟡 [WARNING] Architectural & Code Quality Improvements
(List improvements, edge cases, potential race conditions, or error handling gaps. If none, state "None detected.")

#### 🟢 [VERIFIED] Strengths & Positive Highlights
(List what was done exceptionally well in this PR: modularity, typing, clean algorithms, etc.)

---

### 💡 4. Actionable Next Steps
(List 2-4 concrete, prioritized bullet points for the author to address before merge)

> ⚠️ **Mandatory Screening Aid Notice:** Screening aid — not proof. Human review required for consequential action.
"""


def get_pr_diff(pr_number: str = None) -> str:
    """Get filtered git diff for the pull request."""
    raw_diff = ""
    repo = os.environ.get("GITHUB_REPOSITORY")

    # 1. First try gh pr diff if pr_number is known
    if pr_number:
        try:
            cmd = ["gh", "pr", "diff", str(pr_number)]
            if repo:
                cmd.extend(["--repo", repo])
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                raw_diff = res.stdout
        except Exception:
            pass

    # 2. Fall back to git diff against base branch
    if not raw_diff:
        base_ref = os.environ.get("GITHUB_BASE_REF", "main")
        cmd = ["git", "diff", f"origin/{base_ref}...HEAD"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            raw_diff = res.stdout
        except Exception:
            res = subprocess.run(["git", "diff", "HEAD~1...HEAD"], capture_output=True, text=True)
            raw_diff = res.stdout

    if not raw_diff.strip():
        return "No diff detected."

    # Filter out binary or lockfile diff blocks
    filtered_lines = []
    skip_current_file = False

    for line in raw_diff.splitlines():
        if line.startswith("diff --git"):
            filename = line.split()[-1]
            skip_current_file = any(filename.endswith(ext) for ext in EXCLUDE_EXTENSIONS)
        if not skip_current_file:
            filtered_lines.append(line)

    filtered_diff = "\n".join(filtered_lines)

    # Cap diff at 35,000 characters to stay comfortably within Gemini context window
    if len(filtered_diff) > 35000:
        filtered_diff = filtered_diff[:35000] + "\n\n... [Diff truncated due to size limit] ..."

    return filtered_diff


def call_gemini(prompt: str, api_key: str) -> str:
    """Call Google Gemini API with automatic model fallback and exponential backoff."""
    models = ["gemini-2.5-flash", "gemini-3.5-flash-lite"]
    last_err = None

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 8192,
            },
        }
        data = json.dumps(payload).encode("utf-8")

        for attempt in range(1, 4):
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}, method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    candidates = resp_data.get("candidates", [])
                    if candidates:
                        text = candidates[0]["content"]["parts"][0]["text"]
                        print(f"Gemini API ({model}) returned {len(text)} characters of review.")
                        return text
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                print(f"Gemini API model {model} attempt {attempt} HTTP error {e.code}: {err_body[:200]}")
                last_err = e
                if e.code in (429, 503):
                    time.sleep(attempt * 2)
                    continue
                break  # Don't retry 400/404 client errors
            except Exception as e:
                print(f"Gemini API model {model} attempt {attempt} error: {e}")
                last_err = e
                time.sleep(attempt * 2)
                continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")


def post_or_update_github_comment(pr_number: str, comment_body: str) -> None:
    """Idempotently post or update the review comment to prevent duplicate spam."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")

    if not token or not repo:
        print("Warning: GITHUB_TOKEN or GITHUB_REPOSITORY missing. Attempting standard gh pr comment...")
        cmd = ["gh", "pr", "comment", str(pr_number), "--body", comment_body]
        if repo:
            cmd.extend(["--repo", repo])
        subprocess.run(cmd, check=False)
        return

    # 1. Fetch existing PR comments to look for previous bot reviews
    existing_review_comment_ids = []
    try:
        api_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments?per_page=100"
        req = urllib.request.Request(
            api_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            comments = json.loads(resp.read().decode("utf-8"))
            for c in comments:
                body = c.get("body", "")
                if "<!-- sentinel-v-pr-review -->" in body or "## 🤖 SENTINEL-V" in body:
                    existing_review_comment_ids.append(c["id"])
    except Exception as e:
        print(f"Note: Could not list existing comments ({e}). Will post fresh comment.")

    # 2. If an existing review comment is found, update it in-place
    if existing_review_comment_ids:
        primary_id = existing_review_comment_ids[0]
        print(f"Found existing AI review comment #{primary_id}. Updating in-place...")
        patch_url = f"https://api.github.com/repos/{repo}/issues/comments/{primary_id}"
        req = urllib.request.Request(
            patch_url,
            data=json.dumps({"body": comment_body}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
            },
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                print(f"Successfully updated review comment #{primary_id} (Status {resp.status})")
        except Exception as e:
            print(f"Failed to update comment #{primary_id}: {e}")

        # 3. Clean up extra duplicate review comments if any exist
        for dup_id in existing_review_comment_ids[1:]:
            print(f"Cleaning up duplicate review comment #{dup_id}...")
            del_url = f"https://api.github.com/repos/{repo}/issues/comments/{dup_id}"
            del_req = urllib.request.Request(
                del_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                method="DELETE",
            )
            try:
                with urllib.request.urlopen(del_req, timeout=15):
                    print(f"Removed duplicate comment #{dup_id}")
            except Exception as e:
                print(f"Could not delete duplicate comment #{dup_id}: {e}")
        return

    # 4. If no previous bot comment exists, create a new one
    print(f"No existing AI review comment found. Posting new comment to PR #{pr_number}...")
    post_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    req = urllib.request.Request(
        post_url,
        data=json.dumps({"body": comment_body}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"Successfully posted AI review comment to PR #{pr_number} (Status {resp.status})")
    except Exception as e:
        print(f"Failed to post comment via REST API: {e}. Falling back to gh CLI...")
        cmd = ["gh", "pr", "comment", str(pr_number), "--body", comment_body]
        if repo:
            cmd.extend(["--repo", repo])
        subprocess.run(cmd, check=False)


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    pr_number = os.environ.get("PR_NUMBER")
    pr_title = os.environ.get("PR_TITLE", "Pull Request Review")
    pr_author = os.environ.get("PR_AUTHOR", "contributor")

    if not pr_number:
        # Detect from GitHub Actions event payload
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if event_path and os.path.exists(event_path):
            with open(event_path) as f:
                event_data = json.load(f)
                pr_info = event_data.get("pull_request") or event_data.get("issue", {})
                pr_number = str(pr_info.get("number", ""))
                pr_title = pr_info.get("title", pr_title)
                pr_author = pr_info.get("user", {}).get("login", pr_author)

    if not pr_number:
        print("Error: No PR number detected.")
        sys.exit(1)

    print(f"Reviewing PR #{pr_number}: '{pr_title}' by @{pr_author}...")
    diff = get_pr_diff(pr_number)

    if diff == "No diff detected.":
        print("No changes found in diff to review.")
        return

    prompt = PROMPT_TEMPLATE.format(
        pr_number=pr_number, pr_title=pr_title, pr_author=pr_author, diff_content=diff
    )

    print("Sending diff to Gemini API for deep forensics and code review...")
    review = call_gemini(prompt, api_key)

    footer = (
        "\n\n---\n*Automated review by SENTINEL-V Gemini Bot &bull; Powered by Google Gemini API*"
    )
    full_comment = review.strip() + footer

    if os.environ.get("DRY_RUN", "false").lower() in ("true", "1", "yes"):
        print("\n=== DRY RUN REVIEW OUTPUT ===")
        print(full_comment)
        print("=== END DRY RUN ===")
    else:
        post_or_update_github_comment(pr_number, full_comment)


if __name__ == "__main__":
    main()
