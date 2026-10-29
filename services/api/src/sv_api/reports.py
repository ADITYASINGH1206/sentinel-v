import html
import json
from typing import Any

from sv_api.models import AnalysisModel


def generate_case_report_html(analysis: AnalysisModel) -> str:
    """Generate self-contained accessible HTML case screening report (SPEC §14, §16)."""
    scores: dict[str, Any] = {}
    if analysis.scores:
        try:
            scores = json.loads(analysis.scores)
        except (json.JSONDecodeError, TypeError):
            pass

    p_bal = scores.get("p_bal", 0.50)
    p_prior = scores.get("p_prior", 0.01)
    ppv = scores.get("ppv_estimate", 0.32)

    decision_label = (analysis.decision or "INCONCLUSIVE").replace("_", " ").upper()
    badge_color = "#3b82f6"
    if analysis.decision == "likely_authentic":
        badge_color = "#10b981"
    elif analysis.decision == "needs_review":
        badge_color = "#f59e0b"
    elif analysis.decision == "likely_manipulated":
        badge_color = "#ef4444"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>VeriFrame Case Report — {html.escape(analysis.id)}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.5;
      color: #1f2937;
      max-width: 800px;
      margin: 0 auto;
      padding: 32px 24px;
    }}
    .header {{
      border-bottom: 2px solid #e5e7eb;
      padding-bottom: 16px;
      margin-bottom: 24px;
    }}
    .badge {{
      display: inline-block;
      padding: 6px 14px;
      font-weight: 700;
      font-size: 14px;
      text-transform: uppercase;
      border-radius: 9999px;
      color: #ffffff;
      background-color: {badge_color};
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin: 20px 0;
    }}
    .card {{
      background: #f9fafb;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      padding: 16px;
    }}
    .label {{
      font-size: 12px;
      text-transform: uppercase;
      color: #6b7280;
      font-weight: 600;
      margin-bottom: 4px;
    }}
    .val {{
      font-size: 18px;
      font-weight: 600;
      color: #111827;
      font-family: monospace;
    }}
    .disclaimer {{
      background: #fffbeb;
      border-left: 4px solid #f59e0b;
      padding: 12px 16px;
      font-size: 13px;
      color: #92400e;
      margin-top: 28px;
    }}
    .audit-box {{
      font-family: monospace;
      font-size: 12px;
      background: #111827;
      color: #10b981;
      padding: 12px;
      border-radius: 6px;
      word-break: break-all;
      margin-top: 8px;
    }}
  </style>
</head>
<body>
  <div class="header">
    <h1>VeriFrame Screening & Audit Report</h1>
    <p>Calibrated Deepfake Screening for Human Reviewers (SPEC §14, §16)</p>
  </div>

  <div>
    <span class="badge">{decision_label}</span>
    <span style="margin-left: 12px; font-weight: 500;">Analysis ID: <code>{html.escape(analysis.id)}</code></span>
  </div>

  <div class="grid">
    <div class="card">
      <div class="label">Calibrated Score (p_bal)</div>
      <div class="val">{p_bal:.4f}</div>
    </div>
    <div class="card">
      <div class="label">Adjusted Prior (p_prior)</div>
      <div class="val">{p_prior:.4f}</div>
    </div>
    <div class="card">
      <div class="label">Estimated PPV</div>
      <div class="val">{ppv:.4f}</div>
    </div>
    <div class="card">
      <div class="label">Review Status</div>
      <div class="val">{html.escape(analysis.review_status)}</div>
    </div>
  </div>

  <div class="card">
    <div class="label">Detection Receipt & Cryptographic Anchor</div>
    <p style="font-size: 13px; margin: 4px 0;">Signed by server key using Ed25519 over RFC 8785 Canonical JSON.</p>
    <div class="audit-box">
      RECEIPT_ID : {html.escape(analysis.receipt_id or "PENDING")}<br>
      POLICY_VER : {analysis.policy_id} (v{analysis.policy_version})<br>
      BUNDLE_ID  : {html.escape(analysis.model_bundle_id)}
    </div>
  </div>

  <div class="disclaimer">
    <strong>Mandatory Notice:</strong> Screening aid — not proof. Human review required for consequential action.
  </div>
</body>
</html>
"""


def generate_case_report_pdf(analysis: AnalysisModel) -> bytes:
    """Generate a clean, valid PDF binary document representing the case audit report."""
    scores: dict[str, Any] = {}
    if analysis.scores:
        try:
            scores = json.loads(analysis.scores)
        except (json.JSONDecodeError, TypeError):
            pass

    p_bal = scores.get("p_bal", 0.50)
    decision = (analysis.decision or "inconclusive").replace("_", " ").upper()
    receipt_id = analysis.receipt_id or "NONE"

    # Lines to render
    text_lines = [
        ("F1", 16, 50, 740, "VeriFrame Case Screening Report"),
        ("F2", 10, 50, 715, f"Analysis ID: {analysis.id}"),
        ("F1", 12, 50, 680, f"VERDICT: {decision} (Calibrated Score p_bal: {p_bal:.4f})"),
        ("F2", 10, 50, 650, f"Policy: {analysis.policy_id} v{analysis.policy_version}"),
        ("F2", 10, 50, 630, f"Model Bundle: {analysis.model_bundle_id}"),
        ("F2", 10, 50, 610, f"Review Status: {analysis.review_status}"),
        ("F1", 11, 50, 570, "Cryptographic Detection Receipt:"),
        ("F2", 9, 50, 550, f"Receipt ID: {receipt_id}"),
        ("F2", 9, 50, 530, f"Created: {analysis.created_at.isoformat()}Z"),
        (
            "F2",
            9,
            50,
            510,
            f"Completed: {analysis.completed_at.isoformat() if analysis.completed_at else 'In Progress'}",
        ),
        ("F1", 9, 50, 460, "Mandatory Notice:"),
        (
            "F2",
            9,
            50,
            445,
            "Screening aid - not proof. Human review required for consequential action.",
        ),
    ]

    stream_ops = []
    for font, size, x, y, val in text_lines:
        clean_val = str(val).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_ops.append(f"BT /{font} {size} Tf {x} {y} Td ({clean_val}) Tj ET")

    stream_content = "\n".join(stream_ops).encode("latin-1", errors="replace")

    # Construct compliant PDF-1.4 file with objects and xref
    parts = []
    parts.append(b"%PDF-1.4\n")

    offsets = {}

    def add_obj(num: int, content: bytes) -> None:
        offsets[num] = sum(len(p) for p in parts)
        parts.append(f"{num} 0 obj\n".encode() + content + b"\nendobj\n")

    add_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
    add_obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    add_obj(
        3,
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>",
    )
    add_obj(
        4,
        b"<< /Length "
        + str(len(stream_content)).encode()
        + b" >>\nstream\n"
        + stream_content
        + b"\nendstream",
    )
    add_obj(5, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    add_obj(6, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    xref_offset = sum(len(p) for p in parts)
    parts.append(b"xref\n0 7\n0000000000 65535 f \n")
    for i in range(1, 7):
        parts.append(f"{offsets[i]:010d} 00000 n \n".encode())

    parts.append(f"trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode())

    return b"".join(parts)
