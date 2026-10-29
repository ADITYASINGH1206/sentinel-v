import os

os.environ["SV_TESTING"] = "1"
os.environ["SV_ENGINE_MODE"] = "mock"
os.environ["SV_DATABASE_URL"] = "sqlite+aiosqlite:///./test_fuzz.db"

import asyncio
import tempfile
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sv_api.database import Base, async_session_maker, engine
from sv_api.main import app
from sv_api.models import AnalysisModel
from sv_engine.preprocess.decode import DecodeError, decode_video
from sv_workers.tasks.preprocess import _async_preprocess


@pytest.fixture(autouse=True)
def setup_test_db():
    async def _reset():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_reset())
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_fuzz_truncated_moov_atom():
    """Malformed MP4 with truncated moov atom must reject cleanly with DecodeError."""
    # Construct minimal MP4 header with incomplete moov atom
    data = (
        b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42"
        b"\x00\x00\x00\x08free"
        b"\x00\x00\x01\x00moov"  # declares 256 bytes but terminates immediately
        b"\x00\x00\x00\x6c\x6d\x76\x68\x64"
    )
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(data)
        path = f.name

    try:
        with pytest.raises(DecodeError):
            decode_video(path)
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_fuzz_random_noise_stream():
    """Random noise payloads with .mp4, .mov, and .mkv extensions must fail safely."""
    for ext in (".mp4", ".mov", ".mkv"):
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(os.urandom(2048))
            path = f.name

        try:
            with pytest.raises(DecodeError):
                decode_video(path)
        finally:
            if os.path.exists(path):
                os.remove(path)


def test_fuzz_zero_byte_file():
    """Zero-byte media files must reject cleanly without infinite loop or hang."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        path = f.name

    try:
        with pytest.raises(DecodeError):
            decode_video(path)
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_fuzz_pipeline_fault_tolerance():
    """When a corrupt/fuzzed video reaches worker preprocess, it must classify safely

    as inconclusive (DECODE_FAILURE) without crashing worker task.
    """
    analysis_id = f"an_fuzz_{uuid.uuid4().hex[:12]}"
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(b"CORRUPT_NOT_A_VIDEO_PAYLOAD_AT_ALL")
        corrupt_path = f.name

    async def _test():
        async with async_session_maker() as session:
            model = AnalysisModel(
                id=analysis_id,
                status="processing",
                policy_id="pol_strict_v3",
                policy_version=3,
                model_bundle_id="default",
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
            session.add(model)
            await session.commit()

        # Run preprocessing
        await _async_preprocess(analysis_id, corrupt_path)

        # Inspect database record
        async with async_session_maker() as session:
            stmt = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
            res = await session.execute(stmt)
            curr = res.scalars().first()
            assert curr is not None
            assert curr.decision == "inconclusive"
            assert curr.inconclusive_reason == "DECODE_FAILURE"

    try:
        asyncio.run(_test())
    finally:
        if os.path.exists(corrupt_path):
            os.remove(corrupt_path)


def test_pdf_and_html_case_report_endpoints(client):
    """Verify GET /v1/analyses/{id}/report.pdf returns valid PDF-1.4 binary and report.html returns accessible HTML."""
    analysis_id = f"an_rep_{uuid.uuid4().hex[:12]}"

    async def _seed():
        async with async_session_maker() as session:
            model = AnalysisModel(
                id=analysis_id,
                status="completed",
                decision="needs_review",
                scores='{"p_bal": 0.6543, "p_prior": 0.0123, "ppv_estimate": 0.35}',
                receipt_id=f"rcpt_{uuid.uuid4().hex[:16]}",
                review_status="pending_review",
                policy_id="pol_strict_v3",
                policy_version=3,
                model_bundle_id="smsdt-st-b",
                created_at=datetime.now(UTC).replace(tzinfo=None),
                completed_at=datetime.now(UTC).replace(tzinfo=None),
            )
            session.add(model)
            await session.commit()

    asyncio.run(_seed())

    # 1. Test PDF report
    pdf_res = client.get(f"/v1/analyses/{analysis_id}/report.pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf_res.content

    # 2. Test HTML report
    html_res = client.get(f"/v1/analyses/{analysis_id}/report.html")
    assert html_res.status_code == 200
    assert "text/html" in html_res.headers["content-type"]
    assert "Screening aid" in html_res.text
    assert "0.6543" in html_res.text
    assert analysis_id in html_res.text
