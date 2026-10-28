from typing import Any, Dict, Optional


class SentinelVError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class MediaLimitExceededError(SentinelVError):
    def __init__(self, message: str = "Media limits exceeded"):
        super().__init__("MEDIA_LIMIT_EXCEEDED", message, 413)


class UnsupportedMediaError(SentinelVError):
    def __init__(self, message: str = "Unsupported media container or codec"):
        super().__init__("UNSUPPORTED_MEDIA", message, 415)


class SourceUnreachableError(SentinelVError):
    def __init__(self, message: str = "Source URL unreachable or failed download"):
        super().__init__("SOURCE_UNREACHABLE", message, 502)


class SSRFSecurityError(SentinelVError):
    def __init__(self, message: str = "Blocked potential SSRF target host"):
        super().__init__("SSRF_VIOLATION", message, 403)


class ModelBundleMissingError(SentinelVError):
    def __init__(self, message: str = "Specified model bundle is missing or corrupt"):
        super().__init__("MODEL_BUNDLE_MISSING", message, 500)


class VerificationFailedError(SentinelVError):
    def __init__(self, message: str = "Receipt cryptographic verification failed"):
        super().__init__("VERIFICATION_FAILED", message, 400)

