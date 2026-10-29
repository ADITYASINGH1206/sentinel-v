# Changelog — VeriFrame (formerly SENTINEL-V)

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed — web 1.1.0: VeriFrame rebrand and UI overhaul
- Renamed the product to **VeriFrame** in all user-facing places (ADR 007).
- New public home page (`/`) with an animated scan illustration, "how it works" pipeline, feature grid, base-rate calculator using the S-MSDT paper's operating points, verify teaser, research and known-limitations section, FAQ.
- Console moved to `/app` with an animated, collapsible sidebar, breadcrumbs, theme toggle (system/light/dark, no flash), and page transitions; new Analyze (upload/URL with real upload progress), Cases (filters in the URL, CSV export), Review queue, Policies (presets + simulator via `POST /v1/policies/simulate`), and Settings (theme, motion, data source) pages.
- Case and review pages read `GET /v1/analyses/{id}`; review submissions use the API contract (`authentic | manipulated | cannot_tell`, `reasons`, required `confidence`) and surface HTTP errors instead of reporting success.
- Evidence player: real face-box geometry with letterboxing, labelled DEMO evidence grid only in demo mode, WebM + MP4 sources, frame stepping and peak-clip jump.
- Public verifier restyled; a signature only passes when a public key verified it (embedded or from `/.well-known/sv-keys.json`); Merkle roots without a proof, chain anchors and registry entries are reported as skipped rather than passed; file hashing is streamed in 8 MiB chunks.
- Removed the invented "Avg Triage Speed" metric and hard-coded case values.
- Web image now serves the SPA from nginx on port 8080 with `/v1` proxying (compose maps `5173:8080`).
- Tests: 26 vitest tests (copy rules over the rendered home page, brand guard, calibration maths, demo-data consistency, 422 handling, streamed hashing).

### Added
- **Milestone M10 (Paper B Evaluation Harness & Publication Figures):**
  - Standardized JSONL evaluation manifests for FaceForensics++ c23, DeepfakeDetection, and Celeb-DF v2 (eval/manifests/).
  - High-throughput batch score dumping tool 	ools/dump_scores.py for evaluating video datasets.
  - End-to-end evaluation harness implementing Paper B experiments E1 through E12 in eval/scripts/experiments/ (E1 Serving Parity, E2 Base Rates & Prevalence Sweeps, E3 Cascade Pareto Frontier, E4 In-the-Wild Perturbation Chains, E5 Latency/Cost/VRAM, E6 Calibration Transfer under Sample Budgets, E7 Serving Ablations, E8 Fusion & Generative Diffusion Gap, E9 Heatmap Explanation Faithfulness, E11 Longitudinal Drift & Recalibration, E12 Detection Receipt & Cryptographic Overhead).
  - Single experiment runner CLI eval/scripts/run_experiment.py --id <e1..e12> and all-experiment orchestrator eval/scripts/run_all.py.
  - Publication-grade vector figure generators in eval/figs/ producing vector PDF and SVG graphics (ig_roc, ig_cascade_pareto, ig_drift_timeline, ig_base_rates, ig_robustness_radar) directly from evaluation CSVs with mandatory screening-aid disclaimers.
  - Comprehensive automated test suite eval/tests/test_eval_harness.py verifying manifests, score dumping, experiment runners, and vector figure generators.
- **Milestone M11 (Security Hardening, SSRF Sandboxing, Fuzzing & Release Package):**
  - SSRF protection module `services/api/src/sv_api/security.py` with DNS pre-resolution, private/loopback/link-local/cloud-metadata IP filtering, and 3-hop redirect bounding.
  - Hardened streaming downloader `safe_download_file` with 500 MB size limit and connect/total timeouts.
  - Worker container sandboxing (`infra/compose.yaml`, `infra/docker/worker-cpu.Dockerfile`) with non-root user `svuser:1000`, read-only rootfs, tmpfs scratch spaces, isolated internal network, and cgroup resource limits.
  - Media parser fuzzing resilience (`decode.py`, `preprocess.py`) with dimension bounds ($1 \le w, h \le 8192$), zero-fps normalization, and clean `inconclusive: DECODE_FAILURE` worker fault tolerance.
  - Server-rendered PDF and HTML case audit reports (`services/api/src/sv_api/reports.py`) via `GET /v1/analyses/{analysis_id}/report.pdf` and `report.html`.
  - Locust load testing suite (`infra/locustfile.py`) benchmarking sustained screening throughput of $\ge 100$ videos/hour.
  - End-to-end demo execution script (`scripts/demo.sh`).
  - Security audit and threat modeling report in `docs/SECURITY_REVIEW.md`.
