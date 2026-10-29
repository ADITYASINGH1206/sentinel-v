import json
import secrets
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sv_api.database import async_session_maker
from sv_api.models import AnalysisModel, TrackModel
from sv_api.sse import publish_progress
from sv_core.enums import DecisionBand
from sv_engine.calibration import calibrate_platt
from sv_engine.priors import adjust_for_prior, estimate_ppv
from sv_receipts.crypto import generate_keypair
from sv_receipts.schema import sign_receipt
from sv_workers.celery_app import celery_app
from sv_workers.tasks.utils import run_async

# Known Platt scaling parameters for S-MSDT-ST (SPEC §2.1)
PLATT_A = 0.6470
PLATT_B = -0.5865


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
            return {"analysis_id": analysis_id, "status": "completed", "decision": "inconclusive"}

        # Load tracks
        trk_stmt = select(TrackModel).where(TrackModel.analysis_id == analysis_id)
        trk_res = await session.execute(trk_stmt)
        tracks = trk_res.scalars().all()

        if not tracks:
            u_video = 0.0
            p_bal = 0.5
        else:
            u_video = float(max(t.u for t in tracks))
            p_bal = calibrate_platt(u_video, PLATT_A, PLATT_B)

        prior_prev = 0.01
        p_prior = adjust_for_prior(p_bal, target_prevalence=prior_prev, validation_prevalence=0.50)
        ppv = estimate_ppv(tpr=0.471, fpr=0.01, prevalence=prior_prev)

        # Assign decision band based on calibrated probability
        if p_bal < 0.30:
            decision = DecisionBand.LIKELY_AUTHENTIC.value
        elif p_bal <= 0.751:
            decision = DecisionBand.NEEDS_REVIEW.value
        else:
            decision = DecisionBand.LIKELY_MANIPULATED.value

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
            "model_version": "smsdt-st-b",
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
                "stage1_model": "smsdt-s-a",
                "stage1_p_bal": p_bal,
                "stage2_model": "smsdt-st-b",
                "exited_early": False,
            }
        )
        analysis.receipt_id = signed_rcpt["receipt_id"]
        analysis.completed_at = now
        analysis.review_status = (
            "pending_review" if decision == DecisionBand.NEEDS_REVIEW.value else "not_required"
        )
        await session.commit()

        await publish_progress(
            analysis_id,
            "finalize",
            100,
            f"Screening complete: calibrated score {p_bal:.2f} ({decision})",
        )

        return {
            "analysis_id": analysis_id,
            "status": "completed",
            "decision": decision,
            "p_bal": p_bal,
        }


@celery_app.task(name="sv_workers.tasks.finalize.run_finalize")
def run_finalize(analysis_id: str, inconclusive: bool = False):
    """Task: Calibrate, apply policy band, fuse signals, sign detection receipt."""
    return run_async(_async_finalize(analysis_id, inconclusive))
