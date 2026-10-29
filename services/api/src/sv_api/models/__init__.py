from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sv_api.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), default="submitter", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    key_prefix = Column(String(16), nullable=False)
    hashed_key = Column(String(64), nullable=False, index=True)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="api_keys")


class Media(Base):
    __tablename__ = "media"

    id = Column(String(36), primary_key=True)
    sha256 = Column(String(64), nullable=False, index=True)
    duration_s = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    fps = Column(Float, nullable=True)
    codec = Column(String(32), nullable=True)
    container = Column(String(32), nullable=True)
    s3_key = Column(String(255), nullable=True)
    deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    analyses = relationship("AnalysisModel", back_populates="media")


class PolicyModel(Base):
    __tablename__ = "policies"

    id = Column(String(64), primary_key=True)
    version = Column(Integer, default=1, nullable=False)
    name = Column(String(64), nullable=False)
    config = Column(Text, nullable=False)  # JSON-serialized Policy config
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AnalysisModel(Base):
    __tablename__ = "analyses"

    id = Column(String(36), primary_key=True)
    status = Column(String(32), default="queued", nullable=False, index=True)
    media_id = Column(String(36), ForeignKey("media.id"), nullable=True)
    policy_id = Column(String(64), nullable=False)
    policy_version = Column(Integer, default=1, nullable=False)
    model_bundle_id = Column(String(64), default="default", nullable=False)
    decision = Column(String(32), nullable=True)
    inconclusive_reason = Column(String(32), nullable=True)
    scores = Column(Text, nullable=True)  # JSON-serialized ScoresSummary
    cascade = Column(Text, nullable=True)  # JSON-serialized CascadeInfo
    signals = Column(Text, nullable=True)  # JSON-serialized signals
    labels = Column(Text, nullable=True)  # JSON-serialized labels
    models = Column(Text, nullable=True)  # JSON-serialized model list
    timings_ms = Column(Text, nullable=True)  # JSON-serialized timings
    receipt_id = Column(String(64), nullable=True)
    review_status = Column(String(32), default="not_required", nullable=False)
    cache_hit = Column(Boolean, default=False, nullable=False)
    error_info = Column(Text, nullable=True)  # JSON-serialized error detail
    external_ref = Column(String(128), nullable=True)
    webhook_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    media = relationship("Media", back_populates="analyses")
    tracks = relationship("TrackModel", back_populates="analysis", cascade="all, delete-orphan")
    reviews = relationship("ReviewModel", back_populates="analysis", cascade="all, delete-orphan")


class TrackModel(Base):
    __tablename__ = "tracks"

    id = Column(String(36), primary_key=True)
    analysis_id = Column(String(36), ForeignKey("analyses.id"), nullable=False, index=True)
    track_idx = Column(Integer, nullable=False)
    n_frames = Column(Integer, nullable=False)
    u = Column(Float, nullable=False)
    p_bal = Column(Float, nullable=False)
    decisive = Column(Boolean, default=False, nullable=False)
    clips = Column(Text, nullable=True)  # JSON-serialized clip scores

    analysis = relationship("AnalysisModel", back_populates="tracks")


class ReviewModel(Base):
    __tablename__ = "reviews"

    id = Column(String(36), primary_key=True)
    analysis_id = Column(String(36), ForeignKey("analyses.id"), nullable=False, index=True)
    reviewer_id = Column(String(36), nullable=True)
    source = Column(String(32), default="expert", nullable=False)
    decision = Column(String(32), nullable=False)
    reasons = Column(Text, nullable=False)  # JSON-serialized list
    notes = Column(Text, nullable=True)
    confidence = Column(Integer, default=3, nullable=False)
    telemetry = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    analysis = relationship("AnalysisModel", back_populates="reviews")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=True)
    action = Column(String(64), nullable=False)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(64), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
