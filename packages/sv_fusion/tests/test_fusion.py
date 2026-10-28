from sv_core.enums import DecisionBand, InconclusiveReason
from sv_fusion.fusion import fuse_signals_v1


def test_inconclusive_preservation():
    band, labels, reason = fuse_signals_v1(
        face_decision=DecisionBand.INCONCLUSIVE,
        face_p_bal=0.0,
        inconclusive_reason=InconclusiveReason.NO_FACE,
        c2pa_info={"present": True, "ai_disclosed": True}
    )
    assert band == DecisionBand.INCONCLUSIVE
    assert reason == InconclusiveReason.NO_FACE


def test_c2pa_ai_disclosure_label():
    band, labels, _ = fuse_signals_v1(
        face_decision=DecisionBand.LIKELY_AUTHENTIC,
        face_p_bal=0.15,
        c2pa_info={"present": True, "ai_disclosed": True}
    )
    assert band == DecisionBand.LIKELY_AUTHENTIC
    assert "disclosed_ai_content" in labels


def test_generative_signal_elevation():
    band, labels, _ = fuse_signals_v1(
        face_decision=DecisionBand.LIKELY_AUTHENTIC,
        face_p_bal=0.20,
        gen_image_info={"max": 0.85},
        gen_threshold=0.65
    )
    assert band == DecisionBand.NEEDS_REVIEW
    assert "generative_signal_flagged" in labels
