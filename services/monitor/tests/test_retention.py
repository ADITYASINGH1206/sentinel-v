import asyncio
import os
import tempfile
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sv_api.database import Base
from sv_api.models import AnalysisModel, Media
from sv_monitor.retention import run_retention_policy


def test_retention_purges_aged_artifacts_and_preserves_receipts():
    """Verify retention policy purges media >30d, evidence >180d, and preserves receipts permanently."""

    async def _run():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        now = datetime(2026, 10, 29, 12, 0, 0)

        with tempfile.TemporaryDirectory() as media_tmp, tempfile.TemporaryDirectory() as ev_tmp:
            # Create media files on disk
            fresh_media_file = os.path.join(media_tmp, "fresh.mp4")
            aged_media_file = os.path.join(media_tmp, "aged.mp4")
            with open(fresh_media_file, "wb") as f:
                f.write(b"FRESH_VIDEO_CONTENT")
            with open(aged_media_file, "wb") as f:
                f.write(b"AGED_VIDEO_CONTENT")

            # Create evidence directories on disk
            fresh_ev_dir = os.path.join(ev_tmp, "analysis_fresh")
            aged_ev_dir = os.path.join(ev_tmp, "analysis_aged_ev")
            os.makedirs(fresh_ev_dir, exist_ok=True)
            os.makedirs(aged_ev_dir, exist_ok=True)
            with open(os.path.join(fresh_ev_dir, "manifest.json"), "w") as f:
                f.write("{}")
            with open(os.path.join(aged_ev_dir, "manifest.json"), "w") as f:
                f.write("{}")

            async with session_maker() as session:
                # Media 1: Fresh (10 days old)
                m_fresh = Media(
                    id="med_fresh",
                    sha256="sha_fresh",
                    s3_key="fresh.mp4",
                    deleted=False,
                    created_at=now - timedelta(days=10),
                )

                # Media 2: Aged (45 days old > 30 days)
                m_aged = Media(
                    id="med_aged",
                    sha256="sha_aged",
                    s3_key="aged.mp4",
                    deleted=False,
                    created_at=now - timedelta(days=45),
                )

                # Analysis 1: Fresh with receipt
                a_fresh = AnalysisModel(
                    id="analysis_fresh",
                    policy_id="strict-low-fpr",
                    policy_version=1,
                    receipt_id="rcpt_fresh_12345",
                    created_at=now - timedelta(days=10),
                )

                # Analysis 2: Aged 200 days old with permanent receipt
                a_aged = AnalysisModel(
                    id="analysis_aged_ev",
                    policy_id="strict-low-fpr",
                    policy_version=1,
                    receipt_id="rcpt_permanent_67890",
                    created_at=now - timedelta(days=200),
                )

                session.add_all([m_fresh, m_aged, a_fresh, a_aged])
                await session.commit()

            # Run retention policy
            async with session_maker() as session:
                report = await run_retention_policy(
                    session=session,
                    media_storage_dir=media_tmp,
                    evidence_storage_dir=ev_tmp,
                    media_retention_days=30,
                    evidence_retention_days=180,
                    now=now,
                )

            assert report.media_records_scanned == 1
            assert report.media_files_purged == 1
            assert report.evidence_dirs_purged == 1
            assert report.receipts_preserved == 2
            assert len(report.errors) == 0

            # Physical file checks:
            # Fresh media still exists
            assert os.path.exists(fresh_media_file)
            # Aged media was purged
            assert not os.path.exists(aged_media_file)

            # Fresh evidence dir still exists
            assert os.path.exists(fresh_ev_dir)
            # Aged evidence dir was purged
            assert not os.path.exists(aged_ev_dir)

            # Database state checks:
            async with session_maker() as session:
                m1 = await session.get(Media, "med_fresh")
                assert m1 is not None and m1.deleted is False and m1.s3_key == "fresh.mp4"

                m2 = await session.get(Media, "med_aged")
                assert m2 is not None and m2.deleted is True and m2.s3_key is None

                # CRITICAL INVARIANT: Detection Receipts remain intact
                a1 = await session.get(AnalysisModel, "analysis_fresh")
                assert a1 is not None and a1.receipt_id == "rcpt_fresh_12345"

                a2 = await session.get(AnalysisModel, "analysis_aged_ev")
                assert a2 is not None and a2.receipt_id == "rcpt_permanent_67890"

            await engine.dispose()

    asyncio.run(_run())
