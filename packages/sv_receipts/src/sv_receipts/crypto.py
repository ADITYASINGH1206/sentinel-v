import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


def generate_keypair() -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """Generate an Ed25519 private/public keypair."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    return private_key, private_key.public_key()


def sign_bytes(private_key: ed25519.Ed25519PrivateKey, message: bytes) -> str:
    """Sign message bytes using Ed25519 and return base64url string."""
    sig = private_key.sign(message)
    return base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")


def verify_signature(
    public_key: ed25519.Ed25519PublicKey, message: bytes, signature_b64url: str
) -> bool:
    """Verify an Ed25519 signature."""
    rem = len(signature_b64url) % 4
    if rem > 0:
        signature_b64url += "=" * (4 - rem)
    try:
        sig_bytes = base64.urlsafe_b64decode(signature_b64url)
        public_key.verify(sig_bytes, message)
        return True
    except Exception:
        return False


def export_public_key_raw(public_key: ed25519.Ed25519PublicKey) -> bytes:
    """Export 32-byte raw public key."""
    return public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def export_public_key_b64url(public_key: ed25519.Ed25519PublicKey) -> str:
    """Export public key as base64url string without padding."""
    raw = export_public_key_raw(public_key)
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def load_public_key_raw(raw_bytes: bytes) -> ed25519.Ed25519PublicKey:
    """Load Ed25519 public key from 32-byte raw bytes."""
    return ed25519.Ed25519PublicKey.from_public_bytes(raw_bytes)


def load_public_key_b64url(b64url_str: str) -> ed25519.Ed25519PublicKey:
    """Load Ed25519 public key from base64url string."""
    rem = len(b64url_str) % 4
    if rem > 0:
        b64url_str += "=" * (4 - rem)
    raw = base64.urlsafe_b64decode(b64url_str)
    return load_public_key_raw(raw)


def export_private_key_raw(private_key: ed25519.Ed25519PrivateKey) -> bytes:
    """Export 32-byte raw seed of private key."""
    return private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )


def load_private_key_raw(raw_bytes: bytes) -> ed25519.Ed25519PrivateKey:
    """Load Ed25519 private key from 32-byte raw seed."""
    return ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes)
