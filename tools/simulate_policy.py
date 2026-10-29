import argparse
import json
from typing import Any

from sv_engine.priors import estimate_ppv

__all__ = [
    "MODEL_REFERENCE_POINTS",
    "simulate_policy",
    "simulate_model_preset",
    "sweep_prevalence_curve",
]

# Paper A (SPEC §2.2) measured operating characteristics on pooled test split
MODEL_REFERENCE_POINTS: dict[str, dict[str, Any]] = {
    "smsdt-s-a": {
        "name": "S-MSDT-S (Stage A, T=1)",
        "auc": 0.936,
        "tpr_at_1pct_fpr": 0.507,
        "tpr_at_5pct_fpr": 0.639,
    },
    "smsdt-st-b": {
        "name": "S-MSDT-ST (Stage B, T=8)",
        "auc": 0.938,
        "tpr_at_1pct_fpr": 0.471,
        "tpr_at_5pct_fpr": 0.589,
    },
    "smsdt-full-c": {
        "name": "S-MSDT-Full (Stage C, T=8)",
        "auc": 0.935,
        "tpr_at_1pct_fpr": 0.394,
        "tpr_at_5pct_fpr": 0.530,
    },
}


def simulate_policy(
    tpr: float,
    fpr: float,
    prevalence: float,
    volume_per_day: int = 10000,
    seconds_per_review: float = 90.0,
) -> dict[str, Any]:
    """Calculate expected operational metrics under base-rate prevalence pi (SPEC §7.4).

    Args:
        tpr: True Positive Rate (Recall) at operating threshold tau.
        fpr: False Positive Rate at operating threshold tau.
        prevalence: Deployment base rate pi of manipulated content in incoming traffic.
        volume_per_day: Estimated total daily incoming videos.
        seconds_per_review: Average human review duration in seconds.

    Returns:
        Dictionary of operational workload, flags per 10k, precision (PPV), and missed fakes.
    """
    if not (0.0 <= tpr <= 1.0):
        raise ValueError(f"tpr must be in [0, 1], got {tpr}")
    if not (0.0 <= fpr <= 1.0):
        raise ValueError(f"fpr must be in [0, 1], got {fpr}")
    if not (0.0 < prevalence < 1.0):
        raise ValueError(f"prevalence must be in (0, 1), got {prevalence}")

    # Scale to standard 10,000 video cohort
    n_base = 10000
    n_fake_10k = n_base * prevalence
    n_real_10k = n_base * (1.0 - prevalence)

    tp_10k = n_fake_10k * tpr
    fp_10k = n_real_10k * fpr
    flags_10k = tp_10k + fp_10k
    fn_10k = n_fake_10k - tp_10k
    tn_10k = n_real_10k - fp_10k

    # Precision / Positive Predictive Value
    ppv = estimate_ppv(tpr=tpr, fpr=fpr, prior_pi=prevalence) or 0.0

    # Daily operational projection
    daily_flags = volume_per_day * (flags_10k / n_base)
    daily_tp = volume_per_day * (tp_10k / n_base)
    daily_fp = volume_per_day * (fp_10k / n_base)
    daily_missed = volume_per_day * (fn_10k / n_base)
    daily_review_hours = (daily_flags * seconds_per_review) / 3600.0

    return {
        "prevalence": round(prevalence, 4),
        "prevalence_pct": round(prevalence * 100, 2),
        "tpr": round(tpr, 4),
        "fpr": round(fpr, 4),
        "ppv": round(ppv, 4),
        "ppv_pct": round(ppv * 100, 2),
        "per_10k": {
            "flags": round(flags_10k, 1),
            "flags_rounded": int(round(flags_10k)),
            "true_positives": round(tp_10k, 1),
            "false_positives": round(fp_10k, 1),
            "missed_fakes": round(fn_10k, 1),
            "true_negatives": round(tn_10k, 1),
        },
        "daily_projection": {
            "volume": volume_per_day,
            "flags_count": int(round(daily_flags)),
            "tp_count": int(round(daily_tp)),
            "fp_count": int(round(daily_fp)),
            "missed_count": int(round(daily_missed)),
            "review_hours": round(daily_review_hours, 1),
        },
    }


