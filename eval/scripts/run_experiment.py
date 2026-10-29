"""
SENTINEL-V Paper B Evaluation Experiment Runner.

Executes designated experiment module (E1 through E12), producing CSV outputs in eval/results/.
Usage:
    python eval/scripts/run_experiment.py --id <e1|e2|...|e12> [--output-dir eval/results]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Ensure experiments package is importable
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

EXPERIMENT_ROUTERS = {
    "e1": run_e1,
    "e2": run_e2,
    "e3": run_e3,
    "e4": run_e4,
    "e5": run_e5,
    "e6": run_e6,
    "e7": run_e7,
    "e8": run_e8,
    "e9": run_e9,
    "e11": run_e11,
    "e12": run_e12,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="SENTINEL-V Paper B Experiment Runner")
    parser.add_argument("--id", required=True, help="Experiment ID (e.g. e1, e2, e3, ..., e12)")
    parser.add_argument(
        "--output-dir", default="eval/results", help="Directory for output CSV results"
    )
    args = parser.parse_args()

    exp_id = args.id.lower().strip()
    if exp_id == "e10":
        print(
            "[SENTINEL-V Eval] Experiment E10 (Human Reviewer Calibration & Cognitive Workload Study) "
            "is deferred pending Blocker B6 (Institutional Ethics Board approval) as noted in SPEC §17."
        )
        sys.exit(0)

    if exp_id not in EXPERIMENT_ROUTERS:
        print(
            f"[Error] Unknown experiment ID '{args.id}'. Available: {list(EXPERIMENT_ROUTERS.keys())} or 'e10'"
        )
        sys.exit(1)

    runner = EXPERIMENT_ROUTERS[exp_id]
    print(f"[SENTINEL-V Eval] Launching Experiment {exp_id.upper()}...")
    runner(output_dir=args.output_dir)
    print(f"[SENTINEL-V Eval] Experiment {exp_id.upper()} finished successfully.")


if __name__ == "__main__":
    main()
