# Changelog — SENTINEL-V

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Milestone M5 (Reviewer Console SPA):**
  - Interactive EvidencePlayer syncing video playback with canvas heatmap overlay and bounding boxes.
  - ClipTimeline chart plotting clip anomaly probability over time with decision threshold $\tau$ and sampling windows.
  - ReviewWorkspace route supporting full single-key review triage (`1/2/3`, `Enter`, `P`, `H`, `Space`).
  - Dashboard route for review queue triage metrics and filterable case management.
  - CaseDetail route for technical audit inspection, container specs, and detection receipts.
  - Anti-deception copy rules and WCAG 2.2 AA accessibility verification.
- **Milestone M1 (Video Preprocessing):**
  - PyAV decoding with presentation timestamping (PTS), sampling windows, and rotation normalization.
  - Multi-face tracking with greedy IoU matching and Savitzky-Golay landmark smoothing.
  - Affine transformation to 256x256 ArcFace template and center cropping to 224x224.
  - Inconclusive classification for small faces, decode failures, and short tracks.
  - Compressed NPZ archive serialization for tracked face clips.
- **Milestone M2 (Adapters, Bundle & Parity):**
  - S-MSDT model adapters (`clip_st`, `clip_s`, `cnn_p1`, `full_c` guard).
  - Model bundle builder (`tools/make_bundle.py`) with SHA-256 checksum verification.
  - Calibration fitting tool (`tools/fit_calibration.py`) for Platt parameters, Youden threshold, and ECE.
  - Parity check validation harness (`tools/parity_check.py`).
- **Milestone M3 (FastAPI & Celery):**
  - Asynchronous SQLAlchemy models for analyses, tracks, media, users, and audit logs.
  - Argon2id, JWT, and SHA-256 API-key authentication.
  - Celery pipeline tasks (`ingest`, `preprocess`, `gpu`, `finalize`).
  - Redis Pub/Sub SSE progress streaming with in-memory queue fallback.
  - REST endpoints for analyses submission, status polling, and evidence retrieval.

## [0.1.0] - 2026-10-28

### Added
- Monorepo directory structure across `packages/`, `services/`, `web/`, `contracts/`, `eval/`, and `infra/`.
- Full project specification in `docs/SPEC.md` and agent instructions in `AGENTS.md`.
- Architecture decision records in `docs/DECISIONS.md`.
- Blocker tracking log in `docs/QUESTIONS.md`.
- Milestone tracking templates under `docs/milestones/`.
- Foundational packages:
  - `sv_core`: Settings via pydantic-settings, domain schemas, error classes, RFC 8785 canonical JSON serializer.
  - `sv_engine`: Preprocessing interfaces, model adapter protocols, deterministic mock engine.
  - `sv_fusion`: Multi-signal fusion interfaces (C2PA, SwinV2 AI image detector).
  - `sv_receipts`: Cryptographic detection receipt generation, Ed25519 signing, Merkle trees.
- API service scaffold with FastAPI endpoints, CORS, health checks, and SSE streams.
- Reviewer console web application scaffold (React, TypeScript, Vite, Tailwind).
- Solidity contract `ReceiptAnchor.sol` and Foundry suite for EVM anchoring.
- Docker compose orchestration and Makefile automation.

