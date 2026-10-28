---
name: sentinel-integration
description: Implements and validates the purely additive integration adapter for the SENTINEL Web3 content-verification platform without touching locked files.
---

# SENTINEL Integration Skill

This skill guides the safe, purely additive integration between SENTINEL-V and the SENTINEL Web3 platform (SPEC §11).

## Strict Lock Preservation Rule (GEMINI.md)
The following areas in the SENTINEL repository are **locked**:
- Smart contracts (`SentinelRegistry.sol`, token contracts).
- Web3 wallet interaction files.
- Video processing files.
- Image deepfake model files (`moderation_service/`).

**SENTINEL integration must be 100% additive.** Never touch existing files automatically.

---

## Additive Artifacts Map

| Target in SENTINEL Repo | Purpose | Implementation File in SENTINEL-V |
|---|---|---|
| `backend/services/videoModerationService.js` | Non-blocking Axios client for `/compat/moderate/video` | `integrations/sentinel/backend/services/videoModerationService.js` |
| `backend/routes/svWebhookRoutes.js` | Webhook endpoint receiving async completions with HMAC validation | `integrations/sentinel/backend/routes/svWebhookRoutes.js` |
| `backend/supabase/schema_update_v6_video.sql` | Additive SQL columns on `posts` table | `integrations/sentinel/backend/supabase/schema_update_v6_video.sql` |
| `frontend/src/components/VideoAuthenticityBadge.jsx` | Tailwind authenticity badge linking to evidence | `integrations/sentinel/frontend/src/components/VideoAuthenticityBadge.jsx` |
| `integrations/sentinel/PATCH_NOTES.md` | Human instructions for one-line wiring in `postController.js` | `integrations/sentinel/PATCH_NOTES.md` |

---

## Verifying Integration

### 1. Webhook Signature Validation
All webhook callbacks from SENTINEL-V send:
```http
X-SV-Signature: t=1730149200,v1=9f83...
```
Verification calculation:
$$\text{Signature} = \text{HMAC-SHA256}(K_{\text{secret}}, t \mathbin{\Vert} "." \mathbin{\Vert} \text{RawBody})$$

### 2. Testing Against Local SENTINEL Checkout
1. Start SENTINEL-V: `make dev`.
2. Start SENTINEL backend with:
   ```bash
   SENTINEL_V_URL=http://localhost:8080
   SENTINEL_V_INTERNAL_KEY=default_key
   ```
3. Submit a test post with a video URL. Verify that `video_moderation_status`, `video_deepfake_confidence`, and `sv_receipt_id` are written to Supabase without errors.
