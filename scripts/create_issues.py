#!/usr/bin/env python3
import subprocess
import json

ISSUES = [
    {
        "title": "[M1-ML] Video Preprocessing, InsightFace Tracking & Sampling Pipeline",
        "milestone": "M1: Preprocessing & Tracking",
        "labels": ["stream:ml", "priority:p0", "parallel-paired"],
        "assignee_tag": "@sharadpolackalsunil",
        "parallel_partner": "@AdityaRaj1304 (working on M3: API Gateway & Celery Pipelines)",
        "body": """### Objective
Implement the complete video ingestion and preprocessing pipeline conforming to SPEC §2.3, §6.3, and Appendix A.

### Assignee: @sharadpolackalsunil
**Parallel Stream:** Stream A (ML & Data Forensics)  
**Concurrent Partner:** @AdityaRaj1304 (handling Issue #2 - M3 API Gateway & Celery Pipelines)

---

### Key Requirements
1. **Decode (`packages/sv_engine/src/sv_engine/preprocess/decode.py`):**
   - Use PyAV for frame-accurate decoding.
   - Respect video rotation metadata from container.
   - Convert variable frame rate (VFR) to deterministic index timeline.
   - Implement sampling: decode up to 30s x fps; for videos > 30s, select 4 windows evenly spaced (32 frames each) plus the first 8s.
2. **Face Detection (`faces.py`):**
   - Wrap InsightFace `buffalo_l` (`det_size=(320,320)`).
   - Return boxes, scores, 5-point landmarks, and 106-point landmarks.
3. **Multi-Track Tracking (`tracks.py`):**
   - Greedy IoU association (IoU >= 0.3, max gap 5 frames).
   - Keep up to 4 tracks with >= 8 frames. Drop tracks with median inter-ocular distance < 24 px.
   - Smooth 106-point landmarks with Savitzky-Golay filter matching upstream constants.
4. **Alignment & Cropping (`align.py`):**
   - Import and call upstream `smsdt.preprocess.align_crop.crop_frame(frame_bgr, kps5, out=256, margin=1.3)`.
   - Perform deterministic center-crop 224 from 256.
   - Compute and store affine transformation matrix $M$ and $M_{224} = \\text{translate}(-16, -16) \\circ M$ for back-projection.
5. **Clip Formation (`clips.py`):**
   - Call upstream `contiguous_starts(fidx, T=8, stride=1)`.
   - Sample $K=8$ clips of $T=8$ contiguous frames per track.
   - Serialize preprocessed arrays to S3/MinIO as uint8 `.npz`.
6. **Inconclusive Handling:**
   - Detect and flag `NO_FACE` (>= 90% frames without face), `FACE_TOO_SMALL` (< 24 px IOD), and `TOO_FEW_FRAMES` (< 8 frames).

---

### Target Files
- `packages/sv_engine/src/sv_engine/preprocess/decode.py`
- `packages/sv_engine/src/sv_engine/preprocess/faces.py`
- `packages/sv_engine/src/sv_engine/preprocess/tracks.py`
- `packages/sv_engine/src/sv_engine/preprocess/align.py`
- `packages/sv_engine/src/sv_engine/preprocess/clips.py`
- `packages/sv_engine/tests/test_preprocess.py`

---

### Acceptance Criteria & Tests
- [ ] Synthetic video unit tests passing (no-face, small-face, multi-track).
- [ ] Landmark smoothing reproduces upstream `build_store.py` numerical outputs.
- [ ] **Crop SSIM Parity >= 0.98** against upstream S-MSDT store on 20 validation videos (`make parity-crops`).
"""
    },
    {
        "title": "[M3-SYS] FastAPI Gateway Core, Celery Task Queues & Redis SSE Pipeline",
        "milestone": "M3: API Gateway & Celery Pipelines",
        "labels": ["stream:systems", "priority:p0", "parallel-paired"],
        "assignee_tag": "@AdityaRaj1304",
        "parallel_partner": "@sharadpolackalsunil (working on M1: Video Preprocessing & Tracking)",
        "body": """### Objective
Build the production API gateway, database models, and Celery distributed worker pipeline conforming to SPEC §3, §19, and §20.

### Assignee: @AdityaRaj1304
**Parallel Stream:** Stream B (Systems, Full-Stack & Web3)  
**Concurrent Partner:** @sharadpolackalsunil (handling Issue #1 - M1 Preprocessing Pipeline)

---

### Key Requirements
1. **Database Schema & Migrations (`services/api/src/sv_api/models/` + Alembic):**
   - PostgreSQL 16 schema matching SPEC §20: `users`, `api_keys`, `media`, `model_versions`, `policies`, `analyses`, `tracks`, `clip_scores`, `evidence_artifacts`, `reviews`, `receipts`, `anchor_batches`, `drift_snapshots`, `audit_log`.
2. **Celery Worker Pipeline (`services/workers/src/sv_workers/tasks/`):**
   - Named queues: `ingest`, `preprocess`, `gpu`, `finalize`, `anchor`, `monitor`.
   - `ingest`: download with SSRF protections, magic byte sniffing, ffprobe metadata extraction, SHA-256 calculation.
   - **Deduplication:** check if `(sha256, model_bundle_id, policy_version)` completed within 30 days; return `cache_hit=true`.
   - `preprocess`: trigger M1 preprocessing; store `.npz` tensors.
   - `gpu`: invoke S-MSDT cascade inference.
   - `finalize`: aggregate tracks, apply calibration, evaluate fusion, create receipt, publish SSE events.
3. **API Endpoints (`services/api/src/sv_api/routes/`):**
   - `POST /v1/analyses`: 202 acceptance, multipart upload or URL.
   - `GET /v1/analyses/{id}`: full analysis summary.
   - `GET /v1/analyses/{id}/events`: SSE stream of stage progress `{stage, pct, message}`.
   - `GET /v1/analyses/{id}/evidence`: presigned URLs for WebP maps and overlay MP4.
4. **Authentication & Audit Logging:**
   - Local accounts (Argon2id), JWT access (15 min) and refresh (7d).
   - API keys with prefix `sv_live_` (hashed SHA-256 in DB).
   - Audit logging on every mutation.

---

### Target Files
- `services/api/src/sv_api/routes/analyses.py`
- `services/api/src/sv_api/auth.py`
- `services/api/src/sv_api/sse.py`
- `services/workers/src/sv_workers/tasks/`
- `services/api/tests/test_analyses_pipeline.py`

---

### Acceptance Criteria & Tests
- [ ] Integration test: upload -> completed status in mock engine mode.
- [ ] Deduplication cache returns cached analysis on identical file.
- [ ] Worker crash recovery: Celery `acks_late=True` prevents lost jobs.
- [ ] Read API latency p95 < 100 ms under 50 RPS.
"""
    },
    {
        "title": "[M2-ML] S-MSDT Model Adapters, Bundle Builder & Calibration Parity",
        "milestone": "M2: Engine, Adapters & Calibration",
        "labels": ["stream:ml", "priority:p0", "parallel-paired"],
        "assignee_tag": "@sharadpolackalsunil",
        "parallel_partner": "@AdityaRaj1304 (working on M5: Reviewer Console Core Workspace)",
        "body": """### Objective
Implement the model adapters for S-MSDT variants, strict checkpoint loading, model bundle builder, and validation parity tooling conforming to SPEC §2, §6, and Appendix A.

### Assignee: @sharadpolackalsunil
**Parallel Stream:** Stream A (ML & Data Forensics)  
**Concurrent Partner:** @AdityaRaj1304 (handling Issue #4 - M5 Reviewer Console)

---

### Key Requirements
1. **Model Adapters (`packages/sv_engine/src/sv_engine/adapters/`):**
   - `clip_st.py` (Stage B): `CLIPFrameEncoder` (LayerNorm tuned, `grad_ckpt=False`) + `SMSDTv2`.
   - `clip_s.py` (Stage A): CLIP ViT-L/14 with $T=1$ clip sampling.
   - `cnn_p1.py` (Phase 1): `SMSDT` EfficientNet-B4 + Haar DWT + DensePSIT. Normalization: $[0, 1]$ (no mean/std).
   - `full_c.py` (Stage C): Implement Blocker B1 guard (raise `NotImplementedError` until v3 modules pushed).
   - Strict checkpoint loading: assert `missing_keys == []` and `unexpected_keys == []`.
2. **Model Bundle Format (`models/bundle-.../` & `tools/make_bundle.py`):**
   - Convert `.pt` weights to `.safetensors`.
   - Save CLIP vision backbone offline (no HuggingFace Hub downloads at runtime).
   - Generate `checksums.sha256` for all bundle assets; worker must refuse startup on mismatch.
3. **Calibration Fitting Tool (`tools/fit_calibration.py`):**
   - Class-balanced Platt scaling fitting on validation logits.
   - Calculate Youden-optimal threshold $\\tau^*$ and operating points (TPR @ 1% FPR, TPR @ 5% FPR, 15-bin ECE).
4. **Parity Check Harness (`tools/parity_check.py`):**
   - Validate serving pipeline against `smsdt.eval_cross` on >= 50 validation videos.
   - Criteria: median $|u_{\\text{serve}} - u_{\\text{research}}| \\le 0.05$, p95 $\\le 0.20$, AUC difference $\\le 0.005$.

---

### Target Files
- `packages/sv_engine/src/sv_engine/adapters/clip_st.py`
- `packages/sv_engine/src/sv_engine/adapters/clip_s.py`
- `packages/sv_engine/src/sv_engine/adapters/cnn_p1.py`
- `tools/make_bundle.py`
- `tools/fit_calibration.py`
- `tools/parity_check.py`

---

### Acceptance Criteria & Tests
- [ ] Strict weight loading verifies clean state dicts.
- [ ] Parity test passes on reference GPU: median $|\\Delta u| \\le 0.05$.
- [ ] Checksum verification fails loudly if any bundle file is modified.
"""
    },
    {
        "title": "[M5-SYS] Reviewer Console Core Workspace, Evidence Player & Keyboard Review",
        "milestone": "M5: Reviewer Console SPA",
        "labels": ["stream:systems", "priority:p0", "parallel-paired"],
        "assignee_tag": "@AdityaRaj1304",
        "parallel_partner": "@sharadpolackalsunil (working on M2: Model Adapters & M4: Evidence Maps)",
        "body": """### Objective
Build the high-speed, accessible Reviewer Console SPA and keyboard-driven decision workspace conforming to SPEC §14.

### Assignee: @AdityaRaj1304
**Parallel Stream:** Stream B (Systems, Full-Stack & Web3)  
**Concurrent Partner:** @sharadpolackalsunil (handling Issue #3 - M2 Model Adapters & Issue #5 - M4 Evidence Maps)

---

### Key Requirements
1. **Evidence Player (`web/src/components/EvidencePlayer.tsx`):**
   - Sync `<video>` playback with `<canvas>` heat-map overlay using `requestVideoFrameCallback`.
   - Controls: Play/Pause (`Space`), Frame step (`Left`/`Right`), Jump to peak clip (`P`), Toggle overlay (`H`), Opacity slider, Multi-track selector.
   - Bounding boxes per face track.
2. **Clip Timeline (`web/src/components/ClipTimeline.tsx`):**
   - Recharts area/step chart showing clip probability vs time per track.
   - Horizontal threshold line at $\\tau$ (decision band boundary).
   - Shaded analysis sampling windows. Clickable seek points.
3. **Review Workspace (`web/src/routes/ReviewWorkspace.tsx`):**
   - Right-hand decision panel: Authentic (`1`), Manipulated (`2`), Cannot tell (`3`).
   - Checkbox reason codes: Blending seam, Mouth/teeth, Temporal flicker, Lighting, Identity mismatch.
   - Keyboard submit (`Enter`) immediately opens next queue item.
   - Record telemetry: `time_to_decision_ms`, `overlay_toggled_count`.
4. **Copy & Accessibility Compliance (`web/src/copy/forbidden.ts`):**
   - Strict ban on bare "FAKE"/"REAL" stamps. Mandatory inclusion of screening aid disclaimer.
   - WCAG 2.2 AA compliance: keyboard reachable, screen reader labels, color not sole carrier.

---

### Target Files
- `web/src/components/EvidencePlayer.tsx`
- `web/src/components/ClipTimeline.tsx`
- `web/src/routes/ReviewWorkspace.tsx`
- `web/src/routes/CaseDetail.tsx`
- `web/src/routes/Dashboard.tsx`

---

### Acceptance Criteria & Tests
- [ ] Playwright e2e test: Complete review flow using keyboard shortcuts only (`1/2/3`, `Enter`).
- [ ] Axe accessibility audit: 0 serious or critical violations.
- [ ] Initial JS bundle <= 250 KB gzipped.
"""
    },
    {
        "title": "[M4-ML] Spatiotemporal Patch Evidence Maps & Video Overlay Rendering",
        "milestone": "M4: Evidence & Explainability",
        "labels": ["stream:ml", "parallel-paired"],
        "assignee_tag": "@sharadpolackalsunil",
        "parallel_partner": "@AdityaRaj1304 (working on M5: Reviewer Console)",
        "body": """### Objective
Implement spatiotemporal patch evidence extraction, coordinate back-projection, and video overlay rendering conforming to SPEC §8.

### Assignee: @sharadpolackalsunil
**Parallel Stream:** Stream A (ML & Data Forensics)  
**Concurrent Partner:** @AdityaRaj1304 (handling Issue #4 - M5 Reviewer Console)

---

### Key Requirements
1. **Patch Map Reshaping & Upsampling (`packages/sv_engine/src/sv_engine/evidence.py`):**
   - Extract patch logits $(K, T, P)$ from deciding model readout.
   - Reshape to $(grid, grid)$, apply sigmoid.
   - Bilinearly upsample to $224 \\times 224$. Pad back to $256 \\times 256$ (16px border).
2. **Back-Projection to Original Frame:**
   - Invert the forward affine crop matrix $M^{-1}$.
   - Warp 256 map back onto original frame resolution $(W, H)$ using `cv2.warpAffine(..., flags=INTER_LINEAR)`.
3. **Color Mapping & Artifact Generation:**
   - Apply sequential `magma` colormap.
   - Fixed scale $[0, 1]$ on $\\sigma(\\text{patch\\_logit})$ (never per-frame min-max normalization).
   - Alpha channel floor at 0.15 (below 0.15 is transparent).
   - Output WebP frames (capped at 720p) + `manifest.json`.
   - Render `overlay_{track}.mp4` (H.264, 720p, burned-in heat-map and score banner).
4. **Evidence Merkle Root:**
   - Compute SHA-256 for every generated artifact; derive `evidence_root` for detection receipt.

---

### Target Files
- `packages/sv_engine/src/sv_engine/evidence.py`
- `packages/sv_engine/src/sv_engine/overlay_render.py`
- `packages/sv_engine/tests/test_evidence.py`

---

### Acceptance Criteria & Tests
- [ ] Geometric back-projection round-trip test: warping coordinates and inverting yields error < 0.5 px.
- [ ] Generated WebP frames and MP4 overlays render with correct opacity and alignment.
- [ ] Artifact SHA-256 hashes match `manifest.json`.
"""
    },
    {
        "title": "[M6-ML] Two-Stage Cost Cascade Tuning, Decision Policies & Policy Simulator",
        "milestone": "M6: Policies & Cost Cascade",
        "labels": ["stream:ml", "parallel-paired"],
        "assignee_tag": "@sharadpolackalsunil",
        "parallel_partner": "@AdityaRaj1304 (working on M7: Receipts & EVM Anchoring)",
        "body": """### Objective
Implement the two-stage cost cascade, policy management, and prevalence-aware policy simulation engine conforming to SPEC §6.5, §6.6, and §7.

### Assignee: @sharadpolackalsunil
**Parallel Stream:** Stream A (ML & Data Forensics)  
**Concurrent Partner:** @AdityaRaj1304 (handling Issue #7 - M7 Receipts & EVM Anchoring)

---

### Key Requirements
1. **Cascade Execution (`packages/sv_engine/src/sv_engine/cascade.py`):**
   - Stage 1: S-MSDT-S ($T=1$). Compute $p_1 = \\sigma(a_1 u_1 + b_1)$.
   - Early Exit: If $p_1 < \\text{exit\\_below\\_p\\_bal}$, exit early without invoking Stage 2.
   - Stage 2: S-MSDT-ST ($T=8$). Compute final $p_{\\text{bal}} = \\sigma(a_2 u_2 + b_2)$.
   - Track aggregation: $u(V) = \\max_j u_j$, decisive track = $\\arg\\max_j u_j$.
2. **Cascade Threshold Optimization (`tools/fit_cascade.py`):**
   - Sweep threshold on validation set to find largest exit cutoff where <= 1% validation fakes exit early and stage-2 agreement >= 99%.
3. **Policy Presets & Bands:**
   - Presets: `strict-low-fpr` (S -> ST, $\\pi=0.01$), `transfer-calibrated` (S -> Full/ST, $\\pi=0.05$), `evidence-desk` (ST/Full only, $\\pi=0.20$).
4. **Policy Simulator Engine (`tools/simulate_policy.py` & API):**
   - Interactive calculation of expected flags per 10k, PPV, and missed fakes across prevalence range $\\pi \\in [0.1\\%, 20\\%]$.

---

### Target Files
- `packages/sv_engine/src/sv_engine/cascade.py`
- `tools/fit_cascade.py`
- `tools/simulate_policy.py`
- `packages/sv_engine/tests/test_cascade.py`

---

### Acceptance Criteria & Tests
- [ ] Cascade correctly exits early on authentic clips and escalates ambiguous/fake clips.
- [ ] Policy simulator reproduces SPEC §7.4 base-rate table exactly on Paper A test operating points.
"""
    },
    {
        "title": "[M7-SYS] Detection Receipts, Ed25519 Signing, Merkle Batches & Solidity Contract",
        "milestone": "M7: Receipts & EVM Anchoring",
        "labels": ["stream:systems", "parallel-paired"],
        "assignee_tag": "@AdityaRaj1304",
        "parallel_partner": "@sharadpolackalsunil (working on M6: Cost Cascade & Policy Math)",
        "body": """### Objective
Implement cryptographically verifiable Detection Receipts, RFC 8785 canonical serialization, Ed25519 signatures, Merkle batch trees, and Solidity contract anchoring conforming to SPEC §10.

### Assignee: @AdityaRaj1304
**Parallel Stream:** Stream B (Systems, Full-Stack & Web3)  
**Concurrent Partner:** @sharadpolackalsunil (handling Issue #6 - M6 Cost Cascade)

---

### Key Requirements
1. **Canonical Receipts (`packages/sv_receipts/`):**
   - Canonical JSON serialization via RFC 8785 (JCS).
   - Ed25519 signing using `cryptography` package.
   - Public key distribution at `/.well-known/sv-keys.json`.
   - Append-only review receipts: when human review completes, issue new receipt with `supersedes: <old_receipt_id>`.
2. **Merkle Batching Engine (`merkle.py` & `anchor-worker`):**
   - Collect receipts in configurable time window (default 600s).
   - Leaf: `sha256(0x00 || receipt_sha256)`.
   - Internal: `sha256(0x01 || left || right)`. Odd level duplication.
   - Generate and verify audit inclusion proofs.
3. **Smart Contract (`contracts/src/ReceiptAnchor.sol`):**
   - Deploy immutable `ReceiptAnchor.sol` to Sepolia or Amoy testnet.
   - Owner-only anchoring: `anchor(bytes32 root, uint32 count, string batchId)`.
4. **Zero-Trust Client-Side Verification (`web/src/routes/PublicVerify.tsx`):**
   - 5-step verification: Ed25519 signature, file SHA-256 (via WebCrypto streaming), Merkle proof, EVM contract read (ethers.js), model hash registry.

---

### Target Files
- `packages/sv_receipts/src/sv_receipts/schema.py`
- `packages/sv_receipts/src/sv_receipts/crypto.py`
- `packages/sv_receipts/src/sv_receipts/merkle.py`
- `contracts/src/ReceiptAnchor.sol`
- `web/src/routes/PublicVerify.tsx`

---

### Acceptance Criteria & Tests
- [ ] Foundry test suite: 100% coverage on `ReceiptAnchor.sol` (revert unauthorized, prevent duplicate roots).
- [ ] Tampering test: Modifying any receipt field or 1 byte of the media file causes verification failure.
- [ ] Browser-based WebCrypto verification passes without backend API dependency.
"""
    },
    {
        "title": "[M8-SYS] SENTINEL Integration Adapter, Webhook Dispatch & Supabase Schema",
        "milestone": "M8: SENTINEL Platform Integration",
        "labels": ["stream:systems", "parallel-paired"],
        "assignee_tag": "@AdityaRaj1304",
        "parallel_partner": "@sharadpolackalsunil (working on M9: Drift Monitoring & ECE)",
        "body": """### Objective
Implement the additive, non-invasive integration adapter between SENTINEL-V and the SENTINEL Web3 content-verification platform conforming to SPEC §11.

### Assignee: @AdityaRaj1304
**Parallel Stream:** Stream B (Systems, Full-Stack & Web3)  
**Concurrent Partner:** @sharadpolackalsunil (handling Issue #9 - M9 Drift Monitoring)

---

### Key Requirements
1. **Compatibility Endpoint (`services/api/src/sv_api/routes/compat.py`):**
   - `POST /compat/moderate/video` accepting `{ post_id, video_url }` with `X-Internal-Key` header.
   - Synchronous wait up to `SV_COMPAT_SYNC_TIMEOUT_S=50`, returning payload or `status: "pending"`.
2. **Webhook Dispatch:**
   - When analysis finishes asynchronously, POST final verdict to configured `SENTINEL_WEBHOOK_URL`.
   - Sign payload with HMAC-SHA256 in header `X-SV-Signature: t=<timestamp>,v1=<hex>`.
3. **Additive SENTINEL Deliverables (`integrations/sentinel/`):**
   - `videoModerationService.js`: Non-blocking Axios client for SENTINEL backend.
   - `svWebhookRoutes.js`: Webhook receiver updating Supabase post records.
   - `schema_update_v6_video.sql`: Additive video moderation columns for Supabase.
   - `VideoAuthenticityBadge.jsx`: Tailwind UI badge linking to SENTINEL-V evidence page.
4. **Strict Lock Compliance:**
   - Verify that zero locked files in the SENTINEL repository are modified (CI diff-check).

---

### Target Files
- `services/api/src/sv_api/routes/compat.py`
- `integrations/sentinel/backend/services/videoModerationService.js`
- `integrations/sentinel/backend/routes/svWebhookRoutes.js`
- `integrations/sentinel/backend/supabase/schema_update_v6_video.sql`
- `integrations/sentinel/frontend/src/components/VideoAuthenticityBadge.jsx`

---

### Acceptance Criteria & Tests
- [ ] Test video submission via `/compat/moderate/video` returns expected schema.
- [ ] Webhook HMAC signature verification passes.
- [ ] CI diff check verifies no locked SENTINEL files are modified.
"""
    },
    {
        "title": "[M9-ML] Population Stability Index (PSI) Drift Monitoring & Governed Recalibration",
        "milestone": "M9: Monitoring & Drift",
        "labels": ["stream:ml", "parallel-paired"],
        "assignee_tag": "@sharadpolackalsunil",
        "parallel_partner": "@AdityaRaj1304 (working on M8: SENTINEL Integration)",
        "body": """### Objective
Implement statistical drift monitoring (PSI), rolling ECE tracking, and the governed model recalibration pipeline conforming to SPEC §13.

### Assignee: @sharadpolackalsunil
**Parallel Stream:** Stream A (ML & Data Forensics)  
**Concurrent Partner:** @AdityaRaj1304 (handling Issue #8 - M8 SENTINEL Integration)

---

### Key Requirements
1. **Statistical Drift Detection (`services/monitor/src/sv_monitor/drift.py`):**
   - Score Drift: Compute daily Population Stability Index (PSI) between production logits and bundle validation reference (`reference_scores.parquet`) using 10 quantile bins.
   - Status: PSI < 0.1 OK, 0.1 - 0.25 Watch, > 0.25 Alert.
   - Input Drift: Calculate PSI on face size, detector confidence, frame rate, resolution, and codec.
2. **Calibration Monitoring:**
   - Calculate rolling 30-day Expected Calibration Error (ECE, 15 equal bins) on reviewed items using inverse-probability weighting (accounting for audit sampling rate).
3. **Governed Recalibration Workflow (`recalibration.py`):**
   - `POST /v1/models/{id}/recalibrations`: fit new candidate calibration on reviewed expert items (n >= 200, >= 50 per class).
   - Side-by-side reliability diagrams and confusion matrices before and after.
   - Formal promotion requires admin written justification, generating a new bundle hash. Never overwrite old calibrations.
4. **Retention Worker (`services/monitor/src/sv_monitor/retention.py`):**
   - Nightly automated purging of raw media older than 30 days and evidence artifacts older than 180 days. Receipts preserved permanently.

---

### Target Files
- `services/monitor/src/sv_monitor/drift.py`
- `services/monitor/src/sv_monitor/recalibration.py`
- `services/monitor/src/sv_monitor/retention.py`
- `services/monitor/tests/test_drift.py`

---

### Acceptance Criteria & Tests
- [ ] Simulated 30-day domain shift triggers PSI alert at the expected inflection point.
- [ ] Inverse probability weighting calculation tested against unweighted review data.
- [ ] Retention job purges media while keeping signed detection receipts intact.
"""
    },
    {
        "title": "[M10-ML] Paper B Evaluation Harness Execution (Experiments E1-E12) & Figures",
        "milestone": "M10: Evaluation Harness & Paper B",
        "labels": ["stream:ml", "parallel-paired"],
        "assignee_tag": "@sharadpolackalsunil",
        "parallel_partner": "@AdityaRaj1304 (working on M11: Security Hardening & Release)",
        "body": """### Objective
Build and run the complete experimental evaluation harness for Paper B, generating all results CSVs and publication figures conforming to SPEC §15.

### Assignee: @sharadpolackalsunil
**Parallel Stream:** Stream A (ML & Data Forensics)  
**Concurrent Partner:** @AdityaRaj1304 (handling Issue #10 - M11 Security Hardening)

---

### Key Requirements
1. **Score Extraction Engine (`tools/dump_scores.py`):**
   - Run serving pipeline over evaluation manifests (`eval/manifests/` for FF++ c23, DFD, Celeb-DF v2).
2. **Execute Paper B Experiments (`eval/scripts/`):**
   - **E1 Parity:** Serving vs research evaluation comparison ($|\\Delta u|$, AUC, crop SSIM).
   - **E2 Base Rates:** Precision vs prevalence curves across $\\pi \\in [0.1\\%, 20\\%]$.
   - **E3 Cascade:** Pareto curve of GPU compute saving vs TPR @ 1% FPR.
   - **E4 In-the-Wild Robustness:** Perturbation chains (CRF 28/35, 480p, 15fps, messaging-app, screen-capture).
   - **E5 Latency & Cost:** Per-stage latency p50/p95, parameters, and screening cost per 1k videos.
   - **E6 Calibration Transfer:** Target-domain recalibration label-budget curves ($N \\in \\{25, 50, 100, 200\\}$).
   - **E7 Serving Ablations:** $K$ clips, windowing strategy, multi-track aggregation.
   - **E8 Fusion & Generative Gap:** Evaluate face manipulation vs still-image AI detector on fully generated videos.
   - **E9 Explanation Faithfulness:** Pointing game, top-10% IoU, and deletion AUC against difference masks.
   - **E11 Drift Simulation:** 30-day synthetic drift trajectory.
   - **E12 Receipt Overhead:** Merkle proof sizes, verification latency, and gas benchmarking.
3. **Figure Generation (`eval/figs/`):**
   - Scripts generating vector figures (PDF/SVG) directly from output CSVs. No hardcoded plot numbers.

---

### Target Files
- `tools/dump_scores.py`
- `eval/scripts/run_experiment.py`
- `eval/scripts/run_all.py`
- `eval/figs/roc.py`
- `eval/figs/cascade_pareto.py`
- `eval/figs/drift_timeline.py`

---

### Acceptance Criteria & Tests
- [ ] `make eval-all` executes and produces all CSV files in `eval/results/`.
- [ ] Every number in figures traces directly to an experimental CSV.
"""
    },
    {
        "title": "[M11-SYS] Security Hardening, SSRF Sandboxing, Load Testing & Release Package",
        "milestone": "M11: Security Hardening & Release",
        "labels": ["stream:systems", "parallel-paired"],
        "assignee_tag": "@AdityaRaj1304",
        "parallel_partner": "@sharadpolackalsunil (working on M10: Evaluation Harness & Paper B)",
        "body": """### Objective
Execute the comprehensive security hardening checklist, SSRF sandboxing, media fuzzing, and load testing conforming to SPEC §12, §21, and §23.

### Assignee: @AdityaRaj1304
**Parallel Stream:** Stream B (Systems, Full-Stack & Web3)  
**Concurrent Partner:** @sharadpolackalsunil (handling Issue #10 - M10 Evaluation Harness)

---

### Key Requirements
1. **SSRF Sandboxing & Ingest Hardening (`services/api/src/sv_api/security.py`):**
   - Pre-resolve DNS before connecting; block private (10/8, 172.16/12, 192.168/16), loopback (127/8), link-local, and AWS/GCP cloud metadata IP ranges (169.254.169.254).
   - Enforce maximum 3 redirects; re-resolve DNS at each redirect hop.
   - Stream size limits (`SV_MAX_UPLOAD_MB=500`), connect timeout 10s, total 120s.
2. **Worker Container Sandboxing:**
   - Isolated Docker container network (`internal`).
   - Non-root user execution, read-only root filesystem, tmpfs scratch space, cgroup CPU/memory caps.
3. **Media Parser Fuzzing & Resilience:**
   - Fuzz testing against malformed MP4, MOV, MKV files (truncated moov atoms, extreme dimensions, zero fps). Must reject cleanly without crash or infinite hang.
4. **Locust Load Testing:**
   - Benchmark sustained screening of 100 videos/hour on reference GPU without queue accumulation or memory leaks.
5. **PDF Case Report Generation:**
   - Server-rendered Playwright PDF export containing verdict card, keyframe overlays, timeline, signals, model card limitations, and receipt hashes.
6. **Demo Execution Script:**
   - Create end-to-end demo script `scripts/demo.sh`.

---

### Target Files
- `services/api/src/sv_api/security.py`
- `tests/test_security_ssrf.py`
- `tests/test_media_fuzzing.py`
- `infra/locustfile.py`
- `scripts/demo.sh`
- `docs/SECURITY_REVIEW.md`

---

### Acceptance Criteria & Tests
- [ ] SSRF test suite confirms all private and cloud metadata IPs blocked.
- [ ] Media fuzzing tests pass with zero crashes or hangs.
- [ ] Sustained load test meets 100 videos/hour throughput target.
- [ ] PDF report generation produces valid, accessible case documents.
"""
    }
]

def main():
    print("Creating GitHub Issues for SENTINEL-V Parallel Streams...")
    for issue in ISSUES:
        cmd = [
            "gh", "issue", "create",
            "--title", issue["title"],
            "--body", f"**Assigned Lead:** {issue['assignee_tag']}\\n**Parallel Pairing:** {issue['parallel_partner']}\\n\\n" + issue["body"],
            "--milestone", issue["milestone"]
        ]
        for l in issue["labels"]:
            cmd.extend(["--label", l])
        
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"Created: {issue['title']} -> {res.stdout.strip()}")
        else:
            print(f"Failed: {issue['title']} -> {res.stderr.strip()}")

if __name__ == "__main__":
    main()
