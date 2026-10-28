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
