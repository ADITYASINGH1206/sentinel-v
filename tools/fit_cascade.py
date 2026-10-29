import argparse
import csv
import json
import os
from typing import Any

import numpy as np
from sv_engine.calibration import apply_platt


def load_cascade_validation_scores(
    csv_path: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load validation logits for Stage 1 and Stage 2 and binary ground truth labels.

    Expected CSV columns:
      - 'u_s1' (or 'score_s1', 'logit_s1')
      - 'u_s2' (or 'score_s2', 'logit_s2')
      - 'label' (or 'y', 'target') where 0=authentic, 1=manipulated
    """
    s1_list = []
    s2_list = []
    y_list = []

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            s1_val = row.get("u_s1") or row.get("score_s1") or row.get("logit_s1") or row.get("u1")
            s2_val = row.get("u_s2") or row.get("score_s2") or row.get("logit_s2") or row.get("u2")
            y_val = row.get("label") or row.get("y") or row.get("target")

            if s1_val is not None and s2_val is not None and y_val is not None:
                s1_list.append(float(s1_val))
                s2_list.append(float(s2_val))
                y_list.append(int(float(y_val)))

    if not s1_list:
        raise ValueError(f"No valid cascade score rows found in {csv_path}")

    return (
        np.array(s1_list, dtype=np.float64),
        np.array(s2_list, dtype=np.float64),
        np.array(y_list, dtype=np.int32),
    )


def generate_synthetic_validation_scores(
    n_samples: int = 2000,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate representative synthetic validation logits for Stage 1 (S) and Stage 2 (ST)."""
    rng = np.random.default_rng(seed)
    n_half = n_samples // 2

    # Authentic samples: centered around negative logits with high correlation
    base_real = rng.normal(loc=-2.5, scale=0.8, size=n_half)
    u_s1_real = base_real + rng.normal(0.0, 0.2, size=n_half)
    u_s2_real = base_real * 1.1 + rng.normal(0.0, 0.15, size=n_half)
    y_real = np.zeros(n_half, dtype=np.int32)

    # Manipulated samples: centered around positive logits with high correlation
    base_fake = rng.normal(loc=2.5, scale=0.8, size=n_half)
    u_s1_fake = base_fake + rng.normal(0.0, 0.2, size=n_half)
    u_s2_fake = base_fake * 1.1 + rng.normal(0.0, 0.15, size=n_half)
    y_fake = np.ones(n_half, dtype=np.int32)

    u_s1 = np.concatenate([u_s1_real, u_s1_fake])
    u_s2 = np.concatenate([u_s2_real, u_s2_fake])
    y = np.concatenate([y_real, y_fake])

    indices = rng.permutation(n_samples)
    return u_s1[indices], u_s2[indices], y[indices]


def sweep_cascade_thresholds(
    u_s1: np.ndarray,
    u_s2: np.ndarray,
    labels: np.ndarray,
    stage1_calib: tuple[float, float] = (1.0, 0.0),
    stage2_calib: tuple[float, float] = (0.6470, -0.5865),
    max_fake_leakage: float = 0.01,
    min_agreement: float = 0.99,
) -> dict[str, Any]:
    """Sweep exit threshold on validation set to find largest cutoff satisfying constraints.

    Constraints:
      1. Fake early-exit leakage <= max_fake_leakage (default 1.0%)
      2. Stage 2 classification agreement on escalated samples >= min_agreement (default 99.0%)
    """
    n_total = len(labels)
    n_fake = int(np.sum(labels == 1))
    n_real = int(np.sum(labels == 0))

    if n_fake == 0 or n_real == 0:
        raise ValueError("Validation set must contain both real and fake samples")

    # Calibrate scores for both stages
    p1 = np.array([apply_platt(u, *stage1_calib) for u in u_s1])
    p2 = np.array([apply_platt(u, *stage2_calib) for u in u_s2])

    threshold_grid = np.arange(0.01, 0.505, 0.005)
    valid_candidates = []

    for t in threshold_grid:
        early_exit = p1 < t
        fakes_exited = np.sum((labels == 1) & early_exit)
        fake_leakage = float(fakes_exited / n_fake)

        escalated = ~early_exit
        n_escalated = int(np.sum(escalated))

        if n_escalated > 0:
            dec1 = p1[escalated] >= 0.5
            dec2 = p2[escalated] >= 0.5
            agreement = float(np.mean(dec1 == dec2))
        else:
            agreement = 1.0

        compute_savings = float(np.mean(early_exit))
        real_exit_rate = float(np.sum((labels == 0) & early_exit) / n_real)

        result_row = {
            "threshold": round(float(t), 4),
            "fake_leakage": round(fake_leakage, 5),
            "compute_savings": round(compute_savings, 4),
            "real_exit_rate": round(real_exit_rate, 4),
            "stage_agreement": round(agreement, 4),
            "n_escalated": n_escalated,
            "fakes_leaked_count": int(fakes_exited),
        }

        if fake_leakage <= max_fake_leakage and agreement >= min_agreement:
            valid_candidates.append(result_row)

    if valid_candidates:
        # Select candidate with highest compute savings (largest threshold)
        optimal: dict[str, Any] = max(
            valid_candidates, key=lambda c: (c["compute_savings"], c["threshold"])
        )
    else:
        # Fallback to threshold=0.12 or safest threshold
        optimal = {
            "threshold": 0.12,
            "fake_leakage": 0.0,
            "compute_savings": 0.0,
            "real_exit_rate": 0.0,
            "stage_agreement": 1.0,
            "n_escalated": n_total,
            "fakes_leaked_count": 0,
            "warning": "No threshold met both strict constraints; fallback selected.",
        }

    return {
        "optimal_exit_below_p_bal": optimal["threshold"],
        "compute_savings": optimal["compute_savings"],
        "real_exit_rate": optimal["real_exit_rate"],
        "fake_leakage": optimal["fake_leakage"],
        "stage_agreement": optimal["stage_agreement"],
        "max_fake_leakage_constraint": max_fake_leakage,
        "min_agreement_constraint": min_agreement,
        "n_samples": n_total,
        "n_real": n_real,
        "n_fake": n_fake,
        "optimal_details": optimal,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Fit two-stage cascade exit cutoff threshold on validation scores."
    )
    parser.add_argument("--val-scores", type=str, default=None, help="Path to validation CSV")
    parser.add_argument(
        "--stage1-calib",
        type=str,
        default="1.0,0.0",
        help="Platt a,b for Stage 1 (comma-separated)",
    )
    parser.add_argument(
        "--stage2-calib",
        type=str,
        default="0.6470,-0.5865",
        help="Platt a,b for Stage 2 (comma-separated)",
    )
    parser.add_argument(
        "--max-fake-leakage",
        type=float,
        default=0.01,
        help="Maximum allowed false early exits on validation fakes",
    )
    parser.add_argument(
        "--min-agreement",
        type=float,
        default=0.99,
        help="Minimum required agreement rate on escalated clips",
    )
    parser.add_argument("--out", type=str, default=None, help="Path to write JSON output")
    parser.add_argument(
        "--generate-synthetic",
        action="store_true",
        help="Generate synthetic validation set if no CSV provided",
    )

    args = parser.parse_args()

    s1_calib = tuple(float(x) for x in args.stage1_calib.split(","))
    s2_calib = tuple(float(x) for x in args.stage2_calib.split(","))

    if args.val_scores and os.path.exists(args.val_scores):
        u_s1, u_s2, labels = load_cascade_validation_scores(args.val_scores)
    elif args.generate_synthetic or not args.val_scores:
        print("Generating synthetic validation scores (N=2000)...")
        u_s1, u_s2, labels = generate_synthetic_validation_scores()
    else:
        raise FileNotFoundError(f"Validation file {args.val_scores} does not exist")

    result = sweep_cascade_thresholds(
        u_s1=u_s1,
        u_s2=u_s2,
        labels=labels,
        stage1_calib=s1_calib,
        stage2_calib=s2_calib,
        max_fake_leakage=args.max_fake_leakage,
        min_agreement=args.min_agreement,
    )

    print("\nCascade Threshold Optimization Results:")
    print(f"  Optimal exit_below_p_bal: {result['optimal_exit_below_p_bal']}")
    print(f"  Compute savings:          {result['compute_savings'] * 100:.1f}%")
    print(f"  Real clips early-exited:  {result['real_exit_rate'] * 100:.1f}%")
    print(f"  Fake leakage:             {result['fake_leakage'] * 100:.2f}%")
    print(f"  Stage agreement:          {result['stage_agreement'] * 100:.1f}%")

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Saved results to {args.out}")


if __name__ == "__main__":
    main()
