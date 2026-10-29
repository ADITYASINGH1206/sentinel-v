import numpy as np
import pytest
from sv_engine.adapters.base import ClipBatch, ClipOutput, DetectorAdapter
from sv_engine.cascade import (
    POLICY_PRESETS,
    CascadeResult,
    assign_decision_band,
    evaluate_cascade,
    get_policy,
)

from tools.fit_cascade import generate_synthetic_validation_scores, sweep_cascade_thresholds
from tools.simulate_policy import (
    MODEL_REFERENCE_POINTS,
    simulate_model_preset,
    sweep_prevalence_curve,
)


class MockStageAdapter(DetectorAdapter):
    """Configurable mock adapter returning predetermined logits."""

    def __init__(self, logits_value: float, name: str = "mock"):
        self.logits_value = logits_value
        self.variant_name = name
        self.calls = 0

    def predict(self, batch: ClipBatch) -> ClipOutput:
        self.calls += 1
        n_clips = len(batch.frames_u8)
        logits = np.full(n_clips, self.logits_value, dtype=np.float32)
        return ClipOutput(
            logits=logits,
            patch_logits=None,
            grid=16,
        )


def make_dummy_batch(n_clips: int = 4, t_frames: int = 1) -> ClipBatch:
    """Helper to construct valid ClipBatch."""
    return ClipBatch(
        frames_u8=np.zeros((n_clips, t_frames, 224, 224, 3), dtype=np.uint8),
        landmarks106=None,
        conf=np.ones((n_clips, t_frames), dtype=np.float32),
    )


def test_policy_presets_validity():
    """Verify built-in policy presets contain required fields and compliant thresholds."""
    assert "strict-low-fpr" in POLICY_PRESETS
    assert "transfer-calibrated" in POLICY_PRESETS
    assert "evidence-desk" in POLICY_PRESETS

    for pid, p in POLICY_PRESETS.items():
        assert p.policy_id == pid
        assert 0.0 < p.target_prevalence < 1.0
        assert 0.0 <= p.exit_below_p_bal <= 0.5
        assert p.thresholds.tau_authentic < p.thresholds.tau_manipulated
        assert 0.0 <= p.audit_sample_rate <= 1.0


def test_get_policy_fallback():
    """Verify get_policy returns requested preset or falls back to strict-low-fpr."""
    p_exact = get_policy("strict-low-fpr")
    assert p_exact.policy_id == "strict-low-fpr"

    p_fallback = get_policy("unknown-policy-xyz")
    assert p_fallback.policy_id == "strict-low-fpr"


def test_assign_decision_band_rules():
    """Test decision band mapping conforms to SPEC §14.13 allowed bands."""
    # Inconclusive overrides everything
    assert assign_decision_band(0.99, inconclusive=True) == "inconclusive"

    # Strict thresholds: auth=0.30, manip=0.75
    assert (
        assign_decision_band(0.10, tau_authentic=0.30, tau_manipulated=0.75) == "likely_authentic"
    )
    assert (
        assign_decision_band(0.29, tau_authentic=0.30, tau_manipulated=0.75) == "likely_authentic"
    )
    assert assign_decision_band(0.30, tau_authentic=0.30, tau_manipulated=0.75) == "needs_review"
    assert assign_decision_band(0.74, tau_authentic=0.30, tau_manipulated=0.75) == "needs_review"
    assert (
        assign_decision_band(0.75, tau_authentic=0.30, tau_manipulated=0.75) == "likely_manipulated"
    )
    assert (
        assign_decision_band(0.98, tau_authentic=0.30, tau_manipulated=0.75) == "likely_manipulated"
    )


def test_cascade_early_exit_on_authentic():
    """Stage 1 authentic clip with p1 < exit cutoff exits early without invoking Stage 2."""
    # Stage 1 logit = -3.0 -> with calib (1.0, 0.0), p1 = sigmoid(-3.0) ~ 0.0474 < 0.12
    s1_adapter = MockStageAdapter(logits_value=-3.0, name="s1-s")
    s2_adapter = MockStageAdapter(logits_value=0.0, name="s2-st")

    batch = make_dummy_batch(n_clips=4, t_frames=1)

    result: CascadeResult = evaluate_cascade(
        track_batches=[batch],
        stage1_adapter=s1_adapter,
        stage2_adapter=s2_adapter,
        stage1_calib=(1.0, 0.0),
        stage2_calib=(1.0, 0.0),
        cascade_enabled=True,
        exit_below_p_bal=0.12,
    )

    assert result.exited_early is True
    assert result.decision_band == "likely_authentic"
    assert s1_adapter.calls == 1
    assert s2_adapter.calls == 0  # Stage 2 compute saved!
    assert result.track_results[0].deciding_stage == 1


