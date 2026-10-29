"""
Master Figure Renderer for Paper B (SPEC §15).

Renders all 5 publication-grade vector figures (PDF and SVG) directly from evaluated CSVs:
- ROC & DET Curves (fig_roc.pdf / .svg)
- Cascade Pareto Frontier (fig_cascade_pareto.pdf / .svg)
- Longitudinal Drift Timeline (fig_drift_timeline.pdf / .svg)
- Base Rate Prevalence Curves (fig_base_rates.pdf / .svg)
- Perturbation Robustness Radar (fig_robustness_radar.pdf / .svg)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FIG_DIR = REPO_ROOT / "eval" / "figs"
if str(FIG_DIR) not in sys.path:
    sys.path.insert(0, str(FIG_DIR))

from base_rate_curves import generate_base_rates_plot
from cascade_pareto import generate_cascade_pareto_plot
from drift_timeline import generate_drift_timeline_plot
from robustness_radar import generate_robustness_radar_plot
from roc import generate_roc_plot

FIGURE_GENERATORS = [
    ("ROC Curves", generate_roc_plot, "e4_robustness.csv", ["fig_roc.pdf", "fig_roc.svg"]),
    (
        "Cascade Pareto",
        generate_cascade_pareto_plot,
        "e3_cascade.csv",
        ["fig_cascade_pareto.pdf", "fig_cascade_pareto.svg"],
    ),
    (
        "Drift Timeline",
        generate_drift_timeline_plot,
        "e11_drift.csv",
        ["fig_drift_timeline.pdf", "fig_drift_timeline.svg"],
    ),
    (
        "Base Rates",
        generate_base_rates_plot,
        "e2_base_rates.csv",
        ["fig_base_rates.pdf", "fig_base_rates.svg"],
    ),
    (
        "Robustness Radar",
        generate_robustness_radar_plot,
        "e4_robustness.csv",
        ["fig_robustness_radar.pdf", "fig_robustness_radar.svg"],
    ),
]


def render_all_figures(output_dir: Path | str = "eval/results") -> dict[str, list[str]]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("SENTINEL-V Paper B: Rendering Publication-Grade Vector Figures")
    print("=" * 70)

    rendered: dict[str, list[str]] = {}

    for name, gen_fn, input_csv, expected_figs in FIGURE_GENERATORS:
        csv_file = out_dir / input_csv
        print(f"\n--> Rendering {name} from {csv_file.name}...")
        if not csv_file.exists():
            raise FileNotFoundError(
                f"Cannot render {name}: prerequisite CSV {csv_file} does not exist."
            )

        pdf_path, svg_path = gen_fn(csv_path=csv_file, output_dir=out_dir)

        for fig_name in expected_figs:
            fpath = out_dir / fig_name
            if not fpath.exists() or fpath.stat().st_size == 0:
                raise FileNotFoundError(f"Generated figure {fpath} is missing or empty.")

        rendered[name] = [pdf_path.name, svg_path.name]
        print(
            f"[OK] {name} rendered: {pdf_path.name} ({pdf_path.stat().st_size} bytes), {svg_path.name} ({svg_path.stat().st_size} bytes)"
        )

    print("\n" + "=" * 70)
    print(
        f"Summary: All {len(FIGURE_GENERATORS)} figures successfully generated in vector PDF & SVG formats."
    )
    print("=" * 70)
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser(description="Render all Paper B publication figures")
    parser.add_argument(
        "--output-dir",
        default="eval/results",
        help="Directory where CSVs live and figures are written",
    )
    args = parser.parse_args()
    render_all_figures(output_dir=args.output_dir)


if __name__ == "__main__":
    main()
