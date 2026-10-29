"""
Base Rate Prevalence & Precision Sweeps Plotter for Paper B (SPEC §7.4, §15).

Reads evaluated sweep data from eval/results/e2_base_rates.csv and renders publication-grade
vector PDF and SVG curves demonstrating Precision (PPV) and Workload across operational prevalence.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate_base_rates_plot(
    csv_path: Path | str = "eval/results/e2_base_rates.csv",
    output_dir: Path | str = "eval/results",
) -> tuple[Path, Path]:
    csv_file = Path(csv_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not csv_file.exists():
        raise FileNotFoundError(f"Missing required input CSV: {csv_file}")

    data: dict[str, list[dict[str, float]]] = {}
    with open(csv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            pol = r["policy_id"]
            if pol not in data:
                data[pol] = []
            data[pol].append(
                {
                    "prev": float(r["prevalence"]) * 100.0,
                    "ppv": float(r["ppv"]) * 100.0,
                    "flags": float(r["flags_per_10k"]),
                }
            )

    plt.style.use(
        "seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default"
    )
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.6), dpi=300)

    policy_styles = {
        "strict-low-fpr": {"label": "Strict Low-FPR (pi=1%)", "color": "#1f77b4", "marker": "o"},
        "transfer-calibrated": {
            "label": "Transfer Calibrated (pi=5%)",
            "color": "#ff7f0e",
            "marker": "s",
        },
        "evidence-desk": {"label": "Evidence Desk (pi=20%)", "color": "#2ca02c", "marker": "^"},
    }

    # Left plot: PPV vs Prevalence
    for pol, points in data.items():
        style = policy_styles.get(pol, {"label": pol, "color": "#333333", "marker": "x"})
        x = [p["prev"] for p in points]
        y_ppv = [p["ppv"] for p in points]
        ax1.plot(
            x,
            y_ppv,
            label=style["label"],
            color=style["color"],
            marker=style["marker"],
            linewidth=1.8,
            markersize=5,
        )

    ax1.set_xscale("log")
    ax1.set_xlabel("Operational Prevalence pi (%) [Log Scale]", fontsize=10.5, fontweight="medium")
    ax1.set_ylabel("Empirical Precision (PPV, %)", fontsize=10.5, fontweight="medium")
    ax1.set_title("Empirical Precision vs Base Rate", fontsize=11, fontweight="bold")
    ax1.grid(True, which="both", linestyle=":", alpha=0.6)
    ax1.legend(loc="lower right", fontsize=8.5, framealpha=0.92)

    # Highlight SPEC §7.4 benchmark at pi = 1% on strict policy
    strict_pts = data.get("strict-low-fpr", [])
    pt_1pct = next((p for p in strict_pts if abs(p["prev"] - 1.0) < 0.05), None)
    if pt_1pct:
        ax1.annotate(
            f"SPEC §7.4 Baseline:\nPPV = {pt_1pct['ppv']:.1f}% at pi = 1.0%",
            xy=(1.0, pt_1pct["ppv"]),
            xytext=(0.18, pt_1pct["ppv"] + 15),
            arrowprops={"facecolor": "#222222", "shrink": 0.08, "width": 1.0, "headwidth": 5.0},
            fontsize=8.0,
            fontweight="bold",
            bbox={
                "boxstyle": "round,pad=0.25",
                "facecolor": "#fff2e6",
                "edgecolor": "#ff9933",
                "alpha": 0.9,
            },
        )

    # Right plot: Workload (Flags / 10k) vs Prevalence
    for pol, points in data.items():
        style = policy_styles.get(
            pol, {"label": pol, "color": style["color"], "marker": style["marker"]}
        )
        x = [p["prev"] for p in points]
        y_flags = [p["flags"] for p in points]
        ax2.plot(
            x,
            y_flags,
            label=style["label"],
            color=style["color"],
            marker=style["marker"],
            linewidth=1.8,
            markersize=5,
        )

    ax2.set_xscale("log")
    ax2.set_xlabel("Operational Prevalence pi (%) [Log Scale]", fontsize=10.5, fontweight="medium")
    ax2.set_ylabel("Review Queue Flags per 10,000 Videos", fontsize=10.5, fontweight="medium")
    ax2.set_title("Moderation Workload vs Base Rate", fontsize=11, fontweight="bold")
    ax2.grid(True, which="both", linestyle=":", alpha=0.6)
    ax2.legend(loc="upper left", fontsize=8.5, framealpha=0.92)

    if pt_1pct:
        ax2.annotate(
            f"SPEC §7.4 Baseline:\n{int(pt_1pct['flags'])} flags / 10k at pi = 1.0%",
            xy=(1.0, pt_1pct["flags"]),
            xytext=(0.15, pt_1pct["flags"] + 450),
            arrowprops={"facecolor": "#222222", "shrink": 0.08, "width": 1.0, "headwidth": 5.0},
            fontsize=8.0,
            fontweight="bold",
            bbox={
                "boxstyle": "round,pad=0.25",
                "facecolor": "#fff2e6",
                "edgecolor": "#ff9933",
                "alpha": 0.9,
            },
        )

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

    fig.tight_layout(rect=[0, 0.04, 1, 1])

    pdf_path = out_dir / "fig_base_rates.pdf"
    svg_path = out_dir / "fig_base_rates.svg"
    fig.savefig(pdf_path, format="pdf")
    fig.savefig(svg_path, format="svg")
    plt.close(fig)

    print(f"[Fig Base Rates] Saved vector figures: {pdf_path.name}, {svg_path.name}")
    return pdf_path, svg_path


if __name__ == "__main__":
    generate_base_rates_plot()
