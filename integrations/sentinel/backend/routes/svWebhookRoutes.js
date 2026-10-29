const express = require('express');
const crypto = require('crypto');
const router = express.Router();

/**
 * Webhook handler to receive asynchronous analysis completions from SENTINEL-V (SPEC §11).
 * Validates HMAC-SHA256 signature in X-SV-Signature header: t=<timestamp>,v1=<signature>
 * and updates additive video moderation fields in the Supabase posts table.
 */
router.post('/webhook', express.raw({ type: 'application/json' }), async (req, res) => {
    const signatureHeader = req.headers['x-sv-signature'];
    const webhookSecret = process.env.SENTINEL_V_WEBHOOK_SECRET;

    if (!signatureHeader || !webhookSecret) {
        return res.status(401).json({ error: 'Missing X-SV-Signature header or SENTINEL_V_WEBHOOK_SECRET' });
    }

    // Parse header: t=<timestamp>,v1=<signature>
    const parts = signatureHeader.split(',').reduce((acc, part) => {
        const [k, v] = part.split('=');
        if (k && v) acc[k.trim()] = v.trim();
        return acc;
    }, {});

    if (!parts.t || !parts.v1) {
        return res.status(400).json({ error: 'Malformed X-SV-Signature header format' });
    }

    // Timestamp freshness validation (tolerance: 300 seconds)
    const timestamp = parseInt(parts.t, 10);
    const now = Math.floor(Date.now() / 1000);
    if (isNaN(timestamp) || Math.abs(now - timestamp) > 300) {
        return res.status(403).json({ error: 'Webhook signature expired or timestamp invalid' });
    }

    // Compute expected HMAC-SHA256
    const rawBody = Buffer.isBuffer(req.body) ? req.body : Buffer.from(req.body || '');
    const hmac = crypto.createHmac('sha256', webhookSecret);
    hmac.update(`${parts.t}.`);
    hmac.update(rawBody);
    const expectedSig = hmac.digest('hex');

    const expectedBuffer = Buffer.from(expectedSig, 'utf8');
    const receivedBuffer = Buffer.from(parts.v1, 'utf8');

    if (expectedBuffer.length !== receivedBuffer.length || !crypto.timingSafeEqual(expectedBuffer, receivedBuffer)) {
        return res.status(403).json({ error: 'Invalid HMAC signature' });
    }

    let payload;
    try {
        payload = JSON.parse(rawBody.toString('utf8'));
    } catch (parseErr) {
        return res.status(400).json({ error: 'Invalid JSON payload' });
    }

    console.log(`[SENTINEL-V Webhook] Received completion for analysis ${payload.analysis_id}`);

    // Update additive columns in Supabase posts table if client is attached
    try {
        const supabase = (req.app && req.app.get('supabase')) || global.supabase;
        if (supabase && payload.post_id) {
            const updateData = {
                video_moderation_status: payload.status,
                video_deepfake_confidence: payload.deepfake_confidence,
                video_model_version: payload.deepfake_model_version || 'smsdt-st-b',
                sv_analysis_id: payload.analysis_id,
                sv_receipt_id: payload.receipt_id,
                video_review_required: Boolean(payload.review_required),
            };

            const { error: dbError } = await supabase
                .from('posts')
                .update(updateData)
                .eq('id', payload.post_id);

            if (dbError) {
                console.warn(`[SENTINEL-V Webhook] Supabase update returned error:`, dbError.message);
            }
        }
    } catch (dbErr) {
        console.warn(`[SENTINEL-V Webhook] Supabase update skipped:`, dbErr.message);
    }

    return res.status(200).json({ received: true, analysis_id: payload.analysis_id });
});

module.exports = router;
