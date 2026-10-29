"""
30-Day Domain Drift & Governed Recalibration Timeline Plotter (SPEC §13, §15).

Reads operational drift data from eval/results/e11_drift.csv and renders publication-grade
dual-axis vector PDF and SVG curves tracking 10-quantile PSI, IPW ECE, and recalibration recovery.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate_drift_timeline_plot(
    csv_path: Path | str = "eval/results/e11_drift.csv",
    output_dir: Path | str = "eval/results",
) -> tuple[Path, Path]:
    csv_file = Path(csv_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not csv_file.exists():
        raise FileNotFoundError(f"Missing required input CSV: {csv_file}")

    rows: list[dict[str, str]] = []
    with open(csv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    days = [int(r["day"]) for r in rows]
    psis = [float(r["psi_score"]) for r in rows]
    ece_uncal = [float(r["rolling_ece_uncalibrated"]) for r in rows]
    ece_cal = [float(r["rolling_ece_calibrated"]) for r in rows]

    plt.style.use(
        "seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default"
    )
    fig, ax1 = plt.subplots(figsize=(7.0, 4.8), dpi=300)

    # Primary axis: PSI score
    color_psi = "#1f77b4"
    ax1.plot(days, psis, color=color_psi, linewidth=2.2, label="10-Quantile PSI", zorder=3)
    ax1.set_xlabel("Operational Day", fontsize=10.5, fontweight="medium")
    ax1.set_ylabel(
        "Population Stability Index (PSI)", color=color_psi, fontsize=10.5, fontweight="bold"
    )
    ax1.tick_params(axis="y", labelcolor=color_psi)
    ax1.set_xlim([1, 30])
    ax1.set_ylim([0.0, 0.35])

    # Reference PSI thresholds
    ax1.axhline(
        0.10, color="#ffbb33", linestyle="--", linewidth=1.2, label="Watch Threshold (PSI = 0.10)"
    )
    ax1.axhline(
        0.25, color="#cc0000", linestyle="--", linewidth=1.2, label="Alert Threshold (PSI = 0.25)"
    )

    # Secondary axis: ECE
    ax2 = ax1.twinx()
    color_uncal = "#e377c2"
    color_cal = "#2ca02c"
    ax2.plot(
        days,
        ece_uncal,
        color=color_uncal,
        linestyle=":",
        linewidth=1.8,
        label="ECE (Uncalibrated Drift)",
    )
    ax2.plot(days, ece_cal, color=color_cal, linewidth=2.0, label="ECE (SENTINEL-V Calibrated)")
    ax2.set_ylabel("Rolling 7-Day IPW ECE", color="#333333", fontsize=10.5, fontweight="bold")
    ax2.tick_params(axis="y", labelcolor="#333333")
    ax2.set_ylim([0.0, 0.20])
    ax2.grid(False)

    # Mark Governed Recalibration at Day 22
    ax1.axvline(22, color="#333333", linestyle="-.", linewidth=1.5, alpha=0.85)
    ax1.annotate(
        "Governed Recalibration\nApplied (Day 22)",
        xy=(22, 0.05),
        xytext=(15.5, 0.28),
        arrowprops={"facecolor": "#222222", "shrink": 0.08, "width": 1.0, "headwidth": 5.5},
        fontsize=8.0,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": "#e6f2ff",
            "edgecolor": "#3399ff",
            "alpha": 0.9,
        },
    )

    # Combine legends from both axes
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper left",
        frameon=True,
        fontsize=8.0,
        framealpha=0.92,
    )

    ax1.set_title(
        "30-Day Longitudinal Drift Monitoring & Recalibration Trajectory",
        fontsize=11,
        fontweight="bold",
        pad=12,
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

    fig.tight_layout(rect=[0, 0.03, 1, 1])

    pdf_path = out_dir / "fig_drift_timeline.pdf"
    svg_path = out_dir / "fig_drift_timeline.svg"
    fig.savefig(pdf_path, format="pdf")
    fig.savefig(svg_path, format="svg")
    plt.close(fig)

    print(f"[Fig Drift Timeline] Saved vector figures: {pdf_path.name}, {svg_path.name}")
    return pdf_path, svg_path


if __name__ == "__main__":
    generate_drift_timeline_plot()
