"""
Unit and Integration Tests for SENTINEL-V Paper B Evaluation Harness (SPEC §15, Milestone M10).
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Ensure monorepo environment
os.environ.setdefault("SV_DATABASE_URL", "sqlite+aiosqlite:///./test_dev.db")
os.environ.setdefault("SV_TESTING", "1")
os.environ.setdefault("SV_ENGINE_MODE", "mock")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

for pkg in [
    "packages/sv_core/src",
    "packages/sv_engine/src",
    "packages/sv_fusion/src",
    "packages/sv_receipts/src",
    "services/api/src",
    "services/monitor/src",
    "eval/scripts/experiments",
    "eval/figs",
]:
    p_str = str(REPO_ROOT / pkg)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

from base_rate_curves import generate_base_rates_plot
from cascade_pareto import generate_cascade_pareto_plot
from drift_timeline import generate_drift_timeline_plot
from e1_parity import run_e1
from e2_base_rates import run_e2
from e3_cascade import run_e3
from e4_robustness import run_e4
from e5_latency_cost import run_e5
from e6_calibration_transfer import run_e6
from e7_ablations import run_e7
from e8_fusion_generative import run_e8
from e9_faithfulness import run_e9
from e11_drift import run_e11
from e12_receipts import run_e12
from robustness_radar import generate_robustness_radar_plot
from roc import generate_roc_plot


def test_manifests_structure_and_validity():
    """Verify that all standard Paper B evaluation manifests exist and have valid schema."""
    manifest_dir = REPO_ROOT / "eval" / "manifests"
    manifests = ["faceforensics_c23.jsonl", "deepfake_detection.jsonl", "celeb_df_v2.jsonl"]

    for m in manifests:
        mf = manifest_dir / m
        assert mf.exists(), f"Missing evaluation manifest: {mf}"
        assert mf.stat().st_size > 0, f"Manifest {mf} is empty"

        count = 0
        with open(mf, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                assert "video_id" in record
                assert "path" in record
                assert "label" in record
                assert record["label"] in [0, 1]
                assert "dataset" in record
                count += 1
        assert count >= 10, f"Manifest {m} should have at least 10 entries, got {count}"


def test_batch_dump_scores_cli(tmp_path: Path):
    """Verify tools/dump_scores.py batch scoring CLI."""
    manifest_path = REPO_ROOT / "eval" / "manifests" / "faceforensics_c23.jsonl"
    out_csv = tmp_path / "test_scores.csv"

    cmd = [
        sys.executable,
        str(REPO_ROOT / "tools" / "dump_scores.py"),
        "--manifest",
        str(manifest_path),
        "--output",
        str(out_csv),
        "--batch-size",
        "8",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"dump_scores.py failed: {res.stderr}"
    assert out_csv.exists()
    assert out_csv.stat().st_size > 0

    with open(out_csv, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) > 0
        first = rows[0]
        assert "video_id" in first
        assert "u_score" in first
        assert "p_bal" in first
        assert "stage_reached" in first
        assert "runtime_ms" in first


@pytest.mark.parametrize(
    "exp_fn, expected_csv_name",
    [
        (run_e1, "e1_parity.csv"),
        (run_e2, "e2_base_rates.csv"),
        (run_e3, "e3_cascade.csv"),
        (run_e4, "e4_robustness.csv"),
        (run_e5, "e5_latency_cost.csv"),
        (run_e6, "e6_calibration_transfer.csv"),
        (run_e7, "e7_ablations.csv"),
        (run_e8, "e8_fusion.csv"),
        (run_e9, "e9_faithfulness.csv"),
        (run_e11, "e11_drift.csv"),
        (run_e12, "e12_receipts.csv"),
    ],
)
def test_experiment_runners(tmp_path: Path, exp_fn, expected_csv_name: str):
    """Verify each individual experiment module executes cleanly and produces structured CSV."""
    report = exp_fn(output_dir=tmp_path)
    assert isinstance(report, dict)
    csv_file = tmp_path / expected_csv_name
    assert csv_file.exists()
    assert csv_file.stat().st_size > 50

    with open(csv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) >= 3, f"Experiment {expected_csv_name} produced too few rows: {len(rows)}"


def test_run_experiment_cli_e10_deferral():
    """Verify that experiment E10 is cleanly reported as deferred per Blocker B6."""
    cmd = [sys.executable, str(REPO_ROOT / "eval" / "scripts" / "run_experiment.py"), "--id", "e10"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "Blocker B6" in res.stdout


def test_vector_figure_generation(tmp_path: Path):
    """Verify that all publication vector figures (PDF and SVG) render properly from CSV results."""
    # Run prerequisite experiments in tmp_path
    run_e2(output_dir=tmp_path)
    run_e3(output_dir=tmp_path)
    run_e4(output_dir=tmp_path)
    run_e11(output_dir=tmp_path)

    # 1. ROC curves
    pdf_roc, svg_roc = generate_roc_plot(
        csv_path=tmp_path / "e4_robustness.csv", output_dir=tmp_path
    )
    assert pdf_roc.exists() and pdf_roc.stat().st_size > 10000
    assert svg_roc.exists() and svg_roc.stat().st_size > 10000

    # 2. Cascade Pareto
    pdf_casc, svg_casc = generate_cascade_pareto_plot(
        csv_path=tmp_path / "e3_cascade.csv", output_dir=tmp_path
    )
    assert pdf_casc.exists() and pdf_casc.stat().st_size > 10000
    assert svg_casc.exists() and svg_casc.stat().st_size > 10000

    # 3. Drift timeline
    pdf_drift, svg_drift = generate_drift_timeline_plot(
        csv_path=tmp_path / "e11_drift.csv", output_dir=tmp_path
    )
    assert pdf_drift.exists() and pdf_drift.stat().st_size > 10000
    assert svg_drift.exists() and svg_drift.stat().st_size > 10000

    # 4. Base rates
    pdf_rates, svg_rates = generate_base_rates_plot(
        csv_path=tmp_path / "e2_base_rates.csv", output_dir=tmp_path
    )
    assert pdf_rates.exists() and pdf_rates.stat().st_size > 10000
    assert svg_rates.exists() and svg_rates.stat().st_size > 10000

    # 5. Robustness radar
    pdf_radar, svg_radar = generate_robustness_radar_plot(
        csv_path=tmp_path / "e4_robustness.csv", output_dir=tmp_path
    )
    assert pdf_radar.exists() and pdf_radar.stat().st_size > 10000
    assert svg_radar.exists() and svg_radar.stat().st_size > 10000
