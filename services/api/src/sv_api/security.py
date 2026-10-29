import hashlib
import ipaddress
import logging
import os
import socket
import urllib.parse
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Cloud metadata addresses and special targets
CLOUD_METADATA_IPS = {
    ipaddress.ip_address("169.254.169.254"),  # AWS, GCP, Azure, DigitalOcean
    ipaddress.ip_address("100.100.100.200"),  # Alibaba Cloud
}

BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
    "localhost",
}


class SSRFSecurityError(ValueError):
    """Raised when a target URL resolves to a prohibited internal or metadata IP."""

    pass


class SizeLimitExceededError(ValueError):
    """Raised when an incoming stream exceeds the maximum allowed payload size."""

    pass


def is_ip_prohibited(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> tuple[bool, str]:
    """Inspect an IP address and determine if it belongs to private, loopback,

    link-local, cloud-metadata, or reserved ranges.
    """
    # Unpack IPv6-mapped IPv4 addresses (e.g. ::ffff:127.0.0.1 or ::ffff:169.254.169.254)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped

    if ip in CLOUD_METADATA_IPS:
        return True, "Cloud metadata service IP"

    if ip.is_loopback:
        return True, "Loopback range"

    if ip.is_private:
        return True, "Private RFC 1918 / RFC 4193 network"

    if ip.is_link_local:
        return True, "Link-local address"

    if ip.is_multicast:
        return True, "Multicast address"

    if ip.is_reserved:
        return True, "Reserved IP space"

    if ip.is_unspecified:
        return True, "Unspecified address (0.0.0.0 or ::)"

    return False, ""


def validate_url_ssrf(url: str) -> list[str]:
    """Validate a target URL against SSRF vulnerabilities (SPEC §12).

    1. Enforces HTTP/HTTPS scheme.
    2. Blocks known cloud metadata hostnames.
    3. Pre-resolves DNS to identify all IPv4/IPv6 addresses.
    4. Rejects any URL resolving to private, loopback, or metadata addresses.

    Returns the list of resolved public IP addresses.
    """
    if not url:
        raise SSRFSecurityError("Target URL cannot be empty")

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise SSRFSecurityError(
            f"Unsupported scheme '{parsed.scheme}'. Only http and https are allowed."
        )

    hostname = parsed.hostname
    if not hostname:
        raise SSRFSecurityError("URL must contain a valid hostname")

    if hostname.lower() in BLOCKED_HOSTNAMES:
        raise SSRFSecurityError(f"Prohibited metadata hostname: {hostname}")

    # Check if hostname is already an IP literal
    try:
        literal_ip = ipaddress.ip_address(hostname.strip("[]"))
        prohibited, reason = is_ip_prohibited(literal_ip)
        if prohibited:
            raise SSRFSecurityError(f"Prohibited IP address literal '{hostname}': {reason}")
        return [str(literal_ip)]
    except ValueError:
        # Not an IP literal, proceed to DNS resolution
        pass

    try:
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SSRFSecurityError(f"Failed to resolve hostname '{hostname}': {exc}") from exc

    resolved_ips: list[str] = []
    for family, _, _, _, sockaddr in addr_info:
        ip_str = str(sockaddr[0])
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            prohibited, reason = is_ip_prohibited(ip_obj)
            if prohibited:
                raise SSRFSecurityError(
                    f"Hostname '{hostname}' resolves to prohibited IP '{ip_str}': {reason}"
                )
            if ip_str not in resolved_ips:
                resolved_ips.append(ip_str)
        except ValueError as val_err:
            raise SSRFSecurityError(f"Unparseable resolved IP '{ip_str}': {val_err}") from val_err

    if not resolved_ips:
        raise SSRFSecurityError(f"Hostname '{hostname}' resolved to zero IP addresses")

    return resolved_ips


async def safe_download_file(
    url: str,
    dest_path: str,
    max_bytes: int = 500 * 1024 * 1024,
    connect_timeout: float = 10.0,
    total_timeout: float = 120.0,
    max_redirects: int = 3,
) -> dict[str, Any]:
    """Download a file with strict SSRF protection and bounded streaming (SPEC §12).

    - Pre-resolves DNS and validates against private/metadata IPs at every hop.
    - Limits redirects to max_redirects (default 3).
    - Enforces maximum byte limit while streaming.
    - Computes streaming SHA-256.
    """
    current_url = url
    redirect_count = 0

    timeout = httpx.Timeout(total_timeout, connect=connect_timeout)

    for _ in range(max_redirects + 1):
        # Validate current URL against SSRF before connecting
        validate_url_ssrf(current_url)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            try:
                resp = await client.get(
                    current_url, headers={"User-Agent": "SENTINEL-V-Ingest/1.0"}
                )
            except Exception as exc:
                raise SSRFSecurityError(f"Connection failed to '{current_url}': {exc}") from exc

            # Handle redirects manually to re-verify target IP at each hop
            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("Location")
                if not location:
                    raise SSRFSecurityError(f"Redirect {resp.status_code} missing Location header")

                redirect_count += 1
                if redirect_count > max_redirects:
                    raise SSRFSecurityError(f"Exceeded maximum allowed redirects ({max_redirects})")

                # Resolve relative redirects
                current_url = urllib.parse.urljoin(current_url, location)
                continue

            if resp.is_error:
                raise SSRFSecurityError(
                    f"Download failed with HTTP status {resp.status_code}: {resp.text[:200]}"
                )

            # Check Content-Length header if available
            content_length = resp.headers.get("Content-Length")
            if content_length and int(content_length) > max_bytes:
                if os.path.exists(dest_path):
                    try:
                        os.remove(dest_path)
                    except OSError:
                        pass
                raise SizeLimitExceededError(
                    f"Content-Length ({content_length} bytes) exceeds limit ({max_bytes} bytes)"
                )

            # Stream body to destination file with SHA-256 calculation
            hasher = hashlib.sha256()
            total_bytes = 0

            try:
                with open(dest_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        total_bytes += len(chunk)
                        if total_bytes > max_bytes:
                            raise SizeLimitExceededError(
                                f"Streamed payload exceeded maximum limit of {max_bytes} bytes"
                            )
                        hasher.update(chunk)
                        f.write(chunk)
            except Exception:
                if os.path.exists(dest_path):
                    try:
                        os.remove(dest_path)
                    except OSError:
                        pass
                raise

            return {
                "path": dest_path,
                "sha256": hasher.hexdigest(),
                "size_bytes": total_bytes,
                "url": current_url,
            }

    raise SSRFSecurityError(f"Exceeded maximum allowed redirects ({max_redirects})")