- **Milestone M9 (PSI Drift Monitoring & Governed Recalibration):**
  - 10-quantile PSI continuous drift monitoring with Laplace smoothing and categorical drift across video codecs/containers (`sv_monitor.drift`).
  - Multi-feature input drift evaluator tracking raw score, face size, detector confidence, frame rate, resolution, and codec.
  - Rolling 30-day Inverse-Probability Weighted (IPW) Expected Calibration Error (`compute_ece_ipw`) correcting for review queue selection bias.
  - Recalibration proposal generation with sample size / balance guards ($N \ge 200, \min(N_0, N_1) \ge 50$), Platt scaling calibration fitting, side-by-side reliability curve and confusion matrix generation (`sv_monitor.recalibration`).
  - Governed promotion (`promote_recalibration`) enforcing written admin justification and generating new immutable bundle version and SHA-256 hash.
  - Retention policy engine (`sv_monitor.retention`) enforcing 30-day raw media purge, 180-day evidence artifact purge, and 100% permanent preservation of Detection Receipts.
  - REST API endpoints under `/v1/monitor` and `/v1/models/{model_id}/recalibrations`.
- **Milestone M8 (SENTINEL Platform Integration, Webhooks & Supabase Schema):**
  - Additive compatibility endpoint `POST /compat/moderate/video` with `X-Internal-Key` authentication and synchronous wait up to `SV_COMPAT_SYNC_TIMEOUT_S=50` (or `status: pending` fallback).
  - HMAC-SHA256 webhook signing (`X-SV-Signature: t=<timestamp>,v1=<signature>`) and timing-safe signature verification with 300-second timestamp tolerance.
  - Asynchronous and synchronous webhook dispatchers (`dispatch_webhook`, `dispatch_webhook_sync`) integrated into Celery task finalization.
  - Additive SENTINEL deliverables in `integrations/sentinel/`:
    - `videoModerationService.js`: Non-blocking Axios client for video moderation.
    - `svWebhookRoutes.js`: Express webhook receiver with HMAC-SHA256 validation and Supabase posts table updating.
    - `schema_update_v6_video.sql`: Additive video moderation columns and indexes for Supabase posts table.
    - `VideoAuthenticityBadge.jsx`: React Tailwind badge with confidence percentage, decision band styling, and mandatory screening aid disclaimer.
    - `PATCH_NOTES.md`: One-line non-invasive wiring guide for `postController.js`.
  - Strict lock compliance verification tool `tools/check_locked_files.py` integrated into CI pipeline.
- **Milestone M7 (Detection Receipts & EVM Anchoring):**
  - RFC 8785 JSON Canonicalization Scheme (JCS) and Ed25519 digital signature signing/verification in `packages/sv_receipts`.
  - RFC 6962 compliant Merkle batching tree with domain separation prefixes (`0x00` leaf, `0x01` internal) and inclusion audit path generation.
  - Append-only human review receipts referencing previous verdicts via `supersedes`.
  - Immutable EVM smart contract `ReceiptAnchor.sol` and 100% coverage Foundry test suite in `ReceiptAnchor.t.sol`.
  - FastAPI endpoints for `/.well-known/sv-keys.json` (JWKS public keys), receipt retrieval, and review receipts.
  - Client-side zero-trust verification page `PublicVerify.tsx` running in-browser WebCrypto SHA-256 streaming, Ed25519 signature checks, and Merkle audit path validation with zero server dependencies.
