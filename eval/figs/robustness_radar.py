"""
Perturbation Degradation Radar Chart Plotter for Paper B (SPEC §15.2).

Reads evaluated in-the-wild robustness data from eval/results/e4_robustness.csv and renders
publication-grade vector PDF and SVG polar radar charts comparing AUC across perturbation chains.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def generate_robustness_radar_plot(
    csv_path: Path | str = "eval/results/e4_robustness.csv",
    output_dir: Path | str = "eval/results",
) -> tuple[Path, Path]:
    csv_file = Path(csv_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not csv_file.exists():
        raise FileNotFoundError(f"Missing required input CSV: {csv_file}")

    datasets_order = ["faceforensics_c23", "deepfake_detection", "celeb_df_v2"]
    dataset_labels = {
        "faceforensics_c23": "FF++ c23 (In-Domain)",
        "deepfake_detection": "DFD (Cross-Dataset)",
        "celeb_df_v2": "Celeb-DF v2 (In-the-Wild)",
    }

    data: dict[str, dict[str, float]] = {d: {} for d in datasets_order}
    chains: list[str] = []

    with open(csv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            dset = r["dataset"]
            chain = r["perturbation_chain"]
            auc = float(r["auc"])
            if chain not in chains:
                chains.append(chain)
            if dset in data:
                data[dset][chain] = auc

    num_vars = len(chains)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    # Close the loop
    angles += angles[:1]

    plt.style.use(
        "seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default"
    )
    fig, ax = plt.subplots(figsize=(6.5, 6.0), subplot_kw={"polar": True}, dpi=300)

    # Format chain labels for clean presentation
    display_chains = [c.replace("_", " ").title() for c in chains]
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(display_chains, fontsize=9.0, fontweight="medium")

    ax.set_rlabel_position(0)
    ax.set_yticks([0.60, 0.70, 0.80, 0.90, 1.00])
    ax.set_yticklabels(["0.60", "0.70", "0.80", "0.90", "1.00"], fontsize=7.5, color="#666666")
    ax.set_ylim(0.50, 1.02)

    colors = {
        "faceforensics_c23": "#1f77b4",
        "deepfake_detection": "#ff7f0e",
        "celeb_df_v2": "#2ca02c",
    }

    for dset in datasets_order:
        values = [data[dset].get(c, 0.50) for c in chains]
        values += values[:1]  # close polygon
        color = colors.get(dset, "#333333")
        label = dataset_labels.get(dset, dset)
        ax.plot(angles, values, linewidth=2.0, linestyle="solid", color=color, label=label)
        ax.fill(angles, values, color=color, alpha=0.15)

    ax.set_title(
        "SENTINEL-V Perturbation Robustness Across Benchmarks (AUC)",
        fontsize=11,
        fontweight="bold",
        pad=20,
    )
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.10), fontsize=8.5, framealpha=0.92)

    # Mandatory screening-aid disclaimer footer (SPEC §14.13)
    plt.figtext(
        0.5,
        0.01,
        "Screening-aid only; subject to uncertainty. Never use as sole basis for moderation action.",
        ha="center",
        fontsize=8,
        style="italic",
        color="#555555",
    )

    fig.tight_layout(rect=[0, 0.03, 1, 1])

    pdf_path = out_dir / "fig_robustness_radar.pdf"
    svg_path = out_dir / "fig_robustness_radar.svg"
    fig.savefig(pdf_path, format="pdf")
    fig.savefig(svg_path, format="svg")
    plt.close(fig)

    print(f"[Fig Robustness Radar] Saved vector figures: {pdf_path.name}, {svg_path.name}")
    return pdf_path, svg_path


if __name__ == "__main__":
    generate_robustness_radar_plot()
