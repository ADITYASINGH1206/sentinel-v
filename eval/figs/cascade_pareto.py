"""
Two-Stage Cost Cascade Pareto Frontier Plotter for Paper B (SPEC §6.5, §15).

Reads evaluated sweep data from eval/results/e3_cascade.csv and renders publication-grade
vector PDF and SVG Pareto frontier curves comparing compute savings vs TPR @ 1% FPR.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate_cascade_pareto_plot(
    csv_path: Path | str = "eval/results/e3_cascade.csv",
    output_dir: Path | str = "eval/results",
) -> tuple[Path, Path]:
    csv_file = Path(csv_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not csv_file.exists():
        raise FileNotFoundError(f"Missing required input CSV: {csv_file}")

    rows: list[dict[str, str]] = []
    with open(csv_file, encoding="utf-8") as f:
        reader = csv.DictWriter if False else csv.DictReader(f)
        for r in reader:
            rows.append(r)

    savings = [float(r["compute_savings_pct"]) for r in rows]
    tprs = [float(r["tpr_at_1pct_fpr"]) for r in rows]
    cutoffs = [float(r["exit_cutoff"]) for r in rows]
    meets = [r["meets_constraints"].lower() == "true" for r in rows]

    plt.style.use(
        "seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default"
    )
    fig, ax = plt.subplots(figsize=(6.5, 4.8), dpi=300)

    # Plot Pareto line
    ax.plot(
        savings,
        tprs,
        color="#1f77b4",
        linewidth=2.0,
        linestyle="-",
        label="Cascade Sweep Frontier",
        zorder=2,
    )

    # Compliant vs non-compliant points
    comp_x = [s for s, m in zip(savings, meets, strict=False) if m]
    comp_y = [t for t, m in zip(tprs, meets, strict=False) if m]
    non_comp_x = [s for s, m in zip(savings, meets, strict=False) if not m]
    non_comp_y = [t for t, m in zip(tprs, meets, strict=False) if not m]

    ax.scatter(
        comp_x,
        comp_y,
        color="#2ca02c",
        s=55,
        zorder=3,
        label="Feasible (Leakage <= 1%, Agreement >= 98%)",
    )
    if non_comp_x:
        ax.scatter(
            non_comp_x,
            non_comp_y,
            color="#d62728",
            marker="x",
            s=55,
            zorder=3,
            label="Violates Constraints",
        )

    # Highlight optimal operating point (tau = 0.25)
    best_idx = 0
    max_sav = -1.0
    for i, m in enumerate(meets):
        if m and savings[i] > max_sav:
            max_sav = savings[i]
            best_idx = i

    best_s = savings[best_idx]
    best_t = tprs[best_idx]
    best_c = cutoffs[best_idx]

    ax.scatter(
        [best_s],
        [best_t],
        color="#ff7f0e",
        edgecolors="#b25900",
        s=130,
        zorder=4,
        label=f"Selected Policy Point (tau = {best_c:.2f})",
    )
    ax.annotate(
        f"Optimal Point: tau={best_c:.2f}\nSavings={best_s:.1f}%, TPR={best_t:.1f}%",
        xy=(best_s, best_t),
        xytext=(best_s - 18.0, best_t - 7.5),
        arrowprops={"facecolor": "#333333", "shrink": 0.08, "width": 1.0, "headwidth": 6.0},
        fontsize=8.5,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": "#fff9e6",
            "edgecolor": "#ffbb33",
            "alpha": 0.9,
        },
    )

    ax.set_xlabel(
        "GPU Compute Savings vs Uncascaded Full ST (%)", fontsize=10.5, fontweight="medium"
    )
    ax.set_ylabel("True Positive Rate @ 1% FPR (%)", fontsize=10.5, fontweight="medium")
    ax.set_title(
        "SENTINEL-V Two-Stage Cascade Pareto Frontier (S-MSDT-S -> S-MSDT-ST)",
        fontsize=11,
        fontweight="bold",
        pad=12,
    )
    ax.legend(loc="lower left", frameon=True, fontsize=8.5, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.6)

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

    pdf_path = out_dir / "fig_cascade_pareto.pdf"
    svg_path = out_dir / "fig_cascade_pareto.svg"
    fig.savefig(pdf_path, format="pdf")
    fig.savefig(svg_path, format="svg")
    plt.close(fig)

    print(f"[Fig Cascade Pareto] Saved vector figures: {pdf_path.name}, {svg_path.name}")
    return pdf_path, svg_path


if __name__ == "__main__":
    generate_cascade_pareto_plot()
