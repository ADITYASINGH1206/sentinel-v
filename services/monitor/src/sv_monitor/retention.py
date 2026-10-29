import os
import shutil
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sv_api.models import AnalysisModel, Media

from sv_monitor.schemas import RetentionPurgeReport

__all__ = ["run_retention_policy"]


async def run_retention_policy(
    session: Any,
    media_storage_dir: str | None = None,
    evidence_storage_dir: str | None = None,
    media_retention_days: int = 30,
    evidence_retention_days: int = 180,
    now: datetime | None = None,
) -> RetentionPurgeReport:
    """Execute automated data retention policy for raw media and evidence artifacts.

    Invariants (SPEC §13):
        - Raw media purged after 30 days (SV_RETENTION_MEDIA_DAYS).
        - Evidence artifacts purged after 180 days (SV_RETENTION_EVIDENCE_DAYS).
        - Detection Receipts are NEVER purged (permanent audit retention).
    """
    if now is None:
        now = datetime.now(UTC).replace(tzinfo=None)

    media_cutoff = now - timedelta(days=media_retention_days)
    evidence_cutoff = now - timedelta(days=evidence_retention_days)

    media_purged_count = 0
    evidence_purged_count = 0
    errors: list[str] = []

    # 1. Scan and purge aged raw media
    media_stmt = select(Media).where((Media.created_at < media_cutoff) & (Media.deleted.is_(False)))
    res = await session.execute(media_stmt)
    aged_media = res.scalars().all()
    media_records_scanned = len(aged_media)

    for m in aged_media:
        try:
            if m.s3_key and media_storage_dir:
                file_path = os.path.join(media_storage_dir, m.s3_key)
                if os.path.exists(file_path):
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)

            m.deleted = True
            m.s3_key = None
            media_purged_count += 1
        except Exception as e:
            errors.append(f"Failed to purge media {m.id}: {e}")

    # 2. Scan and purge aged evidence artifacts
    if evidence_storage_dir and os.path.exists(evidence_storage_dir):
        analysis_stmt = select(AnalysisModel).where(AnalysisModel.created_at < evidence_cutoff)
        a_res = await session.execute(analysis_stmt)
        aged_analyses = a_res.scalars().all()

        for a in aged_analyses:
            ev_dir = os.path.join(evidence_storage_dir, a.id)
            if os.path.exists(ev_dir):
                try:
                    shutil.rmtree(ev_dir)
                    evidence_purged_count += 1
                except Exception as e:
                    errors.append(f"Failed to purge evidence for analysis {a.id}: {e}")

    # 3. Permanent Receipt Preservation Invariant Verification
    rcpt_stmt = select(AnalysisModel).where(AnalysisModel.receipt_id.isnot(None))
    rcpt_res = await session.execute(rcpt_stmt)
    receipts_preserved = len(rcpt_res.scalars().all())

    await session.commit()

    return RetentionPurgeReport(
        executed_at=now.isoformat() + "Z",
        media_older_than_days=media_retention_days,
        evidence_older_than_days=evidence_retention_days,
        media_records_scanned=media_records_scanned,
        media_files_purged=media_purged_count,
        evidence_dirs_purged=evidence_purged_count,
        receipts_preserved=receipts_preserved,
        errors=errors,
    )
