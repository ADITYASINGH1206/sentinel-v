import base64
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


def generate_keypair() -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """Generate an Ed25519 private/public keypair."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    return private_key, private_key.public_key()


def sign_bytes(private_key: ed25519.Ed25519PrivateKey, message: bytes) -> str:
    """Sign message bytes using Ed25519 and return base64url string."""
    sig = private_key.sign(message)
    return base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")


def verify_signature(public_key: ed25519.Ed25519PublicKey, message: bytes, signature_b64url: str) -> bool:
    """Verify an Ed25519 signature."""
    # Restore padding if needed
    rem = len(signature_b64url) % 4
    if rem > 0:
        signature_b64url += "=" * (4 - rem)
    try:
        sig_bytes = base64.urlsafe_b64decode(signature_b64url)
        public_key.verify(sig_bytes, message)
        return True
    except Exception:
        return False
