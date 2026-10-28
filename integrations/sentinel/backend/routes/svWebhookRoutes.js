const express = require('express');
const crypto = require('crypto');
const router = express.Router();

/**
 * Webhook handler to receive asynchronous analysis completions from SENTINEL-V.
 */
router.post('/webhook', express.raw({ type: 'application/json' }), async (req, res) => {
    const signatureHeader = req.headers['x-sv-signature'];
    const webhookSecret = process.env.SENTINEL_V_WEBHOOK_SECRET;

    if (!signatureHeader || !webhookSecret) {
        return res.status(401).json({ error: 'Missing signature or webhook secret' });
    }

    // Parse header: t=<timestamp>,v1=<signature>
    const parts = signatureHeader.split(',').reduce((acc, part) => {
        const [k, v] = part.split('=');
        acc[k] = v;
        return acc;
    }, {});

    const expectedSig = crypto
        .createHmac('sha256', webhookSecret)
        .update(`${parts.t}.${req.body}`)
        .digest('hex');

    if (parts.v1 !== expectedSig) {
        return res.status(403).json({ error: 'Invalid HMAC signature' });
    }

    const payload = JSON.parse(req.body.toString());
    console.log(`[SENTINEL-V Webhook] Received completion for analysis ${payload.analysis_id}`);

    // Update post record in Supabase (additive columns)
    return res.status(200).json({ received: true });
});

module.exports = router;
