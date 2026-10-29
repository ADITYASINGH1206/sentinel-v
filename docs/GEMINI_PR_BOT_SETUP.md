# Setting Up the Gemini AI PR Review Bot

SENTINEL-V includes an automated Pull Request review bot powered by Google Gemini API (`gemini-2.5-flash` / `gemini-1.5-flash`). Whenever your teammates (@sharadpolackalsunil or @AdityaRaj1304) open or update a Pull Request, the bot automatically reviews their code diff against the SENTINEL-V specification, checks for forbidden copy, validates test coverage, verifies that locked files remain untouched, and posts a review comment directly on the PR.

---

## 1. How It Works

```
  Teammate opens PR
         │
         ▼
  GitHub Actions triggers `.github/workflows/gemini-pr-review.yml`
         │
         ▼
  Script `scripts/gemini_pr_reviewer.py` computes filtered code diff
         │
         ▼
  Sends diff + PR metadata + AGENTS.md rules to Google Gemini API
         │
         ▼
  Gemini analyzes code for:
  - Compliance with SENTINEL-V SPEC and AGENTS.md rules
  - Locked SENTINEL file protection
  - Forbidden UI copy (no bare "FAKE" or "REAL")
  - Test coverage for new logic
  - Security (SSRF, injection, sandboxing)
         │
         ▼
  Posts structured review comment on the PR
```

---

## 2. One-Time Setup: Adding Your Gemini API Key

To activate the bot, add your Gemini API Key to GitHub Repository Secrets:

### Step 1: Get a Gemini API Key
1. Go to **[Google AI Studio](https://aistudio.google.com/)**.
2. Sign in with your Google account.
3. Click **"Get API key"** and create a new key (free tier is fully sufficient).

### Step 2: Add Secret to GitHub
1. Open your repository on GitHub: [https://github.com/ADITYASINGH1206/veriframe](https://github.com/ADITYASINGH1206/veriframe).
2. Navigate to **Settings** > **Secrets and variables** > **Actions**.
3. Click the green **"New repository secret"** button.
4. Set:
   - **Name:** `GEMINI_API_KEY`
   - **Secret:** *(Paste your Gemini API key from Step 1)*
5. Click **"Add secret"**.

---

## 3. Testing the Bot Locally (Optional)

You can test the review script locally before or during development:

```bash
# Set your Gemini API key in local environment
export GEMINI_API_KEY="your-gemini-api-key"

# Review current branch against main
PR_NUMBER="test-1" PR_TITLE="Test Feature" PR_AUTHOR="developer" GITHUB_BASE_REF="main" python3 scripts/gemini_pr_reviewer.py
```

---

## 4. What the Bot Reviews in Every PR

| Rule / Check | What Gemini Inspects |
|---|---|
| **No Invented Results** | Ensures metrics are read from data files/DB, never hardcoded in UI or documentation. |
| **Locked File Preservation** | Flags any PR that touches locked files in SENTINEL platform or modifies `third_party/smsdt` in-place. |
| **Forbidden Copy Check** | Warns if strings like "FAKE", "REAL", "100%", or "guaranteed" are introduced without the required disclaimer. |
| **Test Requirements** | Checks if unit tests under `tests/` were added or updated alongside new features. |
| **Security & Sandboxing** | Checks for SSRF risks (e.g. unvalidated URLs), subprocess shell injection, and secret leakage. |
| **Code Quality** | Analyzes type hints, error handling, edge cases, and performance bottlenecks. |

