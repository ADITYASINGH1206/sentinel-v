#!/usr/bin/env python3
"""SENTINEL-V Gemini AI PR Reviewer.

Reviews pull request diffs against SENTINEL-V SPEC and AGENTS.md rules using Google Gemini API.
Runs in GitHub Actions with zero external Python dependencies.
"""

import json
import os
import subprocess
import sys
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

PROMPT_TEMPLATE = """You are an expert senior code reviewer and security auditor evaluating a Pull Request for SENTINEL-V.
SENTINEL-V is a calibrated, auditable video deepfake screening platform.

Review the following Pull Request diff against our project guidelines and standards.

### CRITICAL PROJECT RULES (From AGENTS.md & SPEC.md):
1. **Never Invent Results:** Any metric or number in UI or docs must come from data files or DB, never hardcoded. Placeholders must be `null` or `—`.
2. **Locked Files Rule:** SENTINEL platform files (contracts, Web3, video processing) are locked. All integration code in `integrations/sentinel/` must be strictly additive.
3. **Submodule Rule:** Upstream S-MSDT in `third_party/smsdt` must NEVER be modified in-place.
4. **Forbidden Copy Rule:** UI strings must NEVER use bare "FAKE", "REAL", "100%", "guaranteed", or "AI-certified". The mandatory screening disclaimer ("Screening aid — not proof. Human review required for consequential action.") must accompany verdicts.
5. **Test Coverage:** All new logic and bug fixes must have accompanying unit or integration tests.
6. **Security & Sandboxing:** Check for SSRF risks, unsafe shell executions, secret leakage, or unvalidated inputs.

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
Produce a comprehensive GitHub Markdown review with these exact sections:

## 🤖 SENTINEL-V AI Review Summary
**Verdict:** [✅ APPROVE | ⚠️ COMMENT | ❌ REQUEST CHANGES]

### 1. Overview of Changes
(Brief 2-3 sentence summary of what this PR introduces or changes)

### 2. Specification & Rule Compliance
- [ ] No hardcoded metrics / invented results
- [ ] Locked SENTINEL files untouched (additive only)
- [ ] `third_party/smsdt` submodule untouched in-place
- [ ] Forbidden copy rules respected (no bare FAKE/REAL)
- [ ] Unit/Integration tests included for new logic

### 3. Code Quality & Security Findings
(List any bugs, edge cases, type issues, SSRF risks, or performance bottlenecks with file path and suggested fix. If none, write "No critical defects detected.")

### 4. Constructive Recommendations
(Actionable tips to improve readability, test depth, or parity adherence)
"""


def get_pr_diff(pr_number: str = None) -> str:
    """Get filtered git diff for the pull request."""
    raw_diff = ""

    # 1. First try gh pr diff if pr_number is known
    if pr_number:
        try:
            res = subprocess.run(
                ["gh", "pr", "diff", str(pr_number)], capture_output=True, text=True
            )
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

    # Cap diff at 30,000 characters to stay well within Gemini context limits
    if len(filtered_diff) > 30000:
        filtered_diff = filtered_diff[:30000] + "\n\n... [Diff truncated due to size limit] ..."

    return filtered_diff


def call_gemini(prompt: str, api_key: str) -> str:
    """Call Google Gemini API using native urllib."""
    # Prefer gemini-2.5-flash, fallback to gemini-1.5-flash
    models = ["gemini-2.5-flash", "gemini-1.5-flash"]
    last_err = None

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                candidates = resp_data.get("candidates", [])
                if candidates:
                    return candidates[0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            print(f"Gemini API model {model} HTTP error {e.code}: {err_body}")
            last_err = e
            continue
        except Exception as e:
            print(f"Gemini API model {model} error: {e}")
            last_err = e
            continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")


def post_github_comment(pr_number: str, comment_body: str) -> None:
    """Post review comment on GitHub PR using gh CLI."""
    cmd = ["gh", "pr", "comment", pr_number, "--body", comment_body]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print(f"Successfully posted AI review comment to PR #{pr_number}")
    else:
        print(f"Failed to post comment with gh CLI: {res.stderr}")
        # Fallback to GitHub REST API with GITHUB_TOKEN
        token = os.environ.get("GITHUB_TOKEN")
        repo = os.environ.get("GITHUB_REPOSITORY")
        if token and repo:
            api_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
            req = urllib.request.Request(
                api_url,
                data=json.dumps({"body": comment_body}).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req) as r:
                print(f"Posted review via GitHub REST API (Status {r.status})")


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        print("Please add GEMINI_API_KEY to your GitHub Repository Secrets.")
        sys.exit(1)

    pr_number = os.environ.get("PR_NUMBER")
    pr_title = os.environ.get("PR_TITLE", "Pull Request Review")
    pr_author = os.environ.get("PR_AUTHOR", "contributor")

    if not pr_number:
        # Try detecting from GitHub Actions event path
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if event_path and os.path.exists(event_path):
            with open(event_path) as f:
                event_data = json.load(f)
                pr_info = event_data.get("pull_request", {})
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
    full_comment = review + footer

    if os.environ.get("DRY_RUN", "false").lower() in ("true", "1", "yes"):
        print("\n=== DRY RUN REVIEW OUTPUT ===")
        print(full_comment)
        print("=== END DRY RUN ===")
    else:
        post_github_comment(pr_number, full_comment)


if __name__ == "__main__":
    main()