def simulate_model_preset(
    variant: str,
    target_fpr: float = 0.01,
    prevalence: float = 0.01,
    volume_per_day: int = 10000,
) -> dict[str, Any]:
    """Simulate policy metrics using measured operating characteristics from Paper A."""
    # Normalize variant name
    var_key = variant.lower().replace("_", "-")
    if var_key in ("s", "stage-a", "smsdt-s"):
        var_key = "smsdt-s-a"
    elif var_key in ("st", "stage-b", "smsdt-st"):
        var_key = "smsdt-st-b"
    elif var_key in ("full", "stage-c", "smsdt-full"):
        var_key = "smsdt-full-c"

    if var_key not in MODEL_REFERENCE_POINTS:
        raise ValueError(
            f"Unknown variant '{variant}'. Options: {list(MODEL_REFERENCE_POINTS.keys())}"
        )

    model_info = MODEL_REFERENCE_POINTS[var_key]
    if abs(target_fpr - 0.01) < 0.005:
        tpr = model_info["tpr_at_1pct_fpr"]
        actual_fpr = 0.01
    elif abs(target_fpr - 0.05) < 0.005:
        tpr = model_info["tpr_at_5pct_fpr"]
        actual_fpr = 0.05
    else:
        # Interpolate linearly between 1% and 5% FPR points
        tpr_1 = model_info["tpr_at_1pct_fpr"]
        tpr_5 = model_info["tpr_at_5pct_fpr"]
        tpr = tpr_1 + (target_fpr - 0.01) * ((tpr_5 - tpr_1) / 0.04)
        actual_fpr = target_fpr

    sim = simulate_policy(
        tpr=tpr,
        fpr=actual_fpr,
        prevalence=prevalence,
        volume_per_day=volume_per_day,
    )
    sim["model_variant"] = var_key
    sim["model_name"] = model_info["name"]
    sim["model_auc"] = model_info["auc"]
    return sim


def sweep_prevalence_curve(
    tpr: float,
    fpr: float,
    prevalences: list[float] | None = None,
    volume_per_day: int = 10000,
) -> list[dict[str, Any]]:
    """Generate simulation results across a range of prevalence values (0.1% to 20%)."""
    if prevalences is None:
        prevalences = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20]

    return [
        simulate_policy(tpr=tpr, fpr=fpr, prevalence=p, volume_per_day=volume_per_day)
        for p in prevalences
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Simulate prevalence-aware deepfake policy metrics (SPEC §7.4)."
    )
    parser.add_argument(
        "--variant",
        type=str,
        default="smsdt-full-c",
        help="Model variant: smsdt-s-a, smsdt-st-b, smsdt-full-c",
    )
    parser.add_argument(
        "--prevalence",
        type=float,
        default=0.01,
        help="Deployment base rate pi (e.g. 0.01 = 1%%)",
    )
    parser.add_argument(
        "--fpr",
        type=float,
        default=0.01,
        help="Target False Positive Rate (e.g. 0.01 or 0.05)",
    )
    parser.add_argument(
        "--volume",
        type=int,
        default=10000,
        help="Daily incoming video volume",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Sweep prevalence from 0.1% to 20%",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON",
    )

    args = parser.parse_args()

    if args.sweep:
        model_info = MODEL_REFERENCE_POINTS.get(
            args.variant, MODEL_REFERENCE_POINTS["smsdt-full-c"]
        )
        tpr = model_info["tpr_at_1pct_fpr"] if args.fpr <= 0.02 else model_info["tpr_at_5pct_fpr"]
        results = sweep_prevalence_curve(tpr=tpr, fpr=args.fpr, volume_per_day=args.volume)

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(
                f"\nPrevalence Sweep for {args.variant} @ FPR={args.fpr * 100:.1f}% (TPR={tpr * 100:.1f}%):"
            )
            print(
                f"{'Prev (%)':>10} | {'Flags/10k':>10} | {'TP/10k':>8} | {'FP/10k':>8} | {'Missed/10k':>10} | {'PPV (%)':>8}"
            )
            print("-" * 68)
            for r in results:
                p_pct = r["prevalence_pct"]
                fl = r["per_10k"]["flags"]
                tp = r["per_10k"]["true_positives"]
                fp = r["per_10k"]["false_positives"]
                fn = r["per_10k"]["missed_fakes"]
                ppv = r["ppv_pct"]
                print(
                    f"{p_pct:>10.2f} | {fl:>10.1f} | {tp:>8.1f} | {fp:>8.1f} | {fn:>10.1f} | {ppv:>8.2f}"
                )
    else:
        sim = simulate_model_preset(
            variant=args.variant,
            target_fpr=args.fpr,
            prevalence=args.prevalence,
            volume_per_day=args.volume,
        )

        if args.json:
            print(json.dumps(sim, indent=2))
        else:
            print(f"\nPolicy Simulation Results — {sim['model_name']}:")
            print(f"  Prevalence (pi):         {sim['prevalence_pct']}%")
            print(f"  Target FPR:              {sim['fpr'] * 100:.1f}%")
            print(f"  Recall (TPR):            {sim['tpr'] * 100:.1f}%")
            print(f"  Precision (PPV):         {sim['ppv_pct']}%")
            print("  Cohort (per 10,000 videos):")
            print(
                f"    Total flagged:         {sim['per_10k']['flags']} ({sim['per_10k']['flags_rounded']} rounded)"
            )
            print(f"    True Positives (fake): {sim['per_10k']['true_positives']}")
            print(f"    False Positives (real):{sim['per_10k']['false_positives']}")
            print(f"    Missed Fakes:          {sim['per_10k']['missed_fakes']}")
            print(f"  Daily Workload ({sim['daily_projection']['volume']} videos/day):")
            print(f"    Flagged to review:     {sim['daily_projection']['flags_count']} cases")
            print(f"    Human review time:     {sim['daily_projection']['review_hours']} hours/day")


if __name__ == "__main__":
    main()