- **Milestone M6 (Two-Stage Cost Cascade Tuning, Decision Policies & Policy Simulator):**
  - Two-stage cascade evaluation (`packages/sv_engine/src/sv_engine/cascade.py`) with Stage 1 S-MSDT-S ($T=1$) cheap screening and early-exit cutoff ($p_1 < \text{exit\_below\_p\_bal}$), escalating ambiguous/suspicious tracks to Stage 2 S-MSDT-ST ($T=8$).
  - Multi-track aggregation with maximum logit rule $u(V) = \max_j u_j$ and decisive track identification.
  - Decision band mapping (`assign_decision_band`) enforcing compliant bands: `likely_authentic`, `needs_review`, `likely_manipulated`, `inconclusive`.
  - Built-in policy presets: `strict-low-fpr` ($\pi=0.01$), `transfer-calibrated` ($\pi=0.05$), and `evidence-desk` ($\pi=0.20$).
  - Cascade threshold optimization tool (`tools/fit_cascade.py`) sweeping validation cutoffs to maximize early exit compute savings under strict fake leakage ($\le 1\%$) and stage agreement ($\ge 99\%$) constraints.
  - Prevalence-aware policy simulation engine (`tools/simulate_policy.py`) reproducing SPEC §7.4 benchmarks (138 flags/10k, 28.5% PPV at 1% prevalence).
  - Policy REST API endpoints (`services/api/src/sv_api/routes/policies.py`) supporting policy listing, creation with versioning, preset retrieval, and interactive prevalence simulation.
- **Milestone M5 (Reviewer Console SPA):**
  - Interactive EvidencePlayer syncing video playback with canvas heatmap overlay and bounding boxes.
  - ClipTimeline chart plotting clip anomaly probability over time with decision threshold $\tau$ and sampling windows.
  - ReviewWorkspace route supporting full single-key review triage (`1/2/3`, `Enter`, `P`, `H`, `Space`).
  - Dashboard route for review queue triage metrics and filterable case management.
  - CaseDetail route for technical audit inspection, container specs, and detection receipts.
  - Anti-deception copy rules and WCAG 2.2 AA accessibility verification.
- **Milestone M4 (Spatiotemporal Patch Evidence Maps & Video Overlay Rendering):**
  - Patch map reshaping from $(K, T, P)$ token logits to $(K, T, \text{grid}, \text{grid})$ with sigmoid non-linearity, bilinear upsampling to $224 \times 224$, and 16px reflection padding to $256 \times 256$ crop space (`reshape_patch_logits_to_map`).
  - Sub-pixel inverse affine matrix computation (`invert_affine_matrix`) with condition-number singularity checks and coordinate back-projection (`cv2.warpAffine`) onto original video frame dimensions with $< 0.1$ px round-trip error.
  - Perceptually uniform `magma` colormapping with fixed $[0, 1]$ scale and an alpha transparency floor at 0.15 (`apply_colormap_magma`).
  - WebP transparent frame sequence export capped at 720p with cryptographic SHA-256 digests (`save_webp_frame`).
  - Burned-in overlay MP4 rendering (`render_overlay_video`) with score banner and mandatory disclaimer (`"Screening aid — not proof. Human review required for consequential action."`).
  - Reviewer artifact manifest generation (`write_manifest_json`) and Merkle tree evidence root computation (`compute_evidence_root`).
  - End-to-end integration across Celery GPU task (`sv_workers.tasks.gpu`) and receipt generation (`sv_workers.tasks.finalize`).
- **Milestone M3 (FastAPI & Celery):**
  - Asynchronous SQLAlchemy models for analyses, tracks, media, users, and audit logs.
  - Argon2id, JWT, and SHA-256 API-key authentication.
  - Celery pipeline tasks (`ingest`, `preprocess`, `gpu`, `finalize`).
  - Redis Pub/Sub SSE progress streaming with in-memory queue fallback.
  - REST endpoints for analyses submission, status polling, and evidence retrieval.
- **Milestone M2 (Adapters, Bundle & Parity):**
  - S-MSDT model adapters (`clip_st`, `clip_s`, `cnn_p1`, `full_c` guard).
  - Model bundle builder (`tools/make_bundle.py`) with SHA-256 checksum verification.
  - Calibration fitting tool (`tools/fit_calibration.py`) for Platt parameters, Youden threshold, and ECE.
  - Parity check validation harness (`tools/parity_check.py`).
- **Milestone M1 (Video Preprocessing):**
  - PyAV decoding with presentation timestamping (PTS), sampling windows, and rotation normalization.
  - Multi-face tracking with greedy IoU matching and Savitzky-Golay landmark smoothing.
  - Affine transformation to 256x256 ArcFace template and center cropping to 224x224.
  - Inconclusive classification for small faces, decode failures, and short tracks.
  - Compressed NPZ archive serialization for tracked face clips.

## [0.1.0] - 2026-10-28
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
