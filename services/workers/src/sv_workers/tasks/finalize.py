import json
import os
import secrets
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sv_api.database import async_session_maker
from sv_api.models import AnalysisModel, TrackModel
from sv_api.sse import publish_progress
from sv_core.enums import DecisionBand
from sv_core.settings import settings
from sv_engine.calibration import calibrate_platt
from sv_engine.cascade import assign_decision_band, get_policy
from sv_engine.priors import adjust_for_prior, estimate_ppv
from sv_receipts.crypto import generate_keypair
from sv_receipts.schema import sign_receipt
from sv_workers.celery_app import celery_app
from sv_workers.tasks.utils import run_async


def load_bundle_calibration(bundle_id: str) -> tuple[float, float]:
    """Dynamically load Platt scaling calibration parameters (a, b) from bundle metadata."""
    candidate_paths = [
        os.path.join("models", bundle_id, "smsdt-full-c", "calibration.json"),
        os.path.join("models", bundle_id, "smsdt-st-b", "calibration.json"),
        os.path.join("models", bundle_id, "calibration.json"),
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    cdata = json.load(f)
                    params = cdata.get("parameters", {})
                    a = float(params.get("a", cdata.get("a", 0.6470)))
                    b = float(params.get("b", cdata.get("b", -0.5865)))
                    return a, b
            except Exception:
                pass
    return 0.6470, -0.5865


async def _dispatch_completion_webhook(
    analysis: AnalysisModel,
    decision: str,
    p_bal: float,
    receipt_id: str,
    now: datetime,
) -> None:
    target_webhook_url = getattr(analysis, "webhook_url", None) or settings.SENTINEL_WEBHOOK_URL
    if not target_webhook_url:
        return

    if decision == DecisionBand.LIKELY_AUTHENTIC.value:
        compat_status = "allowed"
    elif decision == DecisionBand.NEEDS_REVIEW.value:
        compat_status = "review"
    elif decision == DecisionBand.LIKELY_MANIPULATED.value:
        compat_status = "held"
    elif decision == DecisionBand.INCONCLUSIVE.value:
        compat_status = "inconclusive"
    else:
        compat_status = decision

    review_required = compat_status == "review" or decision == DecisionBand.NEEDS_REVIEW.value
    labels = ["face_manipulation_suspected"] if compat_status in ("review", "held") else []

    webhook_payload = {
        "post_id": getattr(analysis, "external_ref", None),
        "analysis_id": analysis.id,
        "status": compat_status,
        "labels": labels,
        "deepfake_confidence": round(float(p_bal), 4),
        "deepfake_model_version": getattr(analysis, "model_bundle_id", "smsdt-full-c"),
        "review_required": review_required,
        "receipt_id": receipt_id,
        "report_url": f"http://localhost:5173/cases/{analysis.id}",
        "completed_at": now.isoformat() + "Z",
    }

    try:
        from sv_api.webhook import dispatch_webhook

        await dispatch_webhook(target_webhook_url, webhook_payload, settings.WEBHOOK_SECRET)
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning(
            "Failed to dispatch webhook for %s: %s", analysis.id, exc
        )


async def _async_finalize(analysis_id: str, inconclusive: bool = False) -> dict[str, Any]:
    """Execute final aggregation, calibration, receipt signing, and event notification."""
    now = datetime.now(UTC).replace(tzinfo=None)
    async with async_session_maker() as session:
        stmt = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
        res = await session.execute(stmt)
        analysis = res.scalars().first()
        if not analysis:
            return {"error": "Analysis not found"}

        if inconclusive:
            analysis.status = "completed"
            analysis.decision = DecisionBand.INCONCLUSIVE.value
            analysis.completed_at = now
            analysis.receipt_id = f"rcpt_{secrets.token_hex(16)}"
            await session.commit()

            await publish_progress(
                analysis_id,
                "finalize",
                100,
                f"Analysis completed: inconclusive ({analysis.inconclusive_reason})",
            )
            await _dispatch_completion_webhook(
                analysis, DecisionBand.INCONCLUSIVE.value, 0.0, analysis.receipt_id, now
            )
            return {"analysis_id": analysis_id, "status": "completed", "decision": "inconclusive"}

        # Load tracks
        trk_stmt = select(TrackModel).where(TrackModel.analysis_id == analysis_id)
        trk_res = await session.execute(trk_stmt)
        tracks = trk_res.scalars().all()

        bundle_id = getattr(analysis, "model_bundle_id", settings.MODEL_BUNDLE)
        platt_a, platt_b = load_bundle_calibration(bundle_id)

        if not tracks:
            u_video = 0.0
            p_bal = 0.5
        else:
            u_video = float(max(t.u for t in tracks))
            p_bal = calibrate_platt(u_video, platt_a, platt_b)

        # Retrieve dynamic policy configuration
        policy_cfg = get_policy(analysis.policy_id)
        prior_prev = policy_cfg.target_prevalence
        p_prior = adjust_for_prior(p_bal, target_prevalence=prior_prev, validation_prevalence=0.50)
        ppv = estimate_ppv(tpr=0.471, fpr=0.01, prevalence=prior_prev)

        # Assign decision band dynamically based on policy thresholds
        decision = assign_decision_band(
            p_bal,
            tau_authentic=policy_cfg.thresholds.tau_authentic,
            tau_manipulated=policy_cfg.thresholds.tau_manipulated,
        )

        scores_summary = {
            "u": round(u_video, 4),
            "p_bal": round(p_bal, 4),
            "p_prior": round(p_prior, 4),
            "prior_prevalence": prior_prev,
            "ppv_estimate": round(ppv, 4),
        }

        # Read decisive evidence_root from signals if present
        evidence_root = None
        if analysis.signals:
            try:
                signals_data = json.loads(analysis.signals)
                evidence_root = signals_data.get("evidence_root")
            except Exception:
                pass

        # Build Detection Receipt
        priv_key, _ = generate_keypair()
        receipt_dict = {
            "receipt_id": f"rcpt_{secrets.token_hex(16)}",
            "analysis_id": analysis_id,
            "decision": decision,
            "score": scores_summary["p_bal"],
            "model_version": getattr(analysis, "model_bundle_id", "smsdt-full-c"),
            "policy_version": analysis.policy_version,
            "timestamp": now.isoformat() + "Z",
        }
        if evidence_root:
            receipt_dict["evidence_root"] = evidence_root

        signed_rcpt = sign_receipt(receipt_dict, priv_key)

        analysis.status = "completed"
        analysis.decision = decision
        analysis.scores = json.dumps(scores_summary)
        analysis.cascade = json.dumps(
            {
                "stage1_model": policy_cfg.stage1_variant,
                "stage1_p_bal": p_bal,
                "stage2_model": policy_cfg.stage2_variant,
                "exited_early": False,
            }
        )
        analysis.receipt_id = signed_rcpt["receipt_id"]
        analysis.completed_at = now
        analysis.review_status = "pending_review" 
        await session.commit()

        await publish_progress(
            analysis_id,
            "finalize",
            100,
            f"Screening complete: score={p_bal:.3f}, band={decision}",
        )

        await _dispatch_completion_webhook(analysis, decision, p_bal, signed_rcpt["receipt_id"], now)

        return {
            "analysis_id": analysis_id,
            "status": "completed",
            "decision": decision,
            "scores": scores_summary,
            "receipt_id": signed_rcpt["receipt_id"],
        }


@celery_app.task(name="sv_workers.tasks.finalize.run_finalize")
def run_finalize(analysis_id: str, inconclusive: bool = False):
    """Task: Calibrate scores, evaluate policy bands, sign receipts, dispatch webhooks."""
    return run_async(_async_finalize(analysis_id, inconclusive))
