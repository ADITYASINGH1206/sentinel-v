# VeriFrame: Calibrated, Auditable Video Deepfake Screening

> Formerly **SENTINEL-V** (see `docs/DECISIONS.md`, ADR 007). Internal package names (`sv_*`), `SV_` settings and the `sv-receipt/1` format are unchanged.

VeriFrame is a video deepfake screening platform and reviewer console built on the S-MSDT detector family. It provides prevalence-calibrated probabilities, explainable patch-evidence heat-maps, and cryptographically signed detection receipts anchored on EVM blockchains.

```
       ┌────────────────┐
       │ Video Upload   │
       └───────┬────────┘
               │
               ▼
   ┌───────────────────────┐
   │ Ingest & Preprocess   │ ── Detect & Track Faces (Buffalo_L)
   └───────────┬───────────┘
               │
               ▼
   ┌───────────────────────┐
   │ Cost-Aware Cascade    │ ── S-MSDT-S (T=1) ── Exit Early if Authentic
   └───────────┬───────────┘          │ Escalated
               ▼                      ▼
   ┌───────────────────────┐   S-MSDT-ST (T=8)
   │ Evidence & Fusion     │ ── Warped Patch Maps + C2PA + Generative Signals
   └───────────┬───────────┘
               │
               ▼
   ┌───────────────────────┐
   │ Signed Receipt        │ ── RFC 8785 Canonical JSON + Ed25519
   └───────────┬───────────┘
               ▼
   ┌───────────────────────┐
   │ EVM Merkle Anchor     │ ── Immutable Audit Trail
   └───────────────────────┘
```

---

## Key Features

1. **Prevalence-Calibrated Screening:** Probability estimation calibrated against real-world base rates ($\pi$) rather than arbitrary binary thresholds.
2. **Two-Stage Cost Cascade:** Fast screening via S-MSDT-S ($T=1$), escalating uncertain or suspicious clips to S-MSDT-ST ($T=8$); the compute saving is measured in experiment E3 rather than assumed.
3. **Forensic Evidence Maps:** Spatiotemporal patch heat-maps warped back to source video coordinates for frame-by-frame inspection in the Reviewer Console.
4. **Verifiable Detection Receipts:** Cryptographic audit trail linking media SHA-256, model weights hash, calibration hash, and decision policy, anchored to an EVM testnet.
5. **Non-Invasive SENTINEL Integration:** Additive compatibility layer for the SENTINEL Web3 content-verification platform.

---

## Monorepo Layout

```
├── AGENTS.md                  # Autonomous agent instructions & rules
├── docs/                      # Specification, ADRs, blockers, architecture, and developer guide
│   ├── SPEC.md                # Authoritative Build Specification v1.0
│   ├── SENTINEL-V_Build_Spec.md # Verbatim build specification reference
│   ├── ARCHITECTURE.md        # Deep subsystem architecture & data flows
│   ├── CONTRIBUTING.md        # Contributor workflow & parallel stream rules
│   ├── DECISIONS.md           # Architecture Decision Records (ADRs)
│   └── QUESTIONS.md           # Blocker tracking log (B1–B8)
├── skills/                    # Specialized agent & developer skills
│   ├── parity-verification/   # S-MSDT numerical equivalence checks (§6.9)
│   ├── model-bundle-builder/  # Immutable bundle builder & safetensors converter
│   ├── paper-b-evaluation/    # Paper B evaluation harness & experiment runners
│   ├── receipts-and-anchoring/# RFC 8785 JCS, Ed25519 signing & EVM anchoring
│   ├── sentinel-integration/  # Additive SENTINEL integration & webhook signing
│   └── reviewer-console-engineering/ # React console, canvas overlay & keyboard UX
├── packages/
│   ├── sv_core/               # Shared settings, schemas, errors, canonical JSON
│   ├── sv_engine/             # Preprocessing, S-MSDT adapters, calibration, evidence
│   ├── sv_fusion/             # C2PA provenance and generative image signals
│   └── sv_receipts/           # Receipt generation, Ed25519 signing, Merkle trees
├── services/
│   ├── api/                   # FastAPI gateway (analyses, receipts, review queue)
│   ├── workers/               # Celery workers (ingest, preprocess, gpu, finalize, anchor)
│   └── monitor/               # Drift detection (PSI), rolling ECE, retention
├── web/                       # Reviewer Console SPA (React, TypeScript, Vite, Tailwind)
├── contracts/                 # Foundry project with ReceiptAnchor.sol
├── integrations/sentinel/     # Additive adapter for SENTINEL platform
├── models/                    # Model bundle definitions and model cards
├── eval/                      # Paper B experimental evaluation harness
├── tools/                     # Calibration fitting, cascade tuning, parity checks
└── infra/                     # Dockerfiles, docker compose, Prometheus, Grafana
```

