#!/usr/bin/env bash
# ==============================================================================
# SENTINEL-V End-to-End Screening & Verification Demo (SPEC §16, §23)
# ==============================================================================

set -euo pipefail

API_URL="${SV_API_URL:-http://localhost:8080}"
INTERNAL_KEY="${SV_COMPAT_INTERNAL_KEY:-default_key}"

echo "======================================================================"
echo "          SENTINEL-V Video Deepfake Screening Service Demo"
echo "======================================================================"
echo "Target API: ${API_URL}"
echo ""

# 1. Healthcheck
echo "[1/6] Checking service health..."
HEALTH=$(curl -s "${API_URL}/healthz")
echo "  Response: ${HEALTH}"
echo ""

# 2. Submit Video Analysis
echo "[2/6] Submitting video for calibrated screening..."
SUBMIT_RES=$(curl -s -X POST "${API_URL}/v1/analyses" \
  -H "Content-Type: application/json" \
  -d '{"mode":"auto","policy_id":"pol_strict_v3","source_url":"https://example.com/demo.mp4"}')
ANALYSIS_ID=$(echo "${SUBMIT_RES}" | grep -o '"analysis_id":"[^"]*' | cut -d'"' -f4)
echo "  Created Analysis ID: ${ANALYSIS_ID}"
echo ""

# 3. Poll for Completion
echo "[3/6] Polling screening pipeline..."
for i in {1..10}; do
  ANALYSIS_STATUS=$(curl -s "${API_URL}/v1/analyses/${ANALYSIS_ID}")
  STATUS=$(echo "${ANALYSIS_STATUS}" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
  if [ "${STATUS}" = "completed" ] || [ "${STATUS}" = "failed" ]; then
    break
  fi
  sleep 1
done

DECISION=$(echo "${ANALYSIS_STATUS}" | grep -o '"decision":"[^"]*' | cut -d'"' -f4 || echo "unknown")
RECEIPT_ID=$(echo "${ANALYSIS_STATUS}" | grep -o '"receipt_id":"[^"]*' | cut -d'"' -f4 || echo "")
echo "  Status: ${STATUS}"
echo "  Decision Band: ${DECISION}"
echo "  Detection Receipt ID: ${RECEIPT_ID}"
echo ""

# 4. Fetch and Verify Cryptographic Detection Receipt
if [ -n "${RECEIPT_ID}" ] && [ "${RECEIPT_ID}" != "null" ]; then
  echo "[4/6] Inspecting detection receipt..."
  RECEIPT_JSON=$(curl -s "${API_URL}/v1/receipts/${RECEIPT_ID}")
  echo "  Receipt retrieved successfully."
  
  echo "  Verifying receipt on-chain / cryptographic consistency..."
  VERIFY_RES=$(curl -s -X POST "${API_URL}/v1/receipts/verify" \
    -H "Content-Type: application/json" \
    -d "{\"receipt_id\":\"${RECEIPT_ID}\"}")
  echo "  Verification outcome: $(echo "${VERIFY_RES}" | grep -o '"verified":[^,}]*' || echo "${VERIFY_RES}")"
fi
echo ""

# 5. SENTINEL Platform Compatibility Screening
echo "[5/6] Testing SENTINEL Compatibility Adapter (SPEC §11)..."
COMPAT_RES=$(curl -s -X POST "${API_URL}/compat/moderate/video" \
  -H "Content-Type: application/json" \
  -H "X-Internal-Key: ${INTERNAL_KEY}" \
  -d '{"post_id":"demo_post_001","video_url":"https://example.com/demo_compat.mp4"}')
echo "  Compatibility Response: ${COMPAT_RES}"
echo ""

# 6. Download PDF Case Audit Report
echo "[6/6] Generating and downloading PDF Case Report..."
curl -s "${API_URL}/v1/analyses/${ANALYSIS_ID}/report.pdf" -o "/tmp/sentinel_v_report_${ANALYSIS_ID}.pdf" || true
echo "  Report saved to: /tmp/sentinel_v_report_${ANALYSIS_ID}.pdf"
echo ""

echo "======================================================================"
echo "  DEMO COMPLETE: Calibrated, Auditable Video Deepfake Screening"
echo "  Mandatory Notice: Screening aid — not proof."
echo "  Human review required for consequential action."
echo "======================================================================"

