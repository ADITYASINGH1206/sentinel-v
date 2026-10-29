# Changelog — SENTINEL-V

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-10-29

### Added
- **Milestone M4: Spatiotemporal Patch Evidence Maps & Video Overlay Rendering**:
  - Patch map reshaping from $(K, T, P)$ token logits to $(K, T, \text{grid}, \text{grid})$ with sigmoid non-linearity, bilinear upsampling to $224 \times 224$, and 16px reflection padding to $256 \times 256$ crop space (`reshape_patch_logits_to_map`).
  - Sub-pixel inverse affine matrix computation (`invert_affine_matrix`) and coordinate back-projection (`cv2.warpAffine`) onto original video frame dimensions with $< 0.1$ px round-trip error.
  - Perceptually uniform `magma` colormapping with fixed $[0, 1]$ scale and an alpha transparency floor at 0.15 (`apply_colormap_magma`).
  - WebP transparent frame sequence export capped at 720p with cryptographic SHA-256 digests (`save_webp_frame`).
  - Burned-in overlay MP4 rendering (`render_overlay_video`) with score banner and mandatory disclaimer (`"Screening aid — not proof. Human review required for consequential action."`).
  - Reviewer artifact manifest generation (`write_manifest_json`) and Merkle tree evidence root computation (`compute_evidence_root`).
  - End-to-end integration across Celery GPU task (`sv_workers.tasks.gpu`) and receipt generation (`sv_workers.tasks.finalize`).
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