---

## Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 20+**
- *(Optional)* NVIDIA GPU with CUDA 12.x (real inference works on both CPU and CUDA)
- *(Optional)* Docker & Docker Compose

---

### Local Development (Native Python & React)

This is the recommended workflow for local development, active testing, and running real S-MSDT deepfake screening.

#### 1. Backend Setup

Install the monorepo packages in editable mode:

```bash
# From repository root
pip install -e packages/sv_core -e packages/sv_engine -e packages/sv_fusion -e packages/sv_receipts -e services/api -e services/workers
```

Ensure model weights are in place:
- The default model bundle directory is: `models/bundle-2026-11-default/smsdt-full-c/`.
- Ensure `weights.safetensors` is located in this directory.
- If you have an upstream PyTorch checkpoint (e.g., `best_ema.pt`), convert it to the standard bundle layout with:
  ```bash
  python tools/make_bundle.py --weights path/to/best_ema.pt --variant full_c
  ```

#### 2. Start the API Gateway

Launch the API using the bundled root launcher:

```bash
# Starts API on http://127.0.0.1:8080 with SV_ENGINE_MODE=real
python run_api.py
```

*Alternative manual startup with environment variables:*
```powershell
# Windows PowerShell
$env:PYTHONPATH="packages/sv_core/src;packages/sv_engine/src;packages/sv_fusion/src;packages/sv_receipts/src;services/api/src;services/workers/src;services/monitor/src;third_party/smsdt"
$env:SV_DATABASE_URL="sqlite+aiosqlite:///test_dev.db"
$env:SV_ENGINE_MODE="real" # use "mock" for quick synthetic tests without weights
python -m uvicorn sv_api.main:app --host 127.0.0.1 --port 8080
```
```bash
# Linux / macOS
export PYTHONPATH="packages/sv_core/src:packages/sv_engine/src:packages/sv_fusion/src:packages/sv_receipts/src:services/api/src:services/workers/src:services/monitor/src:third_party/smsdt"
export SV_DATABASE_URL="sqlite+aiosqlite:///test_dev.db"
export SV_ENGINE_MODE="real" # use "mock" for quick synthetic tests without weights
python -m uvicorn sv_api.main:app --host 127.0.0.1 --port 8080
```

