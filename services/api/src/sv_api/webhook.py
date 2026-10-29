import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def sign_webhook_payload(
    payload_bytes: bytes,
    secret: str,
    timestamp: int | None = None,
) -> str:
    """Generate an HMAC-SHA256 signature header for webhook payload.

    Format: X-SV-Signature: t=<timestamp>,v1=<hex_signature>
    Calculation: HMAC-SHA256(secret, f"{timestamp}." + payload_bytes)
    """
    ts = timestamp if timestamp is not None else int(time.time())
    msg = f"{ts}.".encode() + payload_bytes
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def verify_webhook_signature(
    signature_header: str,
    payload_bytes: bytes,
    secret: str,
    tolerance_s: int = 300,
    current_time: int | None = None,
) -> bool:
    """Verify an HMAC-SHA256 webhook signature header with timing-safe comparison

    and timestamp tolerance window.
    """
    if not signature_header or not secret:
        return False

    parts: dict[str, str] = {}
    for item in signature_header.split(","):
        if "=" in item:
            k, v = item.split("=", 1)
            parts[k.strip()] = v.strip()

    if "t" not in parts or "v1" not in parts:
        return False

    try:
        ts = int(parts["t"])
    except ValueError:
        return False

    now = current_time if current_time is not None else int(time.time())
    if abs(now - ts) > tolerance_s:
        return False

    msg = f"{ts}.".encode() + payload_bytes
    expected_sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    return hmac.compare_digest(expected_sig, parts["v1"])


async def dispatch_webhook(
    url: str,
    payload: dict[str, Any],
    secret: str,
    timeout_s: float = 10.0,
) -> bool:
    """Dispatch an asynchronous webhook notification with X-SV-Signature header."""
    if not url:
        return False

    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig_header = sign_webhook_payload(payload_bytes, secret)

    headers = {
        "Content-Type": "application/json",
        "X-SV-Signature": sig_header,
        "User-Agent": "SENTINEL-V-Dispatcher/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(url, content=payload_bytes, headers=headers)
            if resp.is_success:
                logger.info(f"Webhook dispatched successfully to {url} (status {resp.status_code})")
                return True
            logger.warning(
                f"Webhook to {url} returned non-success status {resp.status_code}: {resp.text}"
            )
            return False
    except Exception as exc:
        logger.warning(f"Failed to dispatch webhook to {url}: {exc}")
        return False


def dispatch_webhook_sync(
    url: str,
    payload: dict[str, Any],
    secret: str,
    timeout_s: float = 10.0,
) -> bool:
    """Dispatch a synchronous webhook notification with X-SV-Signature header."""
    if not url:
        return False

    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig_header = sign_webhook_payload(payload_bytes, secret)

    headers = {
        "Content-Type": "application/json",
        "X-SV-Signature": sig_header,
        "User-Agent": "SENTINEL-V-Dispatcher/1.0",
    }

    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(url, content=payload_bytes, headers=headers)
            if resp.is_success:
                logger.info(f"Webhook dispatched successfully to {url} (status {resp.status_code})")
                return True
            logger.warning(
                f"Webhook to {url} returned non-success status {resp.status_code}: {resp.text}"
            )
            return False
    except Exception as exc:
        logger.warning(f"Failed to dispatch webhook to {url}: {exc}")
        return False
