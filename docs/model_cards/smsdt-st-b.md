# Model Card: S-MSDT-ST (Stage B Fixed)

## Model Details
- **Model ID:** `smsdt-st-b`
- **Architecture:** CLIP ViT-L/14 Backbone + Temporal Difference + 2 Non-Monotonic Spatial-Spectral Screening (NMSSS) blocks
- **Frames per Clip ($T$):** 8
- **Normalization:** CLIP Mean `[0.48145466, 0.4578275, 0.40821073]`, Std `[0.26862954, 0.26130258, 0.27577711]`
- **Input Dimension:** `(B, 8, 3, 224, 224)` RGB center-cropped

---

## Intended Use
- **Primary Use:** Automated screening aid for face-manipulation detection in video content (identity swapping and expression reenactment).
- **Out of Scope:** Fully generated synthetic video (text-to-video / Diffusion), audio deepfakes, legal admissibility certification.

---

## Known Limitations
1. **No Diffusion/T2V Training:** S-MSDT was trained on FaceForensics++ (FF++) face manipulation benchmarks; it is not calibrated for full-scene synthetic videos.
2. **Domain Transfer Degradation:** Zero-shot cross-dataset evaluation on Celeb-DF v2 shows calibration drift (ECE increases from 0.176 to 0.238). Active drift monitoring is required.
3. **Compression Sensitivity:** Validated primarily on c23 (high quality) video compression. Performance degrades on extreme mobile re-encoding.
4. **Human Review Requirement:** Strictly a screening tool. All consequential actions require human analyst verification.

---

## Calibration & Operating Points (Validation Set)
- **Method:** Class-Balanced Platt Scaling ($\sigma(a \cdot u + b)$)
- **Parameters:** $a = 0.6470$, $b = -0.5865$
- **Youden Threshold ($\tau^*$):** $0.7507$
- **Fit Set:** FF++ c23 validation ($N_{\text{real}}=260$, $N_{\text{fake}}=1164$) + DFD validation

