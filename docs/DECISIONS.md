# Architecture Decision Records (ADR) — SENTINEL-V

This file records all architectural and design decisions made for SENTINEL-V in ADR format.

---

## ADR 001: Monorepo Architecture and Package Isolation

- **Status:** Accepted
- **Date:** 2026-10-28
- **Context:** SENTINEL-V spans ML inference, data preprocessing, high-throughput Celery workers, a FastAPI gateway, React frontend, Foundry smart contracts, and an evaluation harness. Code sharing (schemas, settings, cryptography) is needed across services while keeping ML and web packages cleanly decoupled.
- **Decision:** Adopt a monorepo layout with modular Python packages under `packages/` (`sv_core`, `sv_engine`, `sv_fusion`, `sv_receipts`), independent services under `services/` (`api`, `workers`, `monitor`), React SPA under `web/`, and Solidity contracts under `contracts/`.
- **Consequences:** Enables unified CI/CD, shared type contracts, and strict dependency isolation.

---

## ADR 002: Dual-Engine Architecture (Real GPU + Deterministic Mock)

- **Status:** Accepted
- **Date:** 2026-10-28
- **Context:** S-MSDT requires NVIDIA GPUs and heavy PyTorch/ONNX dependencies. Frontend development, CI testing, and end-to-end integration workflows must run rapidly without requiring GPU hardware.
- **Decision:** Support `SV_ENGINE_MODE=mock` alongside `SV_ENGINE_MODE=real`. The mock engine computes deterministic frame hashes for scores and synthetic Gaussian evidence heat-maps. In mock mode, all API responses and UI badges explicitly label the result as `mock=True` with a visible "MOCK" badge.
- **Consequences:** Developers can run `make dev` and full integration tests on any machine while preserving strict parity testing on reference GPU hardware.

---

## ADR 003: Non-Invasive Submodule Strategy for S-MSDT Upstream

- **Status:** Accepted
- **Date:** 2026-10-28
- **Context:** The core models are derived from `github.com/sharadpolackalsunil/DeepFake`. Forking and altering research code in-place creates drift and breaks upstream synchronization.
- **Decision:** Vendor `smsdt` as a git submodule in `third_party/smsdt`, pinned to a verified commit. All serving-specific logic (in-memory decoding, clip batching, adapters) wraps upstream functions without touching upstream source files.
- **Consequences:** Zero divergence from the research codebase; easy updates from upstream commits.

---

## ADR 004: Purely Additive Integration with SENTINEL Platform

- **Status:** Accepted
- **Date:** 2026-10-28
- **Context:** SENTINEL repository rules declare Web3, smart contracts, and image moderation files locked.
- **Decision:** Implement SENTINEL integration solely via new additive files placed in `integrations/sentinel/` (a Node.js client service, an additive webhook route, an additive SQL migration, and a badge component). No locked files in SENTINEL are modified.
- **Consequences:** Safe integration with zero risk of breaking existing SENTINEL services.

---

## ADR 005: Canonical Receipts using RFC 8785 (JCS) and Ed25519

- **Status:** Accepted
- **Date:** 2026-10-28
- **Context:** Screening verdicts must be cryptographically verifiable across different runtimes (Python, Node.js, browser JavaScript, Solidity). Standard JSON serialization is non-deterministic (key ordering, whitespace, float representations).
- **Decision:** Use RFC 8785 JSON Canonicalization Scheme (JCS) to produce canonical bytes, sign with Ed25519, and support zero-trust in-browser verification using WebCrypto.
- **Consequences:** Tamper-evident, universally verifiable detection receipts.

---

## ADR 006: Parallel Development Streams for Dual Collaborators

- **Status:** Accepted
- **Date:** 2026-10-28
- **Context:** Two teammates (@sharadpolackalsunil and @AdityaRaj1304) must collaborate concurrently without blocking dependencies or merge conflicts.
- **Decision:** Partition the project into two decoupled workstreams:
  - **Stream A (ML & Data Forensics):** Assigned to @sharadpolackalsunil. Covers preprocessing, model adapters, calibration, evidence heat-maps, drift detection, and the Paper B evaluation suite.
  - **Stream B (Systems, Full-Stack & Web3):** Assigned to @AdityaRaj1304. Covers core monorepo infra, FastAPI service, Celery task pipelines, reviewer console SPA, Merkle anchoring contracts, and SENTINEL adapters.
- **Consequences:** Clear task ownership, independent pull requests, and parallel velocity.

---

## ADR 007: Rebrand SENTINEL-V to VeriFrame (user-facing only)

- **Status:** Accepted
- **Date:** 2026-10-29
- **Context:** The product needed its own name, distinct from the SENTINEL platform it integrates with.
- **Decision:** Rename every user-facing string to **VeriFrame**: the web app (single source `web/src/brand.ts`), page titles and favicon, the OpenAPI title, the HTML/PDF case report headers, README and docs titles.
- **Not renamed, on purpose:**
  - Python packages and imports (`sv_core`, `sv_engine`, `sv_api`, …) and the `SV_` environment prefix: renaming them is a large refactor with no user value and would break deployments.
  - The receipt format `sv-receipt/1`, `/.well-known/sv-keys.json`, and the `issuer.name` inside receipts that were already signed (the signed demo receipt keeps its historical issuer name).
  - The `/compat/moderate/video` contract used by SENTINEL, and references to the separate S-MSDT and SENTINEL projects.
- **Follow-ups:** the GitHub repository rename and a name-availability check are human actions (QUESTIONS.md B9, B10). Container names in compose are unchanged to avoid breaking scripts.

---

## ADR 008: Design system, motion policy and honest demo data for the web app

- **Status:** Accepted
- **Date:** 2026-10-29
- **Context:** The console rendered hard-coded sample data and a simulated overlay without saying so, and had no home page.
- **Decision:**
  - Tokens as RGB channels in `web/src/index.css` (light and dark), primitives in `web/src/design/`, `framer-motion` (LazyMotion + `m.*`) for animation.
  - Motion: only opacity/transform/pathLength; durations 80–320 ms; loops pause off-screen; a user setting (system / reduce / full) maps to `MotionConfig reducedMotion`, and CSS loops stop under `html[data-motion='reduce']`.
  - Data: live API first. Where an endpoint does not exist yet (case list, review queue) or the API is unreachable, the console shows generated demo data with a persistent **DEMO DATA** badge and banner. Real analysis ids never fall back to demo data.
  - Demo scores are computed (`p_bal = σ(a·u + b)` with the Stage B calibration), bands come from the mirrored `strict-low-fpr` preset, and the demo video is a synthetic abstract subject (`web/scripts/make_demo_video.py`).
  - Metrics shown on the home page come only from `web/src/content/sourced/` with their source named.
- **Consequences:** The console looks and behaves like the product while being explicit about what is demo data. Routing moved from `HashRouter` to `BrowserRouter` (legacy `#/…` links redirect); nginx serves the SPA with a fallback and proxies `/v1`.
