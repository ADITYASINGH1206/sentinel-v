---
name: model-bundle-builder
description: Builds immutable model bundles conforming to SPEC §6.2, converting PyTorch checkpoints to safetensors, exporting offline CLIP backbones, fitting Platt calibration, and generating checksums.
---

# Model Bundle Builder Skill

This skill guides the construction, calibration fitting, and packaging of immutable model bundles for SENTINEL-V.

## Bundle Directory Layout (SPEC §6.2)

```
models/bundle-<date>-<name>/
├── bundle.yaml                 # Bundle metadata, stage1/stage2 IDs, policy defaults
├── smsdt-s-a/
│   ├── model.yaml              # Architecture parameters, T, grid, eval protocol
│   ├── weights.safetensors     # Converted EMA weights
│   ├── backbone/               # Offline HuggingFace CLIPVisionModel
│   ├── calibration.json        # Class-balanced Platt parameters (a, b)
│   ├── operating_points.json   # Youden tau, TPR@1%FPR, TPR@5%FPR, ROC curves
│   ├── reference_scores.parquet# Validation logits for drift monitoring
│   └── model_card.md           # Model card with known limitations
├── smsdt-st-b/ (same structure)
└── checksums.sha256            # SHA-256 digests of all bundle files
```

---

## Execution Instructions

### 1. Build Bundle Command

```bash
make bundle \
  CKPT=/path/to/stage_b_best.pt \
  VARIANT=st \
  VAL_SCORES=eval/data/ffpp_dfd_val_scores.csv \
  OUT=models/bundle-2026-11-default
```

Under the hood, this executes `tools/make_bundle.py` which performs the following actions:

1. **State Dict Sanitization:**
   - Strips `module.` and `_orig_mod.` prefixes.
   - Extracts `ema_state_dict` if present.
   - Asserts zero missing or unexpected keys against `SMSDTv2`.
   - Saves weights in fast, secure `.safetensors` format.

2. **Offline Backbone Serialization:**
   - Loads `CLIPVisionModel.from_pretrained("openai/clip-vit-large-patch14")`.
   - Saves locally to `<variant>/backbone/` via `save_pretrained()`.
   - **Crucial:** Prevents network requests during production worker initialization.

3. **Platt Calibration Fitting (`tools/fit_calibration.py`):**
   - Fits class-balanced Platt scaling parameters $(a, b)$ on validation set logits.
   - Computes Youden-optimal threshold $\tau^* = \arg\max_\tau (\text{TPR}(\tau) - \text{FPR}(\tau))$.
   - Writes `calibration.json` matching SPEC §6.7.

4. **Operating Points Calculation:**
   - Computes empirical TPR at 1% FPR and 5% FPR on the validation set.
   - Generates 15-bin Expected Calibration Error (ECE) and ROC coordinates.
   - Writes `operating_points.json` matching SPEC §6.8.

5. **Checksum Generation:**
   - Computes SHA-256 for every single file in the bundle and writes `checksums.sha256`.
   - The worker validates this file at startup and fails immediately if any byte differs.

