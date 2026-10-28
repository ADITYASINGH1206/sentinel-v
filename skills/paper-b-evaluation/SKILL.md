---
name: paper-b-evaluation
description: Executes the Paper B evaluation harness across experiments E1-E12, manages benchmark manifests (FF++, DFD, Celeb-DF), and regenerates publication-ready figures.
---

# Paper B Evaluation Harness Skill

This skill guides the reproducible execution of all Paper B experiments (SPEC §15) using the production serving engine.

## Strict Research Integrity Rules
1. **Never Invent Results:** No number may enter any paper table, text, or figure unless it exists in a generated CSV file under `eval/results/<exp_id>/`.
2. **Single Codebase Rule:** All evaluation scores must be dumped directly from the serving engine (`tools/dump_scores.py`). Never maintain separate research scripts.

---

## Experiment Map

| ID | Title | Key Output File | Core Metric |
|---|---|---|---|
| **E1** | Parity Verification | `eval/results/e1/parity.csv` | Median $|\Delta u| \le 0.05$ |
| **E2** | Base Rates & Workload | `eval/results/e2/precision_vs_prevalence.csv` | PPV across $\pi \in [0.1\%, 20\%]$ |
| **E3** | Cascade Efficiency | `eval/results/e3/cascade_pareto.csv` | Compute saved vs TPR @ 1% FPR |
| **E4** | In-The-Wild Robustness | `eval/results/e4/robustness.csv` | AUC / TPR under 6 perturbation chains |
| **E5** | Latency & Compute Cost | `eval/results/e5/timings.csv` | p50/p95 latency, cost/1k videos |
| **E6** | Calibration Transfer | `eval/results/e6/recalibration_curves.csv` | ECE vs labels ($N \in \{25, 50, 100, 200\}$) |
| **E7** | Serving Protocol Ablation | `eval/results/e7/ablation.csv` | AUC vs $K \in \{1, 2, 4, 8, 16\}$, windowing |
| **E8** | Fusion & Generative Gap | `eval/results/e8/fusion_benchmark.csv` | Face manipulation vs T2V detection |
| **E9** | Explanation Faithfulness | `eval/results/e9/pointing_game.csv` | Top-10% IoU, deletion AUC vs masks |
| **E11** | Drift Detection | `eval/results/e11/drift_trajectory.csv` | Days to PSI alert on domain shift |
| **E12** | Receipt Overhead | `eval/results/e12/overhead.csv` | Merkle proof size, signing/verify ms |

---

## Running Experiments

```bash
# Run a specific experiment
make eval-e2

# Run all Paper B experiments end-to-end
make eval-all
```

### Generating Publication Figures
Figure scripts read exclusively from `eval/results/`:

```bash
python3 eval/figs/roc.py           # Produces figures/fig_roc.pdf
python3 eval/figs/cascade_pareto.py# Produces figures/fig_cascade.pdf
python3 eval/figs/drift_timeline.py# Produces figures/fig_drift.pdf
```