The API endpoints will be live at:
- **API Base:** [http://127.0.0.1:8080](http://127.0.0.1:8080)
- **Interactive OpenAPI Documentation:** [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)

#### 3. Start the Web Console

In a separate terminal, start the Vite frontend development server:

```bash
cd web
npm install
npm run dev
```

Open your browser to [http://localhost:5173](http://localhost:5173):
- **Upload & Analyze (`/app/analyze`):** Upload any test video. Videos are decoded, tracked, scored by S-MSDT, and transcoded to browser-compatible H.264 MP4 streams on demand.
- **Evidence Player & Grad-CAM (`/app/cases/{id}`):** Inspect frame-by-frame video playback with dynamic $16 \times 16$ patch-level Grad-CAM attention heatmaps overlaid on detected face bounding boxes.
- **Review Queue (`/app/review`):** Triage cases awaiting auditor review (`pending_review`). Includes hotkeys (`F` for fake, `R` for real, `N` for escalate).
- **Cryptographic Receipts (`/v1/receipts/{id}`):** Download RFC 8785 canonical JSON tamper-proof receipts with Ed25519 signatures.

---

### Docker Compose (Containerized Mode)

To run the full stack containerized with Redis, MinIO, PostgreSQL, API, and Celery workers:

```bash
# Initialize development environment
make dev
```

Visit the containerized services:
- **Reviewer Console:** [http://localhost:5173](http://localhost:5173)
- **API Gateway & Swagger Docs:** [http://localhost:8080/docs](http://localhost:8080/docs)
- **MinIO Storage Console:** [http://localhost:9001](http://localhost:9001)

---

### Frontend Standalone Demo Mode (No Backend)

If you only want to test the React frontend without running a local backend:

```bash
cd web
npm install
npm run dev                          # Falls back to labelled DEMO DATA when API is unreachable
VITE_DATA_MODE=demo npm run dev     # Forces generated demo data everywhere
```

The console marks every generated item with a **DEMO DATA** badge.

---

### Running Tests

```bash
# Run unit & pipeline integration tests
pytest services/api/tests/test_analyses_pipeline.py -v

# Run real weights verification test
pytest packages/sv_engine/tests/test_real_weights.py -v

# Run entire test suite (mock mode)
make test

# Code quality and styling checks
make lint
```

---

## Parallel Development Streams

VeriFrame is built concurrently across two parallel workstreams:

- **Stream A — ML & Data Forensics:** Lead by [@sharadpolackalsunil](https://github.com/sharadpolackalsunil)
  - Video preprocessing, face tracking, and clip formation (M1)
  - S-MSDT adapters, checkpoint verification, and calibration tooling (M2)
  - Patch evidence generation and video heat-map overlays (M4)
  - Cascade exit tuning and policy math (M6)
  - Drift monitoring (PSI) and rolling ECE (M9)
  - Evaluation harness and Paper B experiments (M10)

- **Stream B — Systems, Full-Stack & Web3:** Lead by [@AdityaRaj1304](https://github.com/AdityaRaj1304)
  - Monorepo tooling, Docker Compose, and CI/CD pipelines (M0)
  - FastAPI gateway, Celery task pipelines, and Redis pub/sub (M3)
  - Reviewer Console web application and keyboard workspace (M5)
  - Detection receipts, Ed25519 signing, and EVM contract anchoring (M7)
  - SENTINEL platform integration adapter (M8)
  - Security hardening, SSRF sandboxing, and load testing (M11)

See [GitHub Issues](https://github.com/ADITYASINGH1206/veriframe/issues) for detailed task specifications and acceptance criteria.

---

## Agent & Developer Skills

The repository includes curated, executable skill modules under `skills/` designed to provide deep procedural knowledge for both coding agents and human engineers:

| Skill | Path | Description & Scope |
|---|---|---|
| **Parity Verification** | [`skills/parity-verification/`](skills/parity-verification/SKILL.md) | Step-by-step verification protocol for GPU inference parity ($|\Delta u| \le 0.05$, SSIM $\ge 0.98$). |
| **Model Bundle Builder** | [`skills/model-bundle-builder/`](skills/model-bundle-builder/SKILL.md) | Safetensors conversion, offline CLIP backbone export, Platt calibration fitting, and checksum generation. |
| **Paper B Evaluation** | [`skills/paper-b-evaluation/`](skills/paper-b-evaluation/SKILL.md) | Reproducible execution of experiments E1–E12, dataset manifests, and publication figure plotting. |
| **Receipts & EVM Anchoring** | [`skills/receipts-and-anchoring/`](skills/receipts-and-anchoring/SKILL.md) | RFC 8785 canonical JSON, Ed25519 signatures, Merkle trees, and Foundry `ReceiptAnchor.sol` anchoring. |
| **SENTINEL Integration** | [`skills/sentinel-integration/`](skills/sentinel-integration/SKILL.md) | Purely additive integration adapter, webhook HMAC validation, and locked-file preservation. |
| **Reviewer Console Engineering** | [`skills/reviewer-console-engineering/`](skills/reviewer-console-engineering/SKILL.md) | Canvas heat-map synchronization via `requestVideoFrameCallback`, keyboard shortcuts, and WCAG 2.2 AA. |
