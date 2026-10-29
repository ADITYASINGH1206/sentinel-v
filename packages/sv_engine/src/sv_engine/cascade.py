from dataclasses import dataclass

import numpy as np

from sv_engine.adapters.base import ClipBatch, ClipOutput, DetectorAdapter
from sv_engine.calibration import apply_platt


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
    track_results: list[TrackInferenceResult]


def evaluate_cascade(
    track_batches: list[ClipBatch],
    stage1_adapter: DetectorAdapter,
    stage2_adapter: DetectorAdapter,
    stage1_calib: tuple[float, float],
    stage2_calib: tuple[float, float],
    cascade_enabled: bool = True,
    exit_below_p_bal: float = 0.12,
) -> CascadeResult:
    """Evaluate two-stage cascade across multiple face tracks."""
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
    return CascadeResult(
        video_u=decisive_res.final_u,
        video_p_bal=decisive_res.final_p_bal,
        decisive_track_idx=decisive_idx,
        exited_early=decisive_res.exited_early,
        track_results=track_results,
    )
