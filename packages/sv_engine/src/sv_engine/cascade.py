from dataclasses import dataclass, field

import numpy as np

from sv_engine.adapters.base import ClipBatch, ClipOutput, DetectorAdapter
from sv_engine.calibration import apply_platt

__all__ = [
    "TrackInferenceResult",
    "CascadeResult",
    "PolicyThresholds",
    "PolicyConfig",
    "POLICY_PRESETS",
    "get_policy",
    "assign_decision_band",
    "evaluate_cascade",
]


@dataclass
class PolicyThresholds:
    tau_authentic: float = 0.35
    tau_manipulated: float = 0.75


@dataclass
class PolicyConfig:
    policy_id: str
    version: int = 1
    name: str = ""
    description: str = ""
    target_prevalence: float = 0.01
    stage1_variant: str = "smsdt-s-a"
    stage2_variant: str = "smsdt-st-b"
    cascade_enabled: bool = True
    exit_below_p_bal: float = 0.12
    thresholds: PolicyThresholds = field(default_factory=PolicyThresholds)
    audit_sample_rate: float = 0.02


POLICY_PRESETS: dict[str, PolicyConfig] = {
    "strict-low-fpr": PolicyConfig(
        policy_id="strict-low-fpr",
        version=1,
        name="Strict Low False-Positive Rate",
        description="Optimized for in-domain deployment at low base-rate (pi=1%) with two-stage cascade.",
        target_prevalence=0.01,
        stage1_variant="smsdt-s-a",
        stage2_variant="smsdt-st-b",
        cascade_enabled=True,
        exit_below_p_bal=0.12,
        thresholds=PolicyThresholds(tau_authentic=0.30, tau_manipulated=0.75),
        audit_sample_rate=0.02,
    ),
    "transfer-calibrated": PolicyConfig(
        policy_id="transfer-calibrated",
        version=1,
        name="Transfer Calibrated",
        description="Balanced cross-generator transfer policy (pi=5%) with stage-2 decider.",
        target_prevalence=0.05,
        stage1_variant="smsdt-s-a",
        stage2_variant="smsdt-st-b",
        cascade_enabled=True,
        exit_below_p_bal=0.15,
        thresholds=PolicyThresholds(tau_authentic=0.35, tau_manipulated=0.70),
        audit_sample_rate=0.05,
    ),
    "evidence-desk": PolicyConfig(
        policy_id="evidence-desk",
        version=1,
        name="Evidence Desk High-Sensitivity",
        description="Forensic investigation desk mode (pi=20%) running full ST on all tracks with no early exit.",
        target_prevalence=0.20,
        stage1_variant="smsdt-st-b",
        stage2_variant="smsdt-st-b",
        cascade_enabled=False,
        exit_below_p_bal=0.0,
        thresholds=PolicyThresholds(tau_authentic=0.40, tau_manipulated=0.60),
        audit_sample_rate=0.10,
    ),
}


def get_policy(policy_id: str) -> PolicyConfig:
    """Retrieve policy preset by id or return default strict-low-fpr with warning."""
    if policy_id not in POLICY_PRESETS:
        import logging

        logging.getLogger(__name__).warning(
            f"Unknown policy_id '{policy_id}' requested. Falling back to default 'strict-low-fpr'."
        )
        return POLICY_PRESETS["strict-low-fpr"]
    return POLICY_PRESETS[policy_id]


def assign_decision_band(
    p_bal: float,
    tau_authentic: float = 0.35,
    tau_manipulated: float = 0.75,
    inconclusive: bool = False,
) -> str:
    """Map calibrated probability to one of the compliant decision bands.

    Allowed bands (SPEC §14.13):
      - 'inconclusive'
      - 'likely_authentic'   (p_bal < tau_authentic)
      - 'needs_review'       (tau_authentic <= p_bal < tau_manipulated)
      - 'likely_manipulated' (p_bal >= tau_manipulated)
    """
    if inconclusive:
        return "inconclusive"
    if p_bal < tau_authentic:
        return "likely_authentic"
    if p_bal < tau_manipulated:
        return "needs_review"
    return "likely_manipulated"


@dataclass
class TrackInferenceResult:
    track_idx: int
    decisive: bool
    exited_early: bool
    stage1_p_bal: float
    final_p_bal: float
    final_u: float
    clip_output: ClipOutput
    deciding_stage: int  # 1 or 2


@dataclass
class CascadeResult:
    video_u: float
    video_p_bal: float
    decisive_track_idx: int
    exited_early: bool
    decision_band: str
    track_results: list[TrackInferenceResult]


def evaluate_cascade(
    track_batches: list[ClipBatch],
    stage1_adapter: DetectorAdapter,
    stage2_adapter: DetectorAdapter,
    stage1_calib: tuple[float, float],
    stage2_calib: tuple[float, float],
    cascade_enabled: bool = True,
    exit_below_p_bal: float = 0.12,
    policy: PolicyConfig | None = None,
) -> CascadeResult:
    """Evaluate two-stage cascade across multiple face tracks."""
    if not track_batches:
        return CascadeResult(
            video_u=0.0,
            video_p_bal=0.5,
            decisive_track_idx=-1,
            exited_early=False,
            decision_band="inconclusive",
            track_results=[],
        )

    # Use policy settings if supplied
    if policy is not None:
        cascade_enabled = policy.cascade_enabled
        exit_below_p_bal = policy.exit_below_p_bal
        tau_auth = policy.thresholds.tau_authentic
        tau_manip = policy.thresholds.tau_manipulated
    else:
        tau_auth = 0.35
        tau_manip = 0.75

    track_results: list[TrackInferenceResult] = []

    for idx, batch in enumerate(track_batches):
        s1_out = stage1_adapter.predict(batch)
        s1_u = float(np.mean(s1_out.logits))
        s1_p_bal = apply_platt(s1_u, *stage1_calib)

        if cascade_enabled and s1_p_bal < exit_below_p_bal:
            track_results.append(
                TrackInferenceResult(
                    track_idx=idx,
                    decisive=False,
                    exited_early=True,
                    stage1_p_bal=s1_p_bal,
                    final_p_bal=s1_p_bal,
                    final_u=s1_u,
                    clip_output=s1_out,
                    deciding_stage=1,
                )
            )
        else:
            s2_out = stage2_adapter.predict(batch)
            s2_u = float(np.mean(s2_out.logits))
            s2_p_bal = apply_platt(s2_u, *stage2_calib)
            track_results.append(
                TrackInferenceResult(
                    track_idx=idx,
                    decisive=False,
                    exited_early=False,
                    stage1_p_bal=s1_p_bal,
                    final_p_bal=s2_p_bal,
                    final_u=s2_u,
                    clip_output=s2_out,
                    deciding_stage=2,
                )
            )

    # Decisive track is the one with max final_u
    decisive_idx = int(np.argmax([r.final_u for r in track_results]))
    track_results[decisive_idx].decisive = True

    decisive_res = track_results[decisive_idx]
    decision_band = assign_decision_band(
        decisive_res.final_p_bal, tau_authentic=tau_auth, tau_manipulated=tau_manip
    )

    return CascadeResult(
        video_u=decisive_res.final_u,
        video_p_bal=decisive_res.final_p_bal,
        decisive_track_idx=decisive_idx,
        exited_early=decisive_res.exited_early,
        decision_band=decision_band,
        track_results=track_results,
    )
