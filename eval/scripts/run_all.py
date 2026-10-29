"""
SENTINEL-V Paper B Evaluation Harness Orchestrator.

Executes all 11 evaluation experiments (E1-E9, E11, E12) and validates that all result CSVs
have been generated.
Usage:
    python eval/scripts/run_all.py [--output-dir eval/results]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

EXP_DIR = REPO_ROOT / "eval" / "scripts" / "experiments"
if str(EXP_DIR) not in sys.path:
    sys.path.insert(0, str(EXP_DIR))

from e1_parity import run_e1
from e2_base_rates import run_e2
from e3_cascade import run_e3
from e4_robustness import run_e4
from e5_latency_cost import run_e5
from e6_calibration_transfer import run_e6
from e7_ablations import run_e7
from e8_fusion_generative import run_e8
from e9_faithfulness import run_e9
from e11_drift import run_e11
from e12_receipts import run_e12

ALL_EXPERIMENTS = [
    ("e1", run_e1, "e1_parity.csv"),
    ("e2", run_e2, "e2_base_rates.csv"),
    ("e3", run_e3, "e3_cascade.csv"),
    ("e4", run_e4, "e4_robustness.csv"),
    ("e5", run_e5, "e5_latency_cost.csv"),
    ("e6", run_e6, "e6_calibration_transfer.csv"),
    ("e7", run_e7, "e7_ablations.csv"),
    ("e8", run_e8, "e8_fusion.csv"),
    ("e9", run_e9, "e9_faithfulness.csv"),
    ("e11", run_e11, "e11_drift.csv"),
    ("e12", run_e12, "e12_receipts.csv"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all Paper B evaluation experiments")
    parser.add_argument("--output-dir", default="eval/results", help="Directory for output results")
    args = parser.parse_args()

    out_path = Path(args.output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("SENTINEL-V Paper B Evaluation Harness: Executing Experiments E1-E12")
    print("=" * 70)

    success_count = 0
    failures: list[str] = []

    for exp_id, runner_fn, expected_csv in ALL_EXPERIMENTS:
        print(f"\n--> Running Experiment {exp_id.upper()}...")
        try:
            runner_fn(output_dir=out_path)
            csv_file = out_path / expected_csv
            if not csv_file.exists() or csv_file.stat().st_size == 0:
                raise FileNotFoundError(
                    f"Expected output CSV {csv_file} was not generated or is empty."
                )
            print(
                f"[OK] Experiment {exp_id.upper()} succeeded: {csv_file.name} ({csv_file.stat().st_size} bytes)"
            )
            success_count += 1
        except Exception as exc:
            print(f"[FAILED] Experiment {exp_id.upper()} encountered error: {exc}")
            failures.append(exp_id)

    print("\n" + "=" * 70)
    print(f"Summary: {success_count}/{len(ALL_EXPERIMENTS)} experiments completed successfully.")
    if failures:
        print(f"Failed experiments: {failures}")
        sys.exit(1)
    else:
        print(
            "All Paper B evaluation experiments completed cleanly and generated verified outputs."
        )
        print("=" * 70)


if __name__ == "__main__":
    main()
