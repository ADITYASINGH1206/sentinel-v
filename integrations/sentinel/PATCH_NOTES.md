# SENTINEL-V Integration Patch Notes for SENTINEL Repository

This document details the exact, non-invasive one-line integration change needed in the SENTINEL codebase.

> **CRITICAL RULE (GEMINI.md compliance):** 
> All Web3, smart contracts, video processing, and existing image-deepfake files in the SENTINEL repository remain strictly locked. No automated tool modifies them.

---

## 1. Additive Files Delivered

Place the provided files into the SENTINEL repo:
- `backend/services/videoModerationService.js`
- `backend/routes/svWebhookRoutes.js`
- `backend/supabase/schema_update_v6_video.sql`
- `frontend/src/components/VideoAuthenticityBadge.jsx`

---

## 2. One-Line Wiring in `postController.js`

In `backend/controllers/postController.js`, locate media submission:

```javascript
// ADD THIS IMPORT AT TOP:
const { moderateVideo } = require('../services/videoModerationService');

// INSIDE POST CREATION HANDLER:
if (mediaMimeType && mediaMimeType.startsWith('video/')) {
    moderateVideo(post.id, post.media_url); // Fire-and-forget, non-blocking
}
```

---

## 3. Database Migration

Run `backend/supabase/schema_update_v6_video.sql` on the Supabase project to add the additive video moderation columns.

