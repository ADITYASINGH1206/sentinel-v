# Contributor & Developer Guide — SENTINEL-V

Welcome to **SENTINEL-V**. This guide outlines development practices, workstream separation, testing standards, and contribution workflows for all contributors and agents.

---

## 1. Team & Stream Ownership

SENTINEL-V is engineered concurrently across two independent workstreams:

### Stream A: Machine Learning, Forensics & Evaluation
- **Lead:** [@sharadpolackalsunil](https://github.com/sharadpolackalsunil)
- **Primary Domain:**
  - `packages/sv_engine/` (Preprocessing, Adapters, Calibration, Cascade, Evidence)
  - `models/` (Model bundles, model cards, operating points)
  - `eval/` (Evaluation manifests, experiment scripts E1–E12, figures)
  - `tools/` (Bundle builder, calibration fitter, cascade tuner, parity checker)
  - `services/monitor/` (PSI drift detection, rolling ECE)

### Stream B: Systems, Full-Stack, Web3 & Platform
- **Lead:** [@AdityaRaj1304](https://github.com/AdityaRaj1304)
- **Primary Domain:**
  - `packages/sv_core/` (Settings, schemas, errors, canonical JCS)
  - `packages/sv_receipts/` (Receipt generation, Ed25519 signing, Merkle trees)
  - `services/api/` (FastAPI endpoints, auth, SSE, compatibility layer)
  - `services/workers/` (Celery task queues, Redis pub/sub)
  - `web/` (React Reviewer Console, Evidence Player, Public Verify)
  - `contracts/` (Foundry `ReceiptAnchor.sol` and test suite)
  - `integrations/sentinel/` (Additive compatibility files)
  - `infra/` (Dockerfiles, Docker Compose, monitoring)

---

## 2. Non-Negotiable Rules

1. **Never Invent Results:** All numbers shown anywhere in the UI, documentation, or paper figures must come directly from generated evaluation CSV files (`eval/results/*.csv`), bundle calibration files (`calibration.json`), or database rows. Placeholders are `null` in data and `—` in UI.
2. **Parity Before Features:** The serving pipeline must reproduce upstream `smsdt.eval_cross` within SPEC §6.9 tolerances before any UI work relies on real model scores. Use `SV_ENGINE_MODE=mock` until parity is verified.
3. **Import, Don't Re-implement:** Vendor `smsdt` as a pinned submodule under `third_party/smsdt`. Always import and wrap upstream preprocessing and calibration functions; never rewrite them from scratch.
4. **Additive Integration Only:** SENTINEL platform files (contracts, Web3, video processing) are strictly locked. All integration code resides in `integrations/sentinel/`. Never modify locked upstream files.
5. **Forbidden Copy Rule:** UI copy must never show bare "FAKE" or "REAL". Always show calibrated probability, decision band, model version, policy version, and the screening-aid disclaimer:
   > *"Screening aid — not proof. Human review required for consequential action."*

---

## 3. Git Branching & Workflow

Each teammate should work on isolated feature branches corresponding to their assigned milestones and issues:

```bash
# Stream A (Sharad)
git checkout -b feature/m1-preprocessing
git checkout -b feature/m2-adapters-calibration
git checkout -b feature/m4-evidence-maps

# Stream B (AdityaRaj)
git checkout -b feature/m3-api-gateway
git checkout -b feature/m5-reviewer-console
git checkout -b feature/m7-receipts-anchoring
```

### Pull Request Rules
- Target `main` branch.
- PR title should reference the milestone and issue number (e.g., `feat(m1): implement InsightFace multi-track pipeline (#2)`).
- All PRs must have passing unit tests and lint checks (`make test lint`).

---

## 4. Development Commands

```bash
make dev            # Start Docker Compose services (mock mode) + seed demo data
make test           # Run all unit and integration tests (mock mode)
make lint           # Run ruff, mypy, and forbidden-copy checks
make format         # Auto-format code with ruff
make parity         # Run parity checks on GPU machine (SPEC §6.9)
make bundle CKPT=... VARIANT=st VAL_SCORES=... # Build immutable model bundle
make eval-all       # Run all Paper B experiments (E1 to E12)
```

---

## 5. Milestone Completion Checklist

When finishing any milestone:
1. All unit tests pass: `make test`.
2. Lint and type checks pass: `make lint`.
3. `docs/CHANGELOG.md` updated with completed changes.
4. Milestone summary written in `docs/milestones/Mx.md` detailing:
   - What was built.
   - What was deferred.
   - Measured numbers (latencies, test coverage, parity stats).
