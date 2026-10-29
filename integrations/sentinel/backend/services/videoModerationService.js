const axios = require('axios');

/**
 * Non-blocking, fire-and-forget video moderation client matching SENTINEL style (SPEC §11).
 * Posts video_url and post_id to SENTINEL-V compatibility endpoint.
 */
async function moderateVideo(postId, videoUrl) {
    const sentinelVUrl = process.env.SENTINEL_V_URL || 'http://localhost:8080';
    const internalKey = process.env.SENTINEL_V_INTERNAL_KEY || 'default_key';

    try {
        const response = await axios.post(
            `${sentinelVUrl}/compat/moderate/video`,
            { post_id: postId, video_url: videoUrl },
            {
                headers: {
                    'Content-Type': 'application/json',
                    'X-Internal-Key': internalKey,
                },
                timeout: 50000, // 50s sync timeout conforming to SV_COMPAT_SYNC_TIMEOUT_S
            }
        );
        return response.data;
    } catch (err) {
        // Never throw - log and allow pipeline to proceed asynchronously
        console.warn(`[SENTINEL-V] Video moderation async fallback for post ${postId}:`, err.message);
        return { status: 'pending', post_id: postId };
    }
}

module.exports = { moderateVideo };