def test_cascade_escalate_on_suspicious():
    """Stage 1 suspicious clip with p1 >= exit cutoff triggers Stage 2 evaluation."""
    # Stage 1 logit = 0.5 -> p1 ~ 0.622 >= 0.12 -> escalates to Stage 2
    s1_adapter = MockStageAdapter(logits_value=0.5, name="s1-s")
    s2_adapter = MockStageAdapter(logits_value=2.0, name="s2-st")

    batch = make_dummy_batch(n_clips=4, t_frames=8)

    result: CascadeResult = evaluate_cascade(
        track_batches=[batch],
        stage1_adapter=s1_adapter,
        stage2_adapter=s2_adapter,
        stage1_calib=(1.0, 0.0),
        stage2_calib=(1.0, 0.0),
        cascade_enabled=True,
        exit_below_p_bal=0.12,
    )

    assert result.exited_early is False
    assert s1_adapter.calls == 1
    assert s2_adapter.calls == 1  # Stage 2 executed
    assert result.track_results[0].deciding_stage == 2
    assert result.track_results[0].final_u == 2.0
    assert result.decision_band == "likely_manipulated"


def test_cascade_decisive_track_max_aggregation():
    """Video result selects track with max logit u(V) = max_j u_j."""
    # Track 0: authentic (logit -2.0)
    # Track 1: suspicious (logit +1.5) -> decisive
    # Track 2: intermediate (logit -0.5)
    batches = [
        make_dummy_batch(n_clips=2, t_frames=1),
        make_dummy_batch(n_clips=2, t_frames=1),
        make_dummy_batch(n_clips=2, t_frames=1),
    ]
    batch_values = {
        id(batches[0]): -2.0,
        id(batches[1]): 1.5,
        id(batches[2]): -0.5,
    }

    class IdMappedAdapter(DetectorAdapter):
        def predict(self, batch: ClipBatch) -> ClipOutput:
            val = batch_values.get(id(batch), 0.0)
            n_clips = len(batch.frames_u8)
            return ClipOutput(
                logits=np.full(n_clips, val, dtype=np.float32),
                patch_logits=None,
                grid=16,
            )

    adapter = IdMappedAdapter()

    result = evaluate_cascade(
        track_batches=batches,
        stage1_adapter=adapter,
        stage2_adapter=adapter,
        stage1_calib=(1.0, 0.0),
        stage2_calib=(1.0, 0.0),
        cascade_enabled=False,  # Evaluate all tracks
    )

    assert result.decisive_track_idx == 1
    assert result.video_u == 1.5
    assert result.track_results[1].decisive is True
    assert result.track_results[0].decisive is False
    assert result.track_results[2].decisive is False


def test_fit_cascade_optimization_sweep():
    """Verify sweep_cascade_thresholds selects cutoff satisfying leakage and agreement."""
    u_s1, u_s2, labels = generate_synthetic_validation_scores(n_samples=1000, seed=123)

    opt = sweep_cascade_thresholds(
        u_s1=u_s1,
        u_s2=u_s2,
        labels=labels,
        stage1_calib=(1.0, 0.0),
        stage2_calib=(1.0, 0.0),
        max_fake_leakage=0.01,
        min_agreement=0.99,
    )

    assert opt["optimal_exit_below_p_bal"] > 0.0
    assert opt["fake_leakage"] <= 0.01
    assert opt["stage_agreement"] >= 0.99
    assert opt["compute_savings"] > 0.15  # Saves at least 15% compute


def test_simulate_policy_spec_7_4_benchmark():
    """Reproduce exact SPEC §7.4 benchmark numbers on Paper A S-MSDT-Full.

    SPEC §7.4: At 1% prevalence, Full at 1% FPR flags about 138 videos per 10k,
    of which only about 28.5% are fake.
    """
    sim = simulate_model_preset(
        variant="smsdt-full-c",
        target_fpr=0.01,
        prevalence=0.01,
        volume_per_day=10000,
    )

    # TPR from Table 2.2 for Full @ 1% FPR is 39.4%
    assert sim["tpr"] == 0.394
    assert sim["fpr"] == 0.01
    assert sim["prevalence"] == 0.01

    # Exact SPEC verification: 138 flags per 10,000
    assert sim["per_10k"]["flags_rounded"] == 138
    assert pytest.approx(sim["per_10k"]["flags"], abs=0.5) == 138.4

    # Exact SPEC verification: ~28.5% PPV
    assert pytest.approx(sim["ppv_pct"], abs=0.2) == 28.47


def test_simulate_policy_prevalence_sweep():
    """Verify PPV increases monotonically with prevalence (Bayes theorem)."""
    tpr = MODEL_REFERENCE_POINTS["smsdt-st-b"]["tpr_at_1pct_fpr"]
    fpr = 0.01
    prevalences = [0.001, 0.01, 0.05, 0.10, 0.20]

    curve = sweep_prevalence_curve(tpr=tpr, fpr=fpr, prevalences=prevalences)
    assert len(curve) == 5

    ppvs = [r["ppv"] for r in curve]
    # Check strict monotonic increase
    for i in range(len(ppvs) - 1):
        assert ppvs[i] < ppvs[i + 1]

    # At 20% prevalence, PPV is much higher than at 0.1%
    assert ppvs[-1] > 0.80
    assert ppvs[0] < 0.10


def test_fit_cascade_odd_sample_counts():
    """Verify generate_synthetic_validation_scores handles odd n_samples without index errors."""
    u_s1, u_s2, labels = generate_synthetic_validation_scores(n_samples=1001, seed=42)
    assert len(u_s1) == 1001
    assert len(u_s2) == 1001
    assert len(labels) == 1001
    assert np.sum(labels == 1) + np.sum(labels == 0) == 1001
