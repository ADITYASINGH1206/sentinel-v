from typing import Dict, Any, List, Tuple, Optional
from sv_core.enums import DecisionBand, InconclusiveReason


def fuse_signals_v1(
    face_decision: DecisionBand,
    face_p_bal: float,
    inconclusive_reason: Optional[InconclusiveReason] = None,
    c2pa_info: Optional[Dict[str, Any]] = None,
    gen_image_info: Optional[Dict[str, Any]] = None,
    gen_threshold: Optional[float] = None,
) -> Tuple[DecisionBand, List[str], Optional[InconclusiveReason]]:
    """Deterministic Fusion v1 conforming to SPEC §9."""
    labels: List[str] = []

    # Rule 1: If face_manipulation is inconclusive, decision is inconclusive
    if face_decision == DecisionBand.INCONCLUSIVE:
        return DecisionBand.INCONCLUSIVE, labels, inconclusive_reason

    # Rule 2: If C2PA present with ai_disclosed=true, add label
    if c2pa_info and c2pa_info.get("ai_disclosed", False):
        labels.append("disclosed_ai_content")

    final_band = face_decision

    # Rule 3: If generative_image.max >= gen_threshold and band is likely_authentic, raise to needs_review
    if gen_threshold is not None and gen_image_info:
        max_gen = gen_image_info.get("max", 0.0)
        if max_gen >= gen_threshold and final_band == DecisionBand.LIKELY_AUTHENTIC:
            final_band = DecisionBand.NEEDS_REVIEW
            labels.append("generative_signal_flagged")

    return final_band, labels, None

