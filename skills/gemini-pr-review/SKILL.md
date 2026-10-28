---
name: gemini-pr-review
description: Guides the configuration, customization, and local testing of the automated GitHub Actions Gemini AI code review bot for SENTINEL-V.
---

# Gemini AI PR Review Bot Skill

This skill explains how the automated GitHub Pull Request review bot is configured, executed, and customized for SENTINEL-V.

## Architecture

- **Workflow:** `.github/workflows/gemini-pr-review.yml`
- **Execution Script:** `scripts/gemini_pr_reviewer.py`
- **LLM Engine:** Google Gemini API (`gemini-2.5-flash` / `gemini-1.5-flash`)
- **Dependencies:** Pure Python 3 standard library (`urllib.request`, `json`, `os`, `subprocess`). Zero extra packages needed.

---

## Required Secret Configuration

The workflow requires one GitHub Actions Secret:
- **`GEMINI_API_KEY`**: Obtainable for free at [aistudio.google.com](https://aistudio.google.com/).
- Stored in: `Settings -> Secrets and variables -> Actions -> GEMINI_API_KEY`.

If the secret is not yet set, the workflow gracefully skips the review with a GitHub warning rather than failing the build.

---

## Customizing Review Prompts & Rules

To adjust or add project-specific review instructions (e.g. strict mypy standards or new policy limits):
1. Open `scripts/gemini_pr_reviewer.py`.
2. Edit `PROMPT_TEMPLATE` under `CRITICAL PROJECT RULES`.
3. Test locally by running:
   ```bash
   GEMINI_API_KEY=... python3 scripts/gemini_pr_reviewer.py
   ```
