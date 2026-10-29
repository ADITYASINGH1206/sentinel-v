-- Additive Video Moderation Schema for SENTINEL Supabase Database (SPEC §11)
-- Safe migration: purely additive, never alters existing columns or tables destructively.

ALTER TABLE posts 
ADD COLUMN IF NOT EXISTS video_moderation_status TEXT,
ADD COLUMN IF NOT EXISTS video_deepfake_confidence FLOAT,
ADD COLUMN IF NOT EXISTS video_model_version TEXT,
ADD COLUMN IF NOT EXISTS sv_analysis_id TEXT,
ADD COLUMN IF NOT EXISTS sv_receipt_id TEXT,
ADD COLUMN IF NOT EXISTS video_review_required BOOLEAN DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_posts_video_status ON posts(video_moderation_status);
CREATE INDEX IF NOT EXISTS idx_posts_sv_analysis_id ON posts(sv_analysis_id);
