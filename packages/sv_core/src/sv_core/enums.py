from enum import Enum


class AnalysisStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DecisionBand(str, Enum):
    LIKELY_AUTHENTIC = "likely_authentic"
    NEEDS_REVIEW = "needs_review"
    LIKELY_MANIPULATED = "likely_manipulated"
    INCONCLUSIVE = "inconclusive"


class InconclusiveReason(str, Enum):
    NO_FACE = "NO_FACE"
    FACE_TOO_SMALL = "FACE_TOO_SMALL"
    TOO_FEW_FRAMES = "TOO_FEW_FRAMES"
    DECODE_FAILURE = "DECODE_FAILURE"


class ReviewDecision(str, Enum):
    AUTHENTIC = "authentic"
    MANIPULATED = "manipulated"
    CANNOT_TELL = "cannot_tell"


class ReviewSource(str, Enum):
    EXPERT = "expert"
    COMMUNITY = "community"
    ADJUDICATION = "adjudication"


class ModelVariant(str, Enum):
    CNN = "cnn"
    S = "s"
    ST = "st"
    FULL = "full"


class UserRole(str, Enum):
    SUBMITTER = "submitter"
    REVIEWER = "reviewer"
    ADMIN = "admin"
    AUDITOR = "auditor"


class EngineMode(str, Enum):
    REAL = "real"
    MOCK = "mock"
